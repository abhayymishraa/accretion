"""What a provider exception means, and which models are cooling down (spec 6).

Overflow patterns are Pi's packages/ai/src/utils/overflow.ts, trimmed to the
providers this registry uses: OpenAI, OpenRouter backends, Gemini and Anthropic
("prompt is too long"). Anthropic's other errors are judged by their status, like the others.
"""

import re
import time

import anthropic
import httpx
import openai
from google.genai import errors as genai_errors

_OVERFLOW = re.compile(
    r"exceeds the context window|maximum context length|input token count.*exceeds the maximum"
    r"|exceeds (?:the )?maximum allowed input length|context[_ ]length[_ ]exceeded|too many tokens"
    r"|token limit exceeded|prompt is too long",
    re.IGNORECASE,
)
_NOT_OVERFLOW = re.compile(r"rate limit|too many requests", re.IGNORECASE)
# Rate limits, overload (529 is Anthropic/TypeSafe-style), gateway and server errors.
_TRANSIENT = {408, 409, 429, 500, 502, 503, 504, 529}
# A benched model rejoins on its own after this; one that still fails is benched again. An overload or outage is
# usually over within a minute; an account refusal lasts until someone fixes the account.
_TRANSIENT_COOLDOWN_SECONDS = 60
_ACCOUNT_COOLDOWN_SECONDS = 3600
# Billing refusals: a 429 that no retry fixes, only a top-up.
_OUT_OF_CREDITS = {"insufficient_quota", "credit_balance_exhausted"}
# Account refusals no retry fixes: a bad or revoked key, billing, no access to the model, a model no longer served.
_ACCOUNT_REFUSALS = {401, 402, 403, 404}
_cooling: dict[str, float] = {}


def _status(exc: BaseException) -> int | None:
    if isinstance(exc, (openai.APIStatusError, anthropic.APIStatusError)):
        return exc.status_code
    if isinstance(exc, genai_errors.APIError):
        return exc.code
    return None


def is_context_overflow(exc: BaseException) -> bool:
    """The provider refused the request as too long, on any wire. OpenAI also sets a code."""
    if isinstance(exc, openai.APIStatusError) and exc.code == "context_length_exceeded":
        return True
    status = _status(exc)
    if status == 413:
        return True
    text = str(exc)
    return status == 400 and bool(_OVERFLOW.search(text)) and not _NOT_OVERFLOW.search(text)


def is_transient(exc: BaseException) -> bool:
    """Worth retrying: rate limits, overload, server errors, dropped connections."""
    if isinstance(exc, (openai.APIConnectionError, anthropic.APIConnectionError, httpx.TransportError)):
        return True
    return _status(exc) in _TRANSIENT


def switch_now(exc: BaseException) -> bool:
    """The account behind this model cannot serve it: no credit, or a key that cannot reach it. Retrying cannot
    help; another model can."""
    if isinstance(exc, openai.APIStatusError) and exc.code in _OUT_OF_CREDITS:
        return True
    # Anthropic reports an empty prepaid balance as a 400 that says so.
    if isinstance(exc, anthropic.BadRequestError) and "credit balance" in exc.message:
        return True
    return _status(exc) in _ACCOUNT_REFUSALS


def cool_down(model_id: str, *, account: bool = False) -> None:
    seconds = _ACCOUNT_COOLDOWN_SECONDS if account else _TRANSIENT_COOLDOWN_SECONDS
    _cooling[model_id] = time.monotonic() + seconds


def cooling(model_id: str) -> bool:
    return _cooling.get(model_id, 0.0) > time.monotonic()
