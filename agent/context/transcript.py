"""One append-only model transcript per chat.

Every harness that manages a long conversation keeps a single growing entry log
and appends to it: Pi stores a session as JSONL entries, Reasonix calls its copy
"cache-first, append-only", Codex reads every user message out of one history.
Rebuilding the array per request, as this loop used to, changes the prompt prefix
each time and forfeits the provider's cached-input discount on all of it.

Persistence is incremental and best-effort per turn, so a run that stops partway
still leaves the work it did visible to the next request, matching the promise
the service already makes when it ends a run at a limit.
"""

import logging
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import messages_from_dict, messages_to_dict
from sqlalchemy import Text, cast, delete, func, select

from agent.context.models import TranscriptEntry
from db.base import AsyncSessionLocal

logger = logging.getLogger("webbuilder.runs")


async def load(chat_id):
    """Every entry recorded for this chat, oldest first.

    A transcript that cannot be decoded is dropped rather than raised. These rows
    are a cache of messages the chat already stores; a payload this process no
    longer understands would otherwise fail the run at startup and keep failing
    every run after it, wedging the chat for good. Returning nothing degrades to
    the pre-transcript behaviour, where the request carries its own recent
    history instead.
    """
    async with AsyncSessionLocal() as db:
        rows: Sequence[dict[str, Any]] = (
            (
                await db.execute(
                    select(TranscriptEntry.payload)
                    .where(TranscriptEntry.chat_id == chat_id)
                    .order_by(TranscriptEntry.sequence)
                )
            )
            .scalars()
            .all()
        )
    if not rows:
        return []
    try:
        return messages_from_dict(list(rows))
    except Exception:
        logger.exception("Unreadable transcript; continuing without it chat_id=%s", chat_id)
        return []


async def append(chat_id, messages, start):
    """Record messages from `start` onwards. Returns the new entry count."""
    payloads = messages_to_dict(list(messages[start:]))
    if not payloads:
        return start
    async with AsyncSessionLocal.begin() as db:
        db.add_all(
            [
                TranscriptEntry(chat_id=chat_id, sequence=start + offset, payload=payload)
                for offset, payload in enumerate(payloads)
            ]
        )
    return start + len(payloads)


async def replace(chat_id, messages):
    """Rewrite the transcript after compaction folded part of it away.

    Compaction is the one operation that is not append-only, which is why every
    harness treats it as a deliberate cache-reset point rather than something to
    do a little of each turn.
    """
    async with AsyncSessionLocal.begin() as db:
        await db.execute(delete(TranscriptEntry).where(TranscriptEntry.chat_id == chat_id))
        db.add_all(
            [
                TranscriptEntry(chat_id=chat_id, sequence=offset, payload=payload)
                for offset, payload in enumerate(messages_to_dict(list(messages)))
            ]
        )
    return len(messages)


async def size_chars(chat_id: str) -> int:
    """Stored transcript size in characters: a cheap bound for picking a model that fits."""
    async with AsyncSessionLocal() as db:
        total = await db.scalar(
            select(func.coalesce(func.sum(func.length(cast(TranscriptEntry.payload, Text))), 0)).where(
                TranscriptEntry.chat_id == chat_id
            )
        )
    return int(total or 0)
