"""Reserve native E2B timeout leases, then settle confirmed running intervals."""

from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import BigInteger, DateTime, cast, extract, func, literal, select, update

from agent.budget.models import SpendEntry
from db.base import AutocommitSessionLocal

from .budget import BudgetLimitError, dollar_nanos, merged_details, reserve, settle
from .config import budget_settings


def sandbox_rate(cpu, memory_mb):
    cpu_rate = dollar_nanos(budget_settings.E2B_CPU_USD_PER_SECOND, "E2B_CPU_USD_PER_SECOND")
    ram_rate = dollar_nanos(budget_settings.E2B_GIB_USD_PER_SECOND, "E2B_GIB_USD_PER_SECOND")
    if cpu_rate <= 0 or ram_rate <= 0 or cpu <= 0 or memory_mb <= 0:
        raise ValueError("E2B cost rates and resources must be positive")
    return int(
        (Decimal(cpu) * cpu_rate + Decimal(memory_mb) / 1024 * ram_rate).to_integral_value(rounding=ROUND_CEILING)
    )


async def reserve_runtime(lease_seconds, previous=None, info=None, *, user_id):
    """Reserve a lease against the project's owner, whom every caller has already read."""
    # This configured resource ceiling must cover every permitted starter/revision.
    # Provider-reported sizes validate it on existing and newly created runtimes.
    cpu = budget_settings.E2B_COST_MAX_CPU
    memory = budget_settings.E2B_COST_MAX_MEMORY_MB
    if cpu < 1 or memory < 128:
        raise ValueError("E2B cost resource ceiling is invalid")
    rate = sandbox_rate(cpu, memory)
    if info:
        actual = sandbox_rate(info.cpu_count, info.memory_mb)
        if actual > rate:
            raise BudgetLimitError("This preview exceeds the configured compute allowance. Contact support.")
        rate = actual
    # Native connect only extends a running deadline. Cover existing longer leases.
    remaining = (
        max(0, (info.end_at - datetime.now(UTC)).total_seconds()) if info and info.state.value == "running" else 0
    )
    duration = max(lease_seconds, int(remaining) + 1) + 60
    if duration >= 86400:
        raise BudgetLimitError("Preview timeout exceeds the supported spending window.")
    return await reserve(
        user_id,
        "sandbox",
        rate * duration,
        duration,
        {
            "nanos_per_second": rate,
            "resource_ceiling_cpu": cpu,
            "resource_ceiling_memory_mb": memory,
        },
        replace_id=previous,
    )


async def confirm_runtime(spend_id, info):
    rate = sandbox_rate(info.cpu_count, info.memory_mb)
    # One statement: replace the pessimistic resource ceiling with a full native-timeout hold at the
    # confirmed rate, returning the lease's previous rate and end to check against. A sandbox lease
    # never counts against the model budget, so it needs no user lock.
    previous = (
        select(
            SpendEntry.id,
            SpendEntry.details["nanos_per_second"].as_integer().label("rate"),
            SpendEntry.ends_at.label("ends_at"),
        )
        .where(SpendEntry.id == spend_id)
        .subquery()
    )
    end = literal(info.end_at, DateTime(timezone=True))
    seconds = func.greatest(0, extract("epoch", end - SpendEntry.starts_at))
    async with AutocommitSessionLocal() as db:
        row = (
            await db.execute(
                update(SpendEntry)
                .where(SpendEntry.id == previous.c.id, SpendEntry.state == "reserved")
                .values(
                    details=merged_details(
                        {"nanos_per_second": rate, "cpu_count": info.cpu_count, "memory_mb": info.memory_mb}
                    ),
                    ends_at=func.greatest(SpendEntry.starts_at, end),
                    amount_nanos=cast(func.ceil(seconds * rate), BigInteger),
                )
                .returning(previous.c.rate, previous.c.ends_at)
            )
        ).first()
        if row is None:
            if await db.get(SpendEntry, spend_id) is None:
                raise BudgetLimitError("Preview spend reservation is missing; contact support.")
            raise BudgetLimitError("Preview spend reservation was already closed; contact support.")
    if rate > row.rate or info.end_at > row.ends_at:
        raise BudgetLimitError("Preview resource usage exceeded its reservation; contact support.")


async def settle_runtime(spend_id, rejected=False):
    if spend_id:
        await settle(spend_id, 0 if rejected else None)
