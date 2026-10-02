"""Project listing and message paging."""

from agent.run.worker import OPEN_STATUSES

DEFAULT_MESSAGE_PAGE = 50

# Runs in these states are surfaced as the project's active/pending run.
LIVE_RUN_STATUSES = (*OPEN_STATUSES, "awaiting_input")
