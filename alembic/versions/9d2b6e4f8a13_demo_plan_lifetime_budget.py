"""demo plan: a model budget that never resets

Revision ID: 9d2b6e4f8a13
Revises: 7c4e1a9b2d58
Create Date: 2026-10-12 04:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d2b6e4f8a13"
down_revision: str | Sequence[str] | None = "7c4e1a9b2d58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# reserve_model_spend (alembic f1a2b3c4d5e6) with one change: a 'demo' account sums its model spend
# over all time, not per month, and an 'over' answer carries no window end (nothing resets). The
# signature is unchanged, so the release still serving calls it as before.
_FUNCTION = """
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
    {checks}
    INSERT INTO spend_entries
        (id, user_id, run_id, kind, state, reserved_nanos, amount_nanos, starts_at, ends_at, details)
    VALUES (p_id, p_user, p_run, 'model', 'reserved', p_amount, p_amount, p_starts, p_ends, p_details);
    RETURN QUERY SELECT 'reserved'::text, 0::bigint, NULL::timestamptz;
END
$$
"""

_MONTHLY = """IF v_plan <> 'unlimited' THEN
        FOR i IN 1 .. coalesce(array_length(p_windows, 1), 0) BY 2 LOOP
            SELECT coalesce(sum(amount_nanos), 0) INTO v_used FROM spend_entries
            WHERE user_id = p_user AND kind = 'model' AND starts_at < p_windows[i + 1] AND ends_at >= p_windows[i];
            IF v_used + p_amount > p_limit THEN
                RETURN QUERY SELECT 'over'::text, v_used, p_windows[i + 1];
                RETURN;
            END IF;
        END LOOP;
    END IF;"""

_LIFETIME = (
    """IF v_plan = 'demo' THEN
        SELECT coalesce(sum(amount_nanos), 0) INTO v_used FROM spend_entries
        WHERE user_id = p_user AND kind = 'model';
        IF v_used + p_amount > p_limit THEN
            RETURN QUERY SELECT 'over'::text, v_used, NULL::timestamptz;
            RETURN;
        END IF;
    ELS"""
    + _MONTHLY
)


def upgrade() -> None:
    """Replace the function body only: no table changes. The function is not ORM metadata."""
    op.execute(_FUNCTION.replace("{checks}", _LIFETIME))


def downgrade() -> None:
    op.execute(_FUNCTION.replace("{checks}", _MONTHLY))
