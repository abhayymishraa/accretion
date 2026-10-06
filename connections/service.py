"""Connected MCP servers: the user's library, how each signs in, the tools the user approved, and which servers
each project uses. All network access goes through agent/tools/mcp.py."""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import urlsplit

from redis import RedisError
from sqlalchemy import any_, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.run import bus
from agent.tools import mcp
from auth.schemas import TokenUser
from connections.catalog import BY_ID, CATALOG
from connections.exceptions import (
    IconInvalid,
    ServerAddressInvalid,
    ServerNameReserved,
    ServerNameTaken,
    ServerNotFound,
    ServerUnavailable,
    SignInExpired,
    SignInUnavailable,
)
from connections.schemas import (
    CatalogEntry,
    CatalogList,
    IconSave,
    KeySave,
    ProjectServer,
    ProjectServerList,
    ServerCreate,
    ServerDetail,
    ServerList,
    SignInFinish,
    SignInStart,
    ToolInfo,
)
from db.models import Chat, McpServer
from exceptions import BadRequest
from projects.exceptions import ProjectNotFound

_SIGN_IN_SECONDS = 600
_SLUG = re.compile(r"[^a-z0-9-]+")
# Host labels that say nothing about which service it is: "mcp.notion.com" is "notion".
_GENERIC = {"mcp", "www", "api", "docs", "server", "com", "net", "org", "io", "app", "dev", "co", "ai", "sh"}


def _entry(row: McpServer) -> dict[str, Any] | None:
    """The catalog entry a server was added from: same id and address."""
    entry = BY_ID.get(row.name)
    return dict(entry) if entry and entry["url"] == row.url else None


def _detail(row: McpServer) -> ServerDetail:
    entry = _entry(row)
    return ServerDetail(
        id=row.id,
        name=row.name,
        title=row.title,
        description=row.description,
        url=row.url,
        auth=cast(mcp.Auth, row.auth),
        key_hint=entry["key_hint"] if entry else None,
        connected=row.auth == "none" or bool(row.secret),
        enabled=row.enabled,
        icon=row.icon,
        tools=[
            ToolInfo(
                name=tool["name"],
                description=tool["description"],
                read_only=tool["read_only"],
                approved=bool(tool.get("approved")),
                changed=bool(tool.get("changed")),
            )
            for tool in row.tools
        ],
    )


def _server(row: McpServer) -> mcp.Server:
    return mcp.Server(
        id=row.id,
        name=row.name,
        title=row.title,
        url=row.url,
        auth=cast(mcp.Auth, row.auth),
        description=row.description,
        header_name=row.header_name,
        secret=row.secret,
        tools=row.tools,
    )


def _name_from(url: str) -> str:
    labels = [label for label in (urlsplit(url).hostname or "").split(".") if label not in _GENERIC]
    return _SLUG.sub("-", (labels[0] if labels else "server").lower()).strip("-")[:48] or "server"


def _merged(old: list[dict[str, Any]], listed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The listed tools, keeping each approval whose tool is unchanged. A changed tool loses its approval and is
    marked, so the user sees what to review; a new tool starts unapproved."""
    before = {tool["name"]: tool for tool in old}
    merged = []
    for tool in listed:
        prior = before.get(tool["name"])
        same = prior is not None and prior["fingerprint"] == tool["fingerprint"]
        merged.append(
            {
                **tool,
                "approved": bool(prior and prior.get("approved") and same),
                "changed": bool(prior and not same and (prior.get("approved") or prior.get("changed"))),
            }
        )
    return merged


async def _owned(db: AsyncSession, user: TokenUser, server_id: str) -> McpServer:
    row = await db.scalar(select(McpServer).where(McpServer.id == server_id, McpServer.user_id == user.id))
    if row is None:
        raise ServerNotFound
    return row


async def _save(db: AsyncSession, row: McpServer, **values: Any) -> McpServer:
    saved = await db.scalar(
        update(McpServer)
        .where(McpServer.id == row.id)
        .values(**values, updated_at=datetime.now(UTC))
        .returning(McpServer)
        # The session already holds this row; without populate_existing RETURNING hands back that stale copy.
        .execution_options(synchronize_session=False, populate_existing=True)
    )
    assert saved is not None, "the row was loaded for this user in the same request"
    return saved


async def _refresh(db: AsyncSession, row: McpServer) -> McpServer:
    try:
        listed, icon_src = await mcp.list_tools(_server(row))
    except mcp.McpError as exc:
        raise ServerUnavailable(str(exc)) from None
    entry = _entry(row)
    if entry and entry["read_only"]:
        listed = [{**tool, "read_only": True} for tool in listed]
    # Fetched once, and only for a server added by address: a catalog service shows its own vendored logo, and a
    # logo already stored, the server's or the user's upload, is kept.
    icon = row.icon or (icon_src and not entry and await mcp.fetch_icon(icon_src)) or None
    return await _save(db, row, tools=_merged(row.tools, listed), icon=icon)


def catalog() -> CatalogList:
    # The entries' other keys (header name, read-only) are server-side; the schema drops them.
    return CatalogList(servers=[CatalogEntry.model_validate(entry) for entry in CATALOG])


async def list_servers(db: AsyncSession, user: TokenUser) -> ServerList:
    rows = await db.scalars(select(McpServer).where(McpServer.user_id == user.id).order_by(McpServer.created_at))
    return ServerList(servers=[_detail(row) for row in rows])


async def add_server(db: AsyncSession, user: TokenUser, payload: ServerCreate) -> ServerDetail:
    entry = BY_ID.get(payload.catalog_id) if payload.catalog_id else None
    if payload.catalog_id and entry is None:
        raise ServerNotFound
    url = entry["url"] if entry else (payload.url or "")
    try:
        auth = entry["auth"] if entry else await mcp.detect_auth(url)
    except mcp.AddressRefused as exc:
        raise ServerAddressInvalid(str(exc)) from None
    except mcp.McpError as exc:
        raise ServerUnavailable(str(exc)) from None
    name = entry["id"] if entry else _name_from(url)
    if name in mcp.RESERVED_NAMES:
        raise ServerNameReserved
    now = datetime.now(UTC)
    try:
        row = await db.scalar(
            insert(McpServer)
            .values(
                id=str(uuid.uuid4()),
                user_id=user.id,
                name=name,
                title=payload.title or (entry["title"] if entry else urlsplit(url).hostname or name),
                description=entry["description"] if entry else "",
                url=url,
                auth=auth,
                header_name=entry["header_name"] if entry else None,
                tools=[],
                enabled=True,
                created_at=now,
                updated_at=now,
            )
            .returning(McpServer)
        )
    except IntegrityError:
        raise ServerNameTaken from None
    assert row is not None, "INSERT ... RETURNING returns the row"
    # An open server lists its tools at once, for the user to approve; the others list them once signed in.
    if auth == "none":
        try:
            row = await _refresh(db, row)
        except ServerUnavailable:
            # The row is saved already: a retry here would hit the name conflict. The user lists the tools again
            # from the service's page.
            pass
    return _detail(row)


async def save_key(db: AsyncSession, user: TokenUser, server_id: str, payload: KeySave) -> ServerDetail:
    """A key for a server that takes one in a header. A server added as open can take one too, e.g. for a
    higher rate limit."""
    row = await _owned(db, user, server_id)
    entry = _entry(row)
    if row.auth == "oauth" and entry:
        raise BadRequest("This server signs in with its own page, not a key.")
    # A row added before its catalog entry took a key has no header yet; the entry names it. A server added by
    # address takes the header the user names, then the one saved before. Else, and for every Authorization
    # header, the key goes as a bearer token unless it already names its scheme.
    header = (
        (entry and (row.header_name or entry["header_name"]))
        or payload.header_name
        or row.header_name
        or "Authorization"
    )
    prefix = "Bearer " if header.lower() == "authorization" and " " not in payload.value else ""
    row = await _save(db, row, auth="header", header_name=header, secret=mcp.seal({"value": prefix + payload.value}))
    return _detail(await _refresh(db, row))


async def clear_credentials(db: AsyncSession, user: TokenUser, server_id: str) -> ServerDetail:
    """No sign-in: a server added by address drops its key or tokens and is called anonymously."""
    row = await _owned(db, user, server_id)
    if _entry(row):
        raise BadRequest("This service signs in the way its catalog entry says.")
    row = await _save(db, row, auth="none", header_name=None, secret=None)
    return _detail(await _refresh(db, row))


async def save_icon(db: AsyncSession, user: TokenUser, server_id: str, payload: IconSave) -> ServerDetail:
    """The user's own logo for a server, in place of the one the server names."""
    row = await _owned(db, user, server_id)
    icon = mcp.data_uri_icon(payload.data_uri)
    if icon is None:
        raise IconInvalid
    return _detail(await _save(db, row, icon=icon))


async def refresh_tools(db: AsyncSession, user: TokenUser, server_id: str) -> ServerDetail:
    return _detail(await _refresh(db, await _owned(db, user, server_id)))


async def approve_tools(db: AsyncSession, user: TokenUser, server_id: str, approved: list[str]) -> ServerDetail:
    row = await _owned(db, user, server_id)
    wanted = set(approved)
    tools = [
        {
            **tool,
            "approved": tool["name"] in wanted,
            "changed": bool(tool.get("changed")) and tool["name"] not in wanted,
        }
        for tool in row.tools
    ]
    return _detail(await _save(db, row, tools=tools))


async def set_enabled(db: AsyncSession, user: TokenUser, server_id: str, enabled: bool) -> ServerDetail:
    return _detail(await _save(db, await _owned(db, user, server_id), enabled=enabled))


async def delete_server(db: AsyncSession, user: TokenUser, server_id: str) -> None:
    """Deletes the server and drops its name from every project's turned-off list, in one statement, so a new
    server with the same name starts on."""
    gone = (
        delete(McpServer)
        .where(McpServer.id == server_id, McpServer.user_id == user.id)
        .returning(McpServer.name)
        .cte("gone")
    )
    name = select(gone.c.name).scalar_subquery()
    cleaned = (
        update(Chat)
        .where(Chat.user_id == user.id, name == any_(Chat.disabled_mcp_servers))
        .values(disabled_mcp_servers=func.array_remove(Chat.disabled_mcp_servers, name))
        .cte("cleaned")
    )
    if await db.scalar(select(gone.c.name).add_cte(cleaned)) is None:
        raise ServerNotFound


async def begin_sign_in(db: AsyncSession, user: TokenUser, server_id: str) -> SignInStart:
    row = await _owned(db, user, server_id)
    # A server added by address may sign in whatever it was detected as; the server says whether it can.
    if row.auth != "oauth" and _entry(row):
        raise BadRequest("This server does not sign in with its own page.")
    try:
        url, flow = await mcp.begin_sign_in(_server(row))
    except mcp.McpError as exc:
        raise ServerUnavailable(str(exc)) from None
    # Bound to this user and this server: the callback page finishes it signed in, so a link someone else
    # started can never put their account on this user's server (LibreChat CVE-2026-31944).
    flow |= {"user_id": user.id, "server_id": row.id}
    try:
        await bus.client.set(f"accretion:mcp:sign-in:{flow['state']}", json.dumps(flow), ex=_SIGN_IN_SECONDS)
    except RedisError:
        raise SignInUnavailable from None
    return SignInStart(authorization_url=url)


async def finish_sign_in(db: AsyncSession, user: TokenUser, payload: SignInFinish) -> ServerDetail:
    try:
        stored = await bus.client.getdel(f"accretion:mcp:sign-in:{payload.state}")
    except RedisError:
        raise SignInUnavailable from None
    flow = json.loads(stored) if stored else None
    if flow is None or flow["user_id"] != user.id:
        raise SignInExpired
    row = await _owned(db, user, flow["server_id"])
    try:
        credentials = await mcp.finish_sign_in(flow, payload.code, payload.iss)
    except mcp.McpError as exc:
        raise ServerUnavailable(str(exc)) from None
    row = await _save(db, row, auth="oauth", header_name=None, secret=mcp.seal(credentials))
    return _detail(await _refresh(db, row))


async def project_servers(db: AsyncSession, user: TokenUser, project_id: str) -> ProjectServerList:
    """In one query: the project's turned-off list and the user's servers."""
    pairs = [
        part
        for column in (
            McpServer.name,
            McpServer.title,
            McpServer.description,
            McpServer.enabled,
            McpServer.auth,
            McpServer.icon,
        )
        for part in (column.key, column)
    ]
    servers = (
        select(
            func.coalesce(
                func.json_agg(
                    func.json_build_object(
                        *pairs,
                        "connected",
                        (McpServer.auth == "none") | McpServer.secret.is_not(None),
                        "tool_count",
                        func.jsonb_array_length(McpServer.tools),
                    )
                ),
                func.json_build_array(),
            )
        )
        .where(McpServer.user_id == user.id)
        .scalar_subquery()
    )
    found = (
        await db.execute(
            select(Chat.disabled_mcp_servers, servers).where(Chat.id == project_id, Chat.user_id == user.id)
        )
    ).first()
    if found is None:
        raise ProjectNotFound
    off, rows = found
    return ProjectServerList(
        servers=[
            ProjectServer(
                name=row["name"],
                title=row["title"],
                description=row["description"],
                enabled=row["enabled"] and row["name"] not in off,
                account_enabled=row["enabled"],
                connected=row["connected"],
                tool_count=row["tool_count"],
                icon=row["icon"],
            )
            for row in rows
        ]
    )


async def set_project_server(db: AsyncSession, user: TokenUser, project_id: str, name: str, enabled: bool) -> None:
    """Only turned-off servers are stored, so turning one on removes it from the list."""
    others = func.array_remove(Chat.disabled_mcp_servers, name)
    found = await db.scalar(
        update(Chat)
        .where(Chat.id == project_id, Chat.user_id == user.id)
        .values(disabled_mcp_servers=others if enabled else func.array_append(others, name))
        .returning(Chat.id)
    )
    if found is None:
        raise ProjectNotFound
