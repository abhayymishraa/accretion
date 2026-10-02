"""Read-only, paginated conversation summaries; full tool payloads load separately."""

import base64
import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import ColumnClause, exists, literal, literal_column, select, tuple_, union_all

from db.models import Message, Run, RunEvent

from ..run.worker import OPEN_STATUSES
from ..run.workflow import public_workflow
from ..tools.public_tools import EDIT_TOOLS

# Each diff without its hunks: the edited-files card needs paths and counts, and the hunks are
# most of the bytes. Postgres drops them so they never cross the network.
_DIFF_HEADERS: ColumnClause[Any] = literal_column(
    "(SELECT json_agg(json_build_object('path', d->'path', 'created', d->'created', 'added', d->'added',"
    " 'removed', d->'removed', 'hunks', json_build_array()))"
    " FROM json_array_elements(CASE WHEN json_typeof(run_events.payload->'details'->'diffs') = 'array'"
    " THEN run_events.payload->'details'->'diffs' ELSE '[]'::json END) AS d)"
)
# Runs recorded before structured details kept the changed files in the output text.
_LEGACY_OUTPUT: ColumnClause[Any] = literal_column(
    "CASE WHEN run_events.payload->'details' IS NULL THEN run_events.payload->>'output' END"
)


async def finished_edits(db, run_ids):
    """Each run's file-editing tool calls, enough for the client's edited-files card, in one query
    for the page. The full steps load only when a run is expanded."""
    if not run_ids:
        return {}
    payload = RunEvent.payload
    rows = await db.execute(
        select(
            RunEvent.run_id,
            payload["call_id"].as_string().label("call_id"),
            payload["name"].as_string().label("name"),
            payload["ok"].as_boolean().label("ok"),
            payload["details"]["version"].label("version"),
            payload["details"]["changed_files"].label("changed_files"),
            _DIFF_HEADERS.label("diffs"),
            _LEGACY_OUTPUT.label("output"),
        )
        .where(
            RunEvent.run_id.in_(run_ids),
            payload["e"].as_string() == "tool_completed",
            payload["name"].as_string().in_(EDIT_TOOLS),
        )
        .order_by(RunEvent.run_id, RunEvent.sequence)
    )
    edits: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        details = None
        if row.version is not None:
            details = {"version": row.version, "changed_files": row.changed_files, "diffs": row.diffs}
        edits.setdefault(row.run_id, []).append(
            {
                "id": row.call_id,
                "name": row.name,
                "status": "success" if row.ok else "error",
                "details": details,
                "output": row.output,
            }
        )
    return edits


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
        raise HTTPException(422, "Invalid history cursor") from None


async def conversation_page(db, chat_id, limit=50, before=None):
    if not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid history page size")
    # A run is one transcript item. Its persisted summary must not appear twice.
    legacy = select(Message.id, literal("message").label("kind"), Message.created_at).where(
        Message.chat_id == chat_id,
        (Message.event_type.is_distinct_from("run_summary"))
        | ~exists(select(Run.id).where(Run.id == Message.id, Run.chat_id == chat_id)),
    )
    runs = select(Run.id, literal("run").label("kind"), Run.created_at).where(Run.chat_id == chat_id)
    transcript = union_all(legacy, runs).subquery()
    query = select(transcript)
    if before:
        query = query.where(tuple_(transcript.c.created_at, transcript.c.kind, transcript.c.id) < cursor_value(before))
    rows = (
        await db.execute(
            query.order_by(transcript.c.created_at.desc(), transcript.c.kind.desc(), transcript.c.id.desc()).limit(
                limit + 1
            )
        )
    ).all()
    page = rows[:limit]
    message_ids = [row.id for row in page if row.kind == "message"]
    run_ids = [row.id for row in page if row.kind == "run"]
    messages = (
        (await db.scalars(select(Message).where(Message.chat_id == chat_id, Message.id.in_(message_ids)))).all()
        if message_ids
        else []
    )
    # Select only summary columns, never the legacy events/metrics JSON blobs.
    summaries = (
        (
            await db.execute(
                select(Run.id, Run.status, Run.reason, Run.created_at, Run.finished_at, Run.workflow).where(
                    Run.chat_id == chat_id, Run.id.in_(run_ids)
                )
            )
        ).all()
        if run_ids
        else []
    )
    edits = await finished_edits(db, [r.id for r in summaries if r.status not in OPEN_STATUSES])
    items = {
        ("message", m.id): {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "event_type": m.event_type,
            "tool_calls": m.tool_calls,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    }
    items.update(
        {
            ("run", r.id): {
                "id": f"run:{r.id}",
                "role": "assistant",
                "content": r.reason or "",
                "event_type": "run",
                "created_at": r.created_at.isoformat(),
                "run_status": r.status,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "workflow": public_workflow(r.workflow),
                "details_pending": True,
                "edits": edits.get(r.id),
            }
            for r in summaries
        }
    )
    cursor = None
    if len(rows) > limit:
        last = page[-1]
        cursor = base64.urlsafe_b64encode(
            json.dumps([last.created_at.isoformat(), last.kind, last.id]).encode()
        ).decode()
    return {
        "messages": [items[(row.kind, row.id)] for row in reversed(page) if (row.kind, row.id) in items],
        "next_cursor": cursor,
    }
