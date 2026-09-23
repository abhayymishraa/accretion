"""Atomic cost admission. Integers are billionths of USD, never binary floats.

These ceilings are internal circuit breakers against runaway compute, not a
second allowance. Credits (plans.py) are the limit a user sees, and these are
sized so they do not bind before credits do. Reaching one is an incident, so
the messages say so rather than blaming the user's credits.

Uncertain requests retain their reservation as a conservative charge. Entries
crossing a UTC reset count in both windows; a reset cannot free in-flight money.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
import logging
import os
import uuid

from sqlalchemy import func, select

from db.base import AsyncSessionLocal
from db.models import SpendEntry, User
from plans import METERED_PLANS, month_window

logger = logging.getLogger('webbuilder.runs')

NANOS = 1_000_000_000


class BudgetLimitError(Exception):
    pass


def dollar_nanos(name, default):
    value = Decimal(os.getenv(name, default))
    if not value.is_finite() or value < 0:
        raise ValueError(f'{name} must be a finite nonnegative dollar amount')
    return int((value * NANOS).to_integral_value(rounding=ROUND_CEILING))


def windows(now):
    # Shares month_window with the credit reset so the two clocks cannot drift.
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month, next_month = month_window(now)
    return (
        ('daily', day, day + timedelta(days=1), dollar_nanos('FREE_DAILY_COST_USD', '8.00')),
        ('monthly', month, next_month, dollar_nanos('FREE_MONTHLY_COST_USD', '8.00')),
    )


async def used_in_window(db, user_id, start, end, exclude=None):
    query = select(func.coalesce(func.sum(SpendEntry.amount_nanos), 0)).where(
        SpendEntry.user_id == user_id, SpendEntry.starts_at < end, SpendEntry.ends_at >= start)
    if exclude:
        query = query.where(SpendEntry.id != exclude)
    return await db.scalar(query)


async def free_tier_used(db, start, end):
    return await db.scalar(
        select(func.coalesce(func.sum(SpendEntry.amount_nanos), 0))
        .join(User, User.id == SpendEntry.user_id)
        .where(SpendEntry.starts_at < end, SpendEntry.ends_at >= start,
               User.plan.in_(METERED_PLANS)))


async def allowance(db, user, now=None):
    now = now or datetime.now(timezone.utc)
    result = {'unlimited': user.credits_unlimited, 'currency': 'USD', 'reset_timezone': 'UTC'}
    for name, start, end, limit in windows(now):
        used = await used_in_window(db, user.id, start, end)
        result[name] = {'limit_usd': limit / NANOS, 'used_or_reserved_usd': used / NANOS,
                        'remaining_usd': max(0, limit - used) / NANOS, 'resets_at': end.isoformat()}
    return result


async def require_allowance(db, user):
    # Caller holds the user row lock. Actual operations reserve their entire bound.
    if user.credits_unlimited:
        return
    now = datetime.now(timezone.utc)
    # Per-user limits cannot bound total spend; the user count is unbounded. Checked
    # ahead of them so only new work is refused, never a run already in flight. 0 disables.
    budget = dollar_nanos('FREE_TIER_MONTHLY_BUDGET_USD', '50.00')
    if budget:
        month_start, month_end = month_window(now)
        used = float(await free_tier_used(db, month_start, month_end))
        # Warn before the ceiling bites: reaching it refuses every free account at
        # once, so the operator needs a chance to raise it first.
        if used >= budget * 0.8:
            level = logger.error if used >= budget else logger.warning
            level('Free tier at %d%% of its monthly ceiling: %.2f of %.2f USD',
                  used * 100 // budget, used / NANOS, budget / NANOS)
        if used >= budget:
            raise BudgetLimitError(
                'Free capacity for this month is used up across all accounts. This is a '
                'service-wide ceiling, not your credits, and none were spent. It clears at '
                f'{month_end:%Y-%m-%d %H:%M} UTC.')
    for name, start, end, limit in windows(now):
        if await used_in_window(db, user.id, start, end) >= limit:
            raise BudgetLimitError(
                f'A {name} compute safety limit was reached, so new work is paused. This is not '
                f'your credits: none were spent. It clears at {end:%Y-%m-%d %H:%M} UTC, saved '
                'files remain available, and support can raise it.')


def runtime_amount(entry, end):
    seconds = max(0, (min(end, entry.ends_at) - entry.starts_at).total_seconds())
    return int((Decimal(str(seconds)) *
        entry.details['nanos_per_second']).to_integral_value(rounding=ROUND_CEILING))


async def reserve(user_id, kind, amount, duration, details, run_id=None, replace_id=None):
    """Commit before dispatch; replacement atomically rolls a runtime lease forward."""
    if type(amount) is not int or amount < 0 or not 0 < duration < 86400:
        raise ValueError('Invalid cost reservation bound')
    async with AsyncSessionLocal.begin() as db:
        user = await db.get(User, user_id, with_for_update=True)
        if not user or not user.email_verified:
            raise BudgetLimitError('Verify your email before using paid build or preview resources.')
        now = datetime.now(timezone.utc)
        end = now + timedelta(seconds=duration)
        old = await db.get(SpendEntry, replace_id) if replace_id else None
        if replace_id and not old:
            raise ValueError('Previous sandbox spend reservation is missing')
        if old and (old.user_id != user_id or old.kind != 'sandbox' or old.state != 'reserved'):
            raise ValueError('Invalid sandbox spend reservation')
        old_amount = runtime_amount(old, now) if old else 0
        if not user.credits_unlimited:
            # Charge a crossing reservation to every window it can occupy, including
            # tomorrow/next month. Durations are bounded below one day by callers.
            periods = {period for instant in (now, end) for period in windows(instant)}
            for name, start, finish, limit in sorted(periods, key=lambda p: p[1]):
                used = await used_in_window(db, user_id, start, finish, replace_id)
                if old and old.starts_at < finish and min(now, old.ends_at) >= start:
                    used += old_amount
                if used + amount > limit:
                    raise BudgetLimitError(
                        f'A {name} compute safety limit would be exceeded by this operation, so it '
                        'was not started. This is not your credits. Open previews hold compute '
                        f'until they stop. Clears: {finish:%Y-%m-%d %H:%M} UTC. Saved files remain '
                        'available.')
        if old:
            old.amount_nanos, old.state = old_amount, 'settled'
            old.ends_at = max(old.starts_at, min(now, old.ends_at))
        entry = SpendEntry(id=str(uuid.uuid4()), user_id=user_id, run_id=run_id,
            kind=kind, reserved_nanos=amount, amount_nanos=amount, starts_at=now,
            ends_at=end, state='reserved', details=details)
        db.add(entry)
    return entry


async def settle(entry_id, amount=None, details=None):
    """Idempotent settlement; absent/ambiguous responses never release money."""
    async with AsyncSessionLocal.begin() as db:
        entry = await db.get(SpendEntry, entry_id)
        if not entry:
            raise ValueError('Spend reservation is missing')
        await db.get(User, entry.user_id, with_for_update=True)
        await db.refresh(entry)
        if entry.state != 'reserved':
            return
        now = datetime.now(timezone.utc)
        entry.amount_nanos = runtime_amount(entry, now) if amount is None else max(0, amount)
        entry.ends_at = max(entry.starts_at, min(now, entry.ends_at))
        entry.state = 'settled'
        entry.details = {**entry.details, **(details or {})}
