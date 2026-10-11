"""ORM models owned by the GitHub domain."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class GithubAccount(Base):
    """The user's GitHub connection: who they are on GitHub, the App installation that can reach their repos,
    and their sealed user token (it creates repos; the installation token pushes)."""

    __tablename__ = "github_accounts"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    github_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    login: Mapped[str] = mapped_column(String(64))
    # Null after the App is uninstalled: every repo shows "Reconnect".
    installation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    # Sealed: access token, refresh token and both expiries. Null once the user revokes access.
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ProjectRepo(Base):
    """The repository a project syncs with, and where the two sides last agreed."""

    __tablename__ = "project_repos"
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    # Webhooks name the repository by id; a rename keeps the id.
    repo_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    branch: Mapped[str] = mapped_column(String(255))
    # Where pull requests go; kept current by webhooks.
    default_branch: Mapped[str] = mapped_column(String(255))
    # The commit both sides last agreed on, and the revision it holds.
    synced_sha: Mapped[str] = mapped_column(String(40))
    synced_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # A head seen on GitHub and not pulled yet (a build was running); pulled when the build ends.
    pending_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # "synced", "pushing", "pulling", "conflict", "blocked", "approval", "reconnect", "gone" or "error".
    status: Mapped[str] = mapped_column(String(16))
    # Plain words for the status line, and its details: the conflict pull request, the files that hold a key,
    # the workflow files waiting for approval.
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    # Files changed on GitHub since the builder last ran; the next build is told, then this is cleared.
    outside_changes: Mapped[list[str]] = mapped_column(JSONB, server_default="[]")
    # sha256 of each workflow file the user allowed to be pushed.
    approved_workflows: Mapped[dict[str, str]] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
