"""Settings for publishing apps to the user's own Vercel account."""

from config import BaseConfig


class VercelConfig(BaseConfig):
    # From the Integration registered in the owner's Vercel team (Integrations Console). Its Redirect URL is
    # {FRONTEND_URL}/vercel/callback.
    VERCEL_CLIENT_ID: str = ""
    VERCEL_CLIENT_SECRET: str = ""
    # The Integration's public URL slug: the install page is vercel.com/integrations/<slug>/new.
    VERCEL_INTEGRATION_SLUG: str = "accretion"

    @property
    def configured(self) -> bool:
        return bool(self.VERCEL_CLIENT_ID and self.VERCEL_CLIENT_SECRET)


vercel_settings = VercelConfig()
