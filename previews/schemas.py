"""Responses for the project preview."""

from models import CustomModel


class PreviewState(CustomModel):
    url: str | None = None
    state: str | None = None
    revision_id: str | None = None
