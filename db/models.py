from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from plans import DEFAULT_PLAN, month_window, plan_credits

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str] = mapped_column(String(280), default="", server_default="")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Credits are the only limit a user sees. One credit per root run; follow-ups
    # inside a run are free. The grant and the reset month come from plans.py.
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default=DEFAULT_PLAN, server_default=DEFAULT_PLAN)
    # The user's last pick, pre-filling the picker in the prompt box (spec 4.2, dyad's selectedModel).
    default_model_choice: Mapped[str] = mapped_column(String(128), default="auto", server_default="auto")
    tokens_remaining: Mapped[int] = mapped_column(Integer, default=plan_credits(DEFAULT_PLAN))
    tokens_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    # A User can have many Chats.
    # back_populates="user" links back to the user field in the Chat model.
    # cascade="all, delete-orphan" → if a user is deleted, all their chats are deleted too (prevents orphaned chats).
    chats: Mapped[list["Chat"]] = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

    @property
    def credits_unlimited(self) -> bool:
        return plan_credits(self.plan) is None

    @property
    def credits_limit(self) -> int:
        return plan_credits(self.plan) or 0

    def refund_token(self) -> None:
        """Return a credit for a run that never got service.

        Only for infrastructure faults. A run that spent its budget consumed real
        compute, so refunding that would make an impossible request free to retry.
        """
        if not self.credits_unlimited and self.tokens_remaining < self.credits_limit:
            self.tokens_remaining += 1

    def use_token(self) -> bool:
        """Spend one credit. False when this month's credits are gone."""
        if self.credits_unlimited:
            return True
        now = datetime.now(UTC)
        # Grant this month's credits on first use. The reset instant is the month
        # boundary itself, not `now` plus a duration, so it cannot drift away from
        # the cost windows in agent/budget.py.
        if self.tokens_reset_at is None or now >= self.tokens_reset_at:
            self.tokens_remaining = self.credits_limit
            self.tokens_reset_at = month_window(now)[1]
        if self.tokens_remaining > 0:
            self.tokens_remaining -= 1
            return True
        return False


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    app_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # The kit the project started from (sandbox/kits/<kit>/stack.json).
    kit: Mapped[str] = mapped_column(String(64), server_default="vite-fastapi-postgres")
    # Kept separate: failed drafts must not replace the last verified build.
    latest_saved_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latest_verified_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(50))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)  # Use Text for unlimited size
    event_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # For system events like 'builder_started'
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )  # Store tool calls as JSON: [{name: str, status: 'success'|'error', output: str}]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")


class Run(Base):
    """Bounded activity log and durable outcome; execution stays in one API worker."""

    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    prompt: Mapped[str] = mapped_column(Text)
    # "auto" or the registry id the user picked for this request (spec 4.2).
    model_choice: Mapped[str] = mapped_column(String(128), default="auto", server_default="auto")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict[str, Any])
    # Immutable proposal + atomically recorded continuation; separate from prunable diagnostics.
    workflow: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict[str, Any], server_default="{}")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    log_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    log_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RunEvent(Base):
    __tablename__ = "run_events"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ProjectRevision(Base):
    __tablename__ = "project_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    object_key: Mapped[str] = mapped_column(String(512), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    archive_sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    template_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StorageDeletion(Base):
    __tablename__ = "storage_deletions"
    object_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SandboxRuntime(Base):
    """One owned runtime, retained after project deletion until provider cleanup succeeds."""

    __tablename__ = "sandbox_runtimes"
    # Deliberately no cascade: deleting a project must not erase its cleanup intent.
    chat_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(36), unique=True)
    sandbox_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    template_id: Mapped[str] = mapped_column(String(255))
    generation: Mapped[str] = mapped_column(String(64))
    revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reusable: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(16), index=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    spend_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
