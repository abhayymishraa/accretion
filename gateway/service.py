"""The owner's App services panel: the project's sign-in methods."""

from auth.config import auth_settings
from gateway.schemas import AppServices, SignInMethods


def app_services() -> AppServices:
    return AppServices(sign_in=SignInMethods(google=all(auth_settings.oauth_credentials("google"))))
