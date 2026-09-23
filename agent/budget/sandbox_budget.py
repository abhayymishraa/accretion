"""Reserve native E2B timeout leases, then settle confirmed running intervals."""

from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import select

from agent.budget.models import SpendEntry
from db.base import AsyncSessionLocal
from db.models import Chat, User

from .budget import BudgetLimitError, dollar_nanos, reserve, runtime_amount, settle
from .config import budget_settings


def sandbox_rate(cpu, memory_mb):
    cpu_rate = dollar_nanos(budget_settings.E2B_CPU_USD_PER_SECOND, "E2B_CPU_USD_PER_SECOND")
    ram_rate = dollar_nanos(budget_settings.E2B_GIB_USD_PER_SECOND, "E2B_GIB_USD_PER_SECOND")
    if cpu_rate <= 0 or ram_rate <= 0 or cpu <= 0 or memory_mb <= 0:
        raise ValueError("E2B cost rates and resources must be positive")
    return int(
        (Decimal(cpu) * cpu_rate + Decimal(memory_mb) / 1024 * ram_rate).to_integral_value(rounding=ROUND_CEILING)
    )


async def reserve_runtime(chat_id, timeout, previous=None, info=None):  # noqa: ASYNC109
    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(Chat.user_id).where(Chat.id == chat_id))
        if user_id is None:
            raise BudgetLimitError("Project is unavailable for preview spending.")
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
    duration = max(timeout, int(remaining) + 1) + 60
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
    async with AsyncSessionLocal.begin() as db:
        entry = await db.get(SpendEntry, spend_id)
        rate = sandbox_rate(info.cpu_count, info.memory_mb)
        if not entry:
            raise BudgetLimitError("Preview spend reservation is missing; contact support.")
        await db.get(User, entry.user_id, with_for_update=True)
        await db.refresh(entry)
        if entry.state != "reserved":
            raise BudgetLimitError("Preview spend reservation was already closed; contact support.")
        exceeded = rate > entry.details["nanos_per_second"] or info.end_at > entry.ends_at
        # Replace the pessimistic resource ceiling with a full native-timeout hold
        # at the confirmed rate. Other operations can use the difference immediately.
        entry.details = {
            **entry.details,
            "nanos_per_second": rate,
            "cpu_count": info.cpu_count,
            "memory_mb": info.memory_mb,
        }
        entry.ends_at = max(entry.starts_at, info.end_at)
        entry.amount_nanos = runtime_amount(entry, entry.ends_at)
    if exceeded:
        raise BudgetLimitError("Preview resource usage exceeded its reservation; contact support.")


async def settle_runtime(spend_id, rejected=False):
    if spend_id:
        await settle(spend_id, 0 if rejected else None)
