"""Projects: the chat that owns a generated app, its history and its lifecycle."""

from fastapi import APIRouter

from auth.dependencies import CurrentUser
from db.base import DbSession
from projects import service
from projects.constants import DEFAULT_MESSAGE_PAGE
from projects.dependencies import OwnedProject
from projects.schemas import MessagePage, ProjectDeletion, ProjectList, ProjectRef, ProjectRename, RunAdmission
from request_timing import timed
from runs.schemas import ChatPayload

router = APIRouter()


@router.get("/projects/{project_id}/messages")
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


@router.get("/projects")
async def list_user_projects(current_user: CurrentUser, db: DbSession) -> ProjectList:
    """List projects by the latest accepted prompt, falling back to creation."""
    return await service.list_projects(db, current_user)


@router.patch("/projects/{project_id}")
async def rename_project(payload: ProjectRename, project: OwnedProject, db: DbSession) -> ProjectRef:
    return await service.rename_project(db, project, payload.title)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, current_user: CurrentUser, db: DbSession) -> ProjectDeletion:
    return await service.delete_project(db, project_id, current_user)
