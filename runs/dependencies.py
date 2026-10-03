"""Route dependencies for runs."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select

from auth.dependencies import CurrentUser
from db.base import DbSession
from db.models import Chat, Run
from projects.exceptions import ProjectNotFound
from runs.exceptions import RunNotFound
from runs.stream import ProjectStream


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


async def opened_stream(
    project_id: str,
    current_user: CurrentUser,
    last_event_id: Annotated[str | None, Header(pattern=r"^[0-9a-f-]{36}:\d+$")] = None,
) -> AsyncIterator[ProjectStream]:
    """The project's stream, opened before the response starts: subscribed, then checked as the
    user's in the same single query that reads its ready frame. Another user's project is a 404
    with nothing sent. The subscription closes when the stream ends."""
    stream = ProjectStream(project_id)
    async with AsyncExitStack() as stack:
        if not await stream.open(stack, current_user.id, last_event_id):
            raise ProjectNotFound
        yield stream


OpenedStream = Annotated[ProjectStream, Depends(opened_stream)]
