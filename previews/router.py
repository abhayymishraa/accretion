"""The host-owned preview sandbox for a project."""

from fastapi import APIRouter

from auth.dependencies import CurrentUser
from previews import service
from previews.schemas import PreviewState

router = APIRouter()


@router.post("/projects/{project_id}/preview")
async def open_project_preview(project_id: str, current_user: CurrentUser) -> PreviewState:
    # Ownership is part of the opening query (agent_service.open_preview). No session is held: sandbox
    # startup can take tens of seconds.
    return await service.open_preview(project_id, current_user)


@router.get("/projects/{project_id}/preview")
async def get_preview_status(project_id: str, current_user: CurrentUser) -> PreviewState:
    # Ownership is part of the status query (agent_service.preview_status): one round trip.
    return await service.preview_status(project_id, current_user)
