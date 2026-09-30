"""The configured default model client. Budget and usage hooks ride on its HTTP transport."""

from dotenv import load_dotenv

from ..routing.config import routing_settings
from ..routing.providers import chat_model

load_dotenv()

# chat_model rejects an unknown id or a missing key with a clear message, at boot.
llm = chat_model(routing_settings.DEFAULT_MODEL)
