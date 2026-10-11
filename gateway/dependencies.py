"""The app a request comes from, by its app token."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from gateway.env import token_app
from gateway.exceptions import AppTokenInvalid

_bearer = HTTPBearer(auto_error=False)


async def app_of(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    found = await token_app(credentials.credentials) if credentials else None
    if found is None:
        raise AppTokenInvalid
    return found


AppOf = Annotated[str, Depends(app_of)]
