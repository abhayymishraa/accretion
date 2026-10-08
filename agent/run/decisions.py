"""Resolve one saved question/plan under the caller's admission and database locks."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from db.models import Chat, Run

from .exceptions import (
    AnswerRequired,
    BriefTooLarge,
    ChangesNotAllowed,
    ClarificationLimit,
    DecisionAnswered,
    NotAwaitingInput,
    ProposalStale,
    RequestNotFound,
    UnsupportedAction,
)
from .workflow import public_workflow


async def decision_source(db, user_id, run_id, action, text):
    row = await db.scalar(
        select(Run)
        .join(Chat, Chat.id == Run.chat_id)
        .where(Run.id == run_id, Chat.user_id == user_id)
        .with_for_update()
    )
    if not row:
        raise RequestNotFound
    fingerprint = hashlib.sha256(json.dumps([action, text], ensure_ascii=False).encode()).hexdigest()
    workflow = row.workflow or {}
    if workflow.get("response_hash"):
        if workflow["response_hash"] != fingerprint:
            raise DecisionAnswered
        return row, fingerprint  # Exact HTTP retry: return the recorded continuation.
    if row.status != "awaiting_input":
        raise NotAwaitingInput
    kind = workflow.get("kind")
    if (action in ("approve", "revise") and kind != "plan") or (action == "answer" and kind != "clarify"):
        raise UnsupportedAction
    if action in ("answer", "revise") and not text.strip():
        raise AnswerRequired
    if action in ("approve", "dismiss") and text:
        raise ChangesNotAllowed
    return row, fingerprint


async def prepare_continuation(db, parent, action, text):
    chat = await db.get(Chat, parent.chat_id, with_for_update=True)
    if chat.latest_saved_revision_id != parent.workflow.get("revision_id"):
        raise ProposalStale
    context = parent.workflow.get("context") or {"original_request": parent.prompt, "exchanges": []}
    if len(context["exchanges"]) >= 4:
        raise ClarificationLimit
    context = {
        **context,
        "exchanges": [
            *context["exchanges"],
            {"proposal": public_workflow(parent.workflow), "action": action, "reply": text},
        ],
    }
    if len(json.dumps(context, ensure_ascii=False).encode()) > 48_000:
        raise BriefTooLarge
    # Revising a plan plans again, approving builds it, and an answer continues the run that asked.
    mode = {"revise": "plan", "approve": "auto"}.get(action, parent.workflow.get("mode", "auto"))
    workflow: dict[str, Any] = {"mode": mode, "context": context}
    if action == "approve":
        workflow.update(public_workflow(parent.workflow), approved=True, kind="execute")
    # The entire continuation shares the original cost and tool limits, not a fresh allowance.
    metrics = {
        key: value
        for key, value in (parent.metrics or {}).items()
        if key
        in {
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cost_nanos",
            "model",
            "reserved_tokens",
            "model_calls",
            "tool_calls",
            "turns",
            "repairs",
            "elapsed_ms",
            "preview_screenshots",
            "cached_input_tokens",
            "cache_write_tokens",
            "uncached_input_tokens",
        }
    }
    return workflow, metrics


def resolve_decision(parent, fingerprint, action, continuation_id=None):
    parent.workflow = {
        **parent.workflow,
        "response_hash": fingerprint,
        "resolution": action,
        "continuation_id": continuation_id,
    }
    parent.status = "cancelled" if action == "dismiss" else "answered"
    parent.finished_at = datetime.now(UTC)
