"""Settings for the Supabase connection."""

from config import BaseConfig


class SupabaseConfig(BaseConfig):
    # From the OAuth app registered in the owner's Supabase organization (Organization settings, OAuth Apps).
    SUPABASE_OAUTH_CLIENT_ID: str = ""
    SUPABASE_OAUTH_CLIENT_SECRET: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.SUPABASE_OAUTH_CLIENT_ID and self.SUPABASE_OAUTH_CLIENT_SECRET)


supabase_settings = SupabaseConfig()
