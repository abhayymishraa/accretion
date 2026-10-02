"""users waitlist and role

Revision ID: 962004e2f0f1
Revises: 0a9ff048c441
Create Date: 2026-10-02 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from auth.config import auth_settings

# revision identifiers, used by Alembic.
revision: str = "962004e2f0f1"
down_revision: str | Sequence[str] | None = "0a9ff048c441"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the waitlist and role columns, then backfill existing accounts.

    The backfill is data, not schema: autogenerate cannot see it. Verified
    accounts from before the waitlist keep their access; unverified ones join it.
    """
    op.add_column("users", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(length=16), server_default="user", nullable=False))
    op.execute("UPDATE users SET approved_at = created_at WHERE email_verified")
    op.get_bind().execute(
        sa.text(
            "UPDATE users SET role = 'admin', approved_at = COALESCE(approved_at, now()) WHERE lower(email) = :email"
        ),
        {"email": auth_settings.ADMIN_EMAIL.lower()},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "role")
    op.drop_column("users", "approved_at")
