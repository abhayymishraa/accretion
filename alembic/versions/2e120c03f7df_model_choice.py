"""model choice: runs.model_choice and users.default_model_choice

Revision ID: 2e120c03f7df
Revises: dc1cc61a22ce
Create Date: 2026-09-26 14:40:47.084220

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2e120c03f7df"
down_revision: str | Sequence[str] | None = "dc1cc61a22ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (("runs", "model_choice"), ("users", "default_model_choice"))


def upgrade() -> None:
    """Add the user's model choice (spec 4.2). Guarded like dc1cc61a22ce: it alters
    existing tables, and a re-run must not fail on a column already present."""
    for table, column in _COLUMNS:
        if not _has_column(table, column):
            op.add_column(table, sa.Column(column, sa.String(length=128), nullable=False, server_default="auto"))


def downgrade() -> None:
    for table, column in _COLUMNS:
        if _has_column(table, column):
            op.drop_column(table, column)


def _has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))
