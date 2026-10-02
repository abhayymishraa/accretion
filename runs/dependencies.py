"""Route dependencies for runs."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import CurrentUser, StreamedUser
from db.base import DbSession, get_db
from db.models import Chat, Run
from projects.exceptions import ProjectNotFound
from runs.exceptions import RunNotFound


async def owned_run(run_id: str, current_user: CurrentUser, db: DbSession) -> Run:
    """Load a run whose project the user owns.

    The run is found first so an unknown id reports "Run not found" rather
    than leaking whether some other user owns it.
    """
    run = await db.get(Run, run_id)
    if not run:
        raise RunNotFound
    owner = await db.scalar(select(Chat.id).where(Chat.id == run.chat_id, Chat.user_id == current_user.id))
    if not owner:
        raise ProjectNotFound
    return run


OwnedRun = Annotated[Run, Depends(owned_run)]


async def owned_run_released(
    run_id: str,
    current_user: StreamedUser,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> Run:
    """owned_run for streams: the session closes before the stream starts."""
    return await owned_run(run_id, current_user, db)


StreamedRun = Annotated[Run, Depends(owned_run_released, scope="function")]
