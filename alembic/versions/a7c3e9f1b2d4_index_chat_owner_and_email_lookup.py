"""index chats.user_id and lower(users.email)

Revision ID: a7c3e9f1b2d4
Revises: f1a2b3c4d5e6
Create Date: 2026-10-03 21:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e9f1b2d4"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The sidebar and every preview open filter chats by owner; login, register and verification look
    users up by lower(email), which the plain email index cannot serve. Built concurrently, outside the
    migration's transaction, so the release still serving keeps writing both tables meanwhile.

    The email index is an expression index the ORM cannot express (MIGRATION_OWNED_INDEXES). It is not
    unique: a database may already hold two addresses differing only in case, and register refuses a
    new one through the same lower() lookup.
    """
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_chats_user_id ON chats (user_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email_lower ON users (lower(email))")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_users_email_lower")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_chats_user_id")
