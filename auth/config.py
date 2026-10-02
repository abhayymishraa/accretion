"""Authentication settings: signing, email delivery and OAuth credentials."""

from config import BaseConfig


class AuthConfig(BaseConfig):
    # Empty means "not configured": provider_enabled() and the deploy script
    # both treat a short key as disabled rather than failing at import.
    SECRET_KEY: str = ""

    RESEND_API_KEY: str = ""
    RESEND_FROM: str = ""
    # The one admin account: it skips the waitlist and receives each new signup.
    ADMIN_EMAIL: str = "grabhaymishra@gmail.com"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    def oauth_credentials(self, provider: str) -> tuple[str, str]:
        """Client id and secret for a provider, or empty strings when unset."""
        return (
            getattr(self, f"{provider.upper()}_CLIENT_ID", ""),
            getattr(self, f"{provider.upper()}_CLIENT_SECRET", ""),
        )

    @property
    def email_configured(self) -> bool:
        return bool(self.RESEND_API_KEY and self.RESEND_FROM)


auth_settings = AuthConfig()
