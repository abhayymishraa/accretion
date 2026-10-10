"""Projects: the chat that owns a generated app, its history and its lifecycle."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Path, Response

from agent.sandbox import secrets as sandbox_secrets
from auth.dependencies import CurrentUser
from db.base import Autocommit, DbSession
from projects import service
from projects.constants import DEFAULT_MESSAGE_PAGE
from projects.dependencies import OwnedProject
from projects.schemas import (
    MessagePage,
    ProjectList,
    ProjectRef,
    ProjectRename,
    ProjectSecrets,
    ProjectSecretValue,
    RunAdmission,
)
from request_timing import timed
from runs.schemas import ChatPayload

router = APIRouter()


@router.get("/projects/{project_id}/messages", dependencies=[Autocommit])
@timed("history")
async def get_chat_messages(
    project_id: str,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = DEFAULT_MESSAGE_PAGE,
    before: str | None = None,
) -> MessagePage:
    """Get message history for a chat"""
    return await service.message_page(db, project_id, current_user, limit, before)


@router.post("/projects")
async def create_project(payload: ChatPayload, current_user: CurrentUser) -> RunAdmission:
    return await service.start_project(current_user, payload.prompt, payload.mode, payload.model_choice)


@router.get("/projects", dependencies=[Autocommit])
async def list_user_projects(current_user: CurrentUser, db: DbSession) -> ProjectList:
    """List projects by the latest accepted prompt, falling back to creation."""
    return await service.list_projects(db, current_user)


@router.get("/projects/{project_id}/covers/{cover_id}", dependencies=[Autocommit])
async def get_project_cover(cover_id: str, project: OwnedProject) -> Response:
    data = await service.cover(project, cover_id)
    # Stored once under a random id and never rewritten, so the browser may keep it.
    return Response(data, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.patch("/projects/{project_id}", dependencies=[Autocommit])
async def rename_project(
    project_id: str, payload: ProjectRename, current_user: CurrentUser, db: DbSession
) -> ProjectRef:
    return await service.rename_project(db, project_id, current_user, payload.title)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str, current_user: CurrentUser, background: BackgroundTasks, db: DbSession
) -> None:
    await service.delete_project(db, project_id, current_user, background)


SecretName = Annotated[str, Path(pattern=f"^{sandbox_secrets.NAME.pattern}$")]


@router.get("/projects/{project_id}/secrets", dependencies=[Autocommit])
async def list_project_secrets(project_id: str, current_user: CurrentUser, db: DbSession) -> ProjectSecrets:
    return await service.project_secrets(db, project_id, current_user)


@router.put("/projects/{project_id}/secrets/{name}")
async def save_project_secret(
    project_id: str,
    name: SecretName,
    payload: ProjectSecretValue,
    current_user: CurrentUser,
    background: BackgroundTasks,
    db: DbSession,
) -> ProjectSecrets:
    return await service.save_project_secret(db, project_id, current_user, name, payload.value, background)


@router.delete("/projects/{project_id}/secrets/{name}")
async def delete_project_secret(
    project_id: str, name: SecretName, current_user: CurrentUser, background: BackgroundTasks, db: DbSession
) -> ProjectSecrets:
    return await service.save_project_secret(db, project_id, current_user, name, None, background)
