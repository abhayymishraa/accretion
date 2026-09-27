"""Compaction sizing. Always on; the window comes from the run's model (agent/routing/models.toml)."""

from config import BaseConfig

DEFAULT_RESERVE_TOKENS = 400_000


class ContextConfig(BaseConfig):
    COMPACTION_RESERVE_TOKENS: int = DEFAULT_RESERVE_TOKENS


context_settings = ContextConfig()
