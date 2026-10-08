"""Failures callers can see when connecting MCP servers."""

from fastapi import status

from exceptions import BadRequest, Conflict, DetailedHTTPException, NotFound, ServiceUnavailable


class ServerNotFound(NotFound):
    DETAIL = "Connection not found"


class ServerNameTaken(Conflict):
    DETAIL = "You already have a connection with this name"


class ServerNameReserved(Conflict):
    DETAIL = "This name is kept for Accretion's own connections"


class ServerAddressInvalid(BadRequest):
    DETAIL = "Use an https:// address for the server"


class ServerUnavailable(DetailedHTTPException):
    STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    DETAIL = "The server did not answer. Try again in a moment."


class IconInvalid(BadRequest):
    DETAIL = "Use a PNG, JPEG, WebP, GIF, SVG or ICO image of 32 KB or less"


class KeyNotAccepted(BadRequest):
    DETAIL = "This server signs in with its own page, not a key."


class SignInFixed(BadRequest):
    DETAIL = "This service signs in the way its catalog entry says."


class SignInNotOffered(BadRequest):
    DETAIL = "This server does not sign in with its own page."


class SignInExpired(BadRequest):
    DETAIL = "This sign-in expired or was already used. Connect again."


class SignInUnavailable(ServiceUnavailable):
    DETAIL = "Sign-in is unavailable right now. Try again in a moment."
