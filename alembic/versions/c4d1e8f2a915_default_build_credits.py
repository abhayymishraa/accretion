"""default build credits: users.tokens_remaining gets a server default

Revision ID: c4d1e8f2a915
Revises: b77019ddb4d6
Create Date: 2026-09-29

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d1e8f2a915"
down_revision: str | Sequence[str] | None = "b77019ddb4d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The monthly model budget replaced build credits and the ORM no longer maps
# users.tokens_remaining or users.tokens_reset_at. They stay one release so a failed
# deploy can roll back to code that still reads them: deploy.sh restarts the previous
# release without a downgrade. tokens_remaining is NOT NULL with no default, so the
# new code's inserts need one. d8a3f6b1c207 drops both columns.


def _has(inspector, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns("users"))


def upgrade() -> None:
    """Guarded: alters an existing table, which may predate the baseline (repo rule)."""
    if _has(sa.inspect(op.get_bind()), "tokens_remaining"):
        op.alter_column("users", "tokens_remaining", server_default="15")


def downgrade() -> None:
    if _has(sa.inspect(op.get_bind()), "tokens_remaining"):
        op.alter_column("users", "tokens_remaining", server_default=None)
