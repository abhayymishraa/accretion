"""Request and response shapes for the Connections API. Secrets go in, and never come back out."""

from typing import Annotated

from pydantic import StringConstraints

from agent.tools.mcp import NAME, Auth
from models import CustomModel

ServerName = Annotated[str, StringConstraints(pattern=NAME.pattern)]


class CatalogEntry(CustomModel):
    id: str
    title: str
    description: str
    url: str
    auth: Auth
    maker: str
    docs_url: str


class CatalogList(CustomModel):
    servers: list[CatalogEntry]


class ToolInfo(CustomModel):
    name: str
    description: str
    read_only: bool
    approved: bool
    # The server changed this tool after the user approved it; it stays off until approved again.
    changed: bool


class ServerDetail(CustomModel):
    id: str
    name: str
    title: str
    description: str
    url: str
    auth: Auth
    key_hint: str | None
    # Has what it needs to sign in: always for "none", a stored key or tokens otherwise.
    connected: bool
    enabled: bool
    tools: list[ToolInfo]
    # A data URI, or None: the page shows the catalog logo or the default one.
    icon: str | None


class ServerList(CustomModel):
    servers: list[ServerDetail]


class ServerCreate(CustomModel):
    """A catalog entry by its id, or any server by its https address."""

    catalog_id: str | None = None
    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] | None = None
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None = None


class KeySave(CustomModel):
    value: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]
    # Servers added by URL: the header the key goes in. Catalog servers name their own.
    header_name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9-]{1,128}$")] | None = None


class IconSave(CustomModel):
    # A data URI; its bytes are checked, not its declared type. 32 KB in base64, plus the prefix.
    data_uri: Annotated[str, StringConstraints(max_length=44_000)]


class ToolApproval(CustomModel):
    approved: list[str]


class ServerToggle(CustomModel):
    enabled: bool


class SignInStart(CustomModel):
    authorization_url: str


class SignInFinish(CustomModel):
    state: Annotated[str, StringConstraints(min_length=16, max_length=256)]
    code: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    iss: str | None = None


class ProjectServer(CustomModel):
    name: str
    title: str
    description: str
    # On for this project; a server off for the account is off everywhere.
    enabled: bool
    account_enabled: bool
    connected: bool
    tool_count: int
    icon: str | None


class ProjectServerList(CustomModel):
    servers: list[ProjectServer]
