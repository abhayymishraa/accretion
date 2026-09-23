"""Context window sizing. Compaction is always on; these size it, they do not switch it off."""

from config import BaseConfig

DEFAULT_CONTEXT_WINDOW = 1_050_000
DEFAULT_RESERVE_TOKENS = 400_000


class ContextConfig(BaseConfig):
    MODEL_CONTEXT_WINDOW: int = DEFAULT_CONTEXT_WINDOW
    COMPACTION_RESERVE_TOKENS: int = DEFAULT_RESERVE_TOKENS


context_settings = ContextConfig()
