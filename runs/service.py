"""Business logic for runs."""

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from agent.events import run_events
from agent.routing import providers as routing_providers
from agent.run.service import agent_service
from agent.storage.persistence import archive_slots, read_object
from agent.storage.storage import StorageError
from db.models import Run, User
from projects.schemas import RunAdmission
from runs.constants import (
    DETAIL_RETENTION_DAYS,
    EVENT_RETENTION_DAYS,
    MAX_RUN_LOG_BYTES,
    MAX_RUNS_PAGE,
)
from runs.exceptions import InvalidEventCursor, InvalidHistoryPage, RunLogExpired, RunLogUnavailable, RunNotRunning
from runs.schemas import ModelList, RunEventsPage, RunList


async def start_run(user: User, project_id: str, prompt: str, mode: str, model_choice: str) -> RunAdmission:
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


async def answer_run(user: User, run_id: str, action: str, text: str) -> RunAdmission:
    """An empty answer means the action itself is the reply."""
    text = text.strip()
    prompt = text or ("Approved, build it." if action == "approve" else "Dismissed proposal.")
    return RunAdmission.model_validate(await agent_service.admit(user.id, prompt, response=(run_id, action, text)))


async def run_page(project_id: str, offset: int, limit: int) -> RunList:
    if offset < 0 or not 1 <= limit <= MAX_RUNS_PAGE:
        raise InvalidHistoryPage
    return RunList.model_validate({"runs": await agent_service.snapshot(project_id, offset, limit)})


async def steer(run: Run, text: str) -> RunList:
    if not await agent_service.steer(run.id, text.strip()):
        raise RunNotRunning
    return RunList.model_validate({"runs": await agent_service.snapshot(run.chat_id)})


async def cancel(run: Run) -> RunList:
    await agent_service.cancel(run.id)
    return RunList.model_validate({"runs": await agent_service.snapshot(run.chat_id)})


async def events_page(db: AsyncSession, run: Run, after_sequence: int) -> RunEventsPage:
    if after_sequence < 0:
        raise InvalidEventCursor
    events = await run_events(db, run.id, after_sequence)
    return RunEventsPage.model_validate(
        {
            "events": events,
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
