"""Request and response bodies for the Supabase routes. No response carries a token, password or key."""

from typing import Annotated, Literal

from pydantic import Field

from models import CustomModel


class Organization(CustomModel):
    # The organization's slug: the Management API names organizations by slug.
    id: str
    name: str


class AccountOut(CustomModel):
    configured: bool
    connected: bool
    organizations: list[Organization] = Field(default_factory=list)


class ConnectStart(CustomModel):
    url: str


class ConnectFinish(CustomModel):
    code: str = Field(min_length=1, max_length=2048)
    state: str = Field(min_length=1, max_length=256)


class SupabaseProject(CustomModel):
    ref: str
    name: str
    region: str
    status: str


class ProjectList(CustomModel):
    projects: list[SupabaseProject]


class Region(CustomModel):
    id: str
    name: str


class RegionList(CustomModel):
    regions: list[Region]


class Finding(CustomModel):
    title: str
    detail: str
    remediation: str
    level: str


class DatabaseOut(CustomModel):
    offered: bool
    linked: bool
    ref: str | None = None
    name: str | None = None
    region: str | None = None
    status: str | None = None
    message: str | None = None
    dashboard_url: str | None = None
    findings: list[Finding] = Field(default_factory=list)


class CreateDatabase(CustomModel):
    mode: Literal["create"]
    organization_id: str = Field(pattern=r"^[\w-]+$", max_length=64)
    name: str = Field(min_length=1, max_length=256)
    region: str = Field(pattern=r"^[a-z]{2}-[a-z]+-\d$")


class ExistingDatabase(CustomModel):
    mode: Literal["existing"]
    ref: str = Field(pattern=r"^[a-z]{20}$")


LinkDatabase = Annotated[CreateDatabase | ExistingDatabase, Field(discriminator="mode")]
