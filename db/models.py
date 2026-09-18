from .base import Base
from plans import DEFAULT_PLAN, month_window, plan_credits
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Boolean,
    UniqueConstraint,
    false,
    Date,
    BigInteger,
    Index,
    CheckConstraint,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str] = mapped_column(String(280), default="", server_default="")
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Rate limiting fields
    last_query_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Credits are the only limit a user sees. One credit per root run; follow-ups
    # inside a run are free. The grant and the reset month come from plans.py.
    plan: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DEFAULT_PLAN, server_default=DEFAULT_PLAN
    )
    tokens_remaining: Mapped[int] = mapped_column(
        Integer, default=plan_credits(DEFAULT_PLAN)
    )
    tokens_reset_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # A User can have many Chats.
    # back_populates="user" links back to the user field in the Chat model.
    # cascade="all, delete-orphan" → if a user is deleted, all their chats are deleted too (prevents orphaned chats).
    chats: Mapped[List["Chat"]] = relationship(
        "Chat", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def credits_unlimited(self) -> bool:
        return plan_credits(self.plan) is None

    @property
    def credits_limit(self) -> int:
        return plan_credits(self.plan) or 0

    def use_token(self) -> bool:
        """Spend one credit. False when this month's credits are gone."""
        if self.credits_unlimited:
            return True
        now = datetime.now(timezone.utc)
        # Grant this month's credits on first use. The reset instant is the month
        # boundary itself, not `now` plus a duration, so it cannot drift away from
        # the cost windows in agent/budget.py.
        if self.tokens_reset_at is None or now >= self.tokens_reset_at:
            self.tokens_remaining = self.credits_limit
            self.tokens_reset_at = month_window(now)[1]
        if self.tokens_remaining > 0:
            self.tokens_remaining -= 1
            self.last_query_at = now
            return True
        return False


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("user_id", "provider"),)
    provider: Mapped[str] = mapped_column(String(16), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(24), index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    request_ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    app_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    # Kept separate: failed drafts must not replace the last verified build.
    latest_saved_revision_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    latest_verified_revision_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chats.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(50))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)  # Use Text for unlimited size
    event_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # For system events like 'builder_started'
    tool_calls: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Store tool calls as JSON: [{name: str, status: 'success'|'error', output: str}]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")


class Run(Base):
    """Bounded activity log and durable outcome; execution stays in one API worker."""

    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    prompt: Mapped[str] = mapped_column(Text)
    events: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    # Immutable proposal + atomically recorded continuation; separate from prunable diagnostics.
    workflow: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    log_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    log_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class RunEvent(Base):
    __tablename__ = 'run_events'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id', ondelete='CASCADE'), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ProjectRevision(Base):
    __tablename__ = 'project_revisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey('chats.id', ondelete='CASCADE'), index=True)
    run_id: Mapped[Optional[str]] = mapped_column(ForeignKey('runs.id', ondelete='SET NULL'), nullable=True, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    object_key: Mapped[str] = mapped_column(String(512), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    archive_sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    manifest: Mapped[dict] = mapped_column(JSON)
    template_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class StorageUsage(Base):
    __tablename__ = 'storage_usage'
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    uploaded: Mapped[int] = mapped_column(Integer, default=0)
    downloaded: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_ops: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    downloaded_ops: Mapped[int] = mapped_column(Integer, default=0, server_default='0')


class StorageDeletion(Base):
    __tablename__ = 'storage_deletions'
    object_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ProjectMemory(Base):
    """Derived context only; original messages remain the source of truth."""
    __tablename__ = 'project_memory'
    chat_id: Mapped[str] = mapped_column(ForeignKey('chats.id', ondelete='CASCADE'), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    covered_message_id: Mapped[str] = mapped_column(ForeignKey('messages.id', ondelete='CASCADE'))
    revision_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON)


class SandboxRuntime(Base):
    """One owned runtime, retained after project deletion until provider cleanup succeeds."""
    __tablename__ = 'sandbox_runtimes'
    # Deliberately no cascade: deleting a project must not erase its cleanup intent.
    chat_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(36), unique=True)
    sandbox_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    template_id: Mapped[str] = mapped_column(String(255))
    generation: Mapped[str] = mapped_column(String(64))
    revision_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reusable: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(16), index=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    spend_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class SpendEntry(Base):
    """Content-free cost ledger; project/run deletion must not reset an allowance."""
    __tablename__ = 'spend_entries'
    __table_args__ = (
        Index('ix_spend_user_window', 'user_id', 'ends_at', 'starts_at'),
        CheckConstraint('amount_nanos >= 0 AND reserved_nanos >= 0'),
        CheckConstraint('ends_at >= starts_at'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    # No run/chat foreign keys: deleting content must preserve incurred costs.
    run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), default='reserved')
    reserved_nanos: Mapped[int] = mapped_column(BigInteger)
    amount_nanos: Mapped[int] = mapped_column(BigInteger)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
