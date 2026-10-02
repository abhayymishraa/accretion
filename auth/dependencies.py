from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.exceptions import (
    AdminOnly,
    CredentialsUnverifiable,
    EmailNotVerified,
    MalformedUserId,
    OnWaitlist,
    UserNotFound,
)
from db.base import DbSession, get_db
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


# Signed in, possibly still waitlisted: enough to read and edit one's own account.
SignedInUser = Annotated[User, Depends(get_current_user)]


async def get_approved_user(user: SignedInUser) -> User:
    if user.waitlisted:
        raise OnWaitlist
    return user


# The modern injection form: `user: CurrentUser` instead of a default argument.
CurrentUser = Annotated[User, Depends(get_approved_user)]


async def get_admin_user(user: CurrentUser) -> User:
    if user.role != "admin":
        raise AdminOnly
    return user


AdminUser = Annotated[User, Depends(get_admin_user)]


async def get_current_user_released(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> User:
    """get_current_user for streams: its session closes before the stream starts, instead of
    sitting idle in transaction on a pooled connection for as long as the stream is open."""
    return await get_current_user(credentials, db)


StreamedUser = Annotated[User, Depends(get_current_user_released, scope="function")]


async def client_ip(request: Request) -> str:
    """The caller's address, used to rate-limit verification email requests."""
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]
