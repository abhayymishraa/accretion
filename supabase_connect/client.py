"""The Supabase Management API, called with the user's OAuth token, and the sealing of everything Supabase gave us.

Supabase refresh tokens rotate: each refresh spends the old one. The refresh therefore runs under a row lock on the
account and writes the new pair in the same transaction, so two builds refreshing at once cannot both spend it.
"""

import json
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select, update

from agent.sandbox.secrets import fernet
from db.base import AsyncSessionLocal, AutocommitSessionLocal
from supabase_connect.config import supabase_settings
from supabase_connect.exceptions import Reconnect, SignInExpired, SupabaseRefused, SupabaseUnavailable
from supabase_connect.models import SupabaseAccount

API = "https://api.supabase.com"
_PURPOSE = b"accretion supabase tokens v1"
# Refresh a minute early, so a token never expires between this check and the call it is for.
_MARGIN_SECONDS = 60


def seal(values: dict[str, Any]) -> str:
    return fernet(_PURPOSE).encrypt(json.dumps(values).encode()).decode()


def unseal(text: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(fernet(_PURPOSE).decrypt(text.encode()))
    return result


async def _grant(form: dict[str, str]) -> dict[str, Any] | None:
    """Tokens from /v1/oauth/token, or None when Supabase refused the code or refresh token."""
    form |= {
        "client_id": supabase_settings.SUPABASE_OAUTH_CLIENT_ID,
        "client_secret": supabase_settings.SUPABASE_OAUTH_CLIENT_SECRET,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            response = await http.post(f"{API}/v1/oauth/token", data=form, headers={"Accept": "application/json"})
    except httpx.HTTPError:
        raise SupabaseUnavailable from None
    if response.status_code in (400, 401, 403):
        return None
    if response.status_code >= 300:
        raise SupabaseUnavailable
    body = response.json()
    return {
        "access_token": body["access_token"],
        "refresh_token": body.get("refresh_token") or form.get("refresh_token"),
        "expires_at": time.time() + int(body["expires_in"]),
    }


async def exchange(code: str, verifier: str, redirect_uri: str) -> dict[str, Any]:
    tokens = await _grant(
        {"grant_type": "authorization_code", "code": code, "code_verifier": verifier, "redirect_uri": redirect_uri}
    )
    if tokens is None:
        raise SignInExpired
    return tokens


def _fresh(tokens: dict[str, Any]) -> bool:
    return bool(tokens["expires_at"] > time.time() + _MARGIN_SECONDS)


async def access_token(user_id: int) -> str:
    async with AutocommitSessionLocal() as db:
        secret = await db.scalar(select(SupabaseAccount.secret).where(SupabaseAccount.user_id == user_id))
    if secret is None:
        raise Reconnect
    tokens = unseal(secret)
    if _fresh(tokens):
        return str(tokens["access_token"])
    refused = False
    async with AsyncSessionLocal.begin() as db:
        secret = await db.scalar(
            select(SupabaseAccount.secret).where(SupabaseAccount.user_id == user_id).with_for_update()
        )
        if secret is None:
            raise Reconnect
        tokens = unseal(secret)
        # Another caller may have refreshed while this one waited for the lock.
        if not _fresh(tokens):
            renewed = await _grant({"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]})
            refused = renewed is None
            await db.execute(
                update(SupabaseAccount)
                .where(SupabaseAccount.user_id == user_id)
                .values(secret=None if renewed is None else seal(renewed), updated_at=datetime.now(UTC))
            )
            tokens = renewed or tokens
    # Raised after the block, so the cleared secret commits: the user signs in again.
    if refused:
        raise Reconnect
    return str(tokens["access_token"])


async def call(user_id: int, method: str, path: str, **kwargs: Any) -> Any:
    """One Management API call as the user. Supabase allows 120 requests a minute; callers never poll faster
    than every 5 seconds."""
    token = await access_token(user_id)
    try:
        async with httpx.AsyncClient(base_url=API, timeout=60) as http:
            response = await http.request(method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs)
    except httpx.HTTPError:
        raise SupabaseUnavailable from None
    if response.status_code == 401:
        raise Reconnect
    if response.status_code >= 400:
        try:
            body = response.json()
        except ValueError:
            body = None
        message = body.get("message") if isinstance(body, dict) else None
        raise SupabaseRefused(str(message)[:500] if message else None)
    return response.json() if response.content else None
