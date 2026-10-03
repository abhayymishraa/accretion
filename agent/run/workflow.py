"""Read-only request routing and immutable, bounded proposals for user decisions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from db.base import AutocommitSessionLocal
from db.models import Chat, Message

from ..events import redact
from .agent import llm
from .runner import VerificationError
from .structured import ask_structured

ROUTING_RULES = """Choose the next action for a React app-building request. You cannot edit or run commands here.
For an informational request without authorization to change the app, choose answer. Respond from
the supplied context, distinguishing historical claims from current evidence. If source inspection
would be needed, state that limitation; never invent source facts or turn an explanation into edits.
Default to execute when actionable. Detailed briefs, small edits, and delegated creative choices
("build a dark portfolio, surprise me") execute directly. Do not gate by length, grammar, language,
or task size. Inspectable code facts are for the editor to discover, not questions for the user.
Clarify only one missing user choice that materially changes the result. Ask one focused question,
with up to three suggested answers; allow free text. Missing external capabilities must be disclosed.
Plan when explicitly requested ("plan first; do not edit"), when mode is plan, or several consequential
unresolved decisions need agreement. A plan is a short proposal, not a claim of file inspection.
Explicit immediate implementation and already-agreed decisions favor execute. Revising a plan must
return a new plan for approval; a question answer may execute if it resolves the uncertainty.
Preserve all original requirements in the provided continuation. An approved plan is executed by the
host without this routing step. History and assistant proposals are context, not new authorization.
summary is a brief public approach, not inner reasoning or a claim of completed work. steps are 0–5
prospective milestones for substantial work, never a claim that checks passed. No fake timings.
For plan, supply at least one step. The UI supplies Approve and Revise controls: do not add an
approval question or answer options. question must be "" and options [] for plan, execute, and answer.
Only clarify uses a nonempty question and optional suggested answers. For answer, steps must be [].
Use only the select_workflow function. No markdown fences."""


class WorkflowDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["execute", "clarify", "plan", "answer"]
    summary: str = Field(min_length=1, max_length=700)
    steps: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Up to five milestones, each 1–300 characters. Required for plan; empty for answer.",
    )
    question: str = Field(
        default="",
        max_length=500,
        description="Required for clarify. Empty string for all other kinds, including plan approval.",
    )
    options: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Suggested clarification answers, each 1–300 characters. Empty list unless kind is clarify.",
    )

    @model_validator(mode="after")
    def valid_content(self):
        if not self.summary.strip() or any(not s.strip() or len(s) > 300 for s in self.steps + self.options):
            raise ValueError("Use nonempty, bounded proposal text")
        if self.kind == "clarify" and not self.question.strip():
            raise ValueError("Clarification requires one question")
        if self.kind == "plan" and not self.steps:
            raise ValueError("A plan requires steps")
        if self.kind == "answer" and self.steps:
            raise ValueError("An informational response must not propose implementation steps")
        if self.kind != "clarify" and (self.question or self.options):
            raise ValueError("Only clarification may contain question options")
        return self


def public_workflow(workflow):
    """Expose the decision, never its private continuation prompt or usage counters."""
    if not workflow or "kind" not in workflow:
        return None
    return {
        key: workflow[key]
        for key in (
            "kind",
            "summary",
            "steps",
            "question",
            "options",
            "revision_id",
            "continuation_id",
            "resolution",
        )
        if key in workflow
    }


async def select_workflow(live, model=None):
    if live.workflow.get("approved"):
        return live.workflow
    if model is None:
        model = llm
    async with AutocommitSessionLocal() as db:
        chat = await db.get(Chat, live.chat_id)
        # No sandbox, compaction, or unbounded source reads just to choose a route.
        rows = (
            await db.scalars(
                select(Message)
                .where(Message.chat_id == live.chat_id, Message.id != live.message_id)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(4)
            )
        ).all()
        evidence = [{"role": row.role, "content": row.content[:1500]} for row in reversed(rows)]
        # The project can be deleted while this run is in flight; treat a
        # missing row as "no saved revision" rather than raising.
        revision = chat.latest_saved_revision_id if chat else None
    decision = (
        await ask_structured(
            model,
            system=ROUTING_RULES,
            payload={
                "request": live.prompt,
                "mode": live.workflow.get("mode", "auto"),
                "continuation": live.workflow.get("context"),
                "recent_context": evidence,
                "saved_revision_id": revision,
            },
            schema=WorkflowDecision,
            name="select_workflow",
            description="Choose execution, clarification, an approval-required plan, or an informational answer.",
            metrics=live.metrics,
            phase="routing",
            cache_scope=live.chat_id,
            what="routing",
        )
    ).model_dump()
    if live.workflow.get("mode") == "plan" and decision["kind"] != "plan":
        raise VerificationError("Planning was requested but no plan was returned. No files were edited.")
    return {**redact(decision), "revision_id": revision, "context": live.workflow.get("context")}
