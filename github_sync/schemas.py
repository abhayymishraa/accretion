"""Request and response shapes for GitHub routes."""

from typing import Any

from pydantic import Field

from models import CustomModel


class GithubAccountOut(CustomModel):
    configured: bool
    connected: bool
    login: str | None = None
    installed: bool = False


class ConnectStart(CustomModel):
    url: str


class ConnectFinish(CustomModel):
    code: str = Field(max_length=512)
    state: str = Field(max_length=128)
    installation_id: int | None = None


class RepoItem(CustomModel):
    id: int
    full_name: str
    private: bool
    updated_at: str | None = None


class RepoList(CustomModel):
    repos: list[RepoItem]


class ImportRequest(CustomModel):
    repo_id: int


class ImportResult(CustomModel):
    project_id: str


class ProjectRepoOut(CustomModel):
    linked: bool
    owner: str | None = None
    name: str | None = None
    url: str | None = None
    branch: str | None = None
    default_branch: str | None = None
    status: str | None = None
    message: str | None = None
    # Public by construction: file paths, a pull request URL. Never a value.
    detail: dict[str, Any] = Field(default_factory=dict)


class RepoCreate(CustomModel):
    name: str | None = Field(default=None, max_length=100)


class BranchItem(CustomModel):
    name: str
    current: bool


class BranchList(CustomModel):
    branches: list[BranchItem]


class BranchName(CustomModel):
    name: str = Field(min_length=1, max_length=255)


class PullOut(CustomModel):
    url: str
