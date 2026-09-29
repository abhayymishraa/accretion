"""One model call answered through a single forced tool call, validated into a Pydantic model."""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, ValidationError

from ..budget.usage import invoke_with_usage, prompt_cache_key, record_usage
from ..routing.providers import bind_tools, cache_options, limit_output, output_truncated
from .runner import VerificationError, estimate_input_tokens

logger = logging.getLogger("webbuilder.runs")


async def ask_structured[M: BaseModel](
    model,
    *,
    system: str,
    payload: dict[str, Any],
    schema: type[M],
    name: str,
    description: str,
    metrics: dict[str, Any],
    phase: str,
    cache_scope: str,
    what: str,
    max_output: int = 2048,
) -> M:
    """`what` names the step in user-facing errors, for example "routing"."""
    tool = convert_to_openai_tool(schema)
    tool["function"]["name"], tool["function"]["description"] = name, description
    messages = [SystemMessage(content=system), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
    estimate, _ = estimate_input_tokens(model, messages, json.dumps(tool))
    response = await invoke_with_usage(
        bind_tools(limit_output(model, max_output), [tool], parallel=False, tool_choice=name),
        messages,
        **cache_options(model, prompt_cache_key(system, [tool], cache_scope)),
    )
    record_usage(metrics, response, phase=phase, estimated_input=estimate)
    if output_truncated(response.response_metadata):
        raise VerificationError(f"The {what} response was incomplete. No files were edited.")
    if response.invalid_tool_calls or len(response.tool_calls) != 1 or response.tool_calls[0]["name"] != name:
        raise VerificationError(f"Could not complete {what}. No files were edited.")
    try:
        return schema.model_validate(response.tool_calls[0]["args"])
    except ValidationError as exc:
        # Keep validator diagnostics, never the user's prompt or model arguments.
        errors = exc.errors(include_input=False, include_context=False, include_url=False)
        logger.warning(
            "%s validation failed errors=%s",
            name,
            json.dumps([{"type": error["type"], "message": error["msg"]} for error in errors]),
        )
        raise VerificationError(f"The {what} result was incomplete. No files were edited.") from None
