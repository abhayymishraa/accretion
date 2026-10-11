"""GitHub: the user's connected account, each project's repository, imports and webhooks."""

import json

from fastapi import APIRouter, BackgroundTasks, Request, Response

from auth.dependencies import CurrentUser
from db.base import Autocommit, DbSession
from github_sync import service, sync
from github_sync.schemas import (
    BranchList,
    BranchName,
    ConnectFinish,
    ConnectStart,
    GithubAccountOut,
    ImportRequest,
    ImportResult,
    ProjectRepoOut,
    PullOut,
    RepoCreate,
    RepoList,
)

router = APIRouter()


@router.get("/github/account", dependencies=[Autocommit])
async def get_account(current_user: CurrentUser, db: DbSession) -> GithubAccountOut:
    return await service.account(db, current_user)


@router.post("/github/connect", dependencies=[Autocommit])
async def begin_connect(current_user: CurrentUser, db: DbSession) -> ConnectStart:
    return await service.begin_connect(db, current_user)


@router.post("/github/connect/complete")
async def finish_connect(payload: ConnectFinish, current_user: CurrentUser, db: DbSession) -> GithubAccountOut:
    """Called by the signed-in callback page, so the connection lands on the user who started it."""
    return await service.finish_connect(db, current_user, payload)


@router.delete("/github/account", status_code=204)
async def disconnect(current_user: CurrentUser, db: DbSession) -> None:
    await service.disconnect(db, current_user)


@router.get("/github/repos", dependencies=[Autocommit])
async def list_repos(current_user: CurrentUser, db: DbSession) -> RepoList:
    return await service.list_repos(db, current_user)


@router.post("/github/imports", status_code=201, dependencies=[Autocommit])
async def import_repo(payload: ImportRequest, current_user: CurrentUser, db: DbSession) -> ImportResult:
    return await service.import_repo(db, current_user, payload)


@router.get("/projects/{project_id}/repo", dependencies=[Autocommit])
async def get_project_repo(project_id: str, current_user: CurrentUser, db: DbSession) -> ProjectRepoOut:
    return await service.project_repo(db, current_user, project_id)


@router.post("/projects/{project_id}/repo", status_code=201, dependencies=[Autocommit])
async def create_repo(
    project_id: str, payload: RepoCreate, current_user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> ProjectRepoOut:
    return await service.create_repo(db, current_user, project_id, payload, background)


@router.delete("/projects/{project_id}/repo", status_code=204, dependencies=[Autocommit])
async def unlink_repo(project_id: str, current_user: CurrentUser, db: DbSession) -> None:
    await service.unlink(db, current_user, project_id)


@router.post("/projects/{project_id}/repo/sync", dependencies=[Autocommit])
async def sync_repo(
    project_id: str, current_user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> ProjectRepoOut:
    return await service.sync_now(db, current_user, project_id, background)


@router.post("/projects/{project_id}/repo/workflows/approve", dependencies=[Autocommit])
async def approve_workflows(
    project_id: str, current_user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> ProjectRepoOut:
    return await service.approve_workflows(db, current_user, project_id, background)


@router.get("/projects/{project_id}/repo/branches", dependencies=[Autocommit])
async def list_branches(project_id: str, current_user: CurrentUser, db: DbSession) -> BranchList:
    return await service.branches(db, current_user, project_id)


@router.post("/projects/{project_id}/repo/branches", dependencies=[Autocommit])
async def create_branch(
    project_id: str, payload: BranchName, current_user: CurrentUser, db: DbSession
) -> ProjectRepoOut:
    return await service.create_branch(db, current_user, project_id, payload.name)


@router.put("/projects/{project_id}/repo/branch", dependencies=[Autocommit])
async def switch_branch(
    project_id: str, payload: BranchName, current_user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> ProjectRepoOut:
    return await service.switch_branch(db, current_user, project_id, payload.name, background)


@router.post("/projects/{project_id}/repo/pulls", dependencies=[Autocommit])
async def open_pull(project_id: str, current_user: CurrentUser, db: DbSession) -> PullOut:
    return await service.open_pull(db, current_user, project_id)


@router.post("/github/webhooks", status_code=202)
async def receive_webhook(request: Request, background: BackgroundTasks) -> Response:
    """Answered at once; the work runs after the reply, so GitHub never times out on a slow pull."""
    body = await request.body()
    headers = request.headers
    if await service.accept_webhook(body, headers.get("X-Hub-Signature-256"), headers.get("X-GitHub-Delivery")):
        background.add_task(sync.handle_event, headers.get("X-GitHub-Event", ""), json.loads(body))
    return Response(status_code=202)
