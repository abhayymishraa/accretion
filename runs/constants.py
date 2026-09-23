"""Run history, event retention and socket timing."""

# Reported to callers so a client knows how far back it can ask.
DETAIL_RETENTION_DAYS = 14
EVENT_RETENTION_DAYS = 30

MAX_RUNS_PAGE = 50

# Socket. The heartbeat is shorter than any proxy idle timeout in front of us.
AUTH_FRAME_TIMEOUT_SECONDS = 10
EVENT_QUEUE_SIZE = 64
HEARTBEAT_SECONDS = 25
SNAPSHOT_MESSAGE_LIMIT = 200
CLOSE_POLICY_VIOLATION = 1008

MAX_RUN_LOG_BYTES = 1024 * 1024
