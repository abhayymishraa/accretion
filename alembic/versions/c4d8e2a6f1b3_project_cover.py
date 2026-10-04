"""project cover

Revision ID: c4d8e2a6f1b3
Revises: a7c3e9f1b2d4
Create Date: 2026-10-04 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8e2a6f1b3"
down_revision: str | Sequence[str] | None = "a7c3e9f1b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add chats.cover_updated_at. Only added, so the release still serving keeps working; no backfill:
    existing projects get a cover from their next succeeded run that takes a screenshot."""
    op.add_column("chats", sa.Column("cover_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("chats", "cover_updated_at")
