"""Run-loop ceilings. The model client lives in agent/routing.

The ceilings are runaway backstops, not work limits: compaction keeps a long
run affordable, so a low turn count would end healthy work early. There is no
clock on a run, as Codex has none on a turn (openai/codex@444da31): each
command has its own timeout, and the monthly budget bounds spend.
"""

from config import BaseConfig


class RunConfig(BaseConfig):
    RUN_MAX_TURNS: int = 500
    RUN_MAX_TOOL_CALLS: int = 1000

    # The same everywhere: E2B's own ceiling (Hobby: 20 running sandboxes; paused ones do not
    # count) is the real limit, kept 2 below it so a sandbox whose cleanup is pending never
    # turns a new request away.
    MAX_CONCURRENT_RUNS: int = 18
    MAX_LIVE_SANDBOXES: int = 18


run_settings = RunConfig()
