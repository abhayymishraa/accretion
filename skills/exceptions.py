"""Failures callers can see when managing skills."""

from fastapi import status

from exceptions import BadRequest, Conflict, DetailedHTTPException, NotFound


class SkillNotFound(NotFound):
    DETAIL = "Skill not found"


class SkillNameTaken(Conflict):
    DETAIL = "You already have a skill with this name"


class BuiltinSkillName(Conflict):
    DETAIL = "A built-in skill already uses this name"


class SkillRequired(BadRequest):
    DETAIL = "This skill is part of Accretion and stays on in every project"


class SkillImportInvalid(BadRequest):
    DETAIL = "This file is not a skill"


class SkillImportTooLarge(DetailedHTTPException):
    STATUS_CODE = status.HTTP_413_CONTENT_TOO_LARGE
    DETAIL = "This file is too large to import"


class GitHubUnavailable(DetailedHTTPException):
    STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    DETAIL = "Could not read that repository from GitHub. Try again in a moment."
