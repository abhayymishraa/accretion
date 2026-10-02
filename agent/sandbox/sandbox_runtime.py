"""Durable ownership of disposable E2B runtimes. Callers serialize each project.

Saved source remains authoritative. No operation here replays an AI request.
"""
from typing import Any
from typing import cast
from sqlalchemy.engine import CursorResult
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import uuid

from e2b import (AsyncSandbox, AuthenticationException, InvalidArgumentException,
                 NotFoundException, SandboxQuery, SandboxState)
from e2b.exceptions import RateLimitException, ServiceBusyException
from sqlalchemy import delete, or_, select, update

from db.base import AsyncSessionLocal, ReadSessionLocal
from db.models import Chat, SandboxRuntime
from ..storage.storage import StorageError
from ..budget.sandbox_budget import reserve_runtime, confirm_runtime, settle_runtime
from ..budget.budget import BudgetLimitError
from .config import sandbox_settings

logger = logging.getLogger('webbuilder.runs')
# Bounds one running stretch, not the project's life: the provider parks it at timeout.
RUNTIME_TIMEOUT = 1800
API_TIMEOUT = 10


class SandboxRuntimes:
    def __init__(self):
        self.handles = {}

    async def get(self, chat_id):
        async with AsyncSessionLocal() as db:
            return await db.get(SandboxRuntime, chat_id)

    async def running_for(self, user_id, except_chat):
        """The user's running sandboxes other than except_chat: what one-active-per-user pauses."""
        async with ReadSessionLocal() as db:
            return list((await db.scalars(select(SandboxRuntime)
                .join(Chat, Chat.id == SandboxRuntime.chat_id)
                .where(Chat.user_id == user_id, SandboxRuntime.chat_id != except_chat,
                       SandboxRuntime.state == 'running'))).all())

    async def reserved(self):
        async with AsyncSessionLocal() as db:
            return set((await db.scalars(select(SandboxRuntime.chat_id)
                .where(SandboxRuntime.state != 'paused'))).all())

    async def change(self, row, **values):
        async with AsyncSessionLocal.begin() as db:
            result = await db.execute(update(SandboxRuntime).where(
                SandboxRuntime.chat_id == row.chat_id,
                SandboxRuntime.operation_id == row.operation_id).values(**values))
            if cast(CursorResult[Any], result).rowcount != 1:
                raise StorageError('Preview ownership changed; reopen the project')
        for key, value in values.items():
            setattr(row, key, value)

    def forget_handle(self, chat_id):
        self.handles.pop(chat_id, None)

    async def remove(self, row, *, rejected=False):
        # Only callers with confirmed absence/termination remove runtime ownership.
        await settle_runtime(row.spend_id, rejected=rejected)
        async with AsyncSessionLocal.begin() as db:
            await db.execute(delete(SandboxRuntime).where(
                SandboxRuntime.chat_id == row.chat_id,
                SandboxRuntime.operation_id == row.operation_id))
        self.forget_handle(row.chat_id)

    async def retire(self, chat_id):
        row = await self.get(chat_id)
        handle = self.handles.get(chat_id)
        if row:
            await self.change(row, state='retiring', reusable=False)
        try:
            ids = {row.sandbox_id} if row and row.sandbox_id else set()
            if handle:
                ids.add(handle.sandbox_id)
            if row and not ids:
                # The create response may have been lost. Never provision a replacement
                # merely because a list response is empty or temporarily unavailable.
                async with asyncio.timeout(API_TIMEOUT):
                    pages = AsyncSandbox.list(query=SandboxQuery(
                        metadata={'webbuilder_operation': row.operation_id},
                        state=[SandboxState.RUNNING, SandboxState.PAUSED]), request_timeout=API_TIMEOUT)
                    while pages.has_next:
                        ids.update(info.sandbox_id for info in await pages.next_items())
                if not ids:
                    return False
            for sandbox_id in ids:
                async with asyncio.timeout(API_TIMEOUT):
                    # False means confirmed absent; both outcomes complete cleanup.
                    await AsyncSandbox.kill(sandbox_id, request_timeout=API_TIMEOUT)
        except Exception as exc:
            logger.warning('Sandbox cleanup deferred chat_id=%s error_type=%s', chat_id, type(exc).__name__)
            return False
        if row:
            await self.remove(row)
        else:
            self.forget_handle(chat_id)
        return True

    async def state(self, row, info=None):
        """Control-plane state query. A paused runtime is not a dead health probe."""
        if not row.sandbox_id:
            return 'unknown'
        try:
            info = info or await AsyncSandbox.get_info(row.sandbox_id, request_timeout=API_TIMEOUT)
        except NotFoundException:
            await self.remove(row)
            return 'missing'
        state = info.state.value
        if state in ('running', 'paused'):
            await self.change(row, state=state)
            if state == 'paused':
                await settle_runtime(row.spend_id)
                await self.change(row, spend_id=None)
                self.forget_handle(row.chat_id)
        return state

    async def renew(self, chat_id):
        """Extend a running sandbox's provider timer, metered like connect: reserve the next lease
        first, then extend, then confirm against the provider's reported size. Runs have no clock,
        so a long one renews instead of being parked at RUNTIME_TIMEOUT mid-work."""
        row, handle = await self.get(chat_id), self.handles.get(chat_id)
        if not row or not handle or row.state != 'running':
            return
        info = await AsyncSandbox.get_info(handle.sandbox_id, request_timeout=API_TIMEOUT)
        spend = await reserve_runtime(chat_id, RUNTIME_TIMEOUT, row.spend_id, info)
        await self.change(row, spend_id=spend.id, last_used_at=datetime.now(timezone.utc))
        await handle.set_timeout(RUNTIME_TIMEOUT, request_timeout=API_TIMEOUT)
        await confirm_runtime(spend.id, await AsyncSandbox.get_info(handle.sandbox_id, request_timeout=API_TIMEOUT))

    async def acquire(self, chat_id, revision, template):
        """Return (handle, needs_source_restore); caller already reserved admission and chose the template."""
        revision_id = revision.id if revision else None
        generation = sandbox_settings.E2B_RUNTIME_GENERATION
        row = await self.get(chat_id)
        if row:
            compatible = (row.reusable and row.sandbox_id and row.revision_id == revision_id
                and row.template_id == template and row.generation == generation
                and row.state in ('running', 'paused'))
            if compatible:
                try:
                    info = await AsyncSandbox.get_info(row.sandbox_id, request_timeout=API_TIMEOUT)
                except NotFoundException:
                    await self.remove(row)
                    row = None
                if row and await self.state(row, info) not in ('running', 'paused'):
                    raise StorageError('Preview state is unknown; retry after cleanup')
            if row and compatible:
                spend = await reserve_runtime(chat_id, RUNTIME_TIMEOUT, row.spend_id, info)
                # Reserve durably before connect: connect can wake a paused sandbox.
                await self.change(row, state='running', spend_id=spend.id,
                                  last_used_at=datetime.now(timezone.utc))
                try:
                    async with asyncio.timeout(30):
                        handle = await AsyncSandbox.connect(row.sandbox_id,
                            timeout=RUNTIME_TIMEOUT, request_timeout=API_TIMEOUT)
                    self.handles[chat_id] = handle
                    await confirm_runtime(spend.id, await AsyncSandbox.get_info(
                        handle.sandbox_id, request_timeout=API_TIMEOUT))
                    return handle, False
                except NotFoundException:
                    # Confirm termination below before making a replacement.
                    pass
                except BudgetLimitError:
                    raise
                except Exception:
                    raise StorageError('Preview resume could not be confirmed; retry after cleanup') from None
            if row and not await self.retire(chat_id):
                raise StorageError('Previous preview cleanup is pending; no replacement was started')

        spend = await reserve_runtime(chat_id, RUNTIME_TIMEOUT)
        row = SandboxRuntime(chat_id=chat_id, operation_id=str(uuid.uuid4()), spend_id=spend.id,
            template_id=template, generation=generation, revision_id=None,
            reusable=False, state='creating', last_used_at=datetime.now(timezone.utc))
        async with AsyncSessionLocal.begin() as db:
            if not await db.get(Chat, chat_id):
                raise StorageError('Project no longer exists')
            db.add(row)
        # Ownership intent is committed before the provider request.
        try:
            async with asyncio.timeout(40):
                handle = await AsyncSandbox.create(template=template, timeout=RUNTIME_TIMEOUT,
                    # No auto_resume: a paused sandbox wakes only through acquire, which reserves its
                    # lease. The builder opens a sleeping preview itself (usePreviewLifecycle), and a
                    # stale tab must not wake, unmetered, a sandbox the user switched away from.
                    lifecycle={'on_timeout': 'pause', 'auto_resume': False},
                    metadata={'webbuilder_operation': row.operation_id}, request_timeout=30)
        except (AuthenticationException, InvalidArgumentException, NotFoundException,
                RateLimitException, ServiceBusyException):
            # Explicit request rejection is different from a lost creation response.
            await self.remove(row, rejected=True)
            raise
        self.handles[chat_id] = handle
        await self.change(row, sandbox_id=handle.sandbox_id, state='running')
        await confirm_runtime(spend.id, await AsyncSandbox.get_info(
            handle.sandbox_id, request_timeout=API_TIMEOUT))
        return handle, True

    async def invalidate(self, chat_id):
        row = await self.get(chat_id)
        if not row:
            raise StorageError('Preview ownership is missing')
        await self.change(row, reusable=False)

    async def mark_reusable(self, db, chat_id, revision_id):
        # Caller commits this with successful run completion / preview publication.
        handle = self.handles.get(chat_id)
        if not handle or not revision_id:
            raise StorageError('Saved preview ownership is missing')
        result = await db.execute(update(SandboxRuntime).where(
            SandboxRuntime.chat_id == chat_id, SandboxRuntime.sandbox_id == handle.sandbox_id,
            SandboxRuntime.state == 'running').values(reusable=True, revision_id=revision_id,
                last_used_at=datetime.now(timezone.utc)))
        if result.rowcount != 1:
            raise StorageError('Saved preview ownership changed')

    async def pause(self, row):
        if not row.reusable:
            return await self.retire(row.chat_id)
        try:
            async with asyncio.timeout(30):
                # Explicit since e2b 2.51 stopped presetting it: without memory a
                # resume cold-boots and the preview server is gone.
                await AsyncSandbox.pause(row.sandbox_id, keep_memory=True, request_timeout=30)
            await self.change(row, state='paused')
            await settle_runtime(row.spend_id)
            await self.change(row, spend_id=None)
            self.forget_handle(row.chat_id)
            return True
        except NotFoundException:
            await self.remove(row)
            return True
        except Exception as exc:
            # A refused or timed-out pause may still be running. Keep its reservation.
            logger.warning('Sandbox pause deferred chat_id=%s error_type=%s', row.chat_id, type(exc).__name__)
            return False

    async def maintain(self, busy, shutdown=False):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=sandbox_settings.PAUSED_SANDBOX_RETENTION_DAYS)
        async with AsyncSessionLocal() as db:
            # Healthy paused projects need no provider polling or periodic DB writes.
            rows = (await db.execute(select(SandboxRuntime, Chat).outerjoin(Chat,
                Chat.id == SandboxRuntime.chat_id).where(or_(SandboxRuntime.state != 'paused',
                SandboxRuntime.last_used_at < cutoff, SandboxRuntime.reusable.is_(False),
                Chat.id.is_(None), SandboxRuntime.revision_id != Chat.latest_saved_revision_id,
                SandboxRuntime.generation != sandbox_settings.E2B_RUNTIME_GENERATION)))).all()
        for row, chat in rows:
            if row.chat_id in busy:
                continue
            try:
                if (not chat or not row.reusable or row.state in ('creating', 'retiring')
                        or row.revision_id != chat.latest_saved_revision_id
                        or row.generation != sandbox_settings.E2B_RUNTIME_GENERATION
                        or row.last_used_at < cutoff):
                    await self.retire(row.chat_id)
                    continue
                if row.state == 'paused':
                    continue
                # Reconcile every cycle: the provider pauses on its own timeout, and
                # only this settles that spend and frees the live slot.
                state = await self.state(row)
                if shutdown and state == 'running':
                    await self.pause(row)
            except Exception as exc:
                logger.warning('Sandbox reconciliation deferred chat_id=%s error_type=%s', row.chat_id, type(exc).__name__)
