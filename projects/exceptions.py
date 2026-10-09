"""Failures callers can see when acting on a project."""

from exceptions import BadRequest, Conflict, NotFound, PermissionDenied


class ProjectNotFound(NotFound):
    DETAIL = "Project not found"


class CoverNotFound(NotFound):
    DETAIL = "Project has no cover image"


class ChatNotFound(NotFound):
    DETAIL = "Chat not found"


class NotChatOwner(PermissionDenied):
    DETAIL = "Not authorized to access this chat"


class ProjectBusy(Conflict):
    DETAIL = "Stop the active operation before deleting this project"


class SecretNameReserved(BadRequest):
    DETAIL = "Accretion sets this name for the app. Pick another name."


class TooManySecrets(BadRequest):
    DETAIL = "A project holds at most 100 keys. Delete one first."
