"""ORM models owned by the Vercel domain."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class VercelAccount(Base):
    """The user's Vercel connection: the Integration's sealed access token, and the team it was installed on.
    Vercel's integration tokens do not expire; one stops working when the user removes the Integration."""

    __tablename__ = "vercel_accounts"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # Sealed: access token and team id (null on a personal account).
    secret: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ProjectPublish(Base):
    """An app's published copy on the owner's Vercel: the Vercel project, its address, and the last publish."""

    __tablename__ = "project_publishes"
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    vercel_project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # The public address of the last successful publish; kept while an update runs or fails.
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The saved revision the live address serves.
    revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # "uploading", "building", "live", "database" (the user adds one on Vercel), or "failed".
    status: Mapped[str] = mapped_column(String(16))
    # Plain words for the status line, Vercel's log link, and the variable names this app put on the project.
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
