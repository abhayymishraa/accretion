"""Bounded public diagnostics. Prompts, source files and provider credentials stay out."""
import gzip
import hashlib
import json
import os
import re

from sqlalchemy import select

from db.base import AsyncSessionLocal
from db.models import Run, RunEvent
from .persistence import put_object, read_object
from .storage import StorageError


def redact(value, *, max_length=4000):
    if isinstance(value, dict):
        return {k: redact(v, max_length=max_length) for k, v in value.items() if k.lower() not in
                {'authorization', 'cookie', 'password', 'secret', 'api_key', 'token'}}
    if isinstance(value, list):
        return [redact(v, max_length=max_length) for v in value[:250]]
    if not isinstance(value, str):
        return value
    for key, secret in os.environ.items():
        if len(secret) >= 8 and any(s in key for s in ('KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'DATABASE_URL')):
            value = value.replace(secret, '[redacted]')
    value = re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|password|secret|token)\s*[=:]\s*)[^\s,;\"\']+', r'\1[redacted]', value)
    value = re.sub(r'\b(?:sk-[\w-]{12,}|gh[pousr]_[\w]+|AIza[\w-]+)\b', '[redacted]', value)
    value = re.sub(r'(\w+://)[^\s/@]+:[^\s/@]+@', r'\1[redacted]@', value)
    return value if max_length is None else value[:max_length]


async def run_events(db, run_id, after_sequence=0):
    rows = (await db.scalars(select(RunEvent).where(RunEvent.run_id == run_id,
        RunEvent.sequence > after_sequence).order_by(RunEvent.sequence).limit(201))).all()
    return [{**row.payload, 'sequence': row.sequence} for row in rows]


async def archive_run(run_id):
    async with AsyncSessionLocal() as db:
        run = await db.get(Run, run_id)
        if not run or run.status in ('running', 'awaiting_input') or run.log_sha256:
            return
        events = await run_events(db, run_id)
    if not events:
        return
    lines = []
    for event in events:
        entry = redact(event)
        encoded = json.dumps(entry, ensure_ascii=False, separators=(',', ':')).encode()
        if len(encoded) > 4096:
            # Retain every event's identity/order, visibly truncate oversized legacy diagnostics.
            entry = {k: (v[:128] if isinstance(v, str) else v) for k, v in entry.items()
                     if k in {'e', 'run_id', 'event_id', 'sequence', 'created_at', 'name', 'call_id',
                              'status', 'ok', 'message', 'output', 'revision_id', 'duration_ms'}}
            entry['details_truncated'] = True
            encoded = json.dumps(entry, ensure_ascii=False, separators=(',', ':')).encode()
        lines.append(encoded + b'\n')
    body = b''.join(lines)
    if len(body) > 1024 * 1024:
        raise StorageError('Run diagnostic archive exceeds 1 MiB')
    archive = gzip.compress(body, mtime=0)
    key = f'logs/{run_id}.jsonl.gz'
    await put_object(key, archive, 'application/gzip', chat_id=run.chat_id)
    # Confirm bytes before allowing expanded DB diagnostics to be pruned later.
    stored_sha256 = hashlib.sha256(await read_object(key, len(archive))).hexdigest()
    archive_sha256 = hashlib.sha256(archive).hexdigest()
    if stored_sha256 != archive_sha256:
        raise StorageError('Run log archive verification failed')
    async with AsyncSessionLocal.begin() as db:
        run = await db.get(Run, run_id)
        if not run:
            return  # Project deletion already queued the deterministic log key for cleanup.
        run.log_key, run.log_sha256 = key, archive_sha256
        run.events = []
