"""Responses for the project resource."""

from typing import Any

from models import CustomModel, UtcDatetime


class ProjectSummary(CustomModel):
    id: str
    title: str | None = None
    app_url: str | None = None
    user_id: int
    latest_saved_revision_id: str | None = None
    latest_verified_revision_id: str | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class ProjectList(CustomModel):
    projects: list[ProjectSummary]


class ProjectRef(CustomModel):
    id: str
    title: str | None = None
    app_url: str | None = None
    created_at: UtcDatetime


class MessageItem(CustomModel):
    id: str
    role: str
    content: str | None = None
    event_type: str | None = None
    tool_calls: list[Any] | dict[str, Any] | None = None
    created_at: UtcDatetime


class MessagePage(CustomModel):
    messages: list[MessageItem]
    next_cursor: str | None = None
    active_run_id: str | None = None
    pending_run_id: str | None = None
    chat: ProjectRef


class ProjectDeletion(CustomModel):
    deleted: bool
    storage_cleanup: str
    sandbox_cleanup: str


class RunAdmission(CustomModel):
    """What starting or answering a run returns."""

    chat_id: str
    run_id: str | None = None
    status: str
    tokens_remaining: int | None = None
