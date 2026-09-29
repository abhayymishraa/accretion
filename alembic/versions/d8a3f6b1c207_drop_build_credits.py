"""drop build credits: users.tokens_remaining, users.tokens_reset_at

Revision ID: d8a3f6b1c207
Revises: c4d1e8f2a915
Create Date: 2026-09-29

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8a3f6b1c207"
down_revision: str | Sequence[str] | None = "c4d1e8f2a915"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# c4d1e8f2a915 shipped code that no longer reads these, so a rollback from here lands
# on a release that does not need them.
_COLUMNS = ("tokens_remaining", "tokens_reset_at")


def _has(inspector, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns("users"))


def upgrade() -> None:
    """Guarded: each drop alters an existing table, which may predate the baseline (repo rule)."""
    inspector = sa.inspect(op.get_bind())
    for column in _COLUMNS:
        if _has(inspector, column):
            op.drop_column("users", column)


def downgrade() -> None:
    """Restores the columns as c4d1e8f2a915 left them; spent credits are not recoverable."""
    inspector = sa.inspect(op.get_bind())
    added = {
        "tokens_remaining": sa.Column("tokens_remaining", sa.Integer(), server_default="15", nullable=False),
        "tokens_reset_at": sa.Column("tokens_reset_at", sa.DateTime(timezone=True), nullable=True),
    }
    for column, definition in added.items():
        if not _has(inspector, column):
            op.add_column("users", definition)
