"""Checkpoints commit only after immutable storage succeeds; no model calls on recovery."""

import asyncio
import base64
import hashlib
import logging
import shlex
import uuid
import zipfile
from datetime import UTC, datetime
from typing import Any

from redis import RedisError
from sqlalchemy import func, select

from agent import PACKAGE_ROOT
from db.base import AsyncSessionLocal
from db.models import Chat, ProjectRevision, Run, RunEvent

from ..run import bus
from ..sandbox.archive import MAX_ARCHIVE, content_hash, manifest
from ..tools.tools import ROOT
from .config import storage_settings
from .storage import StorageError, storage_call

# Bound archive memory and provider requests on the small single-worker VM.
archive_slots = asyncio.Semaphore(2)
logger = logging.getLogger("webbuilder.storage")
# Generated project checkouts. Deliberately not `<root>/projects`: that is the
# `projects` domain package, and the deployed bind mount would shadow it.
PROJECTS = PACKAGE_ROOT.parent / "var" / "projects"
# Strong references keep cancelled callers' uploads tracked until SDK completion.
_uploads: dict[str, Any] = {}


# Checks and adds one transfer to today's totals in a single step: bytes, then operations.
_RESERVE = """
local bytes = tonumber(redis.call('HGET', KEYS[1], ARGV[1]) or '0')
local ops = tonumber(redis.call('HGET', KEYS[1], ARGV[2]) or '0')
if bytes + tonumber(ARGV[3]) > tonumber(ARGV[4]) or ops >= tonumber(ARGV[5]) then return 0 end
redis.call('HINCRBY', KEYS[1], ARGV[1], ARGV[3])
redis.call('HINCRBY', KEYS[1], ARGV[2], 1)
redis.call('EXPIRE', KEYS[1], 172800)
return 1
"""


async def reserve_transfer(direction, size):
    """The daily storage transfer budget, kept in Redis like other rate limits so that reading a file
    costs no database round trip. ponytail: Redis has no persistence (deploy/compose.yaml), so a
    Redis restart resets the day's count, and an unreachable Redis lets transfers through; it is a
    soft guard on provider allowances, not billing."""
    limit = storage_settings.daily_limit_bytes(direction)
    key = f"accretion:storage:{datetime.now(UTC).date()}"
    operations = 1000 if direction == "uploaded" else 10000
    try:
        allowed = await bus.client.eval(_RESERVE, 1, key, direction, direction + "_ops", size, limit, operations)
    except RedisError as exc:
        logger.warning("Storage budget unchecked; Redis failed error_type=%s", type(exc).__name__)
        return
    if not allowed:
        raise StorageError("Daily storage transfer budget reached; retry after midnight UTC")


async def read_object(key, size) -> bytes:
    await reserve_transfer("downloaded", size)
    data: bytes = await storage_call("read", key, size)
    return data


async def put_object(key, data, content_type="application/zip", *, chat_id):
    async def upload():
        # Register before any await; deletion drains earlier uploads, and later
        # uploads must reject the deleted owner before starting provider I/O.
        async with AsyncSessionLocal() as db:
            if await db.get(Chat, chat_id) is None:
                raise StorageError("Project was deleted; upload cancelled")
        await reserve_transfer("uploaded", len(data))
        await storage_call("put", key, data, content_type)

    task = asyncio.create_task(upload())
    pending = _uploads.setdefault(key, set())
    pending.add(task)

    def finished(done):
        pending.remove(done)
        if not pending:
            _uploads.pop(key, None)
        if not done.cancelled():
            done.exception()

    task.add_done_callback(finished)
    await asyncio.shield(task)


async def wait_for_uploads(key):
    pending = tuple(_uploads.get(key, ()))
    if pending:
        await asyncio.gather(*(asyncio.shield(task) for task in pending), return_exceptions=True)


async def latest_revision(chat_id):
    async with AsyncSessionLocal() as db:
        return await latest_revision_in(db, chat_id)


async def latest_revision_in(db, chat_id):
    """latest_revision on the caller's session; a Chat it already loaded costs no query."""
    chat = await db.get(Chat, chat_id)
    if not chat or not chat.latest_saved_revision_id:
        return None
    revision = await db.get(ProjectRevision, chat.latest_saved_revision_id)
    if not revision or revision.chat_id != chat_id or revision.status != "ready":
        raise StorageError("Saved revision metadata is unavailable")
    return revision


async def revision_bytes(revision) -> bytes:
    data = await read_object(revision.object_key, revision.size_bytes)
    if len(data) != revision.size_bytes or hashlib.sha256(data).hexdigest() != revision.archive_sha256:
        raise StorageError("Saved revision failed integrity checks; it was not restored")
    try:
        if await asyncio.to_thread(manifest, data) != revision.manifest:
            raise ValueError("Manifest mismatch")
    except (ValueError, zipfile.BadZipFile):
        raise StorageError("Saved revision failed integrity checks; it was not restored") from None
    return data


async def promote(revision_id, event=None, *, recovery=False):
    async with AsyncSessionLocal.begin() as db:
        revision = await db.get(ProjectRevision, revision_id)
        if not revision:
            raise StorageError("Checkpoint was removed")
        chat = await db.scalar(select(Chat).where(Chat.id == revision.chat_id).with_for_update())
        if revision.status == "ready":
            return
        if not chat or revision.status != "pending" or chat.latest_saved_revision_id != revision.parent_id:
            raise StorageError("Checkpoint parent changed; previous files are preserved")
        if recovery and await db.scalar(select(Run.id).where(Run.chat_id == chat.id, Run.status == "running").limit(1)):
            raise StorageError("Recovery deferred while a new run owns the workspace")
        revision.status = "ready"
        chat.latest_saved_revision_id = revision.id
        if event:
            db.add(RunEvent(run_id=event["run_id"], sequence=event["sequence"], payload=event))


async def save_revision(chat_id, run_id, archive, template, event_factory=None):
    files = await asyncio.to_thread(manifest, archive)
    digest = content_hash(files, template)
    revision_id = str(uuid.uuid4())
    async with AsyncSessionLocal.begin() as db:
        # Serialize quota reservations across chats as well as same-chat pointer updates.
        await db.execute(select(func.pg_advisory_xact_lock(73142027)))
        chat = await db.scalar(select(Chat).where(Chat.id == chat_id).with_for_update())
        if not chat:
            raise StorageError("Project was removed")
        previous = (
            await db.get(ProjectRevision, chat.latest_saved_revision_id) if chat.latest_saved_revision_id else None
        )
        if previous and previous.status == "ready" and previous.content_hash == digest:
            return previous.id, None
        total = (
            await db.scalar(
                select(func.coalesce(func.sum(ProjectRevision.size_bytes), 0))
                .join(Chat, Chat.id == ProjectRevision.chat_id)
                .where(Chat.user_id == chat.user_id)
            )
        ) or 0
        project_total = (
            await db.scalar(
                select(func.coalesce(func.sum(ProjectRevision.size_bytes), 0)).where(ProjectRevision.chat_id == chat_id)
            )
        ) or 0
        all_total = await db.scalar(select(func.coalesce(func.sum(ProjectRevision.size_bytes), 0))) or 0
        if (
            total + len(archive) > 1024**3
            or project_total + len(archive) > 200 * 1024**2
            or all_total + len(archive) > 5 * 1024**3
        ):
            raise StorageError("Saved project storage limit reached")
        revision = ProjectRevision(
            id=revision_id,
            chat_id=chat_id,
            run_id=run_id,
            parent_id=chat.latest_saved_revision_id,
            status="pending",
            object_key=f"projects/{chat_id}/revisions/{revision_id}.zip",
            content_hash=digest,
            archive_sha256=hashlib.sha256(archive).hexdigest(),
            size_bytes=len(archive),
            manifest=files,
            template_id=template,
        )
        db.add(revision)
    # A crash here leaves a pending row. Recovery checks this exact object and hash.
    await put_object(revision.object_key, archive, chat_id=chat_id)
    event = event_factory(revision_id) if event_factory else None
    await promote(revision_id, event)
    return revision_id, event


async def sandbox_archive(sandbox, mode, data=None):
    script = (PACKAGE_ROOT / "sandbox" / "archive.py").read_text()
    target = f"/tmp/webbuilder-{uuid.uuid4()}.zip"
    try:
        if data is not None:
            await sandbox.files.write(target, data)
        result = await sandbox.commands.run(
            "python3 -I -c " + shlex.quote(script) + " " + mode + " " + shlex.quote(ROOT) + " " + shlex.quote(target),
            timeout=45,
        )
        if mode == "pack":
            encoded = result.stdout.strip()
            if len(encoded) > ((MAX_ARCHIVE + 2) // 3) * 4:
                raise StorageError("Sandbox archive exceeds 32 MiB")
            return base64.b64decode(encoded, validate=True)
    finally:
        # Delete only the host-chosen temporary path, even on packaging failure.
        try:
            await asyncio.wait_for(sandbox.files.remove(target), timeout=3)
        except Exception:
            pass
