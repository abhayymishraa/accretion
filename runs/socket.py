"""The project event socket.

Transport, not business logic: authentication on the first frame, a bounded
queue per listener, and a heartbeat. What the events mean belongs to the agent
service, which owns the subscriber set.
"""

import asyncio
from contextlib import suppress
from typing import Any

from anyio import CancelScope
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from agent.run.service import agent_service
from auth.utils import decode_token
from db.base import AsyncSessionLocal
from db.models import Chat, Message, User
from runs.constants import (
    AUTH_FRAME_TIMEOUT_SECONDS,
    CLOSE_POLICY_VIOLATION,
    EVENT_QUEUE_SIZE,
    HEARTBEAT_SECONDS,
    SNAPSHOT_MESSAGE_LIMIT,
)


async def listen(websocket: WebSocket, project_id: str):
    # Authenticate in the first frame: bearer tokens never enter URLs or access logs.
    await websocket.accept()
    try:
        first = await asyncio.wait_for(websocket.receive_json(), timeout=AUTH_FRAME_TIMEOUT_SECONDS)
        if not isinstance(first, dict) or not isinstance(first.get("token"), str):
            await websocket.close(code=CLOSE_POLICY_VIOLATION)
            return
        payload = decode_token(first.get("token", "")) if first.get("type") == "auth" else None
        if not payload or not payload.get("sub"):
            await websocket.close(code=CLOSE_POLICY_VIOLATION)
            return
        async with AsyncSessionLocal() as db:
            chat = await db.scalar(select(Chat).where(Chat.id == project_id, Chat.user_id == int(payload["sub"])))
            user = await db.get(User, int(payload["sub"]))
            if not chat or not user or (not user.email_verified):
                await websocket.close(code=CLOSE_POLICY_VIOLATION)
                return
    except (ValueError, TimeoutError, WebSocketDisconnect):
        with suppress(RuntimeError):
            await websocket.close(code=CLOSE_POLICY_VIOLATION)
        return

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=EVENT_QUEUE_SIZE)
    agent_service.subscribers.setdefault(project_id, set()).add(queue)

    async def send_snapshot():
        async with AsyncSessionLocal() as db:
            chat = await db.get(Chat, project_id)
            messages = (
                await db.scalars(
                    select(Message)
                    .where(Message.chat_id == project_id)
                    .order_by(Message.created_at.desc())
                    .limit(SNAPSHOT_MESSAGE_LIMIT)
                )
            ).all()
            messages = list(reversed(messages))
            history = [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "event_type": m.event_type,
                    "tool_calls": m.tool_calls,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ]
            # Re-fetched here, so the project may have been deleted since the
            # socket opened. Treat that as no preview rather than raising.
            app_url = chat.app_url if chat and project_id in agent_service.sandboxes else None
        await websocket.send_json(
            {
                "type": "history",
                "messages": history,
                "app_url": app_url,
                "runs": await agent_service.snapshot(project_id),
            }
        )

    async def receive():
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "resync":
                await queue.put({"e": "resync"})

    async def send():
        events_only = first.get("mode") == "events"
        if events_only:
            await websocket.send_json({"e": "ready"})
        else:
            # Older frontend releases still expect a socket snapshot during rollout.
            await send_snapshot()
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except TimeoutError:
                await websocket.send_json({"e": "heartbeat"})
                continue
            if event.get("e") == "resync" and not events_only:
                await send_snapshot()
            else:
                await websocket.send_json(event)

    tasks = [asyncio.create_task(receive()), asyncio.create_task(send())]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.CancelledError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        with CancelScope(shield=True):
            await asyncio.gather(*tasks, return_exceptions=True)
        agent_service.subscribers[project_id].discard(queue)
        if not agent_service.subscribers[project_id]:
            agent_service.subscribers.pop(project_id)
