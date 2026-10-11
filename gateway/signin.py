"""Sign-in for generated apps: Google or an email link, ending in a signed token the app checks against our JWKS.

Google refuses sign-in inside in-app browsers, so every app also gets the email link. The token travels in the
redirect's fragment, which never reaches a server log or a Referer header.
"""

import base64
import contextlib
import functools
import hashlib
import json
import secrets
import time
from html import escape
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import OKPKey
from redis import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.run import bus
from auth.config import auth_settings
from config import settings
from db.models import Chat
from exceptions import DetailedHTTPException
from gateway.constants import EMAIL_LINK_SECONDS, SESSION_DAYS, SIGN_IN_SECONDS
from gateway.email import deliver
from gateway.env import token_hash
from gateway.exceptions import (
    AppNotFound,
    GoogleNotOffered,
    RedirectNotAllowed,
    SessionInvalid,
    SignInEmailThrottled,
    SignInExpired,
    SignInUnavailable,
)
from gateway.schemas import EmailSignIn, SignInSession

_GOOGLE_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
_GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
_LOCAL_HOSTS = {"localhost", "127.0.0.1"}
_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


@functools.cache
def _signing_key() -> tuple[OKPKey, str]:
    """Ed25519 derived from SECRET_KEY, so every API process signs with the same key and none is stored."""
    seed = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"accretion app sign-in v1").derive(
        auth_settings.SECRET_KEY.encode()
    )
    private = Ed25519PrivateKey.from_private_bytes(seed)
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return OKPKey.import_key(private), hashlib.sha256(public).hexdigest()[:16]


def _issuer() -> str:
    return f"{settings.PUBLIC_API_URL}/apps"


def _google_callback() -> str:
    return f"{settings.PUBLIC_API_URL}/apps/auth/google/callback"


def jwks() -> dict[str, Any]:
    key, kid = _signing_key()
    return {"keys": [{**key.as_dict(private=False), "kid": kid, "alg": "EdDSA", "use": "sig"}]}


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


def allowed_redirect(chat: Chat, url: str) -> bool:
    """Sign-in returns only to the app's own origin: https, or http on this computer. Deploy adds the app's
    production domains here."""
    target = urlsplit(url)
    local = target.scheme == "http" and target.hostname in _LOCAL_HOSTS
    return (target.scheme == "https" or local) and chat.app_url is not None and _origin(url) == _origin(chat.app_url)


def _issue(app_id: str, provider: str, subject: str, email: str, name: str | None, picture: str | None) -> str:
    now = int(time.time())
    claims = {
        "iss": _issuer(),
        "aud": app_id,
        # Stable per app and person, and different across apps, so two apps cannot join their users.
        "sub": hashlib.sha256(f"{app_id}:{provider}:{subject}".encode()).hexdigest()[:32],
        "email": email,
        "name": name,
        "picture": picture,
        "iat": now,
        "exp": now + SESSION_DAYS * 86400,
    }
    key, kid = _signing_key()
    header = {"alg": "EdDSA", "kid": kid, "typ": "JWT"}
    return jwt.encode(header, {k: v for k, v in claims.items() if v is not None}, key, algorithms=["EdDSA"])


def _back(redirect_uri: str, **fragment: str) -> RedirectResponse:
    base = urlsplit(redirect_uri)._replace(fragment="").geturl()
    return RedirectResponse(f"{base}#{urlencode(fragment)}", status_code=303, headers=_NO_STORE)


async def _app(db: AsyncSession, app_id: str, redirect_uri: str) -> Chat:
    chat = await db.get(Chat, app_id)
    if chat is None:
        raise AppNotFound
    if not allowed_redirect(chat, redirect_uri):
        raise RedirectNotAllowed
    return chat


async def google_start(db: AsyncSession, app_id: str, redirect_uri: str) -> RedirectResponse:
    client_id, client_secret = auth_settings.oauth_credentials("google")
    if not (client_id and client_secret):
        raise GoogleNotOffered
    await _app(db, app_id, redirect_uri)
    state, verifier, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(48), secrets.token_urlsafe(16)
    flow = {"app_id": app_id, "redirect_uri": redirect_uri, "verifier": verifier, "nonce": nonce}
    try:
        await bus.client.set(f"accretion:app:google:{state}", json.dumps(flow), ex=SIGN_IN_SECONDS)
    except RedisError:
        raise SignInUnavailable from None
    query = {
        "client_id": client_id,
        "redirect_uri": _google_callback(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": create_s256_code_challenge(verifier),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{_GOOGLE_AUTHORIZE}?{urlencode(query)}", status_code=303, headers=_NO_STORE)


async def _google_identity(flow: dict[str, str], code: str) -> dict[str, Any]:
    client_id, client_secret = auth_settings.oauth_credentials("google")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            _GOOGLE_TOKEN,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _google_callback(),
                "grant_type": "authorization_code",
                "code_verifier": flow["verifier"],
            },
        )
        response.raise_for_status()
    # The ID token came straight from Google's token endpoint over TLS, authenticated by our client secret, so
    # OpenID Connect Core 3.1.3.7 lets TLS stand in for its signature. Its claims are still checked.
    payload = response.json()["id_token"].split(".")[1]
    claims: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    if (
        claims.get("iss") not in _GOOGLE_ISSUERS
        or claims.get("aud") != client_id
        or claims.get("nonce") != flow["nonce"]
        or claims.get("email_verified") is not True
        or not claims.get("sub")
        or not claims.get("email")
        or int(claims.get("exp", 0)) < time.time()
    ):
        raise ValueError("unverified identity")
    return claims


async def google_finish(state: str, code: str, error: str) -> RedirectResponse:
    try:
        stored = await bus.client.getdel(f"accretion:app:google:{state}")
    except RedisError:
        raise SignInUnavailable from None
    if not stored:
        raise SignInExpired
    flow = json.loads(stored)
    if error or not code:
        return _back(flow["redirect_uri"], accretion_error="cancelled")
    try:
        claims = await _google_identity(flow, code)
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return _back(flow["redirect_uri"], accretion_error="sign_in_failed")
    email = str(claims["email"]).lower()
    token = _issue(flow["app_id"], "google", str(claims["sub"]), email, claims.get("name"), claims.get("picture"))
    return _back(flow["redirect_uri"], accretion_token=token)


async def email_start(db: AsyncSession, app_id: str, payload: EmailSignIn) -> None:
    chat = await _app(db, app_id, payload.redirect_uri)
    email = payload.email.lower()
    token = secrets.token_urlsafe(32)
    link = {"app_id": app_id, "email": email, "redirect_uri": payload.redirect_uri}
    throttle = f"accretion:app:sign-in-email:{app_id}:{email}"
    stored = f"accretion:app:email-link:{token_hash(token)}"
    try:
        # One link per address per app per minute; the app's daily email cap bounds the rest.
        first = await bus.client.set(throttle, 1, nx=True, ex=60)
        if first:
            await bus.client.set(stored, json.dumps(link), ex=EMAIL_LINK_SECONDS)
    except RedisError:
        raise SignInUnavailable from None
    if not first:
        raise SignInEmailThrottled
    url = f"{settings.PUBLIC_API_URL}/apps/auth/email/verify?{urlencode({'t': token})}"
    name = chat.title or "the app"
    note = "The link works once, for 15 minutes. Didn't ask to sign in? Ignore this email."
    text = f"Sign in to {name}:\n\n{url}\n\n{note}"
    html = f'<p>Sign in to {escape(name)}:</p><p><a href="{escape(url)}">Sign in</a></p><p>{escape(note)}</p>'
    try:
        await deliver(app_id, chat.title, email, f"Sign in to {name}", text, html)
    except DetailedHTTPException:
        # Nothing went out: the person may ask again at once, and the unsent link is dropped.
        with contextlib.suppress(RedisError):
            await bus.client.delete(throttle, stored)
        raise


def _page(body: str, status_code: int = 200) -> HTMLResponse:
    """A small self-contained page: no outside assets, readable on a phone, light and dark."""
    return HTMLResponse(
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1"><meta name=robots content=noindex>'
        "<title>Sign in</title><style>"
        ":root{color-scheme:light dark;--bg:#fff;--fg:#1f2933;--accent:#1e9df1}"
        "@media (prefers-color-scheme:dark){:root{--bg:#111418;--fg:#e6e9ee}}"
        "body{margin:0;min-height:100dvh;display:grid;place-items:center;background:var(--bg);color:var(--fg);"
        "font:16px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;padding:16px;box-sizing:border-box}"
        "main{max-width:360px;text-align:center}"
        "button{min-height:44px;min-width:44px;padding:0 28px;border:0;border-radius:8px;background:var(--accent);"
        "color:#fff;font-family:inherit;font-size:16px;font-weight:600;cursor:pointer}"
        f"</style></head><body><main>{body}</main></body></html>",
        status_code=status_code,
        headers=_NO_STORE,
    )


def email_confirm(token: str) -> HTMLResponse:
    """The link opens this page and uses nothing: mail scanners open links on their own. The button's POST
    uses the link."""
    action = f"verify?{urlencode({'t': token})}"
    return _page(
        f'<form method="post" action="{escape(action)}"><p>Continue to sign in.</p>'
        '<button type="submit">Sign in</button></form>'
    )


async def email_finish(token: str) -> Response:
    try:
        stored = await bus.client.getdel(f"accretion:app:email-link:{token_hash(token)}")
    except RedisError:
        raise SignInUnavailable from None
    if not stored:
        # Submitted from the page, so a page, not JSON.
        return _page(f"<p>{escape(SignInExpired.DETAIL)}</p>", 400)
    link = json.loads(stored)
    token = _issue(link["app_id"], "email", link["email"], link["email"], None, None)
    return _back(link["redirect_uri"], accretion_token=token)


def session(app_id: str, token: str) -> SignInSession:
    key, _ = _signing_key()
    try:
        claims = jwt.decode(token, key, algorithms=["EdDSA"]).claims
        jwt.JWTClaimsRegistry(
            iss={"essential": True, "value": _issuer()},
            aud={"essential": True, "value": app_id},
            exp={"essential": True},
        ).validate(claims)
    except (JoseError, ValueError):
        raise SessionInvalid from None
    return SignInSession.model_validate(claims)
