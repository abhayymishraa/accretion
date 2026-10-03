"""Business logic for the project resource.

Routers here do routing: they resolve dependencies and hand off. Everything
that touches the database or the agent service lives in this module, so the
same operation can be reached from a second caller without going through HTTP.
"""

import asyncio

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent.context.history import conversation_page, transcript
from agent.run.service import agent_service, open_run
from agent.run.worker import OPEN_STATUSES
from agent.storage.maintenance import attempt_cleanup, cleanup_project_storage
from auth.schemas import TokenUser
from db.models import Chat, Message, ProjectRevision, Run, RunScreenshot, StorageDeletion
from projects.constants import LIVE_RUN_STATUSES
from projects.dependencies import owned_chat
from projects.exceptions import ChatNotFound, NotChatOwner, ProjectBusy, ProjectNotFound
from projects.schemas import MessagePage, ProjectDeletion, ProjectList, ProjectRef, ProjectSummary, RunAdmission


async def message_page(
    db: AsyncSession, project_id: str, user: TokenUser, limit: int, before: str | None
) -> MessagePage:
    """One page of a project's conversation, plus which run is live."""
    # Not `owned_chat`: this route separates "no such chat" from "not yours",
    # and both messages are part of the published behaviour.
    # The project and its live runs in one query: of the two newest live runs, the open one and
    # the one awaiting input.
    live = (
        select(Run.id, Run.status, Run.created_at)
        .where(Run.chat_id == project_id, Run.status.in_(LIVE_RUN_STATUSES))
        .order_by(Run.created_at.desc())
        .limit(2)
        .subquery()
    )
    newest_live = select(live.c.id).order_by(live.c.created_at.desc()).limit(1)
    # The page joins on ownership, so another user's messages never leave the database, and one
    # round trip answers both whether the project is theirs and what it holds.
    page = transcript(project_id, limit, before).subquery()
    rows = (
        await db.execute(
            select(
                Chat,
                newest_live.where(live.c.status.in_(OPEN_STATUSES)).scalar_subquery().label("active_run_id"),
                newest_live.where(live.c.status == "awaiting_input").scalar_subquery().label("pending_run_id"),
                page,
            )
            .outerjoin(page, Chat.user_id == user.id)
            .where(Chat.id == project_id)
            .order_by(page.c.created_at.desc(), page.c.kind.desc(), page.c.id.desc())
        )
    ).all()
    if not rows:
        raise ChatNotFound
    chat, active_run_id, pending_run_id = rows[0][:3]
    if chat.user_id != user.id:
        raise NotChatOwner

    return MessagePage.model_validate(
        {
            **conversation_page([row for row in rows if row.kind], limit),
            "active_run_id": active_run_id,
            "pending_run_id": pending_run_id,
            # ProjectRef sets from_attributes, so pydantic reads the row itself.
            "chat": chat,
        }
    )


async def list_projects(db: AsyncSession, user: TokenUser) -> ProjectList:
    """Projects by the latest accepted prompt, falling back to creation."""
    last_prompt = (
        select(func.max(Message.created_at))
        .where(Message.chat_id == Chat.id, Message.role == "user")
        .correlate(Chat)
        .scalar_subquery()
    )
    updated_at = func.coalesce(last_prompt, Chat.created_at).label("updated_at")
    result = await db.execute(
        select(Chat, updated_at).where(Chat.user_id == user.id).order_by(updated_at.desc(), Chat.id)
    )
    return ProjectList(
        projects=[ProjectSummary(**jsonable_encoder(chat), updated_at=updated) for chat, updated in result.all()]
    )


async def rename_project(db: AsyncSession, project_id: str, user: TokenUser, title: str) -> ProjectRef:
    """One statement, committed by itself: ownership is part of the update, so an unknown project and
    someone else's both change nothing and answer "Project not found", as owned_project does."""
    chat = await db.scalar(
        update(Chat).where(Chat.id == project_id, Chat.user_id == user.id).values(title=title).returning(Chat)
    )
    if chat is None:
        raise ProjectNotFound
    return ProjectRef.model_validate(chat)


async def delete_project(db: AsyncSession, project_id: str, user: TokenUser) -> ProjectDeletion:
    """Revoke access and commit the retry intent before calling any provider."""
    async with agent_service.admission:
        # Checkpoint creation locks this same row before inserting its object key.
        await owned_chat(project_id, user, db, for_update=True)
        if project_id in agent_service.opening or await open_run(db, project_id):
            raise ProjectBusy
        keys = set(
            (await db.scalars(select(ProjectRevision.object_key).where(ProjectRevision.chat_id == project_id))).all()
        )
        keys.update(
            (await db.scalars(select(RunScreenshot.object_key).join(Run).where(Run.chat_id == project_id))).all()
        )
        runs = (await db.execute(select(Run.id, Run.log_key).where(Run.chat_id == project_id))).all()
        for run_id, log_key in runs:
            keys.add(f"logs/{run_id}.jsonl.gz")  # Include archives still being uploaded.
            if log_key:
                keys.add(log_key)
        keys.add(f"legacy/{project_id}")
        for key in keys:
            db.add(StorageDeletion(object_key=key))
        await db.execute(delete(Chat).where(Chat.id == project_id))
        await db.commit()  # Persist retry intent and revoke access before provider calls.
    storage_done, sandbox_done = await asyncio.gather(
        attempt_cleanup(cleanup_project_storage(keys)),
        attempt_cleanup(agent_service.retire_sandbox(project_id)),
    )
    return ProjectDeletion(
        deleted=True,
        storage_cleanup="completed" if storage_done else "queued",
        sandbox_cleanup="completed" if sandbox_done else "queued",
    )


async def start_project(user: TokenUser, prompt: str, mode: str, model_choice: str) -> RunAdmission:
    return RunAdmission.model_validate(await agent_service.admit(user.id, prompt, mode=mode, model_choice=model_choice))
