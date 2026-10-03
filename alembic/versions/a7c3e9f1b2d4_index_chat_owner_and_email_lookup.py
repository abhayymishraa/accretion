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
    # This only reruns after a failed attempt, and a failed concurrent build leaves an invalid index
    # under its name that IF NOT EXISTS would keep: drop whatever is there, then build.
    with op.get_context().autocommit_block():
        for name, definition in (
            ("ix_chats_user_id", "chats (user_id)"),
            ("ix_users_email_lower", "users (lower(email))"),
        ):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
            op.execute(f"CREATE INDEX CONCURRENTLY {name} ON {definition}")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_users_email_lower")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_chats_user_id")
