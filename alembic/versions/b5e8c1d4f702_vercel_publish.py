"""vercel connection and published apps

Revision ID: b5e8c1d4f702
Revises: 9d2b6e4f8a13
Create Date: 2026-10-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5e8c1d4f702"
down_revision: str | Sequence[str] | None = "9d2b6e4f8a13"
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
        "vercel_accounts",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("secret", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "project_publishes",
        sa.Column("chat_id", sa.String(36), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("vercel_project_id", sa.String(64), nullable=True),
        sa.Column("project_name", sa.String(100), nullable=True),
        sa.Column("url", sa.String(255), nullable=True),
        sa.Column("revision_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("detail", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("project_publishes")
    op.drop_table("vercel_accounts")
