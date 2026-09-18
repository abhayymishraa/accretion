"""Plans and the single monthly clock that credits and cost windows both reset on.

One user-facing number: credits. The USD ceilings in agent/budget.py are internal
circuit breakers sized so they never bind before credits do; they are not a
second allowance and are not shown in the product.
"""
from datetime import timedelta

DEFAULT_PLAN = 'free'

# credits=None means uncounted. Add paid tiers here; nothing else needs to change.
PLANS = {
    'free': {'credits': 15},
    'unlimited': {'credits': None},
}


# Accounts the service-wide free ceiling applies to. Uncounted plans are exempt:
# the ceiling exists to bound give-away spend, not to throttle the owner.
METERED_PLANS = tuple(name for name, plan in PLANS.items() if plan['credits'] is not None)


def plan_credits(name):
    """Monthly credit grant for a plan, or None when the plan is uncounted."""
    return PLANS.get(name or DEFAULT_PLAN, PLANS[DEFAULT_PLAN])['credits']


def month_window(now):
    """The UTC calendar month containing `now`, as (start, end).

    Credits and the cost ceilings both derive their reset from this, so the
    'resets at' shown to a user can never drift between the two.
    """
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, (start.replace(day=28) + timedelta(days=4)).replace(day=1)
