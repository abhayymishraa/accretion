"""A project's generated secrets (spec 3 ProjectSecret): encrypted in the DB, written to .env.

Values are generated per project from the kit's `env` list; connection URLs are derived
from them. Fernet with a key derived from SECRET_KEY by HKDF. Rotating SECRET_KEY means
re-encrypting every row; add a key-version column in that migration, not before.
"""

import base64
import json
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from auth.config import auth_settings
from db.base import AsyncSessionLocal

from .kits import Kit
from .models import ProjectSecret

_PROJECT_SECRETS = b"accretion project secrets v1"


def fernet(purpose: bytes) -> Fernet:
    """A key derived from SECRET_KEY for one purpose, so one purpose's ciphertext never opens another's."""
    if not auth_settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is required to encrypt secrets")
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=purpose).derive(auth_settings.SECRET_KEY.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def _derived(kit: Kit, values: dict[str, str]) -> dict[str, str]:
    """Connection URLs for the database the kit's template runs (sandbox/templates.py)."""
    if kit.database == "mongo":
        return {"MONGO_URL": "mongodb://127.0.0.1:27017/app"}
    return {"DATABASE_URL": f"postgresql://app:{values['POSTGRES_PASSWORD']}@127.0.0.1:5432/app"}


async def ensure_secrets(chat_id: str, kit: Kit) -> dict[str, str]:
    """The project's .env values, generating any the kit needs that do not exist yet."""
    async with AsyncSessionLocal.begin() as db:
        row = await db.get(ProjectSecret, chat_id, with_for_update=True)
        values: dict[str, str] = json.loads(fernet(_PROJECT_SECRETS).decrypt(row.ciphertext)) if row else {}
        missing = [name for name in kit.env if name not in values]
        for name in missing:
            values[name] = secrets.token_urlsafe(24)
        if missing or row is None:
            ciphertext = fernet(_PROJECT_SECRETS).encrypt(json.dumps(values).encode())
            if row is None:
                db.add(ProjectSecret(chat_id=chat_id, ciphertext=ciphertext))
            else:
                row.ciphertext = ciphertext
    return {**values, **_derived(kit, values)}


def env_file(values: dict[str, str]) -> str:
    """.env content. Generated values are URL-safe, so no quoting is needed."""
    return "".join(f"{name}={value}\n" for name, value in sorted(values.items()))
