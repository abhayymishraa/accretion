"""Which model runs a request: the user's choice, or Auto (spec 4.1).

Code filters on numbers first, because Jev is weak at arithmetic. Jev then picks
from plain-language cards, and code moves up one price level after a failed run.
One Jev request also answers the front door's kind and difficulty, logged only.
"""

from dataclasses import dataclass
from typing import Any

from ..budget.model_budget import call_bound
from . import jev
from .config import routing_settings
from .providers import auto_models, price
from .registry import MAX_OUTPUT_TOKENS, MODELS, ModelEntry

# Front door (spec 4): logged only in #3.
_KINDS = {
    "answer": "A question or an explanation; nothing in the app should change",
    "small_edit": "A small, local change to an existing app: some text, a colour, one component",
    "feature": "A new capability added to an existing app, touching several parts",
    "new_app": "Build a new app from a description",
}
_DIFFICULTY = [
    "Routine: a small, well-understood change",
    "Moderate: several parts of the app must change together",
    "Hard: complex logic, many files, or unclear requirements",
]


@dataclass(frozen=True)
class Pick:
    model_id: str
    log: dict[str, Any]


def _candidates(needed_tokens: int, remaining_nanos: int | None, failed_model: str | None) -> list[ModelEntry]:
    """Spec 4.1 step 1: drop a model the context would not fit or the budget cannot afford.
    `remaining_nanos` is the user's monthly budget left; None means unlimited. A model fits
    only if one call's reservation does: reserve() counts request bytes as tokens, about
    three per estimated token, at the dearest input rate.
    Step 3: after a failed run, keep only models priced above the one that failed."""
    floor = price(MODELS[failed_model]) if failed_model in MODELS else None
    return [
        entry
        for entry in auto_models()
        if needed_tokens <= entry.context_window * 95 // 100
        and (remaining_nanos is None or call_bound(entry.id, needed_tokens * 3, MAX_OUTPUT_TOKENS) <= remaining_nanos)
        and (floor is None or price(entry) > floor)
    ]


def _card(entry: ModelEntry) -> dict[str, str]:
    card = entry.card
    return {"what": card.what, "not_for": card.not_for, "speed": card.speed, "cost": card.cost}


async def pick_model(
    prompt: str, *, model_choice: str, needed_tokens: int, remaining_nanos: int | None, failed_model: str | None
) -> Pick:
    if model_choice != "auto":
        # Spec 4.2: the user's choice is used for every call; Jev is not asked.
        return Pick(model_choice, {"choice": model_choice})
    candidates = _candidates(needed_tokens, remaining_nanos, failed_model)
    questions: dict[str, Any] = {
        "kind": {"type": "choice", "instructions": "What kind of request is this?", "criteria": _KINDS},
        "difficulty": {"type": "score", "instructions": "How hard is this request to build?", "criteria": _DIFFICULTY},
    }
    if len(candidates) > 1:
        questions["model"] = {
            "type": "choice",
            "instructions": "Pick the cheapest model whose strengths cover this request.",
            "criteria": {entry.id: _card(entry) for entry in candidates},
        }
    answers = await jev.ask({"request": prompt[:12000]}, questions)
    model_answer = (answers or {}).get("model")
    jev_pick = model_answer.get("choice") if isinstance(model_answer, dict) else None
    # Only a model that passed the code filter may run, whatever Jev answered.
    allowed = {entry.id for entry in candidates}
    live_pick = jev_pick if jev_pick in allowed else (candidates[0].id if len(candidates) == 1 else None)
    model_id = live_pick if routing_settings.ROUTER_LIVE and live_pick else routing_settings.DEFAULT_MODEL
    log = {
        "choice": "auto",
        "mode": "live" if routing_settings.ROUTER_LIVE else "shadow",
        "candidates": [entry.id for entry in candidates],
        "failed_model": failed_model,
        "jev": answers,
        "would_pick": live_pick,
        "fallback": None if answers is not None else "jev_unavailable",
    }
    return Pick(model_id, log)
