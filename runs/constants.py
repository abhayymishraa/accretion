"""Run history, event retention and log limits."""

# Reported to callers so a client knows how far back it can ask.
DETAIL_RETENTION_DAYS = 14
EVENT_RETENTION_DAYS = 30

# An idle stream re-checks Postgres; FastAPI pings on the same 15 s, below the 25 s proxy idle bound.
STREAM_IDLE_SECONDS = 15

MAX_RUN_LOG_BYTES = 1024 * 1024
