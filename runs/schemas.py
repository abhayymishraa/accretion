"""Request bodies and responses for runs.

`ChatPayload` and `DecisionPayload` keep their names: they are published
OpenAPI component names, so renaming them breaks generated clients.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from models import CustomModel, UtcDatetime


class ChatPayload(BaseModel):
    prompt: str
    mode: Literal["auto", "plan"] = "auto"


class DecisionPayload(BaseModel):
    action: Literal["approve", "answer", "revise", "dismiss"]
    text: str = Field(default="", max_length=4000)


class RunEventItem(CustomModel):
    """An event row. `extra="allow"` keeps the per-event payload keys, which
    differ by event type; only the timestamp is declared so it is serialised
    the same way as every other timestamp in the API."""

    model_config = ConfigDict(extra="allow")

    created_at: UtcDatetime | None = None


class RunSummary(CustomModel):
    id: str
    status: str
    reason: str | None = None
    created_at: UtcDatetime | None = None
    metrics: dict[str, Any] | None = None
    workflow: dict[str, Any] | None = None
    events: list[RunEventItem] = Field(default_factory=list)


class RunList(CustomModel):
    runs: list[RunSummary]


class RunEventsPage(CustomModel):
    events: list[RunEventItem]
    status: str
    reason: str | None = None
    next_sequence: int
    detail_retention_days: int
    event_retention_days: int
