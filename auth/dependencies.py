from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from auth.exceptions import (
    CredentialsUnverifiable,
    EmailNotVerified,
    MalformedUserId,
    UserNotFound,
)
from db.base import DbSession
from db.models import User
from request_timing import timed

from .utils import decode_token

security = HTTPBearer()


@timed("auth")
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: DbSession,
) -> User:
    """Get the current authenticated user from the token"""

    token = credentials.credentials
    payload = decode_token(token=token)

    if payload is None:
        raise CredentialsUnverifiable

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise CredentialsUnverifiable

    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        raise MalformedUserId from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFound

    if not user.email_verified:
        raise EmailNotVerified

    return user


# The modern injection form: `user: CurrentUser` instead of a default argument.
CurrentUser = Annotated[User, Depends(get_current_user)]


async def client_ip(request: Request) -> str:
    """The caller's address, used to rate-limit verification email requests."""
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]
