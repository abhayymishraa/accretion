"""The monthly budget and the sandbox rates spend is recorded at. Model rates live in agent/routing/models.toml.

Dollar amounts stay strings here and become integer nanos in budget.py; a
binary float must never hold money.
"""

from config import BaseConfig


class BudgetConfig(BaseConfig):
    # Model spend per user per UTC month. Sandbox time does not count.
    MONTHLY_BUDGET_USD: str = "4.00"

    # Recorded sandbox spend. Must cover every template before a release is enabled.
    E2B_COST_MAX_CPU: int = 2
    E2B_COST_MAX_MEMORY_MB: int = 4096
    E2B_CPU_USD_PER_SECOND: str = "0.000014"
    E2B_GIB_USD_PER_SECOND: str = "0.0000045"


budget_settings = BudgetConfig()
