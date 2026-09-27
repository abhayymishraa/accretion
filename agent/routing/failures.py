"""What a provider exception means, and which models are cooling down (spec 6).

Overflow patterns are Pi's packages/ai/src/utils/overflow.ts, trimmed to the
providers this registry uses: OpenAI, OpenRouter backends and Gemini.
"""

import re
import time

import httpx
import openai
from google.genai import errors as genai_errors

_OVERFLOW = re.compile(
    r"exceeds the context window|maximum context length|input token count.*exceeds the maximum"
    r"|exceeds (?:the )?maximum allowed input length|context[_ ]length[_ ]exceeded|too many tokens"
    r"|token limit exceeded",
    re.IGNORECASE,
)
_NOT_OVERFLOW = re.compile(r"rate limit|too many requests", re.IGNORECASE)
# Rate limits, overload (529 is Anthropic/TypeSafe-style), gateway and server errors.
_TRANSIENT = {408, 409, 429, 500, 502, 503, 504, 529}
_COOLDOWN_SECONDS = 300
_cooling: dict[str, float] = {}


def _status(exc: BaseException) -> int | None:
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code
    if isinstance(exc, genai_errors.APIError):
        return exc.code
    return None


def is_context_overflow(exc: BaseException) -> bool:
    """The provider refused the request as too long, on any wire. OpenAI also sets a code; Codex reads it."""
    if isinstance(exc, openai.APIStatusError) and exc.code == "context_length_exceeded":
        return True
    status = _status(exc)
    if status == 413:
        return True
    text = str(exc)
    return status == 400 and bool(_OVERFLOW.search(text)) and not _NOT_OVERFLOW.search(text)


def is_transient(exc: BaseException) -> bool:
    """Worth retrying: rate limits, overload, server errors, dropped connections."""
    if isinstance(exc, (openai.APIConnectionError, httpx.TransportError)):
        return True
    return _status(exc) in _TRANSIENT


def cool_down(model_id: str) -> None:
    _cooling[model_id] = time.monotonic() + _COOLDOWN_SECONDS


def cooling(model_id: str) -> bool:
    return _cooling.get(model_id, 0.0) > time.monotonic()
