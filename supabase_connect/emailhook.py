"""Supabase Auth's Send Email Hook: a linked app's sign-up, sign-in and reset emails go out through our app email
service. Supabase signs each call with the Standard Webhooks scheme and the secret set when the project was linked.
"""

import base64
import hashlib
import hmac
import json
import time
from html import escape
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select

from db.base import AutocommitSessionLocal
from gateway import email as gateway_email
from supabase_connect import client
from supabase_connect.exceptions import HookRefused
from supabase_connect.models import ProjectDatabase

# Standard Webhooks' default tolerance for the signed timestamp, against replays.
_TOLERANCE_SECONDS = 300
_SUBJECTS = {
    "signup": "Confirm your email",
    "invite": "You're invited",
    "magiclink": "Your sign-in link",
    "recovery": "Reset your password",
    "email_change": "Confirm your email change",
    "email": "Your sign-in code",
    "reauthentication": "Your verification code",
}


def _verify(secret: str, body: bytes, headers: dict[str, str]) -> None:
    message_id, stamp = headers.get("webhook-id", ""), headers.get("webhook-timestamp", "")
    if not message_id or not stamp.isdigit() or abs(time.time() - int(stamp)) > _TOLERANCE_SECONDS:
        raise HookRefused
    signed = f"{message_id}.{stamp}.".encode() + body
    expected = base64.b64encode(hmac.new(base64.b64decode(secret), signed, hashlib.sha256).digest()).decode()
    offered = [part.partition(",")[2] for part in headers.get("webhook-signature", "").split()]
    if not any(hmac.compare_digest(expected, signature) for signature in offered):
        raise HookRefused


def _messages(user: dict[str, Any], data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(address, code, token hash) per email. On an email change the hash names are reversed: `token_hash_new`
    goes to the current address and `token_hash` to the new one."""
    if data["email_action_type"] != "email_change":
        return [(user["email"], data.get("token", ""), data.get("token_hash", ""))]
    if data.get("token_hash_new"):
        return [
            (user["email"], data.get("token", ""), data["token_hash_new"]),
            (user["new_email"], data.get("token_new", ""), data["token_hash"]),
        ]
    return [(user["new_email"], data.get("token") or data.get("token_new", ""), data["token_hash"])]


async def handle(chat_id: str, body: bytes, headers: dict[str, str]) -> None:
    async with AutocommitSessionLocal() as db:
        row = await db.scalar(
            select(ProjectDatabase).where(ProjectDatabase.chat_id == chat_id, ProjectDatabase.status != "creating")
        )
    if row is None:
        raise HookRefused
    hook_secret = client.unseal(row.secret).get("hook_secret")
    if not hook_secret:
        raise HookRefused
    _verify(hook_secret, body, headers)
    payload = json.loads(body)
    user, data = payload["user"], payload["email_data"]
    action = data["email_action_type"]
    subject = _SUBJECTS.get(action)
    if subject is None:
        # A notification (password changed, factor enrolled): no link or code to send.
        subject = "Your account was updated"
        text = f"There was a change to your account: {action.replace('_', ' ')}."
        await gateway_email.send_app_email(chat_id, user["email"], subject, text, f"<p>{escape(text)}</p>")
        return
    redirect = data.get("redirect_to") or data.get("site_url", "")
    for address, code, token_hash in _messages(user, data):
        text, html = subject, ""
        # A reauthentication carries a code only.
        if token_hash:
            link = f"https://{row.project_ref}.supabase.co/auth/v1/verify?" + urlencode(
                {"token": token_hash, "type": action, "redirect_to": redirect}
            )
            text += f": {link}"
            html += f'<p><a href="{escape(link)}">{escape(subject)}</a></p>'
        if code:
            text += f"\nEnter this code: {code}"
            html += f"<p>Enter this code: <strong>{escape(code)}</strong></p>"
        await gateway_email.send_app_email(chat_id, address, subject, text, html)
