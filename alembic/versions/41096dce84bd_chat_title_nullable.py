"""chats.title nullable: a new project is untitled until its first request is named

Revision ID: 41096dce84bd
Revises: 42b9122a1610
Create Date: 2026-10-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "41096dce84bd"
down_revision: str | Sequence[str] | None = "42b9122a1610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Relaxes a column both kinds of database have, so nothing needs a guard."""
    op.alter_column("chats", "title", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    # Projects still waiting for a name get the placeholder the frontend shows.
    op.execute("UPDATE chats SET title = 'New project' WHERE title IS NULL")
    op.alter_column("chats", "title", existing_type=sa.String(length=255), nullable=False)
