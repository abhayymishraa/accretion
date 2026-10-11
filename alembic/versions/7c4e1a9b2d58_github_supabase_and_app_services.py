"""github sync, supabase connect and app services

Revision ID: 7c4e1a9b2d58
Revises: 3b7d2e9a4c61
Create Date: 2026-10-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c4e1a9b2d58"
down_revision: str | Sequence[str] | None = "3b7d2e9a4c61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    """New tables only: the release still serving reads none of them."""
    op.create_table(
        "github_accounts",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("github_user_id", sa.BigInteger(), nullable=False),
        sa.Column("login", sa.String(64), nullable=False),
        sa.Column("installation_id", sa.BigInteger(), nullable=True),
        sa.Column("secret", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_github_accounts_installation_id", "github_accounts", ["installation_id"])
    op.create_index("ix_github_accounts_github_user_id", "github_accounts", ["github_user_id"])
    op.create_table(
        "project_repos",
        sa.Column("chat_id", sa.String(36), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("repo_id", sa.BigInteger(), nullable=False),
        sa.Column("owner", sa.String(100), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("branch", sa.String(255), nullable=False),
        sa.Column("default_branch", sa.String(255), nullable=False),
        sa.Column("synced_sha", sa.String(40), nullable=False),
        sa.Column("synced_revision_id", sa.String(36), nullable=True),
        sa.Column("pending_sha", sa.String(40), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("detail", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("outside_changes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("approved_workflows", postgresql.JSONB(), server_default="{}", nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_project_repos_repo_id", "project_repos", ["repo_id"])
    op.create_table(
        "supabase_accounts",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("secret", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_table(
        "project_databases",
        sa.Column("chat_id", sa.String(36), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("project_ref", sa.String(40), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("detail", postgresql.JSONB(), server_default="{}", nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "app_tokens",
        sa.Column("chat_id", sa.String(36), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in ("app_tokens", "project_databases", "supabase_accounts", "project_repos", "github_accounts"):
        op.drop_table(table)
