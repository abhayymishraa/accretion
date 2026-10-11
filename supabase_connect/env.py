"""What a linked app is given to reach its Supabase project. Deploy reuses `app_env` for production values."""

from sqlalchemy import select

from agent.sandbox.kits import public_prefix
from db.base import AutocommitSessionLocal
from supabase_connect.client import unseal
from supabase_connect.models import ProjectDatabase


async def _ready_secret(chat_id: str) -> str | None:
    # Only "ready": while "moving" the app keeps its built-in database, which is the copy's source.
    async with AutocommitSessionLocal() as db:
        return await db.scalar(
            select(ProjectDatabase.secret).where(ProjectDatabase.chat_id == chat_id, ProjectDatabase.status == "ready")
        )


async def linked(chat_id: str) -> bool:
    return await _ready_secret(chat_id) is not None


async def app_env(chat_id: str, kit_id: str) -> dict[str, str]:
    secret = await _ready_secret(chat_id)
    if secret is None:
        return {}
    values = unseal(secret)
    prefix = public_prefix(kit_id)
    return {
        "DATABASE_URL": values["database_url"],
        "SUPABASE_URL": values["url"],
        "SUPABASE_SECRET_KEY": values["secret_key"],
        f"{prefix}SUPABASE_URL": values["url"],
        f"{prefix}SUPABASE_PUBLISHABLE_KEY": values["publishable_key"],
    }
