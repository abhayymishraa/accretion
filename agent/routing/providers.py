"""One chat-model client per provider, with the spend hooks on its async HTTP transport.

Our own thin layer over LangChain's provider packages, calling each provider's
API directly with no gateway in the path (spec section 1). OpenAI uses the
Responses API; OpenRouter uses its OpenAI-compatible Chat Completions; Gemini
uses its native API, because its OpenAI-compatible endpoint drops the thought
signatures that multi-turn tool calls require; Anthropic uses its Messages API,
with automatic prompt caching.

The helpers below exist because the three wires disagree on call options.
Gemini rejects any call kwarg it does not know, so call sites never pass
provider-specific kwargs directly.
"""

import asyncio
import functools
from typing import Any

import anthropic
import httpx
import httpx2
from google.genai import Client, types
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from ..budget.model_budget import model_rates, reserve_model_request, settle_model_response
from ..budget.usage import capture_provider_usage, invoke_with_usage
from . import failures
from .config import routing_settings
from .registry import MAX_OUTPUT_TOKENS, MODELS, ModelEntry

_TIMEOUT_SECONDS = 90
_KEYS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class _RefuseSync(httpx.BaseTransport):
    """Gemini's sync client carries no spend hooks, so it must never send.

    Its one caller is get_num_tokens (a blocking countTokens request); the
    runner's estimator falls back to a byte count on NotImplementedError.
    """

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        raise NotImplementedError("Synchronous model calls are not metered")


class _NoSyncClient:
    """Anthropic's sync client (token counting) carries no spend hooks and would block the loop. It refuses before
    the SDK sends, since the SDK reports a refusing transport as a connection error and the estimator's byte-count
    fallback needs NotImplementedError."""

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError("Synchronous model calls are not metered")


def _hooks() -> dict[str, list[Any]]:
    return {"request": [reserve_model_request], "response": [capture_provider_usage, settle_model_response]}


# One client per model per process, like the old module-level llm; copies share it.
@functools.cache
def chat_model(model_id: str) -> BaseChatModel:
    entry = MODELS.get(model_id)
    if entry is None:
        raise ValueError(f"Model {model_id!r} is not in agent/routing/models.toml")
    key = getattr(routing_settings, _KEYS[entry.provider])
    if not key:
        raise ValueError(f"{_KEYS[entry.provider]} is required for model {model_id!r}")
    if entry.provider == "gemini":
        # Timeout and retries are sent per request from these fields. For this
        # package max_retries counts attempts, so 2 is one retry, as for OpenAI.
        gemini = ChatGoogleGenerativeAI(
            model=model_id,
            api_key=key,
            reasoning_effort="low",
            max_output_tokens=MAX_OUTPUT_TOKENS,
            timeout=_TIMEOUT_SECONDS,
            max_retries=2,
        )
        # LangChain hands client_args to the sync and async clients alike. Rebuild
        # the client so the hooks sit on the async one only, and the sync one refuses.
        # The explicit transport keeps google-genai on httpx: it switches to aiohttp,
        # which has no event hooks, whenever aiohttp is importable and none is given.
        gemini.client = Client(
            api_key=key,
            http_options=types.HttpOptions(
                client_args={"transport": _RefuseSync()},
                async_client_args={"transport": httpx.AsyncHTTPTransport(), "event_hooks": _hooks()},
            ),
        )
        return gemini
    if entry.provider == "anthropic":
        claude = ChatAnthropic(
            model=model_id,
            api_key=key,
            max_tokens=MAX_OUTPUT_TOKENS,
            default_request_timeout=_TIMEOUT_SECONDS,
            max_retries=1,
            # Anthropic's automatic caching: one top-level marker, and the API moves the cache point to the last
            # cacheable block as the conversation grows. Anthropic caches only where asked; the others on their own.
            model_kwargs={"cache_control": {"type": "ephemeral"}},
        )
        # The clients are cached properties: set them so the async one carries the spend hooks and the sync one
        # (token counting) refuses, as for Gemini.
        claude.__dict__["_async_client"] = anthropic.AsyncClient(
            api_key=key,
            max_retries=1,
            timeout=_TIMEOUT_SECONDS,
            http_client=httpx2.AsyncClient(event_hooks=_hooks()),
        )
        claude.__dict__["_client"] = _NoSyncClient()
        return claude
    common: dict[str, Any] = {
        "model": model_id,
        "api_key": key,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "timeout": _TIMEOUT_SECONDS,
        "max_retries": 1,
        "http_async_client": httpx.AsyncClient(event_hooks=_hooks()),
    }
    if entry.provider == "openai":
        return ChatOpenAI(**common, use_responses_api=True, output_version="v0", reasoning={"effort": "low"})
    return ChatOpenAI(**common, base_url="https://openrouter.ai/api/v1", reasoning_effort="low")


def bind_tools(model: BaseChatModel, tools: list[Any], *, parallel: bool = True, **kwargs: Any) -> Any:
    """Bind tools. The editing loop allows several calls per turn (read-only ones run together,
    spec 5); routing needs exactly one. Gemini has no switch for it and rejects the kwarg."""
    if not parallel and not isinstance(model, ChatGoogleGenerativeAI):
        kwargs["parallel_tool_calls"] = False
    return model.bind_tools(tools, **kwargs)


def cache_options(model: BaseChatModel, key: str) -> dict[str, str]:
    """Gemini caches implicitly and rejects `prompt_cache_key`; Anthropic caches through its marker set on the client;
    the OpenAI-shaped wires accept the key."""
    return {} if isinstance(model, (ChatGoogleGenerativeAI, ChatAnthropic)) else {"prompt_cache_key": key}


def limit_output(model: BaseChatModel, max_tokens: int, *, reasoning: bool = True) -> BaseChatModel:
    """A copy with a smaller output ceiling, optionally at the provider's default reasoning.

    model_copy, never bind() or a call kwarg: both documented routes put
    `reasoning: null` on the OpenAI wire, and Gemini rejects unknown call
    kwargs. Setting the field instead makes LangChain omit it. The copy is
    shallow, so the spend-metered HTTP client and its hooks are shared rather
    than rebuilt, and the caller's model is untouched.
    """
    if isinstance(model, ChatGoogleGenerativeAI):
        update: dict[str, Any] = {"max_output_tokens": max_tokens}
        if not reasoning:
            update["reasoning_effort"] = None
    elif isinstance(model, ChatAnthropic):
        # Current Claude models think adaptively and cannot turn it off; only the ceiling changes.
        update = {"max_tokens": max_tokens}
    else:
        assert isinstance(model, ChatOpenAI)
        update = {"max_tokens": max_tokens}
        if not reasoning:
            update["reasoning" if model.use_responses_api else "reasoning_effort"] = None
    return model.model_copy(update=update)


def output_truncated(metadata: dict[str, Any]) -> bool:
    """The reply hit its output ceiling. Each wire names that stop differently.

    Gemini reports a tool call cut off at the ceiling as MALFORMED_FUNCTION_CALL, with no call
    returned: measured on a write_files that stopped at the cap.
    """
    return (
        metadata.get("finish_reason") in ("length", "MAX_TOKENS", "MALFORMED_FUNCTION_CALL")
        or metadata.get("stop_reason") == "max_tokens"
        or (metadata.get("incomplete_details") or {}).get("reason") == "max_output_tokens"
    )


def entry_for(model: BaseChatModel) -> ModelEntry:
    """The registry entry behind a client, including copies made by limit_output."""
    if isinstance(model, ChatGoogleGenerativeAI):
        return MODELS[model.model.removeprefix("models/")]
    if isinstance(model, ChatAnthropic):
        return MODELS[model.model]
    assert isinstance(model, ChatOpenAI)
    return MODELS[model.model_name]


def usable_models() -> list[ModelEntry]:
    """Models this deployment can call now: their provider key is set. Screenshots reach a model
    only when it reads images (agent/run/runner.py), so none is excluded for lacking them."""
    return [entry for entry in MODELS.values() if getattr(routing_settings, _KEYS[entry.provider])]


def price(entry: ModelEntry) -> tuple[int, int]:
    rates = model_rates(entry.id)
    return rates["output"], rates["input"]


def auto_models() -> list[ModelEntry]:
    """The Auto models callable now, cheapest first. A benched model rejoins when its cooldown ends."""
    return sorted((e for e in usable_models() if e.auto and not failures.cooling(e.id)), key=price)


class NoModelAvailable(Exception):
    """Every Auto model failed, replied empty, or is benched."""


async def invoke_auto(messages: list[BaseMessage], max_tokens: int, attempt_seconds: float) -> AIMessage:
    """Call the cheapest Auto model; on a provider failure or a timeout, bench it and try the next.
    An empty reply also moves on, unbenched: it is this call's output cap, not an outage.
    A budget refusal or a bad request is not the model's fault and propagates."""
    for entry in auto_models():
        try:
            async with asyncio.timeout(attempt_seconds):
                response = await invoke_with_usage(limit_output(chat_model(entry.id), max_tokens), messages)
        except Exception as exc:
            if not (isinstance(exc, TimeoutError) or failures.is_transient(exc)):
                raise
            failures.cool_down(entry.id)
            continue
        assert isinstance(response, AIMessage)
        if response.text.strip():
            return response
    raise NoModelAvailable


def same_tier(model_id: str) -> str | None:
    """Spec 6: the next Auto model at the same cost level that is usable and not cooling down."""
    word = MODELS[model_id].card.cost
    return next((e.id for e in auto_models() if e.id != model_id and e.card.cost == word), None)
