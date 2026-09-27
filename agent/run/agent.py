"""The configured default model client. Budget and usage hooks ride on its HTTP transport."""

from dotenv import load_dotenv

from ..routing.config import routing_settings
from ..routing.providers import chat_model
from ..routing.registry import MODELS
from ..sandbox.config import sandbox_settings

load_dotenv()

# chat_model first: it rejects an unknown id or a missing key with a clear message.
llm = chat_model(routing_settings.DEFAULT_MODEL)

# Fail at boot, not with a provider 400 on the first screenshot mid-run.
if sandbox_settings.PREVIEW_SCREENSHOTS_ENABLED and not MODELS[routing_settings.DEFAULT_MODEL].attachment:
    raise ValueError(
        f"DEFAULT_MODEL {routing_settings.DEFAULT_MODEL!r} cannot read images. "
        "Set PREVIEW_SCREENSHOTS_ENABLED=false or choose a model with attachment = true."
    )
