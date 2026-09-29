"""Plans and the monthly clock the model budget resets on.

One limit: a per-user monthly model budget in USD (agent/budget). Sandbox time is
recorded but does not count against it.
"""

from datetime import timedelta

DEFAULT_PLAN = "free"


def month_window(now):
    """The UTC calendar month containing `now`, as (start, end)."""
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, (start.replace(day=28) + timedelta(days=4)).replace(day=1)
