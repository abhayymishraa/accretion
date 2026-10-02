"""The host-owned preview sandbox for a project."""

from fastapi import APIRouter, Depends

from db.base import DbSession, ReadOnly
from previews import service
from previews.schemas import PreviewState
from projects.dependencies import OwnedProject, owned_project

router = APIRouter()


@router.post("/projects/{project_id}/preview", dependencies=[Depends(owned_project)])
async def open_project_preview(project_id: str, db: DbSession) -> PreviewState:
    # Sandbox startup can take tens of seconds; do not hold a pool slot throughout.
    await db.close()
    return await service.open_preview(project_id)


@router.get("/projects/{project_id}/preview", dependencies=[ReadOnly])
async def get_preview_status(project: OwnedProject, db: DbSession) -> PreviewState:
    await db.close()
    return await service.preview_status(project)
