"""E2B runtime settings.

The template references have no default on purpose: a wrong template builds the
wrong project, so an unset value must fail at boot rather than fall back.
"""

from pydantic import Field

from config import BaseConfig


class SandboxConfig(BaseConfig):
    E2B_API_KEY: str = ""
    # Spec 8: the one template, as "name:tag" (sandbox/templates.py tags every build). A new
    # project resolves the tag to its exact build, so moving the tag never changes old projects.
    E2B_TEMPLATE: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*:[A-Za-z0-9._-]+$")
    # The kit a new project starts from until the stack pick (#5) chooses one.
    DEFAULT_KIT: str = "vite-fastapi-postgres"
    # Bump to discard retained environments after a runtime change.
    E2B_RUNTIME_GENERATION: str = "1"

    PAUSED_SANDBOX_RETENTION_DAYS: int = 7
    PREVIEW_SCREENSHOTS_ENABLED: bool = True


sandbox_settings = SandboxConfig()
