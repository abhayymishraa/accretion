"""one open run per project, model spend reservation in one call

Revision ID: f1a2b3c4d5e6
Revises: e5f7a9c3b1d4
Create Date: 2026-10-03 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e5f7a9c3b1d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Locks the user, checks each month the reservation touches, inserts the entry: what
# agent/budget/budget.py reserve() did for a model call in a transaction of five round trips, in
# one. Each statement of a VOLATILE function takes a fresh snapshot, so the sums are read after the
# lock and see every reservation committed before it, as the separate statements did.
RESERVE_MODEL_SPEND = """
CREATE OR REPLACE FUNCTION reserve_model_spend(
    p_id varchar, p_user integer, p_run varchar, p_amount bigint, p_starts timestamptz,
    p_ends timestamptz, p_details json, p_limit bigint, p_windows timestamptz[]
) RETURNS TABLE (outcome text, used bigint, window_end timestamptz)
LANGUAGE plpgsql VOLATILE AS $$
DECLARE
    v_verified boolean;
    v_plan varchar;
    v_used bigint;
BEGIN
    SELECT email_verified, plan INTO v_verified, v_plan FROM users WHERE id = p_user FOR UPDATE;
    IF NOT FOUND OR NOT v_verified THEN
        RETURN QUERY SELECT 'unverified'::text, 0::bigint, NULL::timestamptz;
        RETURN;
    END IF;
    IF v_plan <> 'unlimited' THEN
        FOR i IN 1 .. coalesce(array_length(p_windows, 1), 0) BY 2 LOOP
            SELECT coalesce(sum(amount_nanos), 0) INTO v_used FROM spend_entries
            WHERE user_id = p_user AND kind = 'model' AND starts_at < p_windows[i + 1] AND ends_at >= p_windows[i];
            IF v_used + p_amount > p_limit THEN
                RETURN QUERY SELECT 'over'::text, v_used, p_windows[i + 1];
                RETURN;
            END IF;
        END LOOP;
    END IF;
    INSERT INTO spend_entries
        (id, user_id, run_id, kind, state, reserved_nanos, amount_nanos, starts_at, ends_at, details)
    VALUES (p_id, p_user, p_run, 'model', 'reserved', p_amount, p_amount, p_starts, p_ends, p_details);
    RETURN QUERY SELECT 'reserved'::text, 0::bigint, NULL::timestamptz;
END
$$
"""


def upgrade() -> None:
    """Add the one-open-run index and the reserve_model_spend function.

    Both are additions the release still serving keeps working with. The index build fails, and the
    deploy with it while the old release keeps serving, only if a project already has two queued or
    running runs, which admission has always refused. The function is not ORM metadata, so
    autogenerate neither sees nor drops it.
    """
    op.create_index(
        "uq_runs_one_open_per_chat",
        "runs",
        ["chat_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.execute(RESERVE_MODEL_SPEND)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS reserve_model_spend")
    op.drop_index("uq_runs_one_open_per_chat", table_name="runs")
