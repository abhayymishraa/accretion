"""run edits summary

Revision ID: e5f7a9c3b1d4
Revises: 962004e2f0f1
Create Date: 2026-10-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f7a9c3b1d4"
down_revision: str | Sequence[str] | None = "962004e2f0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add runs.edits, then backfill it from run_events.

    The backfill is data, not schema: autogenerate cannot see it. It builds the same summary
    agent/tools/public_tools.edit_summary writes for new runs, in sequence order. The column is
    only added, so the release still serving during the deploy keeps working.
    """
    op.add_column("runs", sa.Column("edits", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.execute(
        """
        UPDATE runs SET edits = summary.edits
        FROM (
            SELECT run_id, jsonb_agg(jsonb_build_object(
                'id', payload->>'call_id',
                'name', payload->>'name',
                'status', CASE WHEN (payload->>'ok')::boolean THEN 'success' ELSE 'error' END,
                'details', CASE WHEN coalesce(json_typeof(payload->'details'->'version'), 'null') = 'null' THEN NULL
                    ELSE jsonb_build_object(
                        'version', payload->'details'->'version',
                        'changed_files', payload->'details'->'changed_files',
                        'diffs', (
                            SELECT jsonb_agg(jsonb_build_object(
                                'path', d->'path', 'created', d->'created', 'added', d->'added',
                                'removed', d->'removed', 'hunks', jsonb_build_array()))
                            FROM json_array_elements(CASE WHEN json_typeof(payload->'details'->'diffs') = 'array'
                                THEN payload->'details'->'diffs' ELSE '[]'::json END) AS d
                        )
                    ) END,
                'output', CASE WHEN payload->'details' IS NULL THEN payload->>'output' END
            ) ORDER BY sequence) AS edits
            FROM run_events
            WHERE payload->>'e' = 'tool_completed'
                AND payload->>'name' IN ('write_files', 'edit_file', 'edit_files')
            GROUP BY run_id
        ) AS summary
        WHERE runs.id = summary.run_id
        """
    )


def downgrade() -> None:
    op.drop_column("runs", "edits")
