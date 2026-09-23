"""Checkpoints commit only after immutable storage succeeds; no model calls on recovery."""
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from agent import PACKAGE_ROOT
import shlex
import uuid
import zipfile

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from db.base import AsyncSessionLocal
from db.models import Chat, ProjectRevision, Run, RunEvent, StorageUsage
from ..sandbox.archive import MAX_ARCHIVE, MAX_BYTES, MAX_FILES, content_hash, manifest, safe_path
from .storage import storage_call, StorageError
from ..tools.tools import ROOT

# Bound archive memory and provider requests on the small single-worker VM.
archive_slots = asyncio.Semaphore(2)
PROJECTS = PACKAGE_ROOT.parent / 'projects'
_uploads = {}  # Strong references keep cancelled callers' uploads tracked until SDK completion.


async def reserve_transfer(direction, size):
    limit = int(os.getenv('STORAGE_DAILY_UPLOAD_MB' if direction == 'uploaded'
                          else 'STORAGE_DAILY_DOWNLOAD_MB', '256' if direction == 'uploaded' else '1024')) * 1024 * 1024
    today = datetime.now(timezone.utc).date()
    async with AsyncSessionLocal.begin() as db:
        await db.execute(insert(StorageUsage).values(day=today, uploaded=0, downloaded=0).on_conflict_do_nothing())
        column = getattr(StorageUsage, direction)
        operations = getattr(StorageUsage, direction + '_ops')
        result = await db.execute(update(StorageUsage).where(StorageUsage.day == today, column + size <= limit,
            operations < (1000 if direction == 'uploaded' else 10000))
            .values({direction: column + size, direction + '_ops': operations + 1}).returning(StorageUsage.day))
        if result.scalar_one_or_none() is None:
            raise StorageError('Daily storage transfer budget reached; retry after midnight UTC')


async def read_object(key, size):
    await reserve_transfer('downloaded', size)
    return await storage_call('read', key, size)


async def put_object(key, data, content_type='application/zip', *, chat_id):
    async def upload():
        # Register before any await; deletion drains earlier uploads, and later
        # uploads must reject the deleted owner before starting provider I/O.
        async with AsyncSessionLocal() as db:
            if await db.get(Chat, chat_id) is None:
                raise StorageError('Project was deleted; upload cancelled')
        await reserve_transfer('uploaded', len(data))
        await storage_call('put', key, data, content_type)

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
        chat = await db.get(Chat, chat_id)
        if not chat or not chat.latest_saved_revision_id:
            return None
        revision = await db.get(ProjectRevision, chat.latest_saved_revision_id)
        if not revision or revision.chat_id != chat_id or revision.status != 'ready':
            raise StorageError('Saved revision metadata is unavailable')
        return revision


async def revision_bytes(revision):
    data = await read_object(revision.object_key, revision.size_bytes)
    if len(data) != revision.size_bytes or hashlib.sha256(data).hexdigest() != revision.archive_sha256:
        raise StorageError('Saved revision failed integrity checks; it was not restored')
    try:
        if await asyncio.to_thread(manifest, data) != revision.manifest:
            raise ValueError('Manifest mismatch')
    except (ValueError, zipfile.BadZipFile):
        raise StorageError('Saved revision failed integrity checks; it was not restored') from None
    return data


async def promote(revision_id, event=None, *, recovery=False):
    async with AsyncSessionLocal.begin() as db:
        revision = await db.get(ProjectRevision, revision_id)
        if not revision:
            raise StorageError('Checkpoint was removed')
        chat = await db.scalar(select(Chat).where(Chat.id == revision.chat_id).with_for_update())
        if revision.status == 'ready':
            return
        if not chat or revision.status != 'pending' or chat.latest_saved_revision_id != revision.parent_id:
            raise StorageError('Checkpoint parent changed; previous files are preserved')
        if recovery and await db.scalar(select(Run.id).where(Run.chat_id == chat.id, Run.status == 'running').limit(1)):
            raise StorageError('Recovery deferred while a new run owns the workspace')
        revision.status = 'ready'
        chat.latest_saved_revision_id = revision.id
        if event:
            db.add(RunEvent(run_id=event['run_id'], sequence=event['sequence'], payload=event))


async def save_revision(chat_id, run_id, archive, template, event_factory=None):
    files = await asyncio.to_thread(manifest, archive)
    digest = content_hash(files, template)
    revision_id = str(uuid.uuid4())
    async with AsyncSessionLocal.begin() as db:
        # Serialize quota reservations across chats as well as same-chat pointer updates.
        await db.execute(select(func.pg_advisory_xact_lock(73142027)))
        chat = await db.scalar(select(Chat).where(Chat.id == chat_id).with_for_update())
        if not chat:
            raise StorageError('Project was removed')
        previous = await db.get(ProjectRevision, chat.latest_saved_revision_id) if chat.latest_saved_revision_id else None
        if previous and previous.status == 'ready' and previous.content_hash == digest:
            return previous.id, None
        total = await db.scalar(select(func.coalesce(func.sum(ProjectRevision.size_bytes), 0))
            .join(Chat, Chat.id == ProjectRevision.chat_id).where(Chat.user_id == chat.user_id))
        project_total = await db.scalar(select(func.coalesce(func.sum(ProjectRevision.size_bytes), 0))
            .where(ProjectRevision.chat_id == chat_id))
        all_total = await db.scalar(select(func.coalesce(func.sum(ProjectRevision.size_bytes), 0)))
        if (total + len(archive) > 1024**3 or project_total + len(archive) > 200 * 1024**2
                or all_total + len(archive) > 5 * 1024**3):
            raise StorageError('Saved project storage limit reached')
        revision = ProjectRevision(id=revision_id, chat_id=chat_id, run_id=run_id,
            parent_id=chat.latest_saved_revision_id, status='pending',
            object_key=f'projects/{chat_id}/revisions/{revision_id}.zip', content_hash=digest,
            archive_sha256=hashlib.sha256(archive).hexdigest(), size_bytes=len(archive), manifest=files,
            template_id=template)
        db.add(revision)
    # A crash here leaves a pending row. Recovery checks this exact object and hash.
    await put_object(revision.object_key, archive, chat_id=chat_id)
    event = event_factory(revision_id) if event_factory else None
    await promote(revision_id, event)
    return revision_id, event


async def sandbox_archive(sandbox, mode, data=None):
    script = (PACKAGE_ROOT / 'sandbox' / 'archive.py').read_text()
    target = f'/tmp/webbuilder-{uuid.uuid4()}.zip'
    try:
        if data is not None:
            await sandbox.files.write(target, data)
        result = await sandbox.commands.run('python3 -I -c ' + shlex.quote(script) + ' ' + mode + ' '
                                   + shlex.quote(ROOT) + ' ' + shlex.quote(target), timeout=45)
        if mode == 'pack':
            encoded = result.stdout.strip()
            if len(encoded) > ((MAX_ARCHIVE + 2) // 3) * 4:
                raise StorageError('Sandbox archive exceeds 10 MiB')
            return base64.b64decode(encoded, validate=True)
    finally:
        # Delete only the host-chosen temporary path, even on packaging failure.
        try:
            await asyncio.wait_for(sandbox.files.remove(target), timeout=3)
        except Exception:
            pass


def legacy_archive(chat_id):
    # IDs come from owned DB rows, never an arbitrary client path.
    folder = PROJECTS / str(uuid.UUID(chat_id))
    metadata = folder / 'metadata.json'
    if not metadata.is_file():
        return None
    info = json.loads(metadata.read_text())
    names = info.get('files', [])
    if len(names) > MAX_FILES or len(set(names)) != len(names):
        raise StorageError('Legacy snapshot has invalid file metadata')
    buffer, total = io.BytesIO(), 0
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in names:
            safe_path(name)
            path = folder / 'files' / name if info.get('version') == 2 else folder / name.replace('/', '_')
            if not path.resolve().is_relative_to(folder.resolve()) or not path.is_file():
                raise StorageError('Legacy snapshot is incomplete; original files retained')
            total += path.stat().st_size
            if total > MAX_BYTES:
                raise StorageError('Legacy snapshot exceeds storage limits')
            z.write(path, name)
            if buffer.tell() > MAX_ARCHIVE:
                raise StorageError('Legacy snapshot exceeds archive limit')
    return buffer.getvalue()


async def ensure_revision(chat_id):
    revision = await latest_revision(chat_id)
    if revision:
        return revision
    async with archive_slots:
        archive = await asyncio.to_thread(legacy_archive, chat_id)
        if archive is not None:
            await save_revision(chat_id, None, archive, os.environ['E2B_TEMPLATE_ID'])
    return await latest_revision(chat_id)
