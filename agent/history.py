"""Read-only, paginated conversation summaries; tool payloads load separately."""
import base64
from datetime import datetime
import json

from fastapi import HTTPException
from sqlalchemy import exists, literal, select, tuple_, union_all

from db.models import Message, Run


def cursor_value(value):
    try:
        if len(value) > 256:
            raise ValueError
        stamp, kind, identifier = json.loads(base64.urlsafe_b64decode(value))
        stamp = datetime.fromisoformat(stamp)
        if not stamp.tzinfo or kind not in ('message', 'run') or not isinstance(identifier, str):
            raise ValueError
        return stamp, kind, identifier
    except (ValueError, TypeError, KeyError):
        raise HTTPException(422, 'Invalid history cursor') from None


async def conversation_page(db, chat_id, limit=50, before=None):
    if not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid history page size')
    # A run is one transcript item. Its persisted summary must not appear twice.
    legacy = select(Message.id, literal('message').label('kind'), Message.created_at).where(
        Message.chat_id == chat_id,
        (Message.event_type.is_distinct_from('run_summary')) |
        ~exists(select(Run.id).where(Run.id == Message.id, Run.chat_id == chat_id)))
    runs = select(Run.id, literal('run').label('kind'), Run.created_at).where(Run.chat_id == chat_id)
    transcript = union_all(legacy, runs).subquery()
    query = select(transcript)
    if before:
        query = query.where(tuple_(transcript.c.created_at, transcript.c.kind, transcript.c.id) < cursor_value(before))
    rows = (await db.execute(query.order_by(transcript.c.created_at.desc(),
        transcript.c.kind.desc(), transcript.c.id.desc()).limit(limit + 1))).all()
    page = rows[:limit]
    message_ids = [row.id for row in page if row.kind == 'message']
    run_ids = [row.id for row in page if row.kind == 'run']
    messages = (await db.scalars(select(Message).where(Message.chat_id == chat_id,
        Message.id.in_(message_ids)))).all() if message_ids else []
    # Select only summary columns, never the legacy events/metrics JSON blobs.
    summaries = (await db.execute(select(Run.id, Run.status, Run.reason, Run.created_at, Run.finished_at)
        .where(Run.chat_id == chat_id, Run.id.in_(run_ids)))).all() if run_ids else []
    items = {('message', m.id): {'id': m.id, 'role': m.role, 'content': m.content,
        'event_type': m.event_type, 'tool_calls': m.tool_calls, 'created_at': m.created_at.isoformat()}
        for m in messages}
    items.update({('run', r.id): {'id': f'run:{r.id}', 'role': 'assistant', 'content': r.reason or '',
        'event_type': 'run', 'created_at': r.created_at.isoformat(), 'run_status': r.status,
        'finished_at': r.finished_at.isoformat() if r.finished_at else None,
        'details_pending': True} for r in summaries})
    cursor = None
    if len(rows) > limit:
        last = page[-1]
        cursor = base64.urlsafe_b64encode(json.dumps(
            [last.created_at.isoformat(), last.kind, last.id]).encode()).decode()
    return {'messages': [items[(row.kind, row.id)] for row in reversed(page)
                         if (row.kind, row.id) in items], 'next_cursor': cursor}
