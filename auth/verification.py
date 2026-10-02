"""Single-use email proofs and short-lived OAuth handoffs; never store raw tokens."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth import emails
from auth.config import auth_settings
from auth.exceptions import (
    VerificationLinkUsed,
    VerificationNotConfigured,
    VerificationThrottled,
)
from auth.models import AuthToken
from config import settings
from db.models import User


def frontend_url() -> str:
    return settings.FRONTEND_URL


def email_configured() -> bool:
    return auth_settings.email_configured


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_token(db: AsyncSession, user_id: int, purpose: str, minutes: int = 5, request_ip: str = "") -> str:
    now = datetime.now(UTC)
    await db.execute(delete(AuthToken).where(AuthToken.expires_at < now - timedelta(days=1)))
    token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            digest=token_digest(token),
            user_id=user_id,
            purpose=purpose,
            expires_at=now + timedelta(minutes=minutes),
            request_ip=request_ip,
        )
    )
    await db.flush()
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


async def send_verification(db: AsyncSession, user: User, request_ip: str) -> None:
    if not email_configured():
        raise VerificationNotConfigured
    now = datetime.now(UTC)
    # Serialize rate-limit checks across workers, including different target emails.
    lock_id = int.from_bytes(hashlib.sha256(request_ip.encode()).digest()[:8], "big", signed=True)
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
    await db.refresh(user, with_for_update=True)
    if user.email_verified:
        return
    recent = await db.scalar(
        select(func.count())
        .select_from(AuthToken)
        .where(
            AuthToken.purpose == "verify_email",
            AuthToken.request_ip == request_ip,
            AuthToken.created_at > now - timedelta(minutes=15),
        )
    )
    if (recent or 0) >= 5:
        raise VerificationThrottled
    last = await db.scalar(
        select(AuthToken.created_at)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == "verify_email",
        )
        .order_by(AuthToken.created_at.desc())
        .limit(1)
    )
    if last and last > now - timedelta(seconds=60):
        return
    token = await issue_token(db, user.id, "verify_email", 30, request_ip)
    link = f"{frontend_url()}/verify-email#token={token}"
    # Unverified accounts are waitlisted (the migration approved only verified ones),
    # so the confirmation link travels inside the waitlist note.
    await emails.send(user.email, *emails.waitlist(user.name, link), f"verify-{token_digest(token)}")
