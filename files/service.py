"""Business logic for saved project files."""

import io
import zipfile

from sqlalchemy.ext.asyncio import AsyncSession

from agent.run.service import agent_service
from agent.storage.persistence import archive_slots, latest_revision_in, revision_bytes
from db.models import ProjectRevision
from files.constants import MAX_INLINE_TEXT_BYTES
from files.exceptions import FileNotInRevision, NoSavedRevision
from files.schemas import FileList
from request_timing import measure


async def saved_revision(chat_id: str, revision_id: str | None, db: AsyncSession) -> ProjectRevision:
    if revision_id:
        # db.get: owned_project_files loaded a revision of this project into the session.
        revision = await db.get(ProjectRevision, revision_id)
        if revision and (revision.chat_id != chat_id or revision.status != "ready"):
            revision = None
    else:
        revision = await latest_revision_in(db, chat_id)
    if not revision:
        raise NoSavedRevision
    return revision


async def file_list(db: AsyncSession, project_id: str) -> FileList:
    with measure("metadata"):
        revision = await latest_revision_in(db, project_id)
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
