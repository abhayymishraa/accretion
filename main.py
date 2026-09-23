from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Literal
import asyncio
from anyio import CancelScope
import json
import os
import io
import zipfile
from fastapi import Depends

from sqlalchemy import select, text, delete, func
from agent.run.service import agent_service
from agent.budget.budget import BudgetLimitError
from agent.sandbox.archive import safe_path
from agent.storage.persistence import archive_slots, ensure_revision, revision_bytes, read_object
from agent.storage.storage import StorageError
from agent.events import run_events
from agent.context.history import conversation_page
from agent.storage.maintenance import attempt_cleanup, cleanup_project_storage
from auth.router import router
from auth.social import social_router, configure_sessions
from db.models import User, Chat, Message, Run, ProjectRevision, StorageDeletion
from auth.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db, AsyncSessionLocal, engine

from auth.utils import decode_token
from request_timing import measure, request_timing, timed


from contextlib import asynccontextmanager, suppress


@asynccontextmanager
async def lifespan(app):
    await agent_service.startup()
    try:
        yield
    finally:
        await agent_service.shutdown()
        await engine.dispose()


app = FastAPI(title="Accretion", lifespan=lifespan)
app.middleware('http')(request_timing)

origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Server-Timing"],
)

configure_sessions(app)
app.include_router(router=router)
app.include_router(social_router)



class ChatPayload(BaseModel):
    prompt: str
    mode: Literal['auto', 'plan'] = 'auto'


class DecisionPayload(BaseModel):
    action: Literal['approve', 'answer', 'revise', 'dismiss']
    text: str = Field(default='', max_length=4000)


@app.get("/")
async def get_health():
    return {"message": "Welome", "status": "Healthy"}


@app.get("/health/ready")
async def get_readiness(db: AsyncSession = Depends(get_db)):
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=12)
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ready"}


@app.get("/chats/{id}/messages")
@timed('history')
async def get_chat_messages(
    id: str,
    limit: int = 50,
    before: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get message history for a chat"""
    # Verify the chat exists and belongs to the user
    result = await db.execute(select(Chat).where(Chat.id == id))
    chat = result.scalar_one_or_none()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")

    page = await conversation_page(db, id, limit, before)
    active = (await db.execute(select(Run.id, Run.status).where(Run.chat_id == id,
        Run.status.in_(('running', 'awaiting_input'))).order_by(Run.created_at.desc()).limit(2))).all()
    return {
        **page,
        "active_run_id": next((row.id for row in active if row.status == 'running'), None),
        "pending_run_id": next((row.id for row in active if row.status == 'awaiting_input'), None),
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "app_url": chat.app_url,
            "created_at": chat.created_at
        },
    }


@app.post("/chat")
async def create_project(payload: ChatPayload, current_user: User = Depends(get_current_user)):
    return await agent_service.admit(current_user.id, payload.prompt, mode=payload.mode)


@app.post("/chats/{id}/runs")
async def create_run(id: str, payload: ChatPayload, current_user: User = Depends(get_current_user)):
    return await agent_service.admit(current_user.id, payload.prompt, id, mode=payload.mode)


@app.post('/runs/{run_id}/respond')
async def respond_to_run(run_id: str, payload: DecisionPayload, current_user: User = Depends(get_current_user)):
    text = payload.text.strip()
    prompt = text or ('Approved, build it.' if payload.action == 'approve' else 'Dismissed proposal.')
    return await agent_service.admit(current_user.id, prompt, response=(run_id, payload.action, text))


async def owned_chat(id: str, user: User, db: AsyncSession, *, for_update=False):
    query = select(Chat).where(Chat.id == id, Chat.user_id == user.id)
    chat = await db.scalar(query.with_for_update() if for_update else query)
    if not chat:
        raise HTTPException(404, "Project not found")
    return chat


@app.get("/chats/{id}/runs")
async def get_runs(id: str, offset: int = 0, limit: int = 10, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_chat(id, current_user, db)
    if offset < 0 or not 1 <= limit <= 50:
        raise HTTPException(422, 'Invalid history page')
    return {"runs": await agent_service.snapshot(id, offset, limit)}


@app.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    await owned_chat(run.chat_id, current_user, db)
    await agent_service.cancel(run_id)
    return {"runs": await agent_service.snapshot(run.chat_id)}


@app.exception_handler(StorageError)
async def storage_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/projects/{id}/files")
async def get_project_files(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    with measure('metadata'):
        await owned_chat(id, current_user, db)
        # Release this read transaction before helpers acquire their own connection.
        await db.close()
        revision = await ensure_revision(id)
    return {"project_id": id, "files": list(revision.manifest) if revision else [],
            "revision_id": revision.id if revision else None,
            "sandbox_active": id in agent_service.sandboxes}


@app.get("/projects/{id}/files/{file_path:path}")
async def get_file_content(id: str, file_path: str, raw: bool = False, revision_id: str | None = None,
                           current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_chat(id, current_user, db)
    try:
        file_path = safe_path(file_path)
    except ValueError:
        raise HTTPException(422, "Invalid project path") from None
    with measure('metadata'):
        revision = await saved_revision(id, revision_id, db)
    await db.close()
    if file_path not in revision.manifest:
        raise HTTPException(404, "File not found in saved revision")
    with measure('storage'):
        async with archive_slots:
            data = await revision_bytes(revision)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                content = archive.read(file_path)
    if raw:
        from urllib.parse import quote
        return Response(content, media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(file_path.split('/')[-1]),
                     "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
    try:
        text_content = content.decode('utf-8') if len(content) <= 200_000 and b'\x00' not in content else None
    except UnicodeDecodeError:
        text_content = None
    return {"file_path": file_path, "content": text_content, "binary": text_content is None,
            "size": len(content), "revision_id": revision.id}


async def saved_revision(chat_id, revision_id, db):
    if revision_id:
        revision = await db.scalar(select(ProjectRevision).where(ProjectRevision.id == revision_id,
            ProjectRevision.chat_id == chat_id, ProjectRevision.status == 'ready'))
    else:
        await db.close()
        revision = await ensure_revision(chat_id)
    if not revision:
        raise HTTPException(404, "No saved revision available")
    return revision


@app.get("/projects/{id}/download")
async def download_all_files(id: str, revision_id: str | None = None,
                             current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_chat(id, current_user, db)
    revision = await saved_revision(id, revision_id, db)
    async with archive_slots:
        data = await revision_bytes(revision)
    return Response(data, media_type="application/zip", headers={
        "Content-Disposition": f"attachment; filename={id}-project.zip", "Cache-Control": "private, no-store"})


@app.get("/projects/{id}/revisions")
async def get_revisions(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chat = await owned_chat(id, current_user, db)
    rows = (await db.scalars(select(ProjectRevision).where(ProjectRevision.chat_id == id,
        ProjectRevision.status == 'ready').order_by(ProjectRevision.created_at.desc()).limit(50))).all()
    return {"latest_saved_revision_id": chat.latest_saved_revision_id,
            "latest_verified_revision_id": chat.latest_verified_revision_id,
            "revisions": [{"id": r.id, "run_id": r.run_id, "created_at": r.created_at,
                           "size_bytes": r.size_bytes, "file_count": len(r.manifest)} for r in rows]}


@app.get("/runs/{run_id}/events")
async def get_run_events(run_id: str, after_sequence: int = 0,
                         current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    await owned_chat(run.chat_id, current_user, db)
    if after_sequence < 0:
        raise HTTPException(422, "Invalid event cursor")
    events = await run_events(db, run_id, after_sequence)
    return {"events": events, "status": run.status, "reason": run.reason,
            "next_sequence": events[-1].get('sequence', after_sequence) if events else after_sequence,
            "detail_retention_days": 14, "event_retention_days": 30}


@app.post("/projects/{id}/preview")
async def open_project_preview(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_chat(id, current_user, db)
    # Sandbox startup can take tens of seconds; do not hold a pool slot throughout.
    await db.close()
    try:
        with measure('preview_open'):
            return await agent_service.open_preview(id)
    except HTTPException:
        raise
    except BudgetLimitError as exc:
        raise HTTPException(429, str(exc)) from None
    except Exception:
        raise HTTPException(503, "Preview could not start. Saved files are still available; retry opening the preview.") from None


@app.get("/runs/{run_id}/logs")
async def get_run_logs(run_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import hashlib
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    await owned_chat(run.chat_id, current_user, db)
    if not run.log_key:
        raise HTTPException(410 if run.log_sha256 else 404, "Detailed archive expired or is not available yet")
    async with archive_slots:
        data = await read_object(run.log_key, 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != run.log_sha256:
        raise StorageError('Run log archive failed integrity checks')
    return Response(data, media_type="application/gzip", headers={
        "Content-Disposition": f"attachment; filename={run_id}-activity.jsonl.gz", "Cache-Control": "private, no-store"})


@app.get("/projects/{id}/preview")
async def get_preview_status(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chat = await owned_chat(id, current_user, db)
    await db.close()
    with measure('preview_status'):
        return await agent_service.preview_status(chat)


@app.get("/projects")
async def list_user_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List projects by the latest accepted prompt, falling back to creation."""
    last_prompt = (
        select(func.max(Message.created_at))
        .where(Message.chat_id == Chat.id, Message.role == "user")
        .correlate(Chat)
        .scalar_subquery()
    )
    updated_at = func.coalesce(last_prompt, Chat.created_at).label("updated_at")
    result = await db.execute(
        select(Chat, updated_at)
        .where(Chat.user_id == current_user.id)
        .order_by(updated_at.desc(), Chat.id)
    )
    return {
        "projects": [
            {**jsonable_encoder(chat), "updated_at": jsonable_encoder(updated)}
            for chat, updated in result.all()
        ]
    }


@app.delete("/projects/{id}")
async def delete_project(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    async with agent_service.admission:
        # Checkpoint creation locks this same row before inserting its object key.
        await owned_chat(id, current_user, db, for_update=True)
        if id in agent_service.opening or any(r.chat_id == id for r in agent_service.active.values()):
            raise HTTPException(409, 'Stop the active operation before deleting this project')
        keys = set((await db.scalars(select(ProjectRevision.object_key).where(ProjectRevision.chat_id == id))).all())
        runs = (await db.execute(select(Run.id, Run.log_key).where(Run.chat_id == id))).all()
        for run_id, log_key in runs:
            keys.add(f'logs/{run_id}.jsonl.gz')  # Include archives still being uploaded.
            if log_key:
                keys.add(log_key)
        keys.add(f'legacy/{id}')
        for key in keys:
            db.add(StorageDeletion(object_key=key))
        await db.execute(delete(Chat).where(Chat.id == id))
        await db.commit()  # Persist retry intent and revoke access before provider calls.
    storage_done, sandbox_done = await asyncio.gather(
        attempt_cleanup(cleanup_project_storage(keys)),
        attempt_cleanup(agent_service.retire_sandbox(id)),
    )
    return {'deleted': True,
            'storage_cleanup': 'completed' if storage_done else 'queued',
            'sandbox_cleanup': 'completed' if sandbox_done else 'queued'}


@app.websocket("/ws/{id}")
async def ws_listener(websocket: WebSocket, id: str):
    # Authenticate in the first frame: bearer tokens never enter URLs or access logs.
    await websocket.accept()
    try:
        first = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        if not isinstance(first, dict) or not isinstance(first.get('token'), str):
            await websocket.close(code=1008)
            return
        payload = decode_token(first.get("token", "")) if first.get("type") == "auth" else None
        if not payload or not payload.get("sub"):
            await websocket.close(code=1008)
            return
        async with AsyncSessionLocal() as db:
            chat = await db.scalar(select(Chat).where(Chat.id == id, Chat.user_id == int(payload["sub"])))
            user = await db.get(User, int(payload["sub"]))
            if not chat or not user or (not user.email_verified):
                await websocket.close(code=1008)
                return
    except (ValueError, TimeoutError, WebSocketDisconnect):
        with suppress(RuntimeError):
            await websocket.close(code=1008)
        return

    queue = asyncio.Queue(maxsize=64)
    agent_service.subscribers.setdefault(id, set()).add(queue)

    async def send_snapshot():
        async with AsyncSessionLocal() as db:
            chat = await db.get(Chat, id)
            messages = (await db.scalars(select(Message).where(Message.chat_id == id).order_by(Message.created_at.desc()).limit(200))).all()
            messages = list(reversed(messages))
            history = [{"id": m.id, "role": m.role, "content": m.content,
                        "event_type": m.event_type, "tool_calls": m.tool_calls,
                        "created_at": m.created_at.isoformat()} for m in messages]
            app_url = chat.app_url if id in agent_service.sandboxes else None
        await websocket.send_json({"type": "history", "messages": history,
                                   "app_url": app_url, "runs": await agent_service.snapshot(id)})

    async def receive():
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "resync":
                await queue.put({"e": "resync"})

    async def send():
        events_only = first.get('mode') == 'events'
        if events_only:
            await websocket.send_json({"e": "ready"})
        else:
            # Older frontend releases still expect a socket snapshot during rollout.
            await send_snapshot()
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25)
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
        agent_service.subscribers[id].discard(queue)
        if not agent_service.subscribers[id]:
            agent_service.subscribers.pop(id)
        # Generation belongs to the Run service, not this observer connection.
