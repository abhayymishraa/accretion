"""Skills: the user's library and which skills each project uses."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from auth.dependencies import CurrentUser
from db.base import Autocommit, DbSession
from skills import importing, service
from skills.schemas import (
    BuiltinSkillDetail,
    GitHubImport,
    GitHubSkills,
    GitHubSource,
    ImportResult,
    ProjectSkillList,
    SkillCreate,
    SkillDetail,
    SkillList,
    SkillName,
    SkillToggle,
    SkillUpdate,
)

router = APIRouter()


@router.get("/skills", dependencies=[Autocommit])
async def list_skills(current_user: CurrentUser, db: DbSession) -> SkillList:
    return await service.list_skills(db, current_user)


@router.post("/skills", status_code=201, dependencies=[Autocommit])
async def create_skill(payload: SkillCreate, current_user: CurrentUser, db: DbSession) -> SkillDetail:
    return await service.create_skill(db, current_user, payload)


@router.post("/skills/import", status_code=201, dependencies=[Autocommit])
async def import_skill(
    request: Request,
    filename: Annotated[str, Query(min_length=1, max_length=255)],
    current_user: CurrentUser,
    db: DbSession,
) -> SkillDetail:
    """A .md, .mdx or .zip skill sent as the raw request body, so no multipart parser is needed."""
    payload = importing.skill_from_upload(filename, await importing.read_upload(request.stream()))
    return await service.create_skill(db, current_user, payload)


@router.post("/skills/github/discover")
async def discover_github_skills(source: GitHubSource, current_user: CurrentUser) -> GitHubSkills:
    return await importing.discover(source.url)


@router.post("/skills/github/import", status_code=201, dependencies=[Autocommit])
async def import_github_skills(selection: GitHubImport, current_user: CurrentUser, db: DbSession) -> ImportResult:
    return await service.import_github(db, current_user, selection.url, selection.paths)


@router.get("/skills/builtin/{skill_name}")
async def get_builtin_skill(skill_name: str, current_user: CurrentUser) -> BuiltinSkillDetail:
    return service.builtin_skill(skill_name)


@router.get("/skills/{skill_id}", dependencies=[Autocommit])
async def get_skill(skill_id: str, current_user: CurrentUser, db: DbSession) -> SkillDetail:
    return await service.get_skill(db, current_user, skill_id)


@router.patch("/skills/{skill_id}", dependencies=[Autocommit])
async def update_skill(skill_id: str, payload: SkillUpdate, current_user: CurrentUser, db: DbSession) -> SkillDetail:
    return await service.update_skill(db, current_user, skill_id, payload)


@router.delete("/skills/{skill_id}", status_code=204, dependencies=[Autocommit])
async def delete_skill(skill_id: str, current_user: CurrentUser, db: DbSession) -> None:
    await service.delete_skill(db, current_user, skill_id)


@router.put("/skill-settings/{skill_name}", status_code=204, dependencies=[Autocommit])
async def set_account_skill(
    skill_name: Annotated[SkillName, Path()], payload: SkillToggle, current_user: CurrentUser, db: DbSession
) -> None:
    """On or off for every project of this account."""
    await service.set_account_skill(db, current_user, skill_name, payload.enabled)


@router.get("/projects/{project_id}/skills", dependencies=[Autocommit])
async def list_project_skills(project_id: str, current_user: CurrentUser, db: DbSession) -> ProjectSkillList:
    return await service.project_skills(db, current_user, project_id)


@router.post("/projects/{project_id}/skills/{skill_name}/library", status_code=201, dependencies=[Autocommit])
async def save_project_skill(
    project_id: str, skill_name: Annotated[SkillName, Path()], current_user: CurrentUser, db: DbSession
) -> SkillDetail:
    return await service.save_project_skill(db, current_user, project_id, skill_name)


@router.put("/projects/{project_id}/skills/{skill_name}", status_code=204, dependencies=[Autocommit])
async def set_project_skill(
    project_id: str,
    skill_name: Annotated[SkillName, Path()],
    payload: SkillToggle,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    await service.set_project_skill(db, current_user, project_id, skill_name, payload.enabled)
