"""drop unread columns: runs.events, users.last_query_at

Revision ID: b77019ddb4d6
Revises: a27c6ec1ab67
Create Date: 2026-09-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b77019ddb4d6"
down_revision: str | Sequence[str] | None = "a27c6ec1ab67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Nothing reads these. runs.events was copied into run_events by f362c4be2175 and only ever
# cleared since; users.last_query_at was written but no client reads it.
_COLUMNS = (
    ("runs", "events"),
    ("users", "last_query_at"),
)


def _has(inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    """Guarded: each drop alters an existing table, which may predate the baseline (repo rule)."""
    inspector = sa.inspect(op.get_bind())
    for table, column in _COLUMNS:
        if _has(inspector, table, column):
            op.drop_column(table, column)


def downgrade() -> None:
    """Restores the columns empty; dropped values are not recoverable."""
    inspector = sa.inspect(op.get_bind())
    added = {
        ("runs", "events"): sa.Column("events", sa.JSON(), server_default="[]", nullable=False),
        ("users", "last_query_at"): sa.Column("last_query_at", sa.DateTime(timezone=True), nullable=True),
    }
    for (table, column), definition in added.items():
        if not _has(inspector, table, column):
            op.add_column(table, definition)
