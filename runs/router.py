"""Runs: one editing request, its events, its logs and its live stream."""

from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from auth.dependencies import CurrentUser, get_approved_user
from db.base import Autocommit, DbSession
from projects.schemas import RunAdmission
from runs import service
from runs.dependencies import OpenedStream, OwnedRun
from runs.schemas import ChatPayload, DecisionPayload, ModelList, RunEventsPage, SteerPayload

router = APIRouter()


@router.post("/projects/{project_id}/runs")
async def create_run(project_id: str, payload: ChatPayload, current_user: CurrentUser) -> RunAdmission:
    return await service.start_run(current_user, project_id, payload.prompt, payload.mode, payload.model_choice)


@router.get("/models", dependencies=[Autocommit, Depends(get_approved_user)])
async def list_models() -> ModelList:
    return service.model_options()


@router.post("/runs/{run_id}/respond")
async def respond_to_run(run_id: str, payload: DecisionPayload, current_user: CurrentUser) -> RunAdmission:
    return await service.answer_run(current_user, run_id, payload.action, payload.text)


@router.post("/runs/{run_id}/steer", status_code=204, dependencies=[Autocommit])
async def steer_run(run_id: str, payload: SteerPayload, current_user: CurrentUser, db: DbSession) -> None:
    await service.steer(db, run_id, current_user, payload.text)


@router.post("/runs/{run_id}/cancel", status_code=204, dependencies=[Autocommit])
async def cancel_run(run_id: str, current_user: CurrentUser, db: DbSession) -> None:
    await service.cancel(db, run_id, current_user)


@router.get("/runs/{run_id}/events", dependencies=[Autocommit])
async def get_run_events(
    run_id: str, current_user: CurrentUser, db: DbSession, after_sequence: int = 0
) -> RunEventsPage:
    return await service.events_page(db, run_id, current_user, after_sequence)


@router.get("/projects/{project_id}/stream", response_class=EventSourceResponse)
async def stream_project(opened: OpenedStream) -> AsyncIterable[ServerSentEvent]:
    # Ownership and the resume cursor are settled in the dependency: once this generator runs the
    # 200 is already sent.
    async for event in opened.events():
        yield event


@router.get("/runs/{run_id}/logs", dependencies=[Autocommit])
async def get_run_logs(run: OwnedRun):
    data = await service.run_log(run)
    return Response(
        data,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f"attachment; filename={run.id}-activity.jsonl.gz",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/runs/{run_id}/screenshots/{screenshot_id}", dependencies=[Autocommit])
async def get_run_screenshot(run_id: str, screenshot_id: str, current_user: CurrentUser, db: DbSession):
    data, media_type = await service.screenshot(db, run_id, current_user, screenshot_id)
    # Stored once under a random id and never rewritten, so the browser may keep it.
    return Response(data, media_type=media_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})
