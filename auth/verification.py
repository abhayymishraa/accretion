"""Single-use email proofs and short-lived OAuth handoffs; never store raw tokens."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from redis import RedisError
from sqlalchemy import ColumnElement, Insert, delete, insert, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent.run import bus
from auth import emails
from auth.config import auth_settings
from auth.exceptions import (
    VerificationEmailFailed,
    VerificationLinkUsed,
    VerificationThrottled,
)
from auth.models import AuthToken
from config import settings
from db.base import bound

logger = logging.getLogger(__name__)


def frontend_url() -> str:
    return settings.FRONTEND_URL


def email_configured() -> bool:
    return auth_settings.email_configured


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_insert(
    user_id: int | ColumnElement[int], purpose: str, minutes: int = 5, request_ip: str = ""
) -> tuple[Insert, str]:
    """The INSERT of a new token, sweeping tokens expired over a day ago in the same statement, and the
    raw token. user_id is an id, or a column of a CTE the caller adds (a new account's)."""
    now = datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    values = {
        "digest": token_digest(token),
        "purpose": purpose,
        "expires_at": now + timedelta(minutes=minutes),
        "request_ip": request_ip,
        "created_at": now,
    }
    owner = user_id if isinstance(user_id, ColumnElement) else literal(user_id)
    statement = (
        insert(AuthToken)
        .from_select([*values, "user_id"], select(*bound(AuthToken, **values).values(), owner))
        .add_cte(delete(AuthToken).where(AuthToken.expires_at < now - timedelta(days=1)).cte("expired"))
    )
    return statement, token


async def issue_token(db: AsyncSession, user_id: int, purpose: str, minutes: int = 5, request_ip: str = "") -> str:
    statement, token = token_insert(user_id, purpose, minutes, request_ip)
    await db.execute(statement)
    return token


async def consume_token(db: AsyncSession, token: str, purpose: str) -> int:
    now = datetime.now(UTC)
    user_id: int | None = await db.scalar(
        update(AuthToken)
        .where(
            AuthToken.digest == token_digest(token),
            AuthToken.purpose == purpose,
            AuthToken.consumed_at.is_(None),
            AuthToken.expires_at > now,
        )
        .values(consumed_at=now)
        .returning(AuthToken.user_id)
    )
    if user_id is None:
        raise VerificationLinkUsed
    return user_id


# Verification email limits live in Redis like other rate limits. ponytail: unchecked while Redis is
# down; the links still expire.


async def limit_caller(request_ip: str) -> None:
    """Five verification requests per caller per 15 minutes; the sixth raises."""
    caller = f"accretion:verify:ip:{request_ip}"
    try:
        async with bus.client.pipeline() as pipe:
            sent, _ = await pipe.incr(caller).expire(caller, 900, nx=True).execute()
    except RedisError as exc:
        logger.warning("Verification limit unchecked; Redis failed error_type=%s", type(exc).__name__)
        return
    if sent > 5:
        raise VerificationThrottled


async def first_link(email: str) -> bool:
    """One link per address per minute: marks this one, or False when a link just went out."""
    try:
        return bool(await bus.client.set(f"accretion:verify:email:{email}", 1, nx=True, ex=60))
    except RedisError as exc:
        logger.warning("Verification limit unchecked; Redis failed error_type=%s", type(exc).__name__)
        return True


async def send_link(email: str, name: str, token: str) -> None:
    """Runs after the response. Unverified accounts are waitlisted (the migration approved only
    verified ones), so the confirmation link travels inside the waitlist note. A lost email is
    logged; the user can ask for another."""
    link = f"{frontend_url()}/verify-email#token={token}"
    try:
        await emails.send(email, *emails.waitlist(name, link), f"verify-{token_digest(token)}")
    except VerificationEmailFailed:
        logger.warning("Verification email was not sent")
