"""drop unused users.email_verification_required

Revision ID: dc1cc61a22ce
Revises: 19d76ecd82e5
Create Date: 2026-09-23 17:49:49.249481

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc1cc61a22ce"
down_revision: str | Sequence[str] | None = "19d76ecd82e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop a column no model declares and no code reads.

    Guarded because the two kinds of database disagree: one created before
    Alembic has the column, one built from the baseline never had it. An
    unguarded drop_column fails on the second.
    """
    if _has_column():
        op.drop_column("users", "email_verification_required")


def downgrade() -> None:
    """Restore it with its original definition: boolean NOT NULL DEFAULT true."""
    if not _has_column():
        op.add_column(
            "users",
            sa.Column(
                "email_verification_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def _has_column() -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(c["name"] == "email_verification_required" for c in inspector.get_columns("users"))
