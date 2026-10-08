from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from auth.config import auth_settings
from auth.schemas import Token
from db.models import User

SECRET_KEY = auth_settings.SECRET_KEY
if len(SECRET_KEY) < 32:
    raise RuntimeError("Set SECRET_KEY to at least 32 random characters before starting the backend.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Use pbkdf2_sha256 to avoid bcrypt backend issues and 72-byte password limits
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

_GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def canonical_email(email: str) -> str:
    """One account per inbox: Gmail ignores dots and +tags, so each alias would otherwise get its own budget.

    Stored and looked up in this form; mail sent to it still reaches the same Gmail inbox.
    """
    local, _, domain = email.strip().lower().rpartition("@")
    if domain in _GMAIL_DOMAINS:
        return local.split("+", 1)[0].replace(".", "") + "@gmail.com"
    return f"{local}@{domain}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return str(pwd_context.hash(password))


def _encode(claims: dict[str, Any], lifetime: timedelta, token_type: str) -> str:
    return jwt.encode({**claims, "exp": datetime.now(UTC) + lifetime, "type": token_type}, SECRET_KEY, ALGORITHM)


def issue_tokens(user: User) -> Token:
    """A token pair for a verified user. The access token carries what each request checks, so
    authenticating one needs no database query; the refresh token re-reads the user."""
    return Token(
        access_token=_encode(
            {"sub": str(user.id), "role": user.role, "approved": not user.waitlisted},
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "access",
        ),
        refresh_token=_encode({"sub": str(user.id)}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh"),
    )


def decode_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """decode a jwt token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload if payload.get("type") == token_type else None
    except PyJWTError:
        return None


def initial_access(email: str) -> dict[str, Any]:
    """Columns for a new account: the admin skips the waitlist, everyone else joins it."""
    if email == canonical_email(auth_settings.ADMIN_EMAIL):
        return {"role": "admin", "approved_at": datetime.now(UTC)}
    return {}
