"""E2B runtime settings.

E2B_TEMPLATE_ID has no default on purpose: a wrong template builds the wrong
project, so an unset value must fail rather than fall back.
"""

from config import BaseConfig


class SandboxConfig(BaseConfig):
    E2B_API_KEY: str = ""
    E2B_TEMPLATE_ID: str
    # Bump to discard retained environments after a runtime change.
    E2B_RUNTIME_GENERATION: str = "1"

    PAUSED_SANDBOX_RETENTION_DAYS: int = 7
    PREVIEW_SCREENSHOTS_ENABLED: bool = True


sandbox_settings = SandboxConfig()
