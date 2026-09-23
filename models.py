"""The base every response schema inherits, and the timestamp type they use.

One place to decide how values cross the wire. Without it, a datetime rendered
by `jsonable_encoder` and one rendered by a Pydantic model disagree on format
for the same column.

The formatting lives on the annotation rather than in a wildcard
`field_serializer`. A wildcard serializer has to accept and return `Any`, and
pydantic then cannot describe any field it touches: every property in a
top-level response schema loses its `type`, so the published OpenAPI stops
saying what the endpoint returns.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, WithJsonSchema


def _utc_z(value: datetime) -> str:
    """Emit a timestamp as UTC ISO-8601 with a `Z` suffix, naive or aware."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


# `return_type=str` is what keeps the rest of the schema intact; the explicit
# json schema then restores the `date-time` format that plain `str` would lose.
UtcDatetime = Annotated[
    datetime,
    PlainSerializer(_utc_z, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "format": "date-time"}),
]


class CustomModel(BaseModel):
    # `from_attributes` lets a schema be built straight from an ORM row.
    model_config = ConfigDict(from_attributes=True)
