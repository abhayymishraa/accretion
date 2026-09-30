"""Reserve each HTTP attempt, including SDK retries and context compaction.

Three wire formats reach these hooks: OpenAI Responses, OpenAI-compatible Chat
Completions (OpenRouter) and Gemini generateContent. Each has its own request
bound and usage reader; prices come from the routing registry and the cost
arithmetic is shared. A run's spend accumulates in its metrics as cost_nanos.
"""

import json
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from ..routing.registry import JEV_COST, JEV_MODEL, MAX_OUTPUT_TOKENS, MODELS
from .budget import BudgetLimitError, dollar_nanos, reserve, settle

spend_scope: ContextVar[dict[str, Any] | None] = ContextVar("spend_scope", default=None)

_GEMINI_PATH = re.compile(r"/models/([^/:]+):generateContent$")


def _nanos(rates, model):
    return {
        key: dollar_nanos(getattr(rates, field), f"{model!r} {field}")
        for key, field in (("input", "input"), ("cached", "cache_read"), ("write", "cache_write"), ("output", "output"))
    }


def model_rates(model):
    entry = MODELS.get(model)
    if entry is None and model != JEV_MODEL:
        raise BudgetLimitError("The selected model has no configured cost rates. Contact support.")
    rates: dict[str, Any] = _nanos(entry.cost if entry else JEV_COST, model)
    if entry and entry.long_context:
        rates["long"] = {**_nanos(entry.long_context, model), "above": entry.long_context.above}
    return rates


def model_cost(rates, inputs, outputs, cached=0, written=None):
    # Crossing the long-context tier re-prices the whole request, output included.
    long = rates.get("long")
    tier = long if long and inputs > long["above"] else rates
    # Unknown cache creation is conservatively charged at the higher input rate.
    input_rate = max(tier["input"], tier["write"]) if written is None else tier["input"]
    written = written or 0
    numerator = (
        (inputs - cached - written) * input_rate
        + cached * tier["cached"]
        + written * tier["write"]
        + outputs * tier["output"]
    )
    return (numerator + 999_999) // 1_000_000


def _worst_input(tier):
    return {**tier, "input": max(tier["input"], tier["cached"], tier["write"])}


def call_bound(model, inputs, output_limit):
    """The most one call can cost: every input token at its dearest rate, long tier included.

    What reserve_model_request holds, and what the router must fit in the budget left.
    """
    rates = model_rates(model)
    worst = _worst_input(rates)
    if "long" in rates:
        worst["long"] = _worst_input(rates["long"])
    return model_cost(worst, inputs, output_limit)


def request_bound(request):
    """The billed model, its output ceiling and the stream flag, per wire format."""
    path = request.url.path.rstrip("/")
    body = json.loads(request.content)
    if path.endswith("/responses"):
        if body.get("previous_response_id") or body.get("conversation") or body.get("prompt"):
            raise BudgetLimitError("Server-held model history requires separate cost accounting.")
        if any(tool.get("type") != "function" for tool in body.get("tools", [])):
            raise BudgetLimitError("Hosted model tools require separate cost accounting.")
        return body["model"], body.get("max_output_tokens"), body.get("stream")
    if path.endswith("/chat/completions"):
        if any(tool.get("type") != "function" for tool in body.get("tools", [])):
            raise BudgetLimitError("Hosted model tools require separate cost accounting.")
        return body["model"], body.get("max_completion_tokens", body.get("max_tokens")), body.get("stream")
    if match := _GEMINI_PATH.search(path):
        # Explicit caches and built-in tools (search, code execution) bill separately.
        if body.get("cachedContent") or any(set(tool) != {"functionDeclarations"} for tool in body.get("tools", [])):
            raise BudgetLimitError("Hosted model tools require separate cost accounting.")
        return match.group(1), (body.get("generationConfig") or {}).get("maxOutputTokens"), False
    if path.endswith("/v1/systemone"):
        # Jev bills input only and has no output ceiling to send. One token keeps the
        # shared "bounded output" check honest without pricing anything extra.
        return body["model"], 1, False
    raise BudgetLimitError("This model endpoint has no cost accounting configured.")


def response_usage(path, payload):
    """(inputs, outputs, cached, written) as the provider reported them; a count is None when unknown."""
    if path.endswith("/v1/systemone"):
        usage = payload.get("usage") or {}
        return usage.get("input_tokens"), usage.get("output_tokens"), 0, 0
    if path.endswith(":generateContent"):
        usage = payload.get("usageMetadata") or {}
        # Gemini bills thinking as output and omits counts that are zero.
        parts = [usage.get(key, 0) for key in ("candidatesTokenCount", "thoughtsTokenCount")]
        outputs = sum(parts) if all(type(part) is int for part in parts) else None
        # Implicit caching has no write charge.
        return usage.get("promptTokenCount"), outputs, usage.get("cachedContentTokenCount", 0), 0
    if path.endswith("/chat/completions"):
        usage = payload.get("usage") or {}
        details = usage.get("prompt_tokens_details") or {}
        inputs, outputs = usage.get("prompt_tokens"), usage.get("completion_tokens")
        return inputs, outputs, details.get("cached_tokens"), details.get("cache_write_tokens")
    usage = payload.get("usage") or {}
    details = usage.get("input_tokens_details") or {}
    inputs, outputs = usage.get("input_tokens"), usage.get("output_tokens")
    return inputs, outputs, details.get("cached_tokens"), details.get("cache_write_tokens")


def _add_run_cost(scope, nanos):
    metrics = scope["metrics"]
    metrics["cost_nanos"] = metrics.get("cost_nanos", 0) + nanos


async def reserve_model_request(request):
    scope = spend_scope.get()
    if scope is None:
        raise BudgetLimitError("Model spending requires an authenticated run scope.")
    if scope.get("limit_error"):
        raise scope["limit_error"]
    try:
        model, output_limit, stream = request_bound(request)
        rates = model_rates(model)
        if type(output_limit) is not int or not 1 <= output_limit <= MAX_OUTPUT_TOKENS or stream:
            raise BudgetLimitError("Model request needs a supported bounded output limit.")
        # Bound the transmitted body, not just a tokenizer estimate. This includes
        # tool definitions, Unicode, and image payloads (intentionally conservative).
        inputs = len(request.content) + 2000
        amount = call_bound(model, inputs, output_limit)
        entry = await reserve(
            scope["user_id"],
            "model",
            amount,
            690,
            {
                "model": model,
                "rates_nanos_per_million": rates,
                "input_bound": inputs,
                "output_limit": output_limit,
            },
            run_id=scope["run_id"],
        )
        request.extensions["webbuilder_spend"] = entry
        _add_run_cost(scope, amount)
    except BudgetLimitError as exc:
        # OpenAI may wrap hook exceptions as APIConnectionError; preserve the cause
        # in this run's task-local scope so the UI receives an actionable message.
        scope["limit_error"] = exc
        raise
    except Exception:
        scope["limit_error"] = BudgetLimitError(
            "Usage accounting is temporarily unavailable. No new model request was sent."
        )
        raise scope["limit_error"] from None


async def settle_model_response(response):
    try:
        entry = response.request.extensions.get("webbuilder_spend")
        if entry is None:
            return
        scope = spend_scope.get()
        assert scope is not None, "a reservation exists only inside a spend scope"
        # Only explicit rejections and provider errors are released: a 5xx returns no
        # completion to bill. Timeouts and transport failures never reach this hook and can
        # hide billable work, so their reservations stay charged.
        if response.status_code in {400, 401, 403, 404, 413, 422, 429} or response.status_code >= 500:
            await settle(entry.id, 0, {"outcome": "rejected"})
            _add_run_cost(scope, -entry.reserved_nanos)
            return
        if not response.is_success:
            return
        await response.aread()
        try:
            inputs, outputs, cached, written = response_usage(response.request.url.path.rstrip("/"), response.json())
            if any(type(value) is not int or value < 0 for value in (inputs, outputs)):
                return
            # `type(x) is int` above excludes bool deliberately; assert so the
            # arithmetic below is typed, without widening the check to isinstance.
            assert isinstance(inputs, int) and isinstance(outputs, int)
            cached_known = type(cached) is int and 0 <= cached <= inputs
            cached = cached if cached_known else 0
            assert isinstance(cached, int)
            written = written if type(written) is int and 0 <= written <= inputs - cached else None
            amount = model_cost(entry.details["rates_nanos_per_million"], inputs, outputs, cached, written)
        except (ValueError, TypeError, AttributeError):
            return
        await settle(
            entry.id,
            amount,
            {
                "input_tokens": inputs,
                "output_tokens": outputs,
                "cached_input_tokens": cached if cached_known else None,
                "cache_write_tokens": written,
                "usage_recorded_at": datetime.now(UTC).isoformat(),
                "cost_is_estimate": written is None or not cached_known,
            },
        )
        _add_run_cost(scope, amount - entry.reserved_nanos)
        if amount > entry.reserved_nanos:
            # Record the actual overage, stop further calls, and expose configuration drift.
            raise BudgetLimitError(
                "Provider usage exceeded its cost reservation. Saved files remain available; contact support."
            )
    except Exception as exc:
        scope = spend_scope.get()
        error = (
            exc
            if isinstance(exc, BudgetLimitError)
            else BudgetLimitError(
                "Usage accounting could not confirm the model response. Its cost remains reserved; retry later."
            )
        )
        if scope is not None:
            scope["limit_error"] = error
        raise error from None
