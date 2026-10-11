"""Failures an app or its owner can see from the app services."""

from fastapi import status

from exceptions import BadRequest, DetailedHTTPException, NotFound, ServiceUnavailable, TooManyRequests


class AppTokenInvalid(DetailedHTTPException):
    STATUS_CODE = status.HTTP_401_UNAUTHORIZED
    DETAIL = "Unknown app key. Rebuild the app to get a new one."


class AppNotFound(NotFound):
    DETAIL = "App not found"


class EmailLimitReached(TooManyRequests):
    DETAIL = "This app has sent today's emails. It can send more tomorrow."


class EmailUnavailable(ServiceUnavailable):
    DETAIL = "Email is not available right now. Try again in a moment."


class EmailFailed(DetailedHTTPException):
    STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    DETAIL = "The email could not be sent."


class RedirectNotAllowed(BadRequest):
    DETAIL = "Sign-in can only return to this app's own address."


class SignInExpired(BadRequest):
    DETAIL = "This sign-in link has expired or was already used. Ask for a new one."


class SignInUnavailable(ServiceUnavailable):
    DETAIL = "Sign-in is not available right now. Try again in a moment."


class GoogleNotOffered(NotFound):
    DETAIL = "Google sign-in is not set up."


class SignInEmailThrottled(TooManyRequests):
    DETAIL = "A sign-in link was just sent to this address. Check your inbox."


class SessionInvalid(DetailedHTTPException):
    STATUS_CODE = status.HTTP_401_UNAUTHORIZED
    DETAIL = "Signed out. Sign in again."
