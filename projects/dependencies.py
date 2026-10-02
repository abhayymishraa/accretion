"""Route dependencies for the project resource.

Ownership is checked once, here, rather than as the first line of every
handler: a route that forgets the call is a route that leaks another user's
project, and a dependency cannot be forgotten.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import CurrentUser, StreamedUser
from db.base import DbSession, get_db
from db.models import Chat, User
from projects.exceptions import ProjectNotFound


async def owned_chat(project_id: str, user: User, db: DbSession, *, for_update: bool = False) -> Chat:
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


async def owned_project_released(
    project_id: str,
    current_user: StreamedUser,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> Chat:
    """owned_project for streams: the session closes before the stream starts."""
    return await owned_chat(project_id, current_user, db)


StreamedProject = Annotated[Chat, Depends(owned_project_released, scope="function")]
