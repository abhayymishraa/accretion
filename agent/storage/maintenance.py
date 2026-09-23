"""Bounded in-process housekeeping; failures leave database references intact for retry."""
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import shutil
import uuid

from sqlalchemy import delete, select, func, or_

from db.base import AsyncSessionLocal
from db.models import Chat, ProjectRevision, Run, RunEvent, StorageUsage, StorageDeletion
from ..events import archive_run
from .persistence import PROJECTS, archive_slots, promote, revision_bytes, wait_for_uploads
from .storage import storage_call, StorageError

logger = logging.getLogger('webbuilder.runs')
CLEANUP_TIMEOUT = 10


async def attempt_cleanup(action):
    """Bound the request wait; durable storage/runtime records survive failures."""
    try:
        async with asyncio.timeout(CLEANUP_TIMEOUT):
            return await action
    except Exception as exc:
        logger.warning('Project cleanup deferred error_type=%s', type(exc).__name__)
        return False


async def cleanup_project_storage(keys):
    completed = True
    for key in keys:
        try:
            if key.startswith('legacy/'):
                folder = PROJECTS / str(uuid.UUID(key.removeprefix('legacy/')))
                if folder.exists():
                    await asyncio.to_thread(shutil.rmtree, folder)
            else:
                await wait_for_uploads(key)
                await storage_call('delete', key)
        except (StorageError, OSError, ValueError) as exc:
            logger.warning('Project storage cleanup deferred error_type=%s', type(exc).__name__)
            completed = False
            continue  # Retain the durable intent; one failure must not block other keys.
        async with AsyncSessionLocal.begin() as db:
            await db.execute(delete(StorageDeletion).where(StorageDeletion.object_key == key))
    return completed


async def maintain(service):
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        deletions = list((await db.scalars(select(StorageDeletion.object_key)
            .order_by(StorageDeletion.created_at, StorageDeletion.object_key).limit(100))).all())
    for key in deletions:
        await attempt_cleanup(cleanup_project_storage([key]))
    busy = {r.chat_id for r in service.active.values()} | service.opening
    async with AsyncSessionLocal() as db:
        pending = list((await db.scalars(select(ProjectRevision).where(ProjectRevision.status == 'pending')
            .order_by(ProjectRevision.created_at).limit(100))).all())
    for revision in pending:
        if revision.chat_id in busy:
            continue
        try:
            async with archive_slots:
                await revision_bytes(revision)
            await promote(revision.id, recovery=True)
        except StorageError:
            # Never race an in-flight SDK upload; canceled SDK calls may finish in their thread.
            if revision.created_at < now - timedelta(days=1):
                async with AsyncSessionLocal.begin() as db:
                    row = await db.get(ProjectRevision, revision.id, with_for_update=True)
                    if row and row.status == 'pending':
                        row.status = 'failed'

    async with AsyncSessionLocal() as db:
        run_ids = list((await db.scalars(select(Run.id).where(Run.status.not_in(('running', 'awaiting_input')), Run.log_sha256.is_(None),
            Run.id.in_(select(RunEvent.run_id)))
            .order_by(Run.finished_at).limit(20))).all())
    for run_id in run_ids:
        try:
            await archive_run(run_id)
        except StorageError:
            logger.warning('Run log archive deferred run_id=%s', run_id)

    async with AsyncSessionLocal() as db:
        chat_ids = list((await db.scalars(select(ProjectRevision.chat_id).group_by(ProjectRevision.chat_id)
            .having(or_(func.count() > 5, func.bool_or(ProjectRevision.status.in_(['failed', 'deleting'])))))).all())
    for chat_id in chat_ids:
        if chat_id in busy:
            continue
        async with AsyncSessionLocal.begin() as db:
            chat = await db.get(Chat, chat_id, with_for_update=True)
            if not chat:
                continue
            # Re-check DB state under the same lock used for admission/promotion.
            running = await db.scalar(select(Run.id).where(Run.chat_id == chat_id, Run.status == 'running').limit(1))
            if running:
                continue
            rows = list((await db.scalars(select(ProjectRevision).where(ProjectRevision.chat_id == chat_id)
                .order_by(ProjectRevision.created_at.desc()))).all())
            keep = {r.id for r in [r for r in rows if r.status == 'ready'][:5]}
            keep |= {chat.latest_saved_revision_id, chat.latest_verified_revision_id}
            deleting = []
            for row in rows:
                if row.id in keep or row.status == 'pending' or row.created_at > now - timedelta(hours=1):
                    continue
                row.status = 'deleting'
                deleting.append((row.id, row.object_key))
        for revision_id, key in deleting:
            await storage_call('delete', key)
            async with AsyncSessionLocal.begin() as db:
                await db.execute(delete(ProjectRevision).where(ProjectRevision.id == revision_id,
                                                             ProjectRevision.status == 'deleting'))

    async with AsyncSessionLocal() as db:
        expired = list((await db.scalars(select(Run).where(Run.finished_at < now - timedelta(days=14),
            Run.log_key.is_not(None)).limit(50))).all())
    for run in expired:
        async with AsyncSessionLocal.begin() as db:
            events = list((await db.scalars(select(RunEvent).where(RunEvent.run_id == run.id))).all())
            for event in events:
                event.payload = {k: v for k, v in event.payload.items() if k not in {'output', 'checks', 'metrics'}}
            row = await db.get(Run, run.id)
            if not row:
                continue
            row.metrics = {k: v for k, v in row.metrics.items() if k not in {'checks', 'sandbox_check'}}
        await storage_call('delete', run.log_key)
        async with AsyncSessionLocal.begin() as db:
            row = await db.get(Run, run.id)
            if row:
                row.log_key = None
    async with AsyncSessionLocal.begin() as db:
        # Only prune diagnostic rows after their archive was verified and detail was stripped.
        old = select(Run.id).where(Run.finished_at < now - timedelta(days=30), Run.log_key.is_(None), Run.log_sha256.is_not(None))
        await db.execute(delete(RunEvent).where(RunEvent.run_id.in_(old)))
        await db.execute(delete(StorageUsage).where(StorageUsage.day < (now - timedelta(days=32)).date()))


async def maintain_loop(service):
    async def repeat(action, message):
        while True:
            try:
                await action()
            except Exception as exc:
                logger.warning('%s error_type=%s', message, type(exc).__name__)
            await asyncio.sleep(60)

    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(repeat(service.reap_idle_sandboxes, 'Sandbox cleanup deferred'), name='sandbox-cleanup')
        tasks.create_task(repeat(lambda: maintain(service), 'Persistence maintenance deferred'), name='storage-cleanup')
