from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from auth.config import auth_settings

SECRET_KEY = auth_settings.SECRET_KEY
if len(SECRET_KEY) < 32:
    raise RuntimeError("Set SECRET_KEY to at least 32 random characters before starting the backend.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Use pbkdf2_sha256 to avoid bcrypt backend issues and 72-byte password limits
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return str(pwd_context.hash(password))


def create_access_token(data: dict[str, Any]) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encode_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a Jwt"""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt


def decode_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """decode a jwt token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload if payload.get("type") == token_type else None
    except PyJWTError:
        return None
