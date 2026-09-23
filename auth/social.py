"""Authlib handles OAuth state, PKCE and OIDC signatures; local identities stay explicit."""

import os
import secrets
from urllib.parse import urlencode

import httpx
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from joserfc.errors import JoseError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from db.base import get_db
from db.models import AuthIdentity, User
from .dependencies import get_current_user
from .schemas import Token, TokenRequest
from .utils import (
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from .verification import consume_token, email_configured, frontend_url, issue_token

social_router = APIRouter(prefix="/auth", tags=["auth"])
PROVIDERS = ("google", "github")


def api_url() -> str:
    return os.getenv("PUBLIC_API_URL", "http://localhost:8000").rstrip("/")


def provider_enabled(provider: str) -> bool:
    return (
        provider in PROVIDERS
        and len(os.getenv("SECRET_KEY", "")) >= 32
        and all(
            os.getenv(f"{provider.upper()}_{key}")
            for key in ("CLIENT_ID", "CLIENT_SECRET")
        )
    )


def configure_sessions(app):
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        # Renamed with the product. SessionMiddleware reads a single cookie name,
        # so OAuth flows started before a deploy fail closed and the user retries;
        # the window is bounded by max_age below.
        session_cookie="accretion_oauth",
        max_age=600,
        same_site="lax",
        https_only=api_url().startswith("https://"),
    )


def oauth_client(provider: str):
    if not provider_enabled(provider):
        raise HTTPException(503, "This sign-in provider is not configured yet.")
    oauth = OAuth()
    common = dict(
        client_id=os.environ[f"{provider.upper()}_CLIENT_ID"],
        client_secret=os.environ[f"{provider.upper()}_CLIENT_SECRET"],
    )
    if provider == "google":
        return oauth.register(
            "google",
            **common,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid email profile",
                "code_challenge_method": "S256",
                "timeout": 10,
            },
        )
    return oauth.register(
        "github",
        **common,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={
            "scope": "read:user user:email",
            "code_challenge_method": "S256",
            "timeout": 10,
        },
    )


@social_router.get("/options")
async def auth_options():
    return {
        "providers": {name: provider_enabled(name) for name in PROVIDERS},
        "email_verification": email_configured(),
    }


@social_router.post("/oauth/{provider}/link")
async def link_provider(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not provider_enabled(provider):
        raise HTTPException(503, "This sign-in provider is not configured yet.")
    ticket = await issue_token(db, user.id, f"link_{provider}")
    await db.commit()
    return {"url": f"{api_url()}/auth/oauth/{provider}?{urlencode({'ticket': ticket})}"}


@social_router.get("/oauth/{provider}")
async def start_oauth(
    provider: str,
    request: Request,
    ticket: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    client = oauth_client(provider)
    link_user = await consume_token(db, ticket, f"link_{provider}") if ticket else None
    await db.commit()
    request.session.clear()
    if link_user is not None:
        request.session["link_user"] = link_user
    return await client.authorize_redirect(
        request, f"{api_url()}/auth/oauth/{provider}/callback"
    )


async def verified_identity(provider: str, client, token) -> tuple[str, str, str]:
    if provider == "google":
        info = token.get(
            "userinfo", {}
        )  # Authlib validates signature, issuer, audience and nonce.
        if (
            info.get("email_verified") is not True
            or not info.get("sub")
            or not info.get("email")
        ):
            raise ValueError("verified_email_required")
        return (
            str(info["sub"]),
            info["email"].lower(),
            str(info.get("name") or "Accretion member")[:100],
        )
    response = await client.get("user", token=token)
    response.raise_for_status()
    info = response.json()
    response = await client.get("user/emails", token=token)
    response.raise_for_status()
    email = next(
        (
            entry["email"]
            for entry in response.json()
            if entry.get("primary") is True and entry.get("verified") is True
        ),
        None,
    )
    if not email or not info.get("id"):
        raise ValueError("verified_email_required")
    return (
        str(info["id"]),
        email.lower(),
        str(info.get("name") or info.get("login") or "Accretion member")[:100],
    )


async def resolve_identity(
    db: AsyncSession,
    provider: str,
    subject: str,
    email: str,
    name: str,
    link_user: int | None,
) -> User:
    identity = await db.get(AuthIdentity, (provider, subject))
    if identity:
        if link_user is not None and identity.user_id != link_user:
            raise ValueError("account_conflict")
        user = await db.get(User, identity.user_id)
    elif link_user is not None:
        user = await db.get(User, link_user)
        if not user:
            raise ValueError("account_conflict")
        db.add(AuthIdentity(provider=provider, subject=subject, user_id=user.id))
    else:
        existing = await db.scalar(select(User).where(func.lower(User.email) == email))
        if existing:
            # Never silently link by email: authenticate the existing account first.
            raise ValueError("link_required")
        user = User(
            email=email,
            name=name,
            hashed_password=get_password_hash(secrets.token_urlsafe(48)),
            email_verified=True,
        )
        db.add(user)
        await db.flush()
        db.add(AuthIdentity(provider=provider, subject=subject, user_id=user.id))
    if not user:
        raise ValueError("account_conflict")
    if user.email.lower() == email:
        user.email_verified = True
    await db.flush()
    return user


@social_router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str, request: Request, db: AsyncSession = Depends(get_db)
):
    client = oauth_client(provider)
    try:
        token = await client.authorize_access_token(request)
        subject, email, name = await verified_identity(provider, client, token)
        link_user = request.session.pop("link_user", None)
        user = await resolve_identity(db, provider, subject, email, name, link_user)
        if link_user is not None:
            destination = f"{frontend_url()}/profile#connected={provider}"
        else:
            ticket = await issue_token(db, user.id, "oauth_exchange", minutes=1)
            destination = f"{frontend_url()}/auth/callback#ticket={ticket}"
        await db.commit()
    except (OAuthError, JoseError, httpx.HTTPError, ValueError, IntegrityError) as exc:
        await db.rollback()
        code = (
            str(exc)
            if isinstance(exc, ValueError)
            and str(exc)
            in {"link_required", "verified_email_required", "account_conflict"}
            else "oauth_failed"
        )
        destination = f"{frontend_url()}/auth/callback#error={code}"
    request.session.clear()
    return RedirectResponse(
        destination,
        status_code=303,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


@social_router.post("/oauth/exchange", response_model=Token)
async def exchange_oauth(data: TokenRequest, db: AsyncSession = Depends(get_db)):
    user_id = await consume_token(db, data.token, "oauth_exchange")
    user = await db.get(User, user_id)
    if not user or (not user.email_verified):
        raise HTTPException(403, "Verify your email before continuing.")
    await db.commit()
    return Token(
        access_token=create_access_token({"sub": str(user_id)}),
        refresh_token=create_refresh_token({"sub": str(user_id)}),
    )
