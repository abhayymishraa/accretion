"""Runs: one editing request, its events, its logs and the live socket."""

from fastapi import APIRouter, Depends, WebSocket
from fastapi.responses import Response

from auth.dependencies import CurrentUser
from db.base import DbSession
from projects.dependencies import owned_project
from projects.schemas import RunAdmission
from runs import service, socket
from runs.dependencies import OwnedRun
from runs.schemas import ChatPayload, DecisionPayload, RunEventsPage, RunList

router = APIRouter()


@router.post("/projects/{project_id}/runs")
async def create_run(project_id: str, payload: ChatPayload, current_user: CurrentUser) -> RunAdmission:
    return await service.start_run(current_user, project_id, payload.prompt, payload.mode)


@router.post("/runs/{run_id}/respond")
async def respond_to_run(run_id: str, payload: DecisionPayload, current_user: CurrentUser) -> RunAdmission:
    return await service.answer_run(current_user, run_id, payload.action, payload.text)


@router.get("/projects/{project_id}/runs", dependencies=[Depends(owned_project)])
async def get_runs(project_id: str, offset: int = 0, limit: int = 10) -> RunList:
    return await service.run_page(project_id, offset, limit)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run: OwnedRun) -> RunList:
    return await service.cancel(run)


@router.get("/runs/{run_id}/events")
async def get_run_events(run: OwnedRun, db: DbSession, after_sequence: int = 0) -> RunEventsPage:
    return await service.events_page(db, run, after_sequence)


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


@router.websocket("/ws/{project_id}")
async def ws_listener(websocket: WebSocket, project_id: str):
    await socket.listen(websocket, project_id)
