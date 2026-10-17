"""Vercel: the user's connection, and publishing each app to their own Vercel account."""

from fastapi import APIRouter, BackgroundTasks

from auth.dependencies import CurrentUser
from db.base import Autocommit, DbSession
from projects.dependencies import OwnedProject
from vercel_connect import publish, service
from vercel_connect.schemas import AccountOut, ConnectFinish, ConnectStart, PublishOut

router = APIRouter()


@router.get("/vercel/account", dependencies=[Autocommit])
async def get_account(current_user: CurrentUser, db: DbSession) -> AccountOut:
    return await service.account(db, current_user)


@router.post("/vercel/connect")
async def begin_connect(current_user: CurrentUser) -> ConnectStart:
    return await service.begin_connect(current_user)


@router.post("/vercel/connect/complete", dependencies=[Autocommit])
async def finish_connect(payload: ConnectFinish, current_user: CurrentUser, db: DbSession) -> AccountOut:
    """Called by the signed-in callback page, so the connection lands on the user who started it."""
    return await service.finish_connect(db, current_user, payload)


@router.get("/projects/{project_id}/publish", dependencies=[Autocommit])
async def get_publish(chat: OwnedProject, db: DbSession) -> PublishOut:
    return await publish.status(db, chat)


@router.post("/projects/{project_id}/publish", status_code=202, dependencies=[Autocommit])
async def start_publish(
    chat: OwnedProject, current_user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> PublishOut:
    started = await publish.start(db, current_user.id, chat)
    background.add_task(publish.run, chat.id, current_user.id)
    return started


@router.delete("/projects/{project_id}/publish", status_code=204, dependencies=[Autocommit])
async def unpublish(chat: OwnedProject, current_user: CurrentUser, db: DbSession) -> None:
    await publish.unpublish(db, current_user.id, chat)
