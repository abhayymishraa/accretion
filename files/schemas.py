"""Responses for saved project files."""

from datetime import datetime

from models import CustomModel


class FileList(CustomModel):
    project_id: str
    files: list[str]
    revision_id: str | None = None
    sandbox_active: bool


class RevisionItem(CustomModel):
    id: str
    run_id: str | None = None
    created_at: datetime
    size_bytes: int | None = None
    file_count: int


class RevisionList(CustomModel):
    latest_saved_revision_id: str | None = None
    latest_verified_revision_id: str | None = None
    revisions: list[RevisionItem]
