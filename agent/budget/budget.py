"""Atomic cost admission. Integers are billionths of USD, never binary floats.

One limit: each user's monthly model budget, MONTHLY_BUDGET_USD. Sandbox time is
reserved and settled here too, for accounting, but never counts against it.

Uncertain requests retain their reservation as a conservative charge. Entries
crossing a UTC month reset count in both months; a reset cannot free in-flight money.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import func, select

from agent.budget.models import SpendEntry
from db.base import AsyncSessionLocal
from db.models import User
from plans import month_window

from .config import budget_settings

NANOS = 1_000_000_000


class BudgetLimitError(Exception):
    pass


class BudgetSpentError(BudgetLimitError):
    """The monthly budget cannot cover the next call: a stopping point, not a fault."""


def dollar_nanos(amount, name):
    """Parse a configured dollar string into integer nanos."""
    value = Decimal(amount)
    if not value.is_finite() or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative dollar amount")
    return int((value * NANOS).to_integral_value(rounding=ROUND_CEILING))


def _limit():
    return dollar_nanos(budget_settings.MONTHLY_BUDGET_USD, "MONTHLY_BUDGET_USD")


def _spent_error(end, left=0):
    # With money left, the next step alone needs more than that; saying "used" would contradict the balance shown.
    spent = (
        f"This step needs more than the ${left / NANOS:.2f} left in this month's build budget."
        if left
        else "You have used this month's build budget."
    )
    return BudgetSpentError(f"{spent} It resets on {end:%-d %B} UTC. Saved projects and previews remain available.")


def month_spend(user_id, start, end):
    """Model spend only: sandbox entries are recorded but not charged to the user. A select, so a
    caller can run it alone or as a column of a larger query."""
    return select(func.coalesce(func.sum(SpendEntry.amount_nanos), 0)).where(
        SpendEntry.user_id == user_id,
        SpendEntry.kind == "model",
        SpendEntry.starts_at < end,
        SpendEntry.ends_at >= start,
    )


async def used_in_month(db, user_id, start, end):
    return await db.scalar(month_spend(user_id, start, end))


async def remaining_nanos(db, user, month=None):
    """What is left of `month`'s budget (default: this one), or None when the plan is unlimited."""
    if user.unlimited:
        return None
    start, end = month or month_window(datetime.now(UTC))
    return max(0, _limit() - await used_in_month(db, user.id, start, end))


def allowance(user, used, month):
    """The balance shown to the user, from `month`'s spend (month_spend) read by the caller."""
    limit = _limit()
    remaining = None if user.unlimited else max(0, limit - used)
    return {
        "unlimited": remaining is None,
        "limit_usd": limit / NANOS,
        "remaining_usd": (limit if remaining is None else remaining) / NANOS,
        "resets_at": month[1].isoformat(),
    }


async def require_allowance(db, user):
    # Caller holds the user row lock. Each model call also reserves its own bound in reserve().
    month = month_window(datetime.now(UTC))
    if await remaining_nanos(db, user, month) == 0:
        raise _spent_error(month[1])


def runtime_amount(entry, end):
    seconds = max(0, (min(end, entry.ends_at) - entry.starts_at).total_seconds())
    return int((Decimal(str(seconds)) * entry.details["nanos_per_second"]).to_integral_value(rounding=ROUND_CEILING))


async def reserve(user_id, kind, amount, duration, details, run_id=None, replace_id=None):
    """Commit before dispatch; replacement atomically rolls a runtime lease forward."""
    if type(amount) is not int or amount < 0 or not 0 < duration < 86400:
        raise ValueError("Invalid cost reservation bound")
    async with AsyncSessionLocal.begin() as db:
        user = await db.get(User, user_id, with_for_update=True)
        if not user or not user.email_verified:
            raise BudgetLimitError("Verify your email before using paid build or preview resources.")
        now = datetime.now(UTC)
        end = now + timedelta(seconds=duration)
        old = await db.get(SpendEntry, replace_id) if replace_id else None
        if replace_id and not old:
            raise ValueError("Previous sandbox spend reservation is missing")
        if old and (old.user_id != user_id or old.kind != "sandbox" or old.state != "reserved"):
            raise ValueError("Invalid sandbox spend reservation")
        old_amount = runtime_amount(old, now) if old else 0
        if kind == "model" and not user.unlimited:
            # Charge a reservation crossing a month reset to both months. Durations are
            # bounded below one day by callers, so at most two.
            for start, finish in sorted({month_window(now), month_window(end)}):
                used = await used_in_month(db, user_id, start, finish)
                if used + amount > _limit():
                    raise _spent_error(finish, max(0, _limit() - used))
        if old:
            old.amount_nanos, old.state = old_amount, "settled"
            old.ends_at = max(old.starts_at, min(now, old.ends_at))
        entry = SpendEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            run_id=run_id,
            kind=kind,
            reserved_nanos=amount,
            amount_nanos=amount,
            starts_at=now,
            ends_at=end,
            state="reserved",
            details=details,
        )
        db.add(entry)
    return entry


async def settle(entry_id, amount=None, details=None):
    """Idempotent settlement; absent/ambiguous responses never release money."""
    async with AsyncSessionLocal.begin() as db:
        entry = await db.get(SpendEntry, entry_id)
        if not entry:
            raise ValueError("Spend reservation is missing")
        await db.get(User, entry.user_id, with_for_update=True)
        await db.refresh(entry)
        if entry.state != "reserved":
            return
        now = datetime.now(UTC)
        entry.amount_nanos = runtime_amount(entry, now) if amount is None else max(0, amount)
        entry.ends_at = max(entry.starts_at, min(now, entry.ends_at))
        entry.state = "settled"
        entry.details = {**entry.details, **(details or {})}
