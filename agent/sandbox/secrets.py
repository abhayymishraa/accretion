"""A project's secrets (spec 3 ProjectSecret): encrypted in the DB, written into the sandbox.

Two kinds, each in its own column. The kit's values are generated per project from its `env` list, written to .env
and sourced by every command; connection URLs are derived from them. The user's values (API keys they enter) are
written to .env.json, which only the app's services read (preview_process.kit_env): the builder's commands never
have them in their environment. Fernet with a key derived from SECRET_KEY by HKDF. Rotating SECRET_KEY means
re-encrypting every row; add a key-version column in that migration, not before.
"""

import base64
import json
import re
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth.config import auth_settings
from db.base import AsyncSessionLocal, AutocommitSessionLocal

from .kits import KITS, Kit
from .models import ProjectSecret

_PROJECT_SECRETS = b"accretion project secrets v1"
_USER_SECRETS = b"accretion user secrets v1"
# Shell-style names, as every kit's runtime reads them.
NAME = re.compile(r"[A-Z_][A-Z0-9_]{0,127}")
# Names the kits own, and names that would break the app's process if a user set them.
RESERVED = frozenset(
    {name for kit in KITS.values() for name in kit.env} | {"DATABASE_URL", "MONGO_URL", "PATH", "HOME", "PORT"}
)
# Supabase's Edge Function limit (also E2B's and GitHub's), so every key can follow the app there.
MAX_SECRETS = 100


class SecretLimit(Exception):
    """The project already holds MAX_SECRETS keys."""


def fernet(purpose: bytes) -> Fernet:
    """A key derived from SECRET_KEY for one purpose, so one purpose's ciphertext never opens another's."""
    if not auth_settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is required to encrypt secrets")
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=purpose).derive(auth_settings.SECRET_KEY.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def user_values(ciphertext: bytes | None) -> dict[str, str]:
    """The user's secrets from their column; none when the project has none."""
    return json.loads(fernet(_USER_SECRETS).decrypt(ciphertext)) if ciphertext else {}


def _derived(kit: Kit, values: dict[str, str]) -> dict[str, str]:
    """Connection URLs for the database the kit's template runs (sandbox/templates.py)."""
    if kit.database == "mongo":
        return {"MONGO_URL": "mongodb://127.0.0.1:27017/app"}
    return {"DATABASE_URL": f"postgresql://app:{values['POSTGRES_PASSWORD']}@127.0.0.1:5432/app"}


def kit_names(kit: Kit) -> list[str]:
    """The names the kit gives the app: shown to the user read-only, never their values."""
    return sorted([*kit.env, *_derived(kit, dict.fromkeys(kit.env, ""))])


async def _locked_row(db: AsyncSession, chat_id: str) -> ProjectSecret:
    """The project's row, created empty if missing, locked for this transaction. The insert is conflict-safe, so a
    first save and a first build at the same time cannot both create it."""
    empty = fernet(_PROJECT_SECRETS).encrypt(b"{}")
    await db.execute(insert(ProjectSecret).values(chat_id=chat_id, ciphertext=empty).on_conflict_do_nothing())
    row = await db.get(ProjectSecret, chat_id, with_for_update=True, populate_existing=True)
    assert row is not None, "inserted above"
    return row


async def ensure_secrets(chat_id: str, kit: Kit) -> tuple[dict[str, str], dict[str, str]]:
    """The project's .env values, generating any the kit needs that do not exist yet, and the user's values."""
    async with AsyncSessionLocal.begin() as db:
        row = await _locked_row(db, chat_id)
        values: dict[str, str] = json.loads(fernet(_PROJECT_SECRETS).decrypt(row.ciphertext))
        missing = [name for name in kit.env if name not in values]
        for name in missing:
            values[name] = secrets.token_urlsafe(24)
        if missing:
            row.ciphertext = fernet(_PROJECT_SECRETS).encrypt(json.dumps(values).encode())
        user = user_values(row.user_ciphertext)
    return {**values, **_derived(kit, values)}, user


async def user_secrets(chat_id: str) -> dict[str, str]:
    async with AutocommitSessionLocal() as db:
        row = await db.get(ProjectSecret, chat_id)
    return user_values(row.user_ciphertext if row else None)


async def set_user_secret(db, chat_id: str, name: str, value: str | None) -> dict[str, str]:
    """Save (value) or remove (None) one user secret in the caller's transaction; the project's secrets after it.

    The row is locked: two saves at once would each write back the other's missing value."""
    row = await _locked_row(db, chat_id)
    values = user_values(row.user_ciphertext)
    if value is not None and name not in values and len(values) >= MAX_SECRETS:
        raise SecretLimit
    if value is None:
        values.pop(name, None)
    else:
        values[name] = value
    # A project can get a key before its first build; the kit's values are generated at its first start.
    row.user_ciphertext = fernet(_USER_SECRETS).encrypt(json.dumps(values).encode()) if values else None
    return values


def env_file(values: dict[str, str]) -> str:
    """.env content. Generated values are URL-safe, so no quoting is needed."""
    return "".join(f"{name}={value}\n" for name, value in sorted(values.items()))


def user_env_file(values: dict[str, str]) -> str:
    """.env.json content: JSON, so a value the user typed needs no quoting and can hold any character."""
    return json.dumps(values, sort_keys=True)
