"""Failures callers can see when publishing to Vercel."""

from fastapi import status

from exceptions import BadRequest, Conflict, DetailedHTTPException, ServiceUnavailable


class VercelNotConfigured(ServiceUnavailable):
    DETAIL = "Publishing isn't available here yet."


class SignInExpired(BadRequest):
    DETAIL = "This connection expired or was already used. Connect again."


class SignInUnavailable(ServiceUnavailable):
    DETAIL = "Connecting is unavailable right now. Try again in a moment."


class Reconnect(Conflict):
    DETAIL = "Connect Vercel again to keep publishing."


class VercelUnavailable(DetailedHTTPException):
    STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    DETAIL = "Couldn't reach Vercel. Try again in a moment."


class VercelRefused(DetailedHTTPException):
    """Vercel answered with an error; its message is the detail, its status is kept for callers."""

    STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    DETAIL = "Vercel refused the request."

    def __init__(self, detail: str | None = None, *, vercel_status: int = 0) -> None:
        super().__init__(detail)
        self.vercel_status = vercel_status


class NothingToPublish(BadRequest):
    DETAIL = "Build your app before you publish it."


class PublishRunning(Conflict):
    DETAIL = "This app is already publishing."


class NotConnected(Conflict):
    DETAIL = "Connect your Vercel account first."
