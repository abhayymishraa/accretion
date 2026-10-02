"""Runs: one editing request, its events, its logs and its live stream."""

from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from auth.dependencies import CurrentUser, get_current_user
from db.base import DbSession, ReadOnly
from projects.dependencies import StreamedProject, owned_project
from projects.schemas import RunAdmission
from runs import service, stream
from runs.dependencies import OwnedRun
from runs.schemas import ChatPayload, DecisionPayload, ModelList, RunEventsPage, RunList, SteerPayload

router = APIRouter()


@router.post("/projects/{project_id}/runs")
async def create_run(project_id: str, payload: ChatPayload, current_user: CurrentUser) -> RunAdmission:
    return await service.start_run(current_user, project_id, payload.prompt, payload.mode, payload.model_choice)


@router.get("/models", dependencies=[ReadOnly, Depends(get_current_user)])
async def list_models() -> ModelList:
    return service.model_options()


@router.post("/runs/{run_id}/respond")
async def respond_to_run(run_id: str, payload: DecisionPayload, current_user: CurrentUser) -> RunAdmission:
    return await service.answer_run(current_user, run_id, payload.action, payload.text)


@router.get("/projects/{project_id}/runs", dependencies=[Depends(owned_project)])
async def get_runs(project_id: str, offset: int = 0, limit: int = 10) -> RunList:
    return await service.run_page(project_id, offset, limit)


@router.post("/runs/{run_id}/steer")
async def steer_run(run: OwnedRun, payload: SteerPayload) -> RunList:
    return await service.steer(run, payload.text)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run: OwnedRun) -> RunList:
    return await service.cancel(run)


@router.get("/runs/{run_id}/events", dependencies=[ReadOnly])
async def get_run_events(run: OwnedRun, db: DbSession, after_sequence: int = 0) -> RunEventsPage:
    return await service.events_page(db, run, after_sequence)


@router.get("/projects/{project_id}/stream", response_class=EventSourceResponse)
async def stream_project(
    project: StreamedProject,
    last_event_id: Annotated[str | None, Header(pattern=r"^[0-9a-f-]{36}:\d+$")] = None,
) -> AsyncIterable[ServerSentEvent]:
    # Validated by the parameter, not in the body: once this generator runs the 200 is already sent.
    async for event in stream.ProjectStream(project.id).events(last_event_id):
        yield event


@router.get("/runs/{run_id}/logs")
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


@router.get("/runs/{run_id}/screenshots/{screenshot_id}")
async def get_run_screenshot(run: OwnedRun, db: DbSession, screenshot_id: str):
    data, media_type = await service.screenshot(db, run, screenshot_id)
    # Stored once under a random id and never rewritten, so the browser may keep it.
    return Response(data, media_type=media_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})
