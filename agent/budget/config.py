"""Cost ceilings and the sandbox rates they are computed from. Model rates live in agent/routing/models.toml.

Dollar amounts stay strings here and become integer nanos in budget.py; a
binary float must never hold money.
"""

from config import BaseConfig


class BudgetConfig(BaseConfig):
    # Per-user circuit breakers, not an allowance. Credits bind first.
    FREE_DAILY_COST_USD: str = "8.00"
    FREE_MONTHLY_COST_USD: str = "8.00"
    # Total across every metered account. 0 disables the ceiling.
    FREE_TIER_MONTHLY_BUDGET_USD: str = "50.00"

    # Must cover every template before a release is enabled.
    E2B_COST_MAX_CPU: int = 2
    E2B_COST_MAX_MEMORY_MB: int = 4096
    E2B_CPU_USD_PER_SECOND: str = "0.000014"
    E2B_GIB_USD_PER_SECOND: str = "0.0000045"


budget_settings = BudgetConfig()
