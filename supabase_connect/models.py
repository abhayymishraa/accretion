"""ORM models owned by the Supabase domain."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SupabaseAccount(Base):
    """The user's Supabase sign-in: sealed OAuth tokens. Supabase refresh tokens rotate, so a refresh rewrites
    this row under a row lock."""

    __tablename__ = "supabase_accounts"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # Null once Supabase refuses the refresh token: the user signs in again.
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ProjectDatabase(Base):
    """The Supabase project an app uses. The ref is stored here and never taken from the model."""

    __tablename__ = "project_databases"
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    project_ref: Mapped[str] = mapped_column(String(40))
    project_name: Mapped[str] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(32))
    # Sealed: the database password (set when we created the project, or typed by the user), the publishable
    # and secret API keys, and the email hook secret.
    secret: Mapped[str] = mapped_column(Text)
    # "creating", "moving" (the app's data is being copied in), "ready", "reconnect" or "error".
    status: Mapped[str] = mapped_column(String(16))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
