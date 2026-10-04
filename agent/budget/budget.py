"""Atomic cost admission. Integers are billionths of USD, never binary floats.

One limit: each user's monthly model budget, MONTHLY_BUDGET_USD. Sandbox time is
reserved and settled here too, for accounting, but never counts against it.

Uncertain requests retain their reservation as a conservative charge. Entries
crossing a UTC month reset count in both months; a reset cannot free in-flight money.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    String,
    cast,
    exists,
    extract,
    func,
    insert,
    literal,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from agent.budget.models import SpendEntry
from db.base import AutocommitSessionLocal, bound
from db.models import User
from plans import month_window

from .config import budget_settings

NANOS = 1_000_000_000


class BudgetLimitError(Exception):
    pass


class SpendMissing(ValueError):
    """A settlement for a reservation that does not exist. Raised, not ignored: a missing record must
    never release money. A caller that has confirmed there is nothing left to settle may catch it."""


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


def remaining_in(user, used):
    """What is left of a month's budget, given its spend (month_spend); None when the plan is unlimited."""
    return None if user.unlimited else max(0, _limit() - used)


def allowance(user, used, month):
    """The balance shown to the user, from `month`'s spend (month_spend) read by the caller."""
    limit = _limit()
    remaining = remaining_in(user, used)
    return {
        "unlimited": remaining is None,
        "limit_usd": limit / NANOS,
        "remaining_usd": (limit if remaining is None else remaining) / NANOS,
        "resets_at": month[1].isoformat(),
    }


def has_budget_left(plan, spend):
    """require_left as SQL: the unlimited plan, or a month's spend below the limit."""
    return or_(plan == "unlimited", spend < _limit())


def require_left(user, used, month):
    """Refuse a run when nothing is left of `month`'s budget: an early answer, not the guard. Each
    model call reserves its own bound in reserve(), under the user row lock."""
    if remaining_in(user, used) == 0:
        raise _spent_error(month[1])


def runtime_amount(end):
    """A sandbox lease's cost up to `end`, as SQL over the row being updated: its exact seconds
    (numeric, never below zero) times its nanos_per_second, rounded up to whole nanos."""
    seconds = func.greatest(0, extract("epoch", func.least(end, SpendEntry.ends_at) - SpendEntry.starts_at))
    rate = cast(SpendEntry.details["nanos_per_second"].as_string(), Numeric)
    return cast(func.ceil(seconds * rate), BigInteger)


def merged_details(details):
    """The row's details with `details` laid over them (the column is JSON; || needs JSONB)."""
    return cast(cast(SpendEntry.details, JSONB).op("||")(cast(details, JSONB)), JSON)


async def reserve(user_id, kind, amount, duration, details, run_id=None, replace_id=None):
    """Commit before dispatch, in one round trip; replacement atomically rolls a runtime lease forward."""
    if type(amount) is not int or amount < 0 or not 0 < duration < 86400:
        raise ValueError("Invalid cost reservation bound")
    now = datetime.now(UTC)
    end = now + timedelta(seconds=duration)
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
    if kind == "model":
        # Charge a reservation crossing a month reset to both months. Durations are bounded below
        # one day by callers, so at most two. The lock, the sums and the insert run in one call
        # (reserve_model_spend, alembic f1a2b3c4d5e6).
        windows = [moment for window in sorted({month_window(now), month_window(end)}) for moment in window]
        call = func.reserve_model_spend(
            literal(entry.id, String),
            literal(user_id, Integer),
            literal(run_id, String),
            literal(amount, BigInteger),
            literal(now, DateTime(timezone=True)),
            literal(end, DateTime(timezone=True)),
            literal(details, JSON),
            literal(_limit(), BigInteger),
            literal(windows, ARRAY(DateTime(timezone=True))),
        ).table_valued("outcome", "used", "window_end")
        async with AutocommitSessionLocal() as db:
            outcome, used, finish = (await db.execute(select(call))).one()
        if outcome == "unverified":
            raise BudgetLimitError("Verify your email before using paid build or preview resources.")
        if outcome == "over":
            raise _spent_error(finish, max(0, _limit() - used))
        return entry
    # A sandbox lease never counts against the model budget, so it needs no user lock: one statement
    # settles the lease it replaces (if any) and inserts the new one, only for a verified user.
    verified = exists().where(User.id == user_id, User.email_verified)
    values = bound(
        SpendEntry,
        id=entry.id,
        user_id=user_id,
        run_id=run_id,
        kind=kind,
        state="reserved",
        reserved_nanos=amount,
        amount_nanos=amount,
        starts_at=now,
        ends_at=end,
        details=details,
    )
    source = select(*values.values()).where(verified)
    replaced = None
    if replace_id:
        replaced = (
            update(SpendEntry)
            .where(
                SpendEntry.id == replace_id,
                SpendEntry.user_id == user_id,
                SpendEntry.kind == "sandbox",
                SpendEntry.state == "reserved",
                verified,
            )
            .values(
                amount_nanos=runtime_amount(now),
                state="settled",
                ends_at=func.greatest(SpendEntry.starts_at, func.least(now, SpendEntry.ends_at)),
            )
            .returning(SpendEntry.id)
            .cte("replaced")
        )
        source = source.where(exists(select(replaced.c.id)))
    statement = insert(SpendEntry).from_select(list(values), source).returning(SpendEntry.id)
    if replaced is not None:
        # A data-modifying WITH must head the statement, not the INSERT's SELECT.
        statement = statement.add_cte(replaced, nest_here=True)
    async with AutocommitSessionLocal() as db:
        inserted = await db.scalar(statement)
        if inserted is None:
            # Only when refused: say why, as the transaction's checks did.
            if not await db.scalar(select(verified)):
                raise BudgetLimitError("Verify your email before using paid build or preview resources.")
            raise ValueError("Previous sandbox spend reservation is missing or not a reserved lease of this user")
    return entry


async def settle(entry_id, amount=None, details=None):
    """Idempotent settlement in one statement; absent/ambiguous responses never release money. No user
    lock: reserve_model_spend sums under it with a fresh snapshot, so it sees a settlement committed
    before it and the reserved bound (never less) of one still in flight."""
    now = datetime.now(UTC)
    async with AutocommitSessionLocal() as db:
        settled = await db.scalar(
            update(SpendEntry)
            .where(SpendEntry.id == entry_id, SpendEntry.state == "reserved")
            .values(
                # SET reads the row as it was: the lease is measured to its old end, as before.
                amount_nanos=runtime_amount(now) if amount is None else max(0, amount),
                ends_at=func.greatest(SpendEntry.starts_at, func.least(now, SpendEntry.ends_at)),
                state="settled",
                details=merged_details(details or {}),
            )
            .returning(SpendEntry.id)
        )
        if settled is None and await db.get(SpendEntry, entry_id) is None:
            raise SpendMissing("Spend reservation is missing")
