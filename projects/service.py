"""Business logic for the project resource.

Routers here do routing: they resolve dependencies and hand off. Everything
that touches the database or the agent service lives in this module, so the
same operation can be reached from a second caller without going through HTTP.
"""

import asyncio
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.context.history import conversation_page
from agent.run.service import agent_service
from agent.storage.maintenance import attempt_cleanup, cleanup_project_storage
from db.models import Chat, Message, ProjectRevision, Run, StorageDeletion, User
from projects.constants import LIVE_RUN_STATUSES
from projects.dependencies import owned_chat
from projects.exceptions import ChatNotFound, NotChatOwner, ProjectBusy


async def message_page(db: AsyncSession, project_id: str, user: User, limit: int, before: str | None) -> dict[str, Any]:
    """One page of a project's conversation, plus which run is live."""
    # Not `owned_chat`: this route separates "no such chat" from "not yours",
    # and both messages are part of the published behaviour.
    chat = await db.scalar(select(Chat).where(Chat.id == project_id))
    if not chat:
        raise ChatNotFound
    if chat.user_id != user.id:
        raise NotChatOwner

    page = await conversation_page(db, project_id, limit, before)
    active = (
        await db.execute(
            select(Run.id, Run.status)
            .where(Run.chat_id == project_id, Run.status.in_(LIVE_RUN_STATUSES))
            .order_by(Run.created_at.desc())
            .limit(2)
        )
    ).all()
    return {
        **page,
        "active_run_id": next((row.id for row in active if row.status == "running"), None),
        "pending_run_id": next((row.id for row in active if row.status == "awaiting_input"), None),
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "app_url": chat.app_url,
            "created_at": chat.created_at,
        },
    }


async def list_projects(db: AsyncSession, user: User) -> dict[str, Any]:
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
    return {
        "projects": [
            {**jsonable_encoder(chat), "updated_at": jsonable_encoder(updated)} for chat, updated in result.all()
        ]
    }


async def delete_project(db: AsyncSession, project_id: str, user: User) -> dict[str, Any]:
    """Revoke access and commit the retry intent before calling any provider."""
    async with agent_service.admission:
        # Checkpoint creation locks this same row before inserting its object key.
        await owned_chat(project_id, user, db, for_update=True)
        if project_id in agent_service.opening or any(r.chat_id == project_id for r in agent_service.active.values()):
            raise ProjectBusy
        keys = set(
            (await db.scalars(select(ProjectRevision.object_key).where(ProjectRevision.chat_id == project_id))).all()
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
    return {
        "deleted": True,
        "storage_cleanup": "completed" if storage_done else "queued",
        "sandbox_cleanup": "completed" if sandbox_done else "queued",
    }


async def start_project(user: User, prompt: str, mode: str) -> dict[str, Any]:
    return await agent_service.admit(user.id, prompt, mode=mode)
