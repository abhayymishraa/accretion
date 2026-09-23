"""Failures callers can see when reading saved project files."""

from exceptions import NotFound, UnprocessableEntity


class InvalidProjectPath(UnprocessableEntity):
    DETAIL = "Invalid project path"


class FileNotInRevision(NotFound):
    DETAIL = "File not found in saved revision"


class NoSavedRevision(NotFound):
    DETAIL = "No saved revision available"
