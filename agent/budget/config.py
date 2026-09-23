"""Cost ceilings and the provider rates they are computed from.

Dollar amounts stay strings here and become integer nanos in budget.py; a
binary float must never hold money.
"""

from config import BaseConfig


class BudgetConfig(BaseConfig):
    COST_MODEL: str = "gpt-5.6-luna"

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

    # Keep this rate set matched to the model above; USD per million tokens.
    MODEL_INPUT_USD_PER_MILLION: str = "0.20"
    MODEL_CACHED_INPUT_USD_PER_MILLION: str = "0.02"
    MODEL_CACHE_WRITE_USD_PER_MILLION: str = "0.25"
    MODEL_OUTPUT_USD_PER_MILLION: str = "1.20"


budget_settings = BudgetConfig()
