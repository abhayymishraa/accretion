"""project user secrets: project_secrets.user_ciphertext

Revision ID: 3b7d2e9a4c61
Revises: 0809b33a1694
Create Date: 2026-10-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b7d2e9a4c61"
down_revision: str | Sequence[str] | None = "0809b33a1694"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The user's own keys, in their own column so the release still serving reads its kit values unchanged."""
    op.add_column("project_secrets", sa.Column("user_ciphertext", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_secrets", "user_ciphertext")
