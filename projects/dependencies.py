"""Route dependencies for the project resource.

Ownership is checked once, here, rather than as the first line of every
handler: a route that forgets the call is a route that leaks another user's
project, and a dependency cannot be forgotten.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from auth.dependencies import CurrentUser
from auth.schemas import TokenUser
from db.base import DbSession
from db.models import Chat, ProjectRevision
from files.exceptions import NoSavedRevision
from projects.exceptions import ProjectNotFound


async def owned_chat(project_id: str, user: TokenUser, db: DbSession, *, for_update: bool = False) -> Chat:
    """Load a project the user owns, or raise. Used directly when a caller
    needs the row locked, and by the dependencies below otherwise."""
    query = select(Chat).where(Chat.id == project_id, Chat.user_id == user.id)
    chat = await db.scalar(query.with_for_update() if for_update else query)
    if not chat:
        raise ProjectNotFound
    return chat


async def owned_project(project_id: str, current_user: CurrentUser, db: DbSession) -> Chat:
    return await owned_chat(project_id, current_user, db)


OwnedProject = Annotated[Chat, Depends(owned_project)]


async def owned_project_files(
    project_id: str, current_user: CurrentUser, db: DbSession, revision_id: str | None = None
) -> tuple[Chat, ProjectRevision | None]:
    """owned_project for routes that read saved files: the latest saved revision, and a requested one
    (revision_id) of this project, load in the same query, so the service finds them in the session
    and queries nothing. Both rows are returned: the session holds rows weakly, and FastAPI keeps a
    dependency's value for the whole request."""
    requested = (ProjectRevision.id == revision_id) & (ProjectRevision.chat_id == Chat.id)
    found = (
        await db.execute(
            select(Chat, ProjectRevision)
            .options(joinedload(Chat.latest_saved_revision))
            .outerjoin(ProjectRevision, requested)
            .where(Chat.id == project_id, Chat.user_id == current_user.id)
        )
    ).first()
    if not found:
        raise ProjectNotFound
    chat, revision = found.tuple()
    if revision_id and revision is None:
        # Unknown, or another project's: answered from this query, no second read.
        raise NoSavedRevision
    return chat, revision
