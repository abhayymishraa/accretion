"""Read-only, paginated conversation summaries; full tool payloads load separately."""

import base64
import json
from datetime import datetime

from sqlalchemy import cast, exists, literal, null, select, tuple_, union_all

from db.models import Message, Run

from ..run.exceptions import InvalidHistoryCursor, InvalidHistoryPageSize
from ..run.worker import OPEN_STATUSES
from ..run.workflow import public_workflow


def cursor_value(value):
    try:
        if len(value) > 256:
            raise ValueError
        stamp, kind, identifier = json.loads(base64.urlsafe_b64decode(value))
        stamp = datetime.fromisoformat(stamp)
        if not stamp.tzinfo or kind not in ("message", "run") or not isinstance(identifier, str):
            raise ValueError
        return stamp, kind, identifier
    except (ValueError, TypeError, KeyError):
        raise InvalidHistoryCursor from None


def transcript(chat_id, limit=50, before=None):
    """A page of the conversation as rows, newest first, plus one row to tell whether more exist.
    Each row carries what the client shows, so the caller can read it within its own query."""
    if not 1 <= limit <= 100:
        raise InvalidHistoryPageSize
    # A run is one transcript item. Its persisted summary must not appear twice. A run's legacy
    # events/metrics JSON blobs are never selected.
    legacy = select(
        Message.id,
        literal("message").label("kind"),
        Message.created_at,
        Message.role,
        Message.content,
        Message.event_type,
        Message.tool_calls,
        cast(null(), Run.status.type).label("status"),
        cast(null(), Run.reason.type).label("reason"),
        cast(null(), Run.finished_at.type).label("finished_at"),
        cast(null(), Run.workflow.type).label("workflow"),
        cast(null(), Run.edits.type).label("edits"),
    ).where(
        Message.chat_id == chat_id,
        (Message.event_type.is_distinct_from("run_summary"))
        | ~exists(select(Run.id).where(Run.id == Message.id, Run.chat_id == chat_id)),
    )
    runs = select(
        Run.id,
        literal("run").label("kind"),
        Run.created_at,
        null(),
        null(),
        null(),
        null(),
        Run.status,
        Run.reason,
        Run.finished_at,
        Run.workflow,
        Run.edits,
    ).where(Run.chat_id == chat_id)
    rows = union_all(legacy, runs).subquery()
    query = select(rows)
    if before:
        query = query.where(tuple_(rows.c.created_at, rows.c.kind, rows.c.id) < cursor_value(before))
    return query.order_by(rows.c.created_at.desc(), rows.c.kind.desc(), rows.c.id.desc()).limit(limit + 1)


def conversation_page(rows, limit=50):
    """The client's page from transcript rows."""
    page = rows[:limit]
    items = [
        {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "event_type": row.event_type,
            "tool_calls": row.tool_calls,
            "created_at": row.created_at.isoformat(),
        }
        if row.kind == "message"
        else {
            "id": f"run:{row.id}",
            "role": "assistant",
            "content": row.reason or "",
            "event_type": "run",
            "created_at": row.created_at.isoformat(),
            "run_status": row.status,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "workflow": public_workflow(row.workflow),
            "details_pending": True,
            # The edited-files card, once the run has finished.
            "edits": None if row.status in OPEN_STATUSES else row.edits,
        }
        for row in reversed(page)
    ]
    cursor = None
    if len(rows) > limit:
        last = page[-1]
        cursor = base64.urlsafe_b64encode(
            json.dumps([last.created_at.isoformat(), last.kind, last.id]).encode()
        ).decode()
    return {
        "messages": items,
        "next_cursor": cursor,
    }
