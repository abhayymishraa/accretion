"""Request bodies and responses for runs.

`ChatPayload` and `DecisionPayload` keep their names: they are published
OpenAPI component names, so renaming them breaks generated clients.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent.routing import providers as routing_providers
from models import CustomModel, UtcDatetime


class ChatPayload(BaseModel):
    prompt: str
    mode: Literal["auto", "plan"] = "auto"
    # "auto", or a model id from GET /models (spec 4.2).
    model_choice: str = "auto"

    @field_validator("model_choice")
    @classmethod
    def _available(cls, value: str) -> str:
        if value != "auto" and value not in {entry.id for entry in routing_providers.usable_models()}:
            raise ValueError(f"Model {value!r} is not available. Choose Auto.")
        return value


class ModelOption(CustomModel):
    id: str
    name: str
    speed: str
    cost: str


class ModelList(CustomModel):
    models: list[ModelOption]


class SteerPayload(BaseModel):
    # Spec 5 steering: an update the running build should take into account.
    text: str = Field(min_length=1, max_length=4000)


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
    has_more: bool
    detail_retention_days: int
    event_retention_days: int
