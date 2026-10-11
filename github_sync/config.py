"""GitHub App settings: the App that pushes, pulls and signs users in."""

from pydantic import field_validator

from config import BaseConfig


class GithubConfig(BaseConfig):
    GITHUB_APP_ID: str = ""
    GITHUB_APP_SLUG: str = ""
    GITHUB_APP_CLIENT_ID: str = ""
    GITHUB_APP_CLIENT_SECRET: str = ""
    # PEM. An env file often holds it on one line with "\n" escaped.
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_APP_WEBHOOK_SECRET: str = ""

    @field_validator("GITHUB_APP_PRIVATE_KEY")
    @classmethod
    def _unescape(cls, value: str) -> str:
        return value.replace("\\n", "\n")

    @property
    def configured(self) -> bool:
        return all(
            (
                self.GITHUB_APP_ID,
                self.GITHUB_APP_SLUG,
                self.GITHUB_APP_CLIENT_ID,
                self.GITHUB_APP_CLIENT_SECRET,
                self.GITHUB_APP_PRIVATE_KEY,
                self.GITHUB_APP_WEBHOOK_SECRET,
            )
        )


github_settings = GithubConfig()
