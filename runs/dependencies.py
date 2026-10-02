"""Route dependencies for runs."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from auth.dependencies import CurrentUser
from db.base import DbSession
from db.models import Chat, Run
from projects.exceptions import ProjectNotFound
from runs.exceptions import RunNotFound


async def owned_run(run_id: str, current_user: CurrentUser, db: DbSession) -> Run:
    """Load a run whose project the user owns.

    The run is found first so an unknown id reports "Run not found" rather
    than leaking whether some other user owns it.
    """
    row = (
        await db.execute(select(Run, Chat.user_id).join(Chat, Chat.id == Run.chat_id).where(Run.id == run_id))
    ).first()
    if not row:
        raise RunNotFound
    run, owner_id = row
    if owner_id != current_user.id:
        raise ProjectNotFound
    return run


OwnedRun = Annotated[Run, Depends(owned_run)]
