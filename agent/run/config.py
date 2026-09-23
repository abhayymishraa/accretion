"""Model client and run-loop ceilings.

The ceilings are runaway backstops, not work limits: compaction keeps a long
run affordable, so a low turn count would end healthy work early.
"""

from config import BaseConfig


class RunConfig(BaseConfig):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.6-luna"

    RUN_MAX_TURNS: int = 500
    RUN_MAX_TOOL_CALLS: int = 1000
    RUN_MAX_TOKENS: int = 1_000_000
    RUN_TIMEOUT_SECONDS: int = 600

    MAX_CONCURRENT_RUNS: int = 2
    MAX_LIVE_SANDBOXES: int = 2


run_settings = RunConfig()
