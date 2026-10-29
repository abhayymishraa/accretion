"""Request and response bodies for the Vercel routes. No response carries a token or a variable's value."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from models import CustomModel
from supabase_connect.schemas import Finding
from vercel_connect.models import Status


class AccountOut(CustomModel):
    configured: bool
    connected: bool


class ConnectStart(CustomModel):
    url: str


class ConnectFinish(CustomModel):
    code: str = Field(min_length=1, max_length=2048)
    state: str = Field(min_length=1, max_length=256)


class PublishOut(CustomModel):
    # "none": never published.
    status: Status | Literal["none"]
    url: str | None = None
    published_at: datetime | None = None
    # False when the app changed after the live copy was published.
    current: bool = False
    message: str | None = None
    # Vercel's page for this app: where the user adds a database, and reads the build log.
    dashboard_url: str | None = None
    logs_url: str | None = None
    # The end of a failed build's log, values hidden: shown to the user, and handed to the builder to fix.
    log: list[str] = Field(default_factory=list)
    # What the last publish's checks found (vercel_connect/scan.py): a warning each, never a stop.
    findings: list[Finding] = Field(default_factory=list)
    # Which database the app needs on Vercel.
    database: Literal["postgres", "mongo"]
