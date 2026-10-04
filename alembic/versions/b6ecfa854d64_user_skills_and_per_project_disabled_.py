"""user skills, skills turned off per project and per account, and the project's own skills

Revision ID: b6ecfa854d64
Revises: a7c3e9f1b2d4
Create Date: 2026-10-04 00:50:49.967819

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6ecfa854d64"
down_revision: str | Sequence[str] | None = "a7c3e9f1b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additions only, so the release still serving keeps working: a new table it never reads, and
    columns with constant defaults, which Postgres adds without rewriting chats."""
    op.create_table(
        "skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_skills_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("user_id", "name", name=op.f("uq_skills_user_id")),
    )
    op.add_column(
        "chats",
        sa.Column("disabled_skills", postgresql.ARRAY(sa.String(length=64)), server_default="{}", nullable=False),
    )
    op.add_column(
        "chats",
        sa.Column("project_skills", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("disabled_skills", postgresql.ARRAY(sa.String(length=64)), server_default="{}", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "disabled_skills")
    op.drop_column("chats", "project_skills")
    op.drop_column("chats", "disabled_skills")
    op.drop_table("skills")
