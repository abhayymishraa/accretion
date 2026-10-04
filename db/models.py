from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
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
    # Skills turned off for the whole account: no project uses them. Each project's own list is kept.
    disabled_skills: Mapped[list[str]] = mapped_column(ARRAY(String(64)), server_default="{}", default=list)

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
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Null until agent/run/title.py names the project from its first request.
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # The kit the project started from (sandbox/kits/<kit>/stack.json).
    kit: Mapped[str] = mapped_column(String(64), server_default="vite-fastapi-postgres")
    # Kept separate: failed drafts must not replace the last verified build.
    latest_saved_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latest_verified_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Skills are on unless named here: built-in and library skills the user turned off for this project.
    disabled_skills: Mapped[list[str]] = mapped_column(ARRAY(String(64)), server_default="{}", default=list)
    # The project's own skills (.agents/skills) as of its last successful build: name, description and
    # instructions. Always on; written by the build's finish statement, read by the skills list.
    project_skills: Mapped[list[dict[str, str]]] = mapped_column(JSONB, server_default="[]", default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    # Loaded only by the query that checks ownership for file routes; holding it keeps the row in
    # the session, so latest_revision_in finds it without a query. Never lazily loaded.
    latest_saved_revision: Mapped["ProjectRevision | None"] = relationship(
        primaryjoin="foreign(Chat.latest_saved_revision_id) == ProjectRevision.id", viewonly=True, lazy="raise"
    )


class Skill(Base):
    """A skill the user wrote: SKILL.md fields stored as columns. Read by the skills API and by every build."""

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Indexed by the (user_id, name) unique constraint, whose index leads with user_id.
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(1024))
    instructions: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


def library_rows(owner, *columns):
    """An owner's library skills as one JSON array of the given columns, for a query that also reads
    something else: the skills list, a project's skills, a build's setup."""
    pairs = [part for column in columns for part in (column.key, column)]
    return (
        select(func.coalesce(func.json_agg(func.json_build_object(*pairs)), func.json_build_array()))
        .where(Skill.user_id == owner)
        .scalar_subquery()
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
    # One queued or running build per project, enforced by Postgres rather than a read before the insert:
    # admission then needs no fresh read under a lock, and a lost race fails the INSERT (a 409).
    __table_args__ = (
        Index(
            "uq_runs_one_open_per_chat",
            "chat_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )
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
    # Each file-editing call's summary (public_tools.edit_summary), appended as it completes, so
    # history reads the edited-files card with the run's row instead of from run_events.
    edits: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
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
