"""Failures callers can see when connecting Supabase."""

from fastapi import status

from exceptions import BadRequest, Conflict, DetailedHTTPException, NotFound, PermissionDenied, ServiceUnavailable


class SupabaseNotConfigured(ServiceUnavailable):
    DETAIL = "Supabase isn't available here yet."


class SignInExpired(BadRequest):
    DETAIL = "This sign-in expired or was already used. Connect again."


class SignInUnavailable(ServiceUnavailable):
    DETAIL = "Sign-in is unavailable right now. Try again in a moment."


class Reconnect(Conflict):
    DETAIL = "Reconnect Supabase to keep using it."


class SupabaseUnavailable(DetailedHTTPException):
    STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    DETAIL = "Couldn't reach Supabase. Try again in a moment."


class SupabaseRefused(DetailedHTTPException):
    """Supabase answered with an error; its message is the detail."""

    STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    DETAIL = "Supabase refused the request."


class DatabaseNotOffered(BadRequest):
    DETAIL = "This app keeps its data in MongoDB, so it can't use Supabase."


class DatabaseLinked(Conflict):
    DETAIL = "This app already uses a Supabase project. Disconnect it first."


class DatabaseNotLinked(NotFound):
    DETAIL = "This app doesn't use Supabase."


class HookRefused(PermissionDenied):
    STATUS_CODE = status.HTTP_401_UNAUTHORIZED
    DETAIL = "Invalid signature"
