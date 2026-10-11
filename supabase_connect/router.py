"""Supabase: the user's sign-in, each app's Supabase project, and Supabase Auth's email hook."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Path, Query, Request, Response

from auth.dependencies import CurrentUser
from db.base import Autocommit, DbSession
from projects.dependencies import OwnedProject
from supabase_connect import emailhook, service
from supabase_connect.schemas import (
    AccountOut,
    ConnectFinish,
    ConnectStart,
    DatabaseOut,
    LinkDatabase,
    ProjectList,
    RegionList,
)

router = APIRouter()


@router.get("/supabase/account", dependencies=[Autocommit])
async def get_account(current_user: CurrentUser, db: DbSession) -> AccountOut:
    return await service.account(db, current_user)


@router.post("/supabase/connect")
async def begin_connect(current_user: CurrentUser) -> ConnectStart:
    return await service.begin_connect(current_user)


@router.post("/supabase/connect/complete", dependencies=[Autocommit])
async def finish_connect(payload: ConnectFinish, current_user: CurrentUser, db: DbSession) -> AccountOut:
    """Called by the signed-in callback page, so the sign-in is finished by the user who started it."""
    return await service.finish_connect(db, current_user, payload)


@router.delete("/supabase/account", status_code=204, dependencies=[Autocommit])
async def disconnect(current_user: CurrentUser, db: DbSession) -> None:
    await service.disconnect(db, current_user)


@router.get("/supabase/projects")
async def list_projects(
    current_user: CurrentUser, organization_id: Annotated[str, Query(pattern=r"^[\w-]+$", max_length=64)]
) -> ProjectList:
    return await service.projects(current_user, organization_id)


@router.get("/supabase/regions")
async def list_regions(_: CurrentUser) -> RegionList:
    return service.regions()


@router.get("/projects/{project_id}/database", dependencies=[Autocommit])
async def get_database(project_id: str, current_user: CurrentUser, db: DbSession) -> DatabaseOut:
    return await service.database(db, current_user, project_id)


@router.post("/projects/{project_id}/database", status_code=201, dependencies=[Autocommit])
async def link_database(
    payload: LinkDatabase,
    chat: OwnedProject,
    current_user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> DatabaseOut:
    linked = await service.link(db, current_user, chat, payload)
    background.add_task(service.finish_link, chat.id, current_user.id, chat.app_url)
    return linked


@router.delete("/projects/{project_id}/database", status_code=204, dependencies=[Autocommit])
async def unlink_database(chat: OwnedProject, db: DbSession, background: BackgroundTasks) -> None:
    ref, owner = await service.unlink(db, chat)
    background.add_task(service.disable_hook, ref, owner, chat.id)
    background.add_task(service.refresh_app, chat.id, owner)


@router.post("/supabase/email-hook/{chat_id}")
async def email_hook(chat_id: Annotated[str, Path(max_length=36)], request: Request) -> Response:
    """Called by Supabase Auth, not a signed-in user: the signature is the authentication."""
    await emailhook.handle(chat_id, await request.body(), dict(request.headers))
    return Response(content="{}", media_type="application/json")
