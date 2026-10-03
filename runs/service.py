"""Business logic for runs."""

import hashlib

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.events import EVENT_PAGE
from agent.routing import providers as routing_providers
from agent.run.service import agent_service
from agent.storage.persistence import archive_slots, read_object
from agent.storage.storage import StorageError
from agent.tools import tools as agent_tools
from auth.schemas import TokenUser
from db.models import Chat, Run, RunEvent, RunScreenshot
from projects.exceptions import ProjectNotFound
from projects.schemas import RunAdmission
from runs.constants import (
    DETAIL_RETENTION_DAYS,
    EVENT_RETENTION_DAYS,
    MAX_RUN_LOG_BYTES,
)
from runs.exceptions import (
    InvalidEventCursor,
    RunLogExpired,
    RunLogUnavailable,
    RunNotFound,
    RunNotRunning,
    ScreenshotNotFound,
)
from runs.schemas import ModelList, RunEventsPage


async def start_run(user: TokenUser, project_id: str, prompt: str, mode: str, model_choice: str) -> RunAdmission:
    return RunAdmission.model_validate(
        await agent_service.admit(user.id, prompt, project_id, mode=mode, model_choice=model_choice)
    )


def model_options() -> ModelList:
    return ModelList.model_validate(
        {
            "models": [
                {"id": m.id, "name": m.name, "speed": m.card.speed, "cost": m.card.cost}
                for m in routing_providers.usable_models()
            ]
        }
    )


async def answer_run(user: TokenUser, run_id: str, action: str, text: str) -> RunAdmission:
    """An empty answer means the action itself is the reply."""
    text = text.strip()
    prompt = text or ("Approved, build it." if action == "approve" else "Dismissed proposal.")
    return RunAdmission.model_validate(await agent_service.admit(user.id, prompt, response=(run_id, action, text)))


async def steer(run: Run, text: str) -> None:
    if not await agent_service.steer(run.id, text.strip()):
        raise RunNotRunning


async def cancel(run: Run) -> None:
    await agent_service.cancel(run.id)


async def events_page(db: AsyncSession, run_id: str, user: TokenUser, after_sequence: int) -> RunEventsPage:
    if after_sequence < 0:
        raise InvalidEventCursor
    # One extra row says whether another page exists, so a client never asks for an empty one. The
    # page joins on ownership, so one round trip answers whose run it is and what it holds; as in
    # owned_run, an unknown run is "Run not found" and another user's is "Project not found".
    page = (
        select(RunEvent.sequence, RunEvent.payload)
        .where(RunEvent.run_id == run_id, RunEvent.sequence > after_sequence)
        .order_by(RunEvent.sequence)
        .limit(EVENT_PAGE + 1)
        .subquery()
    )
    rows = (
        await db.execute(
            select(Run.status, Run.reason, Chat.user_id, page.c.sequence, page.c.payload)
            .join(Chat, Chat.id == Run.chat_id)
            .outerjoin(page, Chat.user_id == user.id)
            .where(Run.id == run_id)
            .order_by(page.c.sequence)
        )
    ).all()
    if not rows:
        raise RunNotFound
    run = rows[0]
    if run.user_id != user.id:
        raise ProjectNotFound
    events = [{**row.payload, "sequence": row.sequence} for row in rows if row.sequence is not None]
    has_more = len(events) > EVENT_PAGE
    events = events[:EVENT_PAGE]
    return RunEventsPage.model_validate(
        {
            "events": events,
            "has_more": has_more,
            "status": run.status,
            "reason": run.reason,
            "next_sequence": events[-1].get("sequence", after_sequence) if events else after_sequence,
            "detail_retention_days": DETAIL_RETENTION_DAYS,
            "event_retention_days": EVENT_RETENTION_DAYS,
        }
    )


async def run_log(run: Run) -> bytes:
    """The archived activity log, verified against the digest recorded with it."""
    if not run.log_key:
        raise RunLogExpired if run.log_sha256 else RunLogUnavailable
    async with archive_slots:
        data = await read_object(run.log_key, MAX_RUN_LOG_BYTES)
    if hashlib.sha256(data).hexdigest() != run.log_sha256:
        raise StorageError("Run log archive failed integrity checks")
    return data


async def screenshot(db: AsyncSession, run_id: str, user: TokenUser, screenshot_id: str) -> tuple[bytes, str]:
    """A stored browser-check image of a run, with its media type. Ownership and the image row come
    from one query, with owned_run's errors."""
    row = (
        await db.execute(
            select(Chat.user_id, RunScreenshot.object_key, RunScreenshot.media_type)
            .select_from(Run)
            .join(Chat, Chat.id == Run.chat_id)
            .outerjoin(RunScreenshot, and_(RunScreenshot.run_id == Run.id, RunScreenshot.id == screenshot_id))
            .where(Run.id == run_id)
        )
    ).first()
    if row is None:
        raise RunNotFound
    if row.user_id != user.id:
        raise ProjectNotFound
    if row.object_key is None:
        raise ScreenshotNotFound
    return await read_object(row.object_key, agent_tools.MAX_SCREENSHOT_BYTES), row.media_type
