"""Responses for the project resource."""

from typing import Annotated, Any

from pydantic import StringConstraints

from models import CustomModel, UtcDatetime


class ProjectSummary(CustomModel):
    id: str
    title: str | None = None
    app_url: str | None = None
    user_id: int
    latest_saved_revision_id: str | None = None
    latest_verified_revision_id: str | None = None
    cover_updated_at: UtcDatetime | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class ProjectList(CustomModel):
    projects: list[ProjectSummary]


class ProjectRename(CustomModel):
    # 255 is the column width on chats.title.
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


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
    # Set on run items only (agent/context/history.py); without them the client draws no run card.
    run_status: str | None = None
    finished_at: UtcDatetime | None = None
    workflow: dict[str, Any] | None = None
    details_pending: bool | None = None
    # A finished run's file-editing tool calls, diffs without hunks, for its edited-files card.
    edits: list[dict[str, Any]] | None = None


class MessagePage(CustomModel):
    messages: list[MessageItem]
    next_cursor: str | None = None
    active_run_id: str | None = None
    pending_run_id: str | None = None
    chat: ProjectRef


class RunAdmission(CustomModel):
    """What starting or answering a run returns."""

    chat_id: str
    run_id: str | None = None
    status: str
