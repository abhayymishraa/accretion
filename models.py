"""The base every response schema inherits.

One place to decide how values cross the wire. Without it, a datetime rendered
by `jsonable_encoder` and one rendered by a Pydantic model disagree on format
for the same column.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


class CustomModel(BaseModel):
    # `from_attributes` lets a schema be built straight from an ORM row.
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetimes(self, value: Any) -> Any:
        """Emit every timestamp as UTC ISO-8601 with a `Z` suffix."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return value
