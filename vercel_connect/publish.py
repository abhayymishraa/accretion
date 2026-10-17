"""Publishing an app to its owner's Vercel account, as Vercel's own CLI deploys: create the project once, set its
variables, upload the latest saved revision's files, create a production deployment, and wait until it is ready.

The database is the user's: they add Neon (Postgres) or MongoDB Atlas to the project on Vercel, because an
Integration's token cannot create marketplace databases. A project linked to Supabase uses that database instead.
"""

import asyncio
import io
import logging
import re
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from sqlalchemy import Text, delete, literal, or_, select, update
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent import events
from agent.sandbox import project
from agent.sandbox import secrets as sandbox_secrets
from agent.sandbox.kits import KITS, Kit
from agent.storage import persistence
from agent.storage.storage import StorageError
from db.base import AutocommitSessionLocal
from db.models import Chat
from vercel_connect import bundle, client
from vercel_connect.exceptions import (
    NotConnected,
    NothingToPublish,
    PublishRunning,
    Reconnect,
    VercelRefused,
    VercelUnavailable,
)
from vercel_connect.models import ProjectPublish, VercelAccount
from vercel_connect.schemas import PublishOut
from vercel_connect.service import require_configured

logger = logging.getLogger("webbuilder.vercel")

_RUNNING = ("uploading", "building")
# A publish still running after this was cut off by a restart: it reads as failed and can start again.
_STALE = timedelta(minutes=30)
# Vercel builds most apps within two minutes; twenty is the ceiling for a cold dependency install.
_POLL_SECONDS = 5
_POLL_LIMIT = 240
_UPLOADS = 8
_TARGETS = ["production", "preview"]
_LOG_LINES = 30
_MESSAGES = {
    "uploading": "Uploading your app…",
    "building": "Vercel is building your app…",
    "live": "Your app is live.",
}
_DATABASE_MESSAGES = {
    "postgres": "Add a free Neon database to this app on Vercel, then publish again.",
    "mongo": "Add a free MongoDB Atlas database to this app on Vercel, then publish again.",
}
_STOPPED = "Publishing stopped before it finished. Try again."
# Terminal colour codes in Vercel's build output.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


class _BuildFailed(Exception):
    def __init__(self, message: str, log: list[str]) -> None:
        super().__init__(message)
        self.log = log


def _dashboard(name: str, page: str = "") -> str:
    # Vercel resolves [team] to the signed-in user's team that owns the project.
    return "https://vercel.com/d?to=" + quote(f"/[team]/{name}{page}", safe="")


def _stale(row: ProjectPublish) -> bool:
    return row.status in _RUNNING and row.updated_at < datetime.now(UTC) - _STALE


def view(chat: Chat, row: ProjectPublish | None) -> PublishOut:
    database = KITS[chat.kit].database
    if row is None:
        return PublishOut(status="none", database=database)
    stale = _stale(row)
    status = "failed" if stale else row.status
    name = row.project_name
    return PublishOut(
        status=status,
        url=row.url,
        published_at=row.published_at,
        current=row.url is not None and row.revision_id == chat.latest_saved_revision_id,
        message=_STOPPED if stale else row.detail.get("message"),
        dashboard_url=(_dashboard(name, "/stores") if status == "database" else _dashboard(name)) if name else None,
        logs_url=row.detail.get("logs_url"),
        log=row.detail.get("log", []) if status == "failed" else [],
        database=database,
    )


async def status(db: AsyncSession, chat: Chat) -> PublishOut:
    return view(chat, await db.get(ProjectPublish, chat.id))


async def start(db: AsyncSession, user_id: int, chat: Chat) -> PublishOut:
    """Marks the publish as running in one statement, unless one is running already. The work runs after the
    reply (`run`)."""
    require_configured()
    if chat.latest_saved_revision_id is None:
        raise NothingToPublish
    if await db.scalar(select(VercelAccount.user_id).where(VercelAccount.user_id == user_id)) is None:
        raise NotConnected
    now = datetime.now(UTC)
    detail = {"message": _MESSAGES["uploading"]}
    new = insert(ProjectPublish).values(chat_id=chat.id, status="uploading", detail=detail, updated_at=now)
    row = await db.scalar(
        new.on_conflict_do_update(
            index_elements=[ProjectPublish.chat_id],
            # The names of the variables this app set stay: the next publish removes the ones it no longer sets.
            set_={
                "status": "uploading",
                "detail": ProjectPublish.detail.op("-")(literal(["message", "log", "logs_url"], ARRAY(Text))).op("||")(
                    literal(detail, JSONB)
                ),
                "updated_at": now,
            },
            where=or_(ProjectPublish.status.not_in(_RUNNING), ProjectPublish.updated_at < now - _STALE),
        ).returning(ProjectPublish)
    )
    if row is None:
        raise PublishRunning
    return view(chat, row)


async def _save(chat_id: str, status: str, message: str | None = None, **values: Any) -> None:
    """One statement; `detail` keys given in `values` are merged into the row's detail."""
    detail = values.pop("detail", {}) | {"message": message or _MESSAGES.get(status)}
    async with AutocommitSessionLocal() as db:
        await db.execute(
            update(ProjectPublish)
            .where(ProjectPublish.chat_id == chat_id)
            .values(
                status=status,
                detail=ProjectPublish.detail.op("||")(literal(detail, JSONB)),
                updated_at=datetime.now(UTC),
                **values,
            )
        )


async def run(chat_id: str, user_id: int) -> None:
    """The publish itself, after the reply. Whatever stops it, the row ends as failed or live, never running."""
    finished = False
    try:
        await _publish(chat_id, user_id)
        finished = True
    except Reconnect:
        await _save(chat_id, "failed", "Connect Vercel again, then publish.")
        finished = True
    except bundle.NotPublishable as error:
        await _save(chat_id, "failed", str(error))
        finished = True
    except _BuildFailed as error:
        await _save(chat_id, "failed", str(error), detail={"log": error.log})
        finished = True
    except VercelRefused as error:
        await _save(chat_id, "failed", f"Vercel refused the publish: {error.detail}")
        finished = True
    except (VercelUnavailable, StorageError):
        await _save(chat_id, "failed", "Couldn't reach Vercel. Try again in a moment.")
        finished = True
    finally:
        if not finished:
            logger.exception("Publish of %s stopped", chat_id)
            await _save(chat_id, "failed", _STOPPED)


def _unzip(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


async def _publish(chat_id: str, user_id: int) -> None:
    async with AutocommitSessionLocal() as db:
        chat = await db.get(Chat, chat_id)
        row = await db.get(ProjectPublish, chat_id)
    assert chat is not None and row is not None, "start() stored the row; the project cascade deletes it"
    kit = KITS[chat.kit]
    vercel = await client.session(user_id)
    revision = await persistence.latest_revision(chat_id)
    if revision is None:
        raise bundle.NotPublishable(NothingToPublish.DETAIL)
    files = bundle.files(kit.id, await asyncio.to_thread(_unzip, await persistence.revision_bytes(revision)))
    project_id, name = await _project(vercel, chat, kit, row)
    await _save(chat_id, "uploading", vercel_project_id=project_id, project_name=name)
    values = await _environment(vercel, chat, kit, project_id, set(row.detail.get("env", [])))
    if values is None:
        await _save(chat_id, "database", _DATABASE_MESSAGES[kit.database])
        return
    deployment = await _deploy(vercel, chat_id, kit, project_id, name, files)
    url = await _wait(vercel, deployment, set(values.values()))
    await _save(
        chat_id,
        "live",
        url=url,
        revision_id=revision.id,
        published_at=datetime.now(UTC),
    )


def _slug(title: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:40].strip("-") or "app"


async def _project(vercel: client.Session, chat: Chat, kit: Kit, row: ProjectPublish) -> tuple[str, str]:
    """The app's Vercel project: the one it published to before, or a new one. A name Vercel already has gets a
    longer piece of the app's id."""
    if row.vercel_project_id:
        found = await vercel.call_allowing_missing("GET", f"/v9/projects/{row.vercel_project_id}")
        if found:
            return str(found["id"]), str(found["name"])
    for length in (6, 12, 32):
        name = f"{_slug(chat.title)}-{chat.id.replace('-', '')[:length]}"
        try:
            created = await vercel.call(
                "POST",
                "/v11/projects",
                # Vercel's default protection leaves the production address public; Integrations cannot change it.
                json={"name": name, "framework": bundle.framework(kit.id)},
            )
        except VercelRefused as error:
            if error.vercel_status == 409:
                continue
            raise
        return str(created["id"]), str(created["name"])
    raise VercelRefused("Couldn't find a free project name on Vercel.")


async def _value(vercel: client.Session, project_id: str, env: dict[str, Any]) -> str:
    found = await vercel.call("GET", f"/v10/projects/{project_id}/env/{env['id']}")
    return str(found["value"])


async def _environment(
    vercel: client.Session, chat: Chat, kit: Kit, project_id: str, owned: set[str]
) -> dict[str, str] | None:
    """Sets the app's variables on the project: the kit's keys, the platform's, the user's, and the database
    address in the name the kit reads. None when the project has no database yet."""
    listed = {env["key"]: env for env in (await vercel.call("GET", f"/v10/projects/{project_id}/env"))["envs"]}
    # Variables someone else put on the project: a database Integration's, or one the user set on Vercel.
    theirs = {key: env for key, env in listed.items() if key not in owned}
    kit_values, user = await sandbox_secrets.ensure_secrets(chat.id, kit)
    # The kit's generated keys only: its derived database address points at the sandbox's own database.
    values = {name: kit_values[name] for name in kit.env} | await project.app_env(chat.id, kit.id) | user
    if kit.database == "mongo" and "MONGO_URL" not in values and "MONGO_URL" not in theirs:
        if "MONGODB_URI" not in theirs:
            return None
        values["MONGO_URL"] = await _value(vercel, project_id, theirs["MONGODB_URI"])
    if kit.database == "postgres" and "DATABASE_URL" not in values and "DATABASE_URL" not in theirs:
        if "POSTGRES_URL" not in theirs:
            return None
        values["DATABASE_URL"] = await _value(vercel, project_id, theirs["POSTGRES_URL"])
    values = {key: value for key, value in values.items() if value}
    await vercel.call(
        "POST",
        f"/v10/projects/{project_id}/env",
        params={"upsert": "true"},
        json=[{"key": key, "value": value, "type": "encrypted", "target": _TARGETS} for key, value in values.items()],
    )
    for key in owned - values.keys():
        if key in listed:
            await vercel.call_allowing_missing("DELETE", f"/v9/projects/{project_id}/env/{listed[key]['id']}")
    await _save(chat.id, "uploading", detail={"env": sorted(values)})
    return values


async def _deploy(
    vercel: client.Session, chat_id: str, kit: Kit, project_id: str, name: str, files: dict[str, bytes]
) -> str:
    """Uploads every file (Vercel keeps one copy per content, so an unchanged file costs one quick call), then
    creates the production deployment from them."""
    limit = asyncio.Semaphore(_UPLOADS)

    async def upload(path: str, data: bytes) -> dict[str, Any]:
        async with limit:
            return {"file": path, "sha": await vercel.upload(data), "size": len(data)}

    listed = await asyncio.gather(*(upload(path, data) for path, data in sorted(files.items())))
    created = await vercel.call(
        "POST",
        "/v13/deployments",
        params={"skipAutoDetectionConfirmation": "1"},
        json={
            "name": name,
            "project": project_id,
            "target": "production",
            "files": listed,
            "projectSettings": {"framework": bundle.framework(kit.id)},
        },
    )
    deployment = str(created["id"])
    await _save(chat_id, "building", detail={"logs_url": created.get("inspectorUrl")})
    return deployment


async def _log(vercel: client.Session, deployment: str, secrets: set[str]) -> list[str]:
    """The end of the build log, with the app's variable values hidden, for the user and the builder."""
    try:
        listed = await vercel.call(
            "GET", f"/v3/deployments/{deployment}/events", params={"builds": 1, "direction": "backward", "limit": 200}
        )
    except (VercelRefused, VercelUnavailable):
        return []
    lines = [str(event.get("text") or event.get("payload", {}).get("text") or "") for event in reversed(listed or [])]
    forms = events.secret_forms(secrets)
    return [events.hide_secrets(_ANSI.sub("", line), forms) for line in lines if line.strip()][-_LOG_LINES:]


async def _wait(vercel: client.Session, deployment: str, secrets: set[str]) -> str:
    """The deployment's public address once Vercel has built it."""
    for _ in range(_POLL_LIMIT):
        await asyncio.sleep(_POLL_SECONDS)
        found = await vercel.call("GET", f"/v13/deployments/{deployment}")
        state = found.get("readyState")
        if state == "READY":
            aliases = sorted(found.get("alias") or [], key=len)
            return f"https://{aliases[0] if aliases else found['url']}"
        if state in ("ERROR", "CANCELED"):
            reason = found.get("errorMessage") or "The build failed."
            raise _BuildFailed(f"Vercel couldn't build the app: {reason}", await _log(vercel, deployment, secrets))
    raise _BuildFailed("Vercel took too long to build the app. Try again.", [])


async def unpublish(db: AsyncSession, user_id: int, chat: Chat) -> None:
    """Deletes the app's Vercel project, so its address stops working. The database the user added stays in
    their Vercel account."""
    row = await db.get(ProjectPublish, chat.id)
    if row is None:
        return
    if row.status in _RUNNING and not _stale(row):
        raise PublishRunning
    if row.vercel_project_id:
        vercel = await client.session(user_id)
        await vercel.call_allowing_missing("DELETE", f"/v9/projects/{row.vercel_project_id}")
    await db.execute(delete(ProjectPublish).where(ProjectPublish.chat_id == chat.id))
