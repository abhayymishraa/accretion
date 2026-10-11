"""Settings for the services a generated app calls: email and sign-in."""

from config import BaseConfig


class GatewayConfig(BaseConfig):
    APP_EMAILS_PER_DAY: int = 100
    APP_EMAIL_FROM: str = ""


gateway_settings = GatewayConfig()
