"""Transactional email through Resend: the waitlist, approval and new-signup notes.

Each note is short HTML that reads like a personal message, with a plain-text
twin. Heavy designed layouts land in Promotions and get fewer clicks.
"""

import logging
from html import escape

import httpx

from auth.config import auth_settings
from auth.exceptions import VerificationEmailFailed
from config import settings
from db.models import User

logger = logging.getLogger(__name__)

_BRAND = "#1e9df1"


def _html(
    paragraphs: list[str],
    button: tuple[str, str] | None = None,
    after: list[str] | None = None,
    signed: bool = True,
) -> str:
    """Wrap pre-escaped paragraphs in the shared layout."""
    p = '<p style="margin:0 0 16px;font-size:16px;line-height:1.6;color:#1f2933">{}</p>'
    body = "".join(p.format(text) for text in paragraphs)
    if button:
        label, url = button
        body += (
            f'<p style="margin:24px 0"><a href="{escape(url)}" style="display:inline-block;padding:12px 22px;'
            f'background:{_BRAND};color:#ffffff;text-decoration:none;font-weight:600;border-radius:6px">'
            f"{escape(label)}</a></p>"
        )
    body += "".join(p.format(text) for text in after or [])
    signature = (
        '<p style="margin:24px 0 0;font-size:16px;line-height:1.6;color:#1f2933">Abhay<br>'
        '<span style="color:#6b7785">Founder, Accretion</span></p>'
    )
    return (
        '<div style="background:#f5f7fa;padding:32px 16px;font-family:-apple-system,Segoe UI,Helvetica,Arial,'
        'sans-serif"><div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:8px;'
        f'padding:32px;border-top:4px solid {_BRAND}">'
        # Gmail strips SVG and data: images, so the mark is the hosted PNG.
        f'<p style="margin:0 0 24px"><img src="{settings.FRONTEND_URL}/brand/icon-192.png" width="32" height="32"'
        ' alt="" style="vertical-align:middle;border:0">'
        '<span style="vertical-align:middle;margin-left:10px;font-size:20px;font-weight:800;color:#1c1917;'
        'letter-spacing:-.02em">Accretion</span></p>'
        f"{body}{signature if signed else ''}</div></div>"
    )


async def send(to: str, subject: str, text: str, html: str, idempotency_key: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {auth_settings.RESEND_API_KEY}",
                    "Idempotency-Key": idempotency_key,
                },
                json={
                    "from": auth_settings.RESEND_FROM,
                    "reply_to": auth_settings.ADMIN_EMAIL,
                    "to": [to],
                    "subject": subject,
                    "text": text,
                    "html": html,
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Resend says why it refused (an unverified sending domain, a bad sender, a rate limit);
        # without this line every failure reads the same.
        logger.warning("Resend refused an email status=%s reason=%r", exc.response.status_code, exc.response.text[:300])
        raise VerificationEmailFailed from None
    except httpx.HTTPError as exc:
        logger.warning("Resend unreachable error_type=%s", type(exc).__name__)
        raise VerificationEmailFailed from None


def _first(name: str) -> str:
    return (name.split() or ["there"])[0]


def waitlist(name: str, confirm_link: str | None) -> tuple[str, str, str]:
    """Subject, text and HTML for a new signup. Email signups also confirm their address here."""
    hi = f"Hi {_first(name)},"
    lines = [
        "Thanks for joining Accretion. You're on the list.",
        "We let people in a few at a time, so everyone gets a good first experience. When your spot opens,"
        " you'll get an email with a button that signs you straight in.",
    ]
    ask = (
        "While you wait, one question: what's the first app you'd want to build? Just hit reply."
        " I read every answer, and it helps decide who gets in next."
    )
    text = "\n\n".join([hi, *lines])
    html = [escape(hi), *map(escape, lines)]
    button = None
    if confirm_link:
        confirm = "First, confirm your email so we can hold your spot. The link works for 30 minutes."
        text += f"\n\n{confirm}\n\n{confirm_link}"
        html.append(escape(confirm))
        button = ("Confirm my spot", confirm_link)
    text += f"\n\n{ask}\n\nAbhay\nFounder, Accretion"
    return "You're on the Accretion list", text, _html(html, button, [escape(ask)])


def approved(name: str, link: str) -> tuple[str, str, str]:
    hi = f"Hi {_first(name)},"
    lead = "Good news: your Accretion spot is ready. Describe the app you want in plain words, and Accretion builds it."
    note = (
        "This button signs you in with one click. It works once and expires in 7 days. After that, sign in"
        f" at {settings.FRONTEND_URL}/signin with your email or Google or GitHub."
    )
    ignore = "Didn't sign up for Accretion? You can safely ignore this email. Questions? Just reply."
    text = f"{hi}\n\n{lead}\n\nSign in: {link}\n\n{note}\n\n{ignore}\n\nAbhay\nFounder, Accretion"
    fallback = (
        "Button not working? Paste this link into your browser:<br>"
        f'<span style="word-break:break-all">{escape(link)}</span>'
    )
    html = _html([escape(hi), escape(lead)], ("Sign in to Accretion", link), [escape(note), fallback, escape(ignore)])
    return "You're in: start building on Accretion", text, html


async def enrolled(user: User) -> None:
    """A provider signup arrives verified, so it gets the waitlist note without a confirm link."""
    try:
        await send(user.email, *waitlist(user.name, None), f"enrolled-{user.id}")
    except VerificationEmailFailed:
        logger.warning("Waitlist note for user %s was not sent", user.id)
    await notify_admin(user)


async def notify_admin(user: User) -> None:
    """Tell the admin someone joined. Best effort: a lost notice must not fail the signup."""
    review_url = f"{settings.FRONTEND_URL}/admin?approve={user.id}"
    line = f"{user.name} ({user.email}) just joined the waitlist."
    html = _html([escape(line)], ("Review and approve", review_url), signed=False)
    try:
        await send(
            auth_settings.ADMIN_EMAIL,
            f"Waitlist: {user.name}",
            f"{line}\n\nReview: {review_url}",
            html,
            f"waitlist-{user.id}",
        )
    except VerificationEmailFailed:
        logger.warning("Waitlist notice for user %s was not sent", user.id)
