"""Business logic for saved project files."""

import io
import zipfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.run.service import agent_service
from agent.storage.persistence import archive_slots, latest_revision, revision_bytes
from db.models import ProjectRevision
from files.constants import MAX_INLINE_TEXT_BYTES, MAX_REVISIONS_PAGE
from files.exceptions import FileNotInRevision, NoSavedRevision
from files.schemas import FileList, RevisionItem, RevisionList
from request_timing import measure


async def saved_revision(chat_id: str, revision_id: str | None, db: AsyncSession) -> ProjectRevision:
    if revision_id:
        revision = await db.scalar(
            select(ProjectRevision).where(
                ProjectRevision.id == revision_id,
                ProjectRevision.chat_id == chat_id,
                ProjectRevision.status == "ready",
            )
        )
    else:
        await db.close()
        revision = await latest_revision(chat_id)
    if not revision:
        raise NoSavedRevision
    return revision


async def file_list(db: AsyncSession, project_id: str) -> FileList:
    with measure("metadata"):
        # Release this read transaction before helpers acquire their own connection.
        await db.close()
        revision = await latest_revision(project_id)
    return FileList(
        project_id=project_id,
        files=list(revision.manifest) if revision else [],
        revision_id=revision.id if revision else None,
        sandbox_active=project_id in agent_service.sandboxes,
    )


async def read_file(db: AsyncSession, project_id: str, file_path: str, revision_id: str | None):
    """The bytes of one file, with the revision it came from."""
    with measure("metadata"):
        revision = await saved_revision(project_id, revision_id, db)
    await db.close()
    if file_path not in revision.manifest:
        raise FileNotInRevision
    with measure("storage"):
        async with archive_slots:
            data = await revision_bytes(revision)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                content = archive.read(file_path)
    return revision, content


def inline_text(content: bytes) -> str | None:
    """Decoded text, or None when the file is binary or too large to inline."""
    try:
        if len(content) <= MAX_INLINE_TEXT_BYTES and b"\x00" not in content:
            return content.decode("utf-8")
    except UnicodeDecodeError:
        pass
    return None


async def project_archive(db: AsyncSession, project_id: str, revision_id: str | None) -> bytes:
    revision = await saved_revision(project_id, revision_id, db)
    async with archive_slots:
        return await revision_bytes(revision)


async def revision_list(db: AsyncSession, project) -> RevisionList:
    rows = (
        await db.scalars(
            select(ProjectRevision)
            .where(ProjectRevision.chat_id == project.id, ProjectRevision.status == "ready")
            .order_by(ProjectRevision.created_at.desc())
            .limit(MAX_REVISIONS_PAGE)
        )
    ).all()
    return RevisionList(
        latest_saved_revision_id=project.latest_saved_revision_id,
        latest_verified_revision_id=project.latest_verified_revision_id,
        revisions=[
            RevisionItem(
                id=r.id,
                run_id=r.run_id,
                created_at=r.created_at,
                size_bytes=r.size_bytes,
                file_count=len(r.manifest),
            )
            for r in rows
        ],
    )
