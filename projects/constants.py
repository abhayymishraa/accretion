"""Project listing and message paging."""

DEFAULT_MESSAGE_PAGE = 50

# Runs in these states are surfaced as the project's active/pending run.
LIVE_RUN_STATUSES = ("running", "awaiting_input")
