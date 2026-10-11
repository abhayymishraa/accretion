"""A project's app token and the environment its app gets for the platform services."""

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from agent.sandbox.kits import public_prefix
from agent.sandbox.secrets import fernet
from config import settings
from db.base import AutocommitSessionLocal
from gateway.constants import TOKEN_PREFIX
from gateway.models import AppToken

_SEAL = b"accretion app tokens v1"
_PUBLIC = ("ACCRETION_API_URL", "ACCRETION_APP_ID")

# Every name app_env can return, for both kit prefixes, so a user secret can never shadow one.
PLATFORM_NAMES = frozenset(
    {
        "ACCRETION_APP_TOKEN",
        *_PUBLIC,
        *(prefix + name for prefix in ("VITE_", "NEXT_PUBLIC_") for name in _PUBLIC),
    }
)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def app_env(chat_id: str, kit_id: str) -> dict[str, str]:
    """The app's platform variables, creating its token on first use. The no-op update makes RETURNING hand back
    the existing row, so a race between two starts still reads one token in one statement."""
    # A new token's row. Only its hash finds it; the sealed copy is what each sandbox start writes.
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    new = insert(AppToken).values(
        chat_id=chat_id, token_hash=token_hash(token), secret=fernet(_SEAL).encrypt(token.encode()).decode()
    )
    statement = new.on_conflict_do_update(
        index_elements=[AppToken.chat_id], set_={"chat_id": new.excluded.chat_id}
    ).returning(AppToken.secret)
    async with AutocommitSessionLocal() as db:
        sealed = await db.scalar(statement)
    assert sealed is not None, "an upsert always returns its row"
    token = fernet(_SEAL).decrypt(sealed.encode()).decode()
    api = settings.PUBLIC_API_URL
    prefix = public_prefix(kit_id)
    return {
        "ACCRETION_APP_TOKEN": token,
        "ACCRETION_API_URL": api,
        "ACCRETION_APP_ID": chat_id,
        f"{prefix}ACCRETION_API_URL": api,
        f"{prefix}ACCRETION_APP_ID": chat_id,
    }


async def token_app(token: str) -> str | None:
    """The project a token belongs to."""
    async with AutocommitSessionLocal() as db:
        return await db.scalar(select(AppToken.chat_id).where(AppToken.token_hash == token_hash(token)))
