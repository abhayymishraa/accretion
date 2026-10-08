"""Failures callers can see when admitting a run, answering a decision or opening a preview."""

from exceptions import (
    Conflict,
    DetailedHTTPException,
    NotFound,
    PermissionDenied,
    ServiceUnavailable,
    TooManyRequests,
    UnprocessableEntity,
)


class UserNotFound(DetailedHTTPException):
    STATUS_CODE = 401
    DETAIL = "User not found"


class ProjectNotFound(NotFound):
    DETAIL = "Project not found"


class NoSavedProject(NotFound):
    DETAIL = "No saved project yet"


class RequestNotFound(NotFound):
    DETAIL = "Request not found"


class EmailNotVerified(PermissionDenied):
    DETAIL = "Verify your email before continuing."


class ProjectRunning(Conflict):
    DETAIL = "This project already has a running request."


class DecisionPending(Conflict):
    DETAIL = "Answer or dismiss the pending question or plan first."


class OperationInProgress(Conflict):
    DETAIL = "Wait for the current operation to finish"


class DecisionAnswered(Conflict):
    DETAIL = "This question or plan has already been answered. Reload the conversation."


class NotAwaitingInput(Conflict):
    DETAIL = "This request is no longer waiting for a response."


class ProposalStale(Conflict):
    DETAIL = "Project files changed after this proposal. Dismiss it and request a new plan."


class ClarificationLimit(Conflict):
    DETAIL = "This request reached its clarification limit. Dismiss it and send a fresh brief."


class InvalidPrompt(UnprocessableEntity):
    DETAIL = "Describe a change in 1–12000 characters"


class UnsupportedAction(UnprocessableEntity):
    DETAIL = "Choose an action supported by this question or plan."


class AnswerRequired(UnprocessableEntity):
    DETAIL = "Enter your answer or requested changes."


class ChangesNotAllowed(UnprocessableEntity):
    DETAIL = "Approval and dismissal cannot include changes. Use Revise plan instead."


class BriefTooLarge(UnprocessableEntity):
    DETAIL = "The accumulated brief is too large. Dismiss it and send a concise new request."


class InvalidHistoryCursor(UnprocessableEntity):
    DETAIL = "Invalid history cursor"


class InvalidHistoryPageSize(UnprocessableEntity):
    DETAIL = "Invalid history page size"


class BuilderBusy(TooManyRequests):
    DETAIL = "The builder is busy. Try again shortly."


class SandboxCapacityReached(TooManyRequests):
    DETAIL = "Live preview capacity reached or cleanup is pending. Try again after a preview closes."


class StorageNotConfigured(ServiceUnavailable):
    DETAIL = "Project storage is not configured."


class PreviewStatusUnavailable(ServiceUnavailable):
    DETAIL = "Preview status temporarily unavailable"
