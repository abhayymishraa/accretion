"""Responses for saved project files."""

from models import CustomModel


class FileList(CustomModel):
    project_id: str
    files: list[str]
    revision_id: str | None = None
    sandbox_active: bool
