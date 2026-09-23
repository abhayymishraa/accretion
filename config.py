"""Settings shared by more than one domain.

Domain-scoped settings live in `<domain>/config.py`. Nothing belongs here
unless two domains read it: a single app-wide settings object makes every
domain depend on every variable.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """How every settings class in this repository loads its values.

    Defined once so a change to the environment source is one edit, not seven.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppConfig(BaseConfig):
    DATABASE_URL: str = "postgresql://user:password@localhost/webbuilder"

    # Public origins. Trailing slashes are stripped once, here, so callers can
    # concatenate paths without each deciding how to normalise.
    FRONTEND_URL: str = "http://localhost:3000"
    PUBLIC_API_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @field_validator("FRONTEND_URL", "PUBLIC_API_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = AppConfig()
