"""Failures callers can see when starting, reading or cancelling a run."""

from exceptions import Gone, NotFound, UnprocessableEntity


class RunNotFound(NotFound):
    DETAIL = "Run not found"


class InvalidHistoryPage(UnprocessableEntity):
    DETAIL = "Invalid history page"


class InvalidEventCursor(UnprocessableEntity):
    DETAIL = "Invalid event cursor"


# One message, two statuses: 410 once an archive existed and was pruned, 404
# while it has never been written.
_LOG_UNAVAILABLE = "Detailed archive expired or is not available yet"


class RunLogUnavailable(NotFound):
    DETAIL = _LOG_UNAVAILABLE


class RunLogExpired(Gone):
    DETAIL = _LOG_UNAVAILABLE
