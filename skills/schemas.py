"""Requests and responses for skills. The rules a skill must meet live here, once."""

from typing import Annotated, Literal

from pydantic import AfterValidator, Field, StringConstraints
from pydantic_core import PydanticCustomError

from agent.tools.skills import MAX_SKILL_BYTES, SKILL_NAME, bundled_catalog
from models import CustomModel, UtcDatetime
from skills.exceptions import BuiltinSkillName


def _own_name(name: str) -> str:
    # A custom error, so the message reaches the form as written, without pydantic's "Value error," prefix.
    if name.startswith(("anthropic-", "claude-")):
        raise PydanticCustomError("skill_name", "Names starting with anthropic- or claude- are reserved")
    if name in bundled_catalog():
        raise PydanticCustomError("skill_name", BuiltinSkillName.DETAIL)
    return name


# max_length kept beside the pattern: a too-long name gets that message, not "should match pattern".
SkillName = Annotated[str, StringConstraints(pattern=rf"^{SKILL_NAME.pattern}$", max_length=64)]
# One line: the description sits in the model's skill catalog, which has no newlines.
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1024, pattern=r"^[^\r\n]+$")
]
Instructions = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SKILL_BYTES)]


class SkillCreate(CustomModel):
    name: Annotated[SkillName, AfterValidator(_own_name)]
    description: Description
    instructions: Instructions


class SkillUpdate(CustomModel):
    # The name is fixed: per-project settings refer to a skill by name.
    description: Description | None = None
    instructions: Instructions | None = None


class SkillSummary(CustomModel):
    name: str
    description: str
    source: Literal["builtin", "library", "project"]
    # Library skills only.
    id: str | None = None
    # Built-in skills only: a platform skill the user cannot turn off.
    required: bool = False
    # Turned off for the whole account, so no project can use it.
    off_everywhere: bool = False


class SkillList(CustomModel):
    skills: list[SkillSummary]


class BuiltinSkillDetail(CustomModel):
    name: str
    description: str
    instructions: str


class SkillDetail(CustomModel):
    id: str
    name: str
    description: str
    instructions: str
    created_at: UtcDatetime
    updated_at: UtcDatetime


class ProjectSkill(SkillSummary):
    enabled: bool
    # Project skills only: the user's library already has a skill of this name.
    in_library: bool = False


class ProjectSkillList(CustomModel):
    skills: list[ProjectSkill]


class SkillToggle(CustomModel):
    enabled: bool


class GitHubSource(CustomModel):
    # A repository, or a folder in one: github.com/<owner>/<repo>[/tree/<ref>/<path>], or <owner>/<repo>.
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]


class GitHubImport(GitHubSource):
    paths: Annotated[list[Annotated[str, StringConstraints(max_length=300)]], Field(min_length=1, max_length=100)]


class ImportFailure(CustomModel):
    path: str
    reason: str


class FoundSkill(CustomModel):
    path: str
    name: str
    description: str


class GitHubSkills(CustomModel):
    repository: str
    ref: str
    skills: list[FoundSkill]
    # Files named SKILL.md that cannot become a skill, with the reason, so the list explains the gap.
    skipped: list[ImportFailure]


class ImportResult(CustomModel):
    imported: list[SkillDetail]
    failed: list[ImportFailure]
