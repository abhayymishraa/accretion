"""Projects: the chat that owns a generated app, its history and its lifecycle."""

from fastapi import APIRouter, BackgroundTasks, Response

from auth.dependencies import CurrentUser
from db.base import Autocommit, DbSession
from projects import service
from projects.constants import DEFAULT_MESSAGE_PAGE
from projects.dependencies import OwnedProject
from projects.schemas import MessagePage, ProjectList, ProjectRef, ProjectRename, RunAdmission
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


@router.get("/projects/{project_id}/cover", dependencies=[Autocommit])
async def get_project_cover(project: OwnedProject) -> Response:
    data = await service.cover(project)
    # The client asks with ?v=<cover_updated_at>: a new cover is a new URL, so the browser may keep this one.
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
