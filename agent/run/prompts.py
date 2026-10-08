"""The system prompt. A product surface: changing it changes every future build.

It lives in prompts.md so no formatter can re-wrap a line and alter what the model reads.
"""

from agent import PACKAGE_ROOT

SYSTEM_PROMPT = (PACKAGE_ROOT / "run" / "prompts.md").read_text()
# Appended in plan mode only: that run has its own tool list, so its prefix is cached apart from builds.
PLANNING_PROMPT = (PACKAGE_ROOT / "run" / "planning.md").read_text()
