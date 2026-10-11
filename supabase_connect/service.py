"""Supabase: the user's sign-in, and the Supabase project each app keeps its data in.

Linking a project sets it up in the background (create, wait until healthy, app login, keys, email hook), then marks
it "moving". The app's data is copied in when a sandbox is next acquired (`sandbox.prepare`), and only then does
the app switch to Supabase ("ready").
"""

import asyncio
import base64
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from authlib.oauth2.rfc7636 import create_s256_code_challenge
from redis import RedisError
from sqlalchemy import delete, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent.run import bus
from agent.sandbox.kits import KITS
from auth.schemas import TokenUser
from config import settings
from db.base import AutocommitSessionLocal
from db.models import Chat
from exceptions import DetailedHTTPException
from projects.exceptions import ProjectNotFound
from supabase_connect import client
from supabase_connect.config import supabase_settings
from supabase_connect.exceptions import (
    DatabaseLinked,
    DatabaseNotLinked,
    DatabaseNotOffered,
    Reconnect,
    SignInExpired,
    SignInUnavailable,
    SupabaseNotConfigured,
    SupabaseUnavailable,
)
from supabase_connect.models import ProjectDatabase, SupabaseAccount
from supabase_connect.schemas import (
    AccountOut,
    ConnectFinish,
    ConnectStart,
    CreateDatabase,
    DatabaseOut,
    ExistingDatabase,
    Finding,
    Organization,
    ProjectList,
    Region,
    RegionList,
    SupabaseProject,
)

logger = logging.getLogger("webbuilder.supabase")

_SIGN_IN_SECONDS = 600
# Each app its own login on an existing project, so a second app linked to the same project never resets the first's
# password. A project id is a UUID: its first hex digits are a safe role name.
_APP_ROLE = "accretion_app_{}"
# Supabase allows 120 requests a minute; a new project is usually healthy within two minutes.
_POLL_SECONDS = 10
_POLL_LIMIT = 90
# Past the poll limit with room to spare: a row still creating after this was orphaned by a restart.
_SETUP_STALE = timedelta(minutes=20)
_REGIONS = {
    "us-east-1": "East US (North Virginia)",
    "us-east-2": "East US (Ohio)",
    "us-west-1": "West US (North California)",
    "us-west-2": "West US (Oregon)",
    "ca-central-1": "Canada (Central)",
    "sa-east-1": "South America (São Paulo)",
    "eu-west-1": "West EU (Ireland)",
    "eu-west-2": "West Europe (London)",
    "eu-west-3": "West EU (Paris)",
    "eu-central-1": "Central EU (Frankfurt)",
    "eu-central-2": "Central Europe (Zurich)",
    "eu-north-1": "North EU (Stockholm)",
    "ap-south-1": "South Asia (Mumbai)",
    "ap-southeast-1": "Southeast Asia (Singapore)",
    "ap-southeast-2": "Oceania (Sydney)",
    "ap-northeast-1": "Northeast Asia (Tokyo)",
    "ap-northeast-2": "Northeast Asia (Seoul)",
    "ap-east-1": "East Asia (Hong Kong)",
}
_MESSAGES = {
    "creating": "Creating your Supabase project…",
    "moving": "Moving your data to Supabase…",
    "ready": "Connected to Supabase",
    "error": "Couldn't move your data. Your app still uses its built-in database.",
}


def _redirect_uri() -> str:
    return f"{settings.FRONTEND_URL}/supabase/callback"


def _require_configured() -> None:
    if not supabase_settings.configured:
        raise SupabaseNotConfigured


async def save_status(chat_id: str, status: str, **detail: Any) -> None:
    """One statement; `detail` keys are merged into the row's detail."""
    async with AutocommitSessionLocal() as db:
        await db.execute(
            update(ProjectDatabase)
            .where(ProjectDatabase.chat_id == chat_id)
            .values(
                status=status,
                detail=ProjectDatabase.detail.op("||")(literal(detail, JSONB)),
                updated_at=datetime.now(UTC),
            )
        )


async def account(db: AsyncSession, user: TokenUser) -> AccountOut:
    if not supabase_settings.configured:
        return AccountOut(configured=False, connected=False)
    secret = await db.scalar(select(SupabaseAccount.secret).where(SupabaseAccount.user_id == user.id))
    if secret is None:
        return AccountOut(configured=True, connected=False)
    try:
        listed = await client.call(user.id, "GET", "/v1/organizations")
    except Reconnect:
        return AccountOut(configured=True, connected=False)
    return AccountOut(
        configured=True,
        connected=True,
        organizations=[Organization(id=org["slug"], name=org["name"]) for org in listed],
    )


async def begin_connect(user: TokenUser) -> ConnectStart:
    _require_configured()
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(24)
    # Bound to this user: the signed-in callback page finishes it, so a link someone else started can never put
    # their Supabase account on this user.
    flow = {"user_id": user.id, "verifier": verifier}
    try:
        await bus.client.set(f"accretion:supabase:sign-in:{state}", json.dumps(flow), ex=_SIGN_IN_SECONDS)
    except RedisError:
        raise SignInUnavailable from None
    query = urlencode(
        {
            "client_id": supabase_settings.SUPABASE_OAUTH_CLIENT_ID,
            "redirect_uri": _redirect_uri(),
            "response_type": "code",
            "state": state,
            "code_challenge": create_s256_code_challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    return ConnectStart(url=f"{client.API}/v1/oauth/authorize?{query}")


async def finish_connect(db: AsyncSession, user: TokenUser, payload: ConnectFinish) -> AccountOut:
    _require_configured()
    try:
        stored = await bus.client.getdel(f"accretion:supabase:sign-in:{payload.state}")
    except RedisError:
        raise SignInUnavailable from None
    flow = json.loads(stored) if stored else None
    if flow is None or flow["user_id"] != user.id:
        raise SignInExpired
    tokens = await client.exchange(payload.code, flow["verifier"], _redirect_uri())
    sealed = client.seal(tokens)
    await db.execute(
        insert(SupabaseAccount)
        .values(user_id=user.id, secret=sealed)
        .on_conflict_do_update(
            index_elements=[SupabaseAccount.user_id], set_={"secret": sealed, "updated_at": datetime.now(UTC)}
        )
    )
    return await account(db, user)


async def disconnect(db: AsyncSession, user: TokenUser) -> None:
    # Linked apps keep working: their database login and keys do not depend on this sign-in.
    await db.execute(delete(SupabaseAccount).where(SupabaseAccount.user_id == user.id))


async def projects(user: TokenUser, organization_id: str) -> ProjectList:
    _require_configured()
    listed = await client.call(user.id, "GET", f"/v1/organizations/{organization_id}/projects")
    return ProjectList(
        projects=[
            SupabaseProject(ref=p["ref"], name=p["name"], region=p["region"], status=p["status"])
            for p in listed["projects"]
        ]
    )


def regions() -> RegionList:
    return RegionList(regions=[Region(id=key, name=name) for key, name in _REGIONS.items()])


def _out(kit: str, row: ProjectDatabase | None, signed_in: bool) -> DatabaseOut:
    stack = KITS.get(kit)
    offered = stack is not None and stack.database == "postgres"
    if row is None:
        return DatabaseOut(offered=offered, linked=False)
    message = row.detail.get("message") if row.status == "error" else None
    if row.status == "creating" and datetime.now(UTC) - row.updated_at > _SETUP_STALE:
        # The setup ran in the background of a server that restarted: nothing will finish it.
        message = "Setting up Supabase was interrupted. Disconnect it and connect again."
    status = row.status
    if row.status == "ready" and not signed_in:
        message = "Reconnect Supabase to keep using it."
        status = "reconnect"
    return DatabaseOut(
        offered=offered,
        linked=True,
        ref=row.project_ref,
        name=row.project_name,
        region=row.region,
        status=status,
        message=message or _MESSAGES.get(row.status),
        dashboard_url=f"https://supabase.com/dashboard/project/{row.project_ref}",
        findings=[Finding.model_validate(item) for item in row.detail.get("findings", [])],
    )


async def database(db: AsyncSession, user: TokenUser, project_id: str) -> DatabaseOut:
    """One query: ownership, the link and whether the user is still signed in to Supabase."""
    found = (
        await db.execute(
            select(Chat.kit, ProjectDatabase, SupabaseAccount.secret.is_not(None))
            .outerjoin(ProjectDatabase, ProjectDatabase.chat_id == Chat.id)
            .outerjoin(SupabaseAccount, SupabaseAccount.user_id == Chat.user_id)
            .where(Chat.id == project_id, Chat.user_id == user.id)
        )
    ).first()
    if found is None:
        raise ProjectNotFound
    kit, row, signed_in = found.tuple()
    return _out(kit, row, bool(signed_in))


async def link(
    db: AsyncSession, user: TokenUser, chat: Chat, payload: CreateDatabase | ExistingDatabase
) -> DatabaseOut:
    """Starts the link; the caller runs `finish_link` after the response."""
    _require_configured()
    if KITS[chat.kit].database != "postgres":
        raise DatabaseNotOffered
    # Checked before creating anything at Supabase; the insert below settles a race.
    if await db.scalar(select(ProjectDatabase.chat_id).where(ProjectDatabase.chat_id == chat.id)):
        raise DatabaseLinked
    if isinstance(payload, CreateDatabase):
        password = secrets.token_urlsafe(24)
        project = await client.call(
            user.id,
            "POST",
            "/v1/projects",
            json={
                "name": payload.name,
                "organization_slug": payload.organization_id,
                "db_pass": password,
                "region_selection": {"type": "specific", "code": payload.region},
            },
        )
        login = {"db_user": "postgres", "db_password": password}
    else:
        project = await client.call(user.id, "GET", f"/v1/projects/{payload.ref}")
        # We never learn an existing project's postgres password: the app gets its own login (finish_link).
        login = {"db_user": _APP_ROLE.format(chat.id.replace("-", "")[:12]), "db_password": secrets.token_urlsafe(24)}
    row = await db.scalar(
        insert(ProjectDatabase)
        .values(
            chat_id=chat.id,
            project_ref=project["ref"],
            project_name=project["name"],
            region=project["region"],
            secret=client.seal(login),
            status="creating",
        )
        .on_conflict_do_nothing(index_elements=[ProjectDatabase.chat_id])
        .returning(ProjectDatabase)
    )
    if row is None:
        raise DatabaseLinked
    return _out(chat.kit, row, True)


async def _wait_healthy(user_id: int, ref: str) -> None:
    for _ in range(_POLL_LIMIT):
        health = await client.call(user_id, "GET", f"/v1/projects/{ref}/health", params={"services": "db,pooler,auth"})
        if all(service["healthy"] for service in health):
            return
        await asyncio.sleep(_POLL_SECONDS)
    raise SupabaseUnavailable("Your Supabase project didn't start. Check it in the Supabase dashboard.")


async def _app_login(user_id: int, ref: str, role: str, password: str) -> None:
    """A login role for the app on an existing project. It owns what the app's migrations create: tables in public,
    and a schema of its own where the migration tool keeps its record (Drizzle's `drizzle`)."""
    # token_urlsafe passwords hold only [A-Za-z0-9_-], so the literal needs no escaping.
    sql = f"""
do $$ begin
  if exists (select from pg_roles where rolname = '{role}') then
    alter role {role} with login password '{password}';
  else
    create role {role} with login password '{password}';
  end if;
end $$;
grant usage, create on schema public to {role};
grant create on database postgres to {role};
grant all on all tables in schema public to {role};
grant all on all sequences in schema public to {role};
"""
    await client.call(user_id, "POST", f"/v1/projects/{ref}/database/query", json={"query": sql})


async def _keys(user_id: int, ref: str) -> tuple[str, str]:
    listed = await client.call(user_id, "GET", f"/v1/projects/{ref}/api-keys", params={"reveal": "true"})
    by_type = {key["type"]: key["api_key"] for key in listed if key.get("type") in ("publishable", "secret")}
    if len(by_type) == 2:
        return by_type["publishable"], by_type["secret"]
    # Projects without the new keys: the legacy JWT keys, which Supabase retires at the end of 2026.
    legacy = {key["name"]: key["api_key"] for key in listed}
    return legacy["anon"], legacy["service_role"]


async def finish_link(chat_id: str, user_id: int, app_url: str | None) -> None:
    """Background: wait for the project, give the app a login, read the keys, point Auth's emails at us."""
    async with AutocommitSessionLocal() as db:
        row = await db.scalar(select(ProjectDatabase).where(ProjectDatabase.chat_id == chat_id))
    if row is None:
        return
    ref, values = row.project_ref, client.unseal(row.secret)
    try:
        await _wait_healthy(user_id, ref)
        created = values["db_user"] == "postgres"
        if not created:
            await _app_login(user_id, ref, values["db_user"], values["db_password"])
        poolers = await client.call(user_id, "GET", f"/v1/projects/{ref}/config/database/pooler")
        pooler = next((entry for entry in poolers if entry["database_type"] == "PRIMARY"), None)
        if pooler is None:
            raise SupabaseUnavailable
        publishable, secret_key = await _keys(user_id, ref)
        hook_secret = base64.b64encode(secrets.token_bytes(32)).decode()
        # A project we created is the app's alone. An existing one may serve other apps: its own email setup and
        # addresses are kept, and the app's address is added beside them.
        current = {} if created else await client.call(user_id, "GET", f"/v1/projects/{ref}/config/auth")
        auth: dict[str, Any] = {}
        if not (current.get("smtp_host") or current.get("hook_send_email_enabled")):
            auth |= {
                "hook_send_email_enabled": True,
                "hook_send_email_uri": f"{settings.PUBLIC_API_URL}/supabase/email-hook/{chat_id}",
                "hook_send_email_secrets": f"v1,whsec_{hook_secret}",
            }
        if app_url:
            allowed = [entry for entry in (current.get("uri_allow_list") or "").split(",") if entry]
            auth["uri_allow_list"] = ",".join(dict.fromkeys([*allowed, f"{app_url}/**"]))
            if created or not current.get("site_url"):
                auth["site_url"] = app_url
        if auth:
            await client.call(user_id, "PATCH", f"/v1/projects/{ref}/config/auth", json=auth)
    except (DetailedHTTPException, KeyError) as exc:
        logger.warning("Supabase link failed chat=%s error_type=%s", chat_id, type(exc).__name__)
        message = exc.detail if isinstance(exc, DetailedHTTPException) else None
        await save_status(chat_id, "error", message=message or "Couldn't set up your Supabase project.")
        return
    # The session pooler: IPv4 (sandboxes have no IPv6), and session mode, which migrations need. It listens on
    # 5432 of the pooler host; the config's own port is the transaction pooler's.
    values |= {
        "database_url": f"postgresql://{values['db_user']}.{ref}:{values['db_password']}"
        f"@{pooler['db_host']}:5432/{pooler['db_name']}",
        "url": f"https://{ref}.supabase.co",
        "publishable_key": publishable,
        "secret_key": secret_key,
        "hook_secret": hook_secret,
    }
    async with AutocommitSessionLocal() as db:
        await db.execute(
            update(ProjectDatabase)
            .where(ProjectDatabase.chat_id == chat_id)
            .values(secret=client.seal(values), status="moving", updated_at=datetime.now(UTC))
        )
    # A preview running now reopens, which copies the data in and restarts the app on Supabase; otherwise the next
    # open or build does it.
    await refresh_app(chat_id, user_id)


async def refresh_app(chat_id: str, user_id: int) -> None:
    """A running preview reopens with the app's current values: after a link is ready to move, and after unlink."""
    # Imported here to break a real cycle: the run service imports this domain's sandbox module, which imports this one.
    from agent.run.service import agent_service

    await agent_service.apply_secrets(chat_id, user_id)


async def unlink(db: AsyncSession, chat: Chat) -> tuple[str, int]:
    """Drops the link; the app goes back to its built-in database and the Supabase data stays. Returns (ref,
    owner) for `disable_hook` after the response."""
    ref = await db.scalar(
        delete(ProjectDatabase).where(ProjectDatabase.chat_id == chat.id).returning(ProjectDatabase.project_ref)
    )
    if ref is None:
        raise DatabaseNotLinked
    return ref, chat.user_id


async def disable_hook(ref: str, user_id: int, chat_id: str) -> None:
    """Background, best effort: Supabase Auth sends its own emails again instead of calling a route that now
    refuses them. Only this app's hook: another app linked to the project may own it."""
    try:
        current = await client.call(user_id, "GET", f"/v1/projects/{ref}/config/auth")
        if (current.get("hook_send_email_uri") or "").endswith(f"/email-hook/{chat_id}"):
            await client.call(
                user_id, "PATCH", f"/v1/projects/{ref}/config/auth", json={"hook_send_email_enabled": False}
            )
    except DetailedHTTPException as exc:
        logger.warning("Supabase hook not turned off ref=%s error_type=%s", ref, type(exc).__name__)
