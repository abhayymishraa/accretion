"""The default model and each provider's key. Key names are the ones each provider's SDK reads."""

from config import BaseConfig


class RoutingConfig(BaseConfig):
    # A registry id (agent/routing/models.toml). Checked at boot by agent/run/agent.py.
    DEFAULT_MODEL: str = "gemini-3.8-flash"

    # Only the default model's provider needs a key.
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    TYPESAFE_API_KEY: str = ""

    # Shadow mode (spec 4.1 step 4): Auto runs on DEFAULT_MODEL while Jev's pick is
    # logged next to the run's outcome and cost. True makes Auto use Jev's pick.
    ROUTER_LIVE: bool = False


routing_settings = RoutingConfig()
