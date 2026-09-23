"""Base HTTP exceptions.

A domain raises a named exception rather than an `HTTPException` with a literal
status and message, so the status and wording for one failure live in exactly
one place. Domain subclasses live in `<domain>/exceptions.py`.
"""

from fastapi import HTTPException, status


class DetailedHTTPException(HTTPException):
    STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR
    DETAIL = "Server error"

    def __init__(self, detail: str | None = None, **kwargs) -> None:
        super().__init__(status_code=self.STATUS_CODE, detail=detail or self.DETAIL, **kwargs)


class BadRequest(DetailedHTTPException):
    STATUS_CODE = status.HTTP_400_BAD_REQUEST
    DETAIL = "Bad request"


class PermissionDenied(DetailedHTTPException):
    STATUS_CODE = status.HTTP_403_FORBIDDEN
    DETAIL = "Permission denied"


class NotFound(DetailedHTTPException):
    STATUS_CODE = status.HTTP_404_NOT_FOUND
    DETAIL = "Not found"


class Conflict(DetailedHTTPException):
    STATUS_CODE = status.HTTP_409_CONFLICT
    DETAIL = "Conflict"


class Gone(DetailedHTTPException):
    STATUS_CODE = status.HTTP_410_GONE
    DETAIL = "No longer available"


class UnprocessableEntity(DetailedHTTPException):
    STATUS_CODE = status.HTTP_422_UNPROCESSABLE_ENTITY
    DETAIL = "Unprocessable request"


class TooManyRequests(DetailedHTTPException):
    STATUS_CODE = status.HTTP_429_TOO_MANY_REQUESTS
    DETAIL = "Too many requests"


class ServiceUnavailable(DetailedHTTPException):
    STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE
    DETAIL = "Service unavailable"
