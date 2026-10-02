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

from plans import DEFAULT_PLAN

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
    # Null while the account waits on the waitlist; set once an admin lets it in.
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # "admin" opens the waitlist page. It grants no budget: that is `plan`.
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user", server_default="user")

    # The monthly model budget (agent/budget) applies unless the plan is unlimited.
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default=DEFAULT_PLAN, server_default=DEFAULT_PLAN)
    # The user's last pick, pre-filling the picker in the prompt box (spec 4.2, dyad's selectedModel).
    default_model_choice: Mapped[str] = mapped_column(String(128), default="auto", server_default="auto")

    # A User can have many Chats.
    # back_populates="user" links back to the user field in the Chat model.
    # cascade="all, delete-orphan" → if a user is deleted, all their chats are deleted too (prevents orphaned chats).
    chats: Mapped[list["Chat"]] = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

    @property
    def waitlisted(self) -> bool:
        return self.approved_at is None

    @property
    def unlimited(self) -> bool:
        # The one plan the monthly budget does not apply to.
        return self.plan == "unlimited"


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    # Null until agent/run/title.py names the project from its first request.
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    """A run's queue row, owner lease, bounded activity log and durable outcome."""

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
    # The worker holding this run (agent/run/worker.py) and when its lease lapses.
    claimed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Durable stop request; every heartbeat reads it, the Redis command only makes it immediate.
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # The user message that started the run; the worker needs it to build the run's context.
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class RunEvent(Base):
    __tablename__ = "run_events"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RunScreenshot(Base):
    """An image a run's browser check saved. The bytes live in private storage at `object_key`."""

    __tablename__ = "run_screenshots"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    object_key: Mapped[str] = mapped_column(String(512))
    media_type: Mapped[str] = mapped_column(String(32))
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
