"""Saved project files: manifests, contents, downloads and revisions."""

from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from agent.sandbox.archive import safe_path
from db.base import DbSession, ReadOnly
from files import service
from files.exceptions import InvalidProjectPath
from files.schemas import FileList, RevisionList
from projects.dependencies import OwnedProject, owned_project

router = APIRouter()


@router.get("/projects/{project_id}/files", dependencies=[ReadOnly, Depends(owned_project)])
async def get_project_files(project_id: str, db: DbSession) -> FileList:
    return await service.file_list(db, project_id)


@router.get("/projects/{project_id}/files/{file_path:path}", dependencies=[ReadOnly, Depends(owned_project)])
async def get_file_content(
    project_id: str,
    file_path: str,
    db: DbSession,
    raw: bool = False,
    revision_id: str | None = None,
):
    try:
        file_path = safe_path(file_path)
    except ValueError:
        raise InvalidProjectPath from None
    revision, content = await service.read_file(db, project_id, file_path, revision_id)
    if raw:
        return Response(
            content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''" + quote(file_path.split("/")[-1]),
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, no-store",
            },
        )
    text_content = service.inline_text(content)
    return {
        "file_path": file_path,
        "content": text_content,
        "binary": text_content is None,
        "size": len(content),
        "revision_id": revision.id,
    }


@router.get("/projects/{project_id}/download", dependencies=[Depends(owned_project)])
async def download_all_files(project_id: str, db: DbSession, revision_id: str | None = None):
    data = await service.project_archive(db, project_id, revision_id)
    return Response(
        data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={project_id}-project.zip",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/projects/{project_id}/revisions")
async def get_revisions(project: OwnedProject, db: DbSession) -> RevisionList:
    return await service.revision_list(db, project)
