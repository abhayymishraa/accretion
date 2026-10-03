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
from db.models import Chat
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


async def owned_project_files(project_id: str, current_user: CurrentUser, db: DbSession) -> Chat:
    """owned_project for routes that read saved files: the latest saved revision loads in the same
    query, so latest_revision_in then finds both rows in the session and queries nothing."""
    chat = await db.scalar(
        select(Chat)
        .options(joinedload(Chat.latest_saved_revision))
        .where(Chat.id == project_id, Chat.user_id == current_user.id)
    )
    if not chat:
        raise ProjectNotFound
    return chat

