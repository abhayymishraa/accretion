"""Connections: the MCP servers a user connects, and which ones each project uses."""

from typing import Annotated

from fastapi import APIRouter, Path

from auth.dependencies import CurrentUser
from connections import service
from connections.schemas import (
    CatalogList,
    IconSave,
    KeySave,
    ProjectServerList,
    ServerCreate,
    ServerDetail,
    ServerList,
    ServerName,
    ServerToggle,
    SignInFinish,
    SignInStart,
    ToolApproval,
)
from db.base import Autocommit, DbSession

router = APIRouter()


@router.get("/mcp-catalog")
async def get_catalog(_: CurrentUser) -> CatalogList:
    return service.catalog()


@router.get("/mcp-servers", dependencies=[Autocommit])
async def list_servers(current_user: CurrentUser, db: DbSession) -> ServerList:
    return await service.list_servers(db, current_user)


@router.post("/mcp-servers", status_code=201, dependencies=[Autocommit])
async def add_server(payload: ServerCreate, current_user: CurrentUser, db: DbSession) -> ServerDetail:
    return await service.add_server(db, current_user, payload)


@router.post("/mcp-servers/sign-in/complete", dependencies=[Autocommit])
async def finish_sign_in(payload: SignInFinish, current_user: CurrentUser, db: DbSession) -> ServerDetail:
    """Called by the signed-in callback page, so the sign-in is finished by the user who started it."""
    return await service.finish_sign_in(db, current_user, payload)


@router.put("/mcp-servers/{server_id}/key", dependencies=[Autocommit])
async def save_key(server_id: str, payload: KeySave, current_user: CurrentUser, db: DbSession) -> ServerDetail:
    return await service.save_key(db, current_user, server_id, payload)


@router.delete("/mcp-servers/{server_id}/key", dependencies=[Autocommit])
async def clear_credentials(server_id: str, current_user: CurrentUser, db: DbSession) -> ServerDetail:
    """No sign-in, for a server added by address: its key or tokens are dropped."""
    return await service.clear_credentials(db, current_user, server_id)


@router.put("/mcp-servers/{server_id}/icon", dependencies=[Autocommit])
async def save_icon(server_id: str, payload: IconSave, current_user: CurrentUser, db: DbSession) -> ServerDetail:
    return await service.save_icon(db, current_user, server_id, payload)


@router.post("/mcp-servers/{server_id}/sign-in", dependencies=[Autocommit])
async def begin_sign_in(server_id: str, current_user: CurrentUser, db: DbSession) -> SignInStart:
    return await service.begin_sign_in(db, current_user, server_id)


@router.post("/mcp-servers/{server_id}/tools/refresh", dependencies=[Autocommit])
async def refresh_tools(server_id: str, current_user: CurrentUser, db: DbSession) -> ServerDetail:
    return await service.refresh_tools(db, current_user, server_id)


@router.put("/mcp-servers/{server_id}/tools", dependencies=[Autocommit])
async def approve_tools(
    server_id: str, payload: ToolApproval, current_user: CurrentUser, db: DbSession
) -> ServerDetail:
    return await service.approve_tools(db, current_user, server_id, payload.approved)


@router.patch("/mcp-servers/{server_id}", dependencies=[Autocommit])
async def set_enabled(server_id: str, payload: ServerToggle, current_user: CurrentUser, db: DbSession) -> ServerDetail:
    """On or off for every project of this account; its sign-in is kept."""
    return await service.set_enabled(db, current_user, server_id, payload.enabled)


@router.delete("/mcp-servers/{server_id}", status_code=204, dependencies=[Autocommit])
async def delete_server(server_id: str, current_user: CurrentUser, db: DbSession) -> None:
    await service.delete_server(db, current_user, server_id)


@router.get("/projects/{project_id}/mcp-servers", dependencies=[Autocommit])
async def list_project_servers(project_id: str, current_user: CurrentUser, db: DbSession) -> ProjectServerList:
    return await service.project_servers(db, current_user, project_id)


@router.put("/projects/{project_id}/mcp-servers/{server_name}", status_code=204, dependencies=[Autocommit])
async def set_project_server(
    project_id: str,
    server_name: Annotated[ServerName, Path()],
    payload: ServerToggle,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    await service.set_project_server(db, current_user, project_id, server_name, payload.enabled)
