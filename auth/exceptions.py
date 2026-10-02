"""Failures a caller can see while registering, signing in or verifying email.

Several are raised from more than one module; defining them once keeps the
status and the wording from drifting apart between call sites.
"""

from exceptions import (
    BadRequest,
    Conflict,
    DetailedHTTPException,
    NotFound,
    PermissionDenied,
    ServiceUnavailable,
    TooManyRequests,
    UnprocessableEntity,
)


class NotAuthenticated(DetailedHTTPException):
    STATUS_CODE = 401
    DETAIL = "Not authenticated"


class InvalidRequest(NotAuthenticated):
    DETAIL = "Invalid request"


class CredentialsUnverifiable(NotAuthenticated):
    DETAIL = "could not validate credentials"


class MalformedUserId(NotAuthenticated):
    DETAIL = "Invalid user ID format"


class InvalidCredentials(NotAuthenticated):
    DETAIL = "Incorrect email or password."


class InvalidRefreshToken(NotAuthenticated):
    DETAIL = "Invalid refresh token."


class InvalidTokenPayload(NotAuthenticated):
    DETAIL = "Invalid token payload."


class UserNotFound(NotAuthenticated):
    DETAIL = "User not found."


class EmailNotVerified(PermissionDenied):
    DETAIL = "Verify your email before continuing."


class OnWaitlist(PermissionDenied):
    DETAIL = "You're on the waitlist. We'll email you when your access is ready."


class AdminOnly(PermissionDenied):
    DETAIL = "Only an admin can do this."


class ApplicantNotFound(NotFound):
    DETAIL = "No account with that ID."


class EmailNotVerifiedForSignIn(PermissionDenied):
    DETAIL = "Verify your email before signing in."


class EmailTaken(BadRequest):
    DETAIL = "Email already registered. Sign in or request a verification email."


class EmailTakenConflict(Conflict):
    DETAIL = "Email already registered."


class AccountUnavailable(BadRequest):
    DETAIL = "This account is no longer available."


class DisposableEmail(UnprocessableEntity):
    DETAIL = "Disposable email addresses are not accepted. Use a permanent address."


class NameRequired(UnprocessableEntity):
    DETAIL = "Enter your name."


class VerificationLinkUsed(BadRequest):
    DETAIL = "This link has expired or was already used. Request a new one."


class VerificationNotConfigured(ServiceUnavailable):
    DETAIL = "Email verification is not configured yet. Please try again later."


class VerificationEmailFailed(ServiceUnavailable):
    DETAIL = "We could not send the email. Please try again later."


class VerificationThrottled(TooManyRequests):
    DETAIL = "Too many requests. Please wait 15 minutes before trying again."


class ProviderNotConfigured(ServiceUnavailable):
    DETAIL = "This sign-in provider is not configured yet."
