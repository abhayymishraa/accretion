"""The user's Vercel connection: the Integration install flow, and the sealed token it gives."""

import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode

from redis import RedisError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent.run import bus
from auth.schemas import TokenUser
from config import settings
from vercel_connect import client
from vercel_connect.config import vercel_settings
from vercel_connect.exceptions import (
    Reconnect,
    SignInExpired,
    SignInUnavailable,
    VercelNotConfigured,
    VercelRefused,
)
from vercel_connect.models import VercelAccount
from vercel_connect.schemas import AccountOut, ConnectFinish, ConnectStart

_SIGN_IN_SECONDS = 1800


def require_configured() -> None:
    if not vercel_settings.configured:
        raise VercelNotConfigured


def _state_key(state: str) -> str:
    return f"accretion:vercel:connect:{state}"


async def account(db: AsyncSession, user: TokenUser) -> AccountOut:
    if not vercel_settings.configured:
        return AccountOut(configured=False, connected=False)
    secret = await db.scalar(select(VercelAccount.secret).where(VercelAccount.user_id == user.id))
    if secret is None:
        return AccountOut(configured=True, connected=False)
    # One cheap call proves the Integration is still installed: a removed one's token stops working.
    try:
        await client.Session(client.unseal(secret)).call("GET", "/v9/projects", params={"limit": 1})
    except Reconnect:
        return AccountOut(configured=True, connected=False)
    except VercelRefused as error:
        if error.vercel_status == 403:
            return AccountOut(configured=True, connected=False)
        raise
    return AccountOut(configured=True, connected=True)


async def begin_connect(user: TokenUser) -> ConnectStart:
    require_configured()
    state = secrets.token_urlsafe(32)
    # Bound to this user and used once: the signed-in callback page finishes it, so an install someone else
    # started can never put their Vercel account on this user.
    try:
        await bus.client.set(_state_key(state), str(user.id), ex=_SIGN_IN_SECONDS)
    except RedisError:
        raise SignInUnavailable from None
    query = urlencode({"state": state})
    return ConnectStart(url=f"https://vercel.com/integrations/{vercel_settings.VERCEL_INTEGRATION_SLUG}/new?{query}")


async def finish_connect(db: AsyncSession, user: TokenUser, payload: ConnectFinish) -> AccountOut:
    require_configured()
    try:
        stored = await bus.client.getdel(_state_key(payload.state))
    except RedisError:
        raise SignInUnavailable from None
    if stored != str(user.id):
        raise SignInExpired
    sealed = client.seal(await client.exchange(payload.code, f"{settings.FRONTEND_URL}/vercel/callback"))
    await db.execute(
        insert(VercelAccount)
        .values(user_id=user.id, secret=sealed)
        .on_conflict_do_update(
            index_elements=[VercelAccount.user_id], set_={"secret": sealed, "updated_at": datetime.now(UTC)}
        )
    )
    return AccountOut(configured=True, connected=True)
