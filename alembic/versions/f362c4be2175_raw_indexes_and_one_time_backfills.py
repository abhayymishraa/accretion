"""raw indexes and one-time backfills

Revision ID: f362c4be2175
Revises: 937a780e272e
Create Date: 2026-09-23 14:32:27.557551

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f362c4be2175"
down_revision: str | Sequence[str] | None = "937a780e272e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Objects and backfills that `create_all` could not express.

    These ran on every start in the old `db/migrate.py`. Each is written to be
    safe on a database that already has them, because production does.
    """
    # A partial GIN index: not expressible as an ORM Index, so autogenerate
    # cannot see it and a metadata-only baseline would silently drop it.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_messages_context_search ON messages"
        " USING gin (to_tsvector('simple', content))"
        " WHERE role IN ('user', 'assistant')"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_context_order ON messages (chat_id, created_at, id)")

    # One-time backfills. On a fresh database these match no rows; on the
    # deployed one they already ran, and every statement is idempotent.
    op.execute(
        "UPDATE users SET tokens_reset_at = NULL WHERE tokens_reset_at IS NOT NULL"
        " AND tokens_reset_at <> date_trunc('month', tokens_reset_at)"
    )
    op.execute(
        """
        INSERT INTO run_events (run_id, sequence, payload, created_at)
        SELECT r.id, e.ordinality, e.value, r.created_at
        FROM runs r, json_array_elements(CASE WHEN json_typeof(r.events) = 'array'
            THEN r.events ELSE '[]'::json END) WITH ORDINALITY e(value, ordinality)
        WHERE r.log_sha256 IS NULL
        ON CONFLICT (run_id, sequence) DO NOTHING
        """
    )
    # Superseded by the chat transcript, which keeps those messages verbatim.
    op.execute("DROP TABLE IF EXISTS project_memory")


def downgrade() -> None:
    """Drop only what this revision created. The backfills are not reversible."""
    op.execute("DROP INDEX IF EXISTS ix_messages_context_order")
    op.execute("DROP INDEX IF EXISTS ix_messages_context_search")
