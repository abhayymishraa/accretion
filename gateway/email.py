"""Sign-in and Supabase Auth email for generated apps: one recipient per send, a daily cap per project, sent
through Resend."""

import logging
import uuid
from datetime import UTC, datetime
from html import escape

import httpx
from redis import RedisError
from sqlalchemy import select

from agent.run import bus
from auth.config import auth_settings
from db.base import AutocommitSessionLocal
from db.models import Chat
from gateway.config import gateway_settings
from gateway.exceptions import EmailFailed, EmailLimitReached, EmailUnavailable

logger = logging.getLogger(__name__)


async def send_app_email(chat_id: str, to: str, subject: str, text: str, html: str) -> None:
    """For callers that do not hold the app's title: reads it, then sends as deliver does."""
    async with AutocommitSessionLocal() as db:
        title = await db.scalar(select(Chat.title).where(Chat.id == chat_id))
    await deliver(chat_id, title, to, subject, text, html)


async def deliver(chat_id: str, title: str | None, to: str, subject: str, text: str, html: str) -> None:
    """Send one email for a project's app, counted against its daily cap, with a footer naming the app so the
    reader knows who sent it. Raises when refused or not sent."""
    if not (auth_settings.RESEND_API_KEY and gateway_settings.APP_EMAIL_FROM):
        raise EmailUnavailable
    key = f"accretion:app:email:{chat_id}:{datetime.now(UTC):%Y-%m-%d}"
    try:
        async with bus.client.pipeline() as pipe:
            sent, _ = await pipe.incr(key).expire(key, 2 * 86400, nx=True).execute()
    except RedisError as exc:
        # Fails closed, unlike the other limits: an app mailing anyone, uncounted, from our domain is the abuse
        # this cap exists to stop. The app sees a retryable 503.
        logger.warning("App email refused; Redis failed error_type=%s", type(exc).__name__)
        raise EmailUnavailable from None
    if sent > gateway_settings.APP_EMAILS_PER_DAY:
        raise EmailLimitReached
    message = {"from": gateway_settings.APP_EMAIL_FROM, "to": [to], "subject": subject}
    footer = f"Sent by {title or 'an app'} on Accretion."
    if text:
        message["text"] = f"{text}\n\n--\n{footer}"
    if html:
        message["html"] = f'{html}<p style="margin-top:24px;font-size:12px;color:#6b7785">{escape(footer)}</p>'
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {auth_settings.RESEND_API_KEY}",
                    "Idempotency-Key": f"app-{uuid.uuid4()}",
                },
                json=message,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status, reason = exc.response.status_code, exc.response.text[:300]
        logger.warning("Resend refused an app email status=%s reason=%r", status, reason)
        raise EmailFailed from None
    except httpx.HTTPError as exc:
        logger.warning("Resend unreachable error_type=%s", type(exc).__name__)
        raise EmailFailed from None
