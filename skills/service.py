"""Skills: the bundled catalog, the user's library, and which of them each project uses.

Every function is one statement. Ownership is part of the statement, so an unknown row and someone
else's both answer "not found" without a second read."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, exists, func, insert, literal, select, true, type_coerce, update
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.tools.skills import REQUIRED_SKILLS, bundled, bundled_catalog
from auth.schemas import TokenUser
from db.base import bound
from db.models import Chat, Skill, User, library_rows
from projects.exceptions import ProjectNotFound
from skills import importing
from skills.exceptions import BuiltinSkillName, SkillNameTaken, SkillNotFound, SkillRequired
from skills.schemas import (
    BuiltinSkillDetail,
    ImportFailure,
    ImportResult,
    ProjectSkill,
    ProjectSkillList,
    SkillCreate,
    SkillDetail,
    SkillList,
    SkillSummary,
    SkillUpdate,
)


def _builtin() -> list[SkillSummary]:
    return [
        SkillSummary(name=name, description=description, source="builtin", required=name in REQUIRED_SKILLS)
        for name, description in sorted(bundled_catalog().items())
    ]


def builtin_skill(name: str) -> BuiltinSkillDetail:
    """Read from the catalog in memory: no statement at all."""
    entry = bundled().get(name)
    if entry is None:
        raise SkillNotFound
    return BuiltinSkillDetail(name=name, description=entry["description"], instructions=entry["instructions"])


def _library_rows(owner):
    # Names and descriptions only: the instructions stay in the row.
    return library_rows(owner, Skill.id, Skill.name, Skill.description)


def _off_everywhere(name: str, account_off: set[str]) -> bool:
    return name in account_off and name not in REQUIRED_SKILLS


async def list_skills(db: AsyncSession, user: TokenUser) -> SkillList:
    """Built-in skills, then the user's own, each marked when it is turned off for the whole account: one
    query reads the user's list and their skills together."""
    account, rows = (
        await db.execute(select(User.disabled_skills, _library_rows(User.id)).where(User.id == user.id))
    ).one()
    off = set(account)
    library = [
        SkillSummary(**row, source="library", off_everywhere=_off_everywhere(row["name"], off))
        for row in sorted(rows, key=lambda row: row["name"])
    ]
    builtin = [skill.model_copy(update={"off_everywhere": _off_everywhere(skill.name, off)}) for skill in _builtin()]
    return SkillList(skills=[*builtin, *library])


async def create_skill(db: AsyncSession, user: TokenUser, payload: SkillCreate) -> SkillDetail:
    """The import's insert with one row: the only conflict is a name the user already has."""
    created = await create_skills(db, user, [payload])
    if not created:
        raise SkillNameTaken
    return created[0]


async def get_skill(db: AsyncSession, user: TokenUser, skill_id: str) -> SkillDetail:
    skill = await db.scalar(select(Skill).where(Skill.id == skill_id, Skill.user_id == user.id))
    if skill is None:
        raise SkillNotFound
    return SkillDetail.model_validate(skill)


async def update_skill(db: AsyncSession, user: TokenUser, skill_id: str, payload: SkillUpdate) -> SkillDetail:
    skill = await db.scalar(
        update(Skill)
        .where(Skill.id == skill_id, Skill.user_id == user.id)
        .values(updated_at=datetime.now(UTC), **payload.model_dump(exclude_none=True))
        .returning(Skill)
    )
    if skill is None:
        raise SkillNotFound
    return SkillDetail.model_validate(skill)


async def delete_skill(db: AsyncSession, user: TokenUser, skill_id: str) -> None:
    """Deletes the skill and drops its name from the account's turned-off list, in one statement, so a
    new skill with the same name starts on."""
    gone = delete(Skill).where(Skill.id == skill_id, Skill.user_id == user.id).returning(Skill.name).cte("gone")
    deleted = await db.scalar(
        update(User)
        .add_cte(gone)
        .where(User.id == user.id, exists(select(gone.c.name)))
        .values(disabled_skills=func.array_remove(User.disabled_skills, select(gone.c.name).scalar_subquery()))
        .returning(User.id)
        .execution_options(synchronize_session=False)
    )
    if deleted is None:
        raise SkillNotFound


async def create_skills(db: AsyncSession, user: TokenUser, payloads: list[SkillCreate]) -> list[SkillDetail]:
    """Imports in one statement; a name the user already has is skipped, not an error for the whole batch."""
    if not payloads:
        return []
    now = datetime.now(UTC)
    rows = [
        {"id": str(uuid.uuid4()), "user_id": user.id, "created_at": now, "updated_at": now, **payload.model_dump()}
        for payload in payloads
    ]
    created = await db.scalars(upsert(Skill).values(rows).on_conflict_do_nothing().returning(Skill))
    return [SkillDetail.model_validate(skill) for skill in created]


async def import_github(db: AsyncSession, user: TokenUser, url: str, paths: list[str]) -> ImportResult:
    """The chosen skills from a repository, in one insert; a name the user already has is reported, not fatal."""
    found, failed = await importing.fetch_selected(url, paths)
    created = await create_skills(db, user, [skill for _, skill in found])
    names = {skill.name for skill in created}
    taken = [ImportFailure(path=path, reason=SkillNameTaken.DETAIL) for path, skill in found if skill.name not in names]
    return ImportResult(imported=created, failed=[*failed, *taken])


async def project_skills(db: AsyncSession, user: TokenUser, project_id: str) -> ProjectSkillList:
    """The project's own skills (always on), then built-in and library skills marked on or off for this
    project, in one query. A project skill hides a built-in or library skill of the same name, and says
    whether the library has one, since that skill is no longer listed to show it."""
    library = _library_rows(Chat.user_id)
    account = select(User.disabled_skills).where(User.id == Chat.user_id).scalar_subquery()
    # Names and descriptions only: the instructions stay in the row.
    own_names = func.jsonb_path_query_array(Chat.project_skills, literal("$[*].name", JSONPATH))
    own_descriptions = func.jsonb_path_query_array(Chat.project_skills, literal("$[*].description", JSONPATH))
    found = (
        await db.execute(
            select(Chat.disabled_skills, library, own_names, own_descriptions, account).where(
                Chat.id == project_id, Chat.user_id == user.id
            )
        )
    ).first()
    if found is None:
        raise ProjectNotFound
    disabled, rows, account_off = set(found[0]), sorted(found[1], key=lambda row: row["name"]), set(found[4])
    saved = {row["name"] for row in rows}
    own = [
        ProjectSkill(name=name, description=description, source="project", enabled=True, in_library=name in saved)
        for name, description in sorted(zip(found[2], found[3], strict=True))
    ]
    shadowed = {skill.name for skill in own}
    others = [
        *(summary.model_dump() for summary in _builtin()),
        *({**row, "source": "library"} for row in rows),
    ]
    return ProjectSkillList(
        skills=[
            *own,
            *(
                ProjectSkill(
                    **{**skill, "off_everywhere": _off_everywhere(skill["name"], account_off)},
                    # On means usable here: required, or on for the account and not turned off here.
                    enabled=skill.get("required")
                    or (skill["name"] not in account_off and skill["name"] not in disabled),
                )
                for skill in others
                if skill["name"] not in shadowed
            ),
        ]
    )


async def save_project_skill(db: AsyncSession, user: TokenUser, project_id: str, name: str) -> SkillDetail:
    """Copies one of the project's own skills into the user's library, so every project gets it: one
    statement, reading the skill from the project row. An unknown project or skill both answer 404."""
    if name in bundled_catalog():
        raise BuiltinSkillName
    matching = func.jsonb_path_query_first(
        Chat.project_skills, literal("$[*] ? (@.name == $name)", JSONPATH), func.jsonb_build_object("name", name)
    )
    skill = type_coerce(matching, JSONB)
    source = select(skill.label("skill")).where(Chat.id == project_id, Chat.user_id == user.id).subquery()
    now = datetime.now(UTC)
    values = bound(Skill, id=str(uuid.uuid4()), user_id=user.id, name=name, created_at=now, updated_at=now)
    copy = select(
        values["id"],
        values["user_id"],
        values["name"],
        source.c.skill["description"].astext,
        source.c.skill["instructions"].astext,
        values["created_at"],
        values["updated_at"],
    ).where(source.c.skill.is_not(None))
    try:
        saved = await db.scalar(
            insert(Skill)
            .from_select(["id", "user_id", "name", "description", "instructions", "created_at", "updated_at"], copy)
            .returning(Skill)
        )
    except IntegrityError:
        raise SkillNameTaken from None
    if saved is None:
        raise SkillNotFound
    return SkillDetail.model_validate(saved)


def _toggled(column, name: str, enabled: bool):
    """The stored list of turned-off skills after turning one on or off; a required skill stays on."""
    if not enabled and name in REQUIRED_SKILLS:
        raise SkillRequired
    others = func.array_remove(column, name)
    return others if enabled else func.array_append(others, name)


async def set_account_skill(db: AsyncSession, user: TokenUser, name: str, enabled: bool) -> None:
    """Turns a built-in or library skill on or off for every project, in one statement. Each project's
    own list is untouched, so turning it back on restores what each project had chosen."""
    disabled = _toggled(User.disabled_skills, name, enabled)
    known = true() if name in bundled_catalog() else exists().where(Skill.user_id == user.id, Skill.name == name)
    found = await db.scalar(
        update(User).where(User.id == user.id, known).values(disabled_skills=disabled).returning(User.id)
    )
    if found is None:
        raise SkillNotFound


async def set_project_skill(db: AsyncSession, user: TokenUser, project_id: str, name: str, enabled: bool) -> None:
    """Only turned-off skills are stored, so turning one on removes it from the list. A required skill
    cannot be turned off."""
    found = await db.scalar(
        update(Chat)
        .where(Chat.id == project_id, Chat.user_id == user.id)
        .values(disabled_skills=_toggled(Chat.disabled_skills, name, enabled))
        .returning(Chat.id)
    )
    if found is None:
        raise ProjectNotFound
