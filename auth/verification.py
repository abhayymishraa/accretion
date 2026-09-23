"""Single-use email proofs and short-lived OAuth handoffs; never store raw tokens."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuthToken, User


def frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def email_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("RESEND_FROM"))


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_token(
    db: AsyncSession, user_id: int, purpose: str, minutes: int = 5, request_ip: str = ""
) -> str:
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(AuthToken).where(AuthToken.expires_at < now - timedelta(days=1))
    )
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
    now = datetime.now(timezone.utc)
    user_id = await db.scalar(
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
        raise HTTPException(
            400, "This link has expired or was already used. Request a new one."
        )
    return user_id


async def send_verification(db: AsyncSession, user: User, request_ip: str) -> None:
    if not email_configured():
        raise HTTPException(
            503, "Email verification is not configured yet. Please try again later."
        )
    now = datetime.now(timezone.utc)
    # Serialize rate-limit checks across workers, including different target emails.
    lock_id = int.from_bytes(
        hashlib.sha256(request_ip.encode()).digest()[:8], "big", signed=True
    )
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
    if recent >= 5:
        raise HTTPException(
            429, "Too many requests. Please wait 15 minutes before trying again."
        )
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
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
                    "Idempotency-Key": f"verify-{token_digest(token)}",
                },
                json={
                    "from": os.environ["RESEND_FROM"],
                    "to": [user.email],
                    "subject": "Verify your Accretion email",
                    "text": f"Verify your email to continue in Accretion:\n\n{link}\n\nThis link expires in 30 minutes. If you did not request it, ignore this email.",
                },
            )
            response.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(
            503, "We could not send the email. Please try again later."
        ) from None
