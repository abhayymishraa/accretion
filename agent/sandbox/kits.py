"""Kits: working quickstart apps a project starts from (spec 8), described by stack.json.

The kit's code lives in sandbox/kits/<id>/ and is baked into the one E2B template with every
kit; the backend only reads each kit's stack.json. Loaded and validated at import,
so a bad kit fails at boot.
"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent import PACKAGE_ROOT

from .config import sandbox_settings

KITS_DIR = PACKAGE_ROOT.parent / "sandbox" / "kits"
# Where the template keeps each kit, dependencies installed (sandbox/templates.py).
TEMPLATE_KITS_DIR = "/opt/accretion/kits"


class Service(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    cwd: str
    start: str
    port: int = Field(gt=0, lt=65536)
    # HTTP path polled on `port` until it answers 200.
    ready: str


class Kit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    database: Literal["postgres", "mongo"]
    services: list[Service] = Field(min_length=1)
    preview_port: int
    install: str
    build: str
    typecheck: str
    migrate: str
    seed: str
    dump: str
    restore: str
    # Paths (files or folder prefixes) holding migrations; a change there runs the migration gate.
    migrations: list[str]
    # Secret names generated per project and written to .env (agent/sandbox/secrets.py).
    env: list[str]
    # Files shown to the model first (context.choose_files).
    entry: list[str] = Field(default_factory=list)


def _load() -> dict[str, Kit]:
    kits = {}
    for path in sorted(KITS_DIR.glob("*/stack.json")):
        kit = Kit.model_validate(json.loads(path.read_text()))
        if kit.id != path.parent.name:
            raise ValueError(f"Kit {kit.id!r} must live in a folder of the same name")
        if kit.preview_port not in {service.port for service in kit.services}:
            raise ValueError(f"Kit {kit.id!r} previews a port no service listens on")
        kits[kit.id] = kit
    if sandbox_settings.DEFAULT_KIT not in kits:
        raise ValueError(f"DEFAULT_KIT {sandbox_settings.DEFAULT_KIT!r} has no stack.json in sandbox/kits")
    return kits


KITS = _load()
