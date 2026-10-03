from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from auth.exceptions import (
    AdminOnly,
    CredentialsUnverifiable,
    EmailNotVerified,
    OnWaitlist,
    UserNotFound,
)
from auth.schemas import TokenUser
from db.base import DbSession, ReadSessionLocal
from db.models import User
from request_timing import timed

from .utils import decode_token

security = HTTPBearer()


@timed("auth")
async def get_token_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> TokenUser:
    """The caller from their access token alone: no database query on the request path."""
    payload = decode_token(token=credentials.credentials)
    if payload is None:
        raise CredentialsUnverifiable
    try:
        return TokenUser(id=int(payload["sub"]), role=payload["role"], approved=payload["approved"])
    except (KeyError, TypeError, ValueError):
        # Also an access token issued before tokens carried role and approval: the client renews it.
        raise CredentialsUnverifiable from None


async def get_current_user(user: Annotated[TokenUser, Depends(get_token_user)], db: DbSession) -> User:
    """The caller's row, for routes that read or change the account itself."""
    row = await db.get(User, user.id)
    if row is None:
        raise UserNotFound
    if not row.email_verified:
        raise EmailNotVerified
    return row


# Signed in, possibly still waitlisted: enough to read and edit one's own account.
SignedInUser = Annotated[User, Depends(get_current_user)]


async def get_approved_user(user: Annotated[TokenUser, Depends(get_token_user)]) -> TokenUser:
    if not user.approved:
        # Approved since this token was issued: let it in until it renews carrying the approval.
        async with ReadSessionLocal() as db:
            approved = await db.scalar(select(User.approved_at.is_not(None)).where(User.id == user.id))
        if not approved:
            raise OnWaitlist
    return user


# The modern injection form: `user: CurrentUser` instead of a default argument.
CurrentUser = Annotated[TokenUser, Depends(get_approved_user)]


async def get_admin_user(user: CurrentUser) -> TokenUser:
    if user.role != "admin":
        raise AdminOnly
    return user


AdminUser = Annotated[TokenUser, Depends(get_admin_user)]


async def client_ip(request: Request) -> str:
    """The caller's address, used to rate-limit verification email requests."""
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]
