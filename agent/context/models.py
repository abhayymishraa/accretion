"""ORM models owned by the context group."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class TranscriptEntry(Base):
    """One model-visible message, append-only, shared by every run in a chat.

    Runs used to rebuild their message array from a summary blob, which made the
    prompt prefix different on every request and cost us the provider's cache.
    Keeping one transcript per chat makes that prefix stable and gives compaction
    a single history to work on instead of two half-histories.
    """

    __tablename__ = "transcript_entries"
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
