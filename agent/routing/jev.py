"""Jev, TypeSafe's System One model: fast typed judgments for routing. Fails open on
any Jev error; a BudgetLimitError from the spend hook still propagates, like any model call.

Plain httpx, not typesafe-sdk: the SDK brings httpx2, which the spend hooks cannot
see, and retries for up to 30 s by default. The API is one POST (docs.typesafe.ai/api.md).
"""

import asyncio
import time
from typing import Any

import httpx

from ..budget.model_budget import reserve_model_request, settle_model_response
from .config import routing_settings
from .registry import JEV_MODEL

_URL = "https://api.typesafe.ai/v1/systemone"
# Spec 6: a 1.5 s ceiling and no retry; after 5 straight failures Jev is skipped for 60 s.
_TIMEOUT_SECONDS = 1.5
_TRIP_AFTER = 5
_SKIP_SECONDS = 60
_client = httpx.AsyncClient(
    timeout=_TIMEOUT_SECONDS,
    event_hooks={"request": [reserve_model_request], "response": [settle_model_response]},
)
_failures = 0
_skip_until = 0.0


async def ask(state: Any, questions: dict[str, Any]) -> dict[str, Any] | None:
    global _failures, _skip_until
    key = routing_settings.TYPESAFE_API_KEY
    if not key or time.monotonic() < _skip_until:
        return None
    try:
        # httpx timeouts apply per phase (connect, write, each read); this bounds the whole call.
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            response = await _client.post(
                _URL,
                json={"state": state, "model": JEV_MODEL, "questions": questions},
                headers={"Authorization": f"Bearer {key}"},
            )
        response.raise_for_status()
        answers = response.json()["answers"]
        if not isinstance(answers, dict):
            raise ValueError("Jev returned no answers map")
    except (httpx.HTTPError, TimeoutError, KeyError, ValueError):
        _failures += 1
        if _failures >= _TRIP_AFTER:
            _failures, _skip_until = 0, time.monotonic() + _SKIP_SECONDS
        return None
    _failures = 0
    return answers
