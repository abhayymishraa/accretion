"""run screenshots: images a run's browser checks saved, stored in private object storage

Revision ID: 42b9122a1610
Revises: d8a3f6b1c207
Create Date: 2026-10-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "42b9122a1610"
down_revision: str | Sequence[str] | None = "d8a3f6b1c207"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """A new table in both kinds of database, so nothing needs a guard."""
    op.create_table(
        "run_screenshots",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_run_screenshots_run_id_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_screenshots")),
    )
    op.create_index(op.f("ix_run_screenshots_run_id"), "run_screenshots", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_run_screenshots_run_id"), table_name="run_screenshots")
    op.drop_table("run_screenshots")
