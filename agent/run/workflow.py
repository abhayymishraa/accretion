"""Read-only request routing and immutable, bounded proposals for user decisions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from db.base import AutocommitSessionLocal
from db.models import Chat, Message

from ..sandbox.secrets import NAME, RESERVED
from .runner import VerificationError
from .structured import ask_structured

ROUTING_RULES = """You are a routing step for an app builder. Your sole function is to label the user's latest message,
read with recent_context, as a change or a question. You cannot edit, run commands or read files; never answer it.

A message is a change if it meets ONE OR MORE of these:
1. It asks for something to be built, added, fixed, removed or made to look or work differently, in any words or
   language: an instruction, a polite request, a stated need ("I want a login page").
2. It agrees to a change proposed in recent_context ("yes", "do it", "sounds good", "2").
3. saved_revision_id is null and it describes anything to build.

A message is a question only if it asks about the app or the work so far and asks for no change ("did you use X?",
"how does login work?", "why is the header blue?"), or weighs an idea without asking for it yet.

Wording does not decide the label; what the user wants done does. A request phrased as a question is a change.
When unsure, choose change: a builder that answers a request with a question fails the user, and the builder can still
answer a question itself.

Examples:
"can you make the header blue?" -> {"reasoning": "A request phrased as a question.", "kind": "change"}
"yes" after an offer to switch the backend -> {"reasoning": "Agrees to the proposed change.", "kind": "change"}
"did you use fastify for the backend?" -> {"reasoning": "Asks what the app uses; no change.", "kind": "question"}
"what about a dark mode?" -> {"reasoning": "Weighs an idea; asks for nothing yet.", "kind": "question"}
"login kaam nahi kar raha" -> {"reasoning": "Reports a broken feature to fix.", "kind": "change"}
"the header feels off" -> {"reasoning": "Unclear; may want it fixed, so change.", "kind": "change"}

Use only the label_request function."""


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Reasoning first: the label is written after it, so it follows from it.
    reasoning: str = Field(description="One short sentence on why, referring to the rules above.")
    kind: Literal["change", "question"]


class WorkflowDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["clarify", "plan"]
    summary: str = Field(min_length=1, max_length=700)
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
    # The plan file's markdown, shown whole on the approval card; only a plan from plan mode carries it.
    plan: str = Field(default="", max_length=12_000)
    # Keys a question asks the user for: the card shows a field for each, saved as a project secret.
    secrets: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def valid_content(self):
        if not self.summary.strip() or any(not s.strip() or len(s) > 300 for s in self.options):
            raise ValueError("Use nonempty, bounded proposal text")
        if self.kind == "clarify" and not self.question.strip():
            raise ValueError("Clarification requires one question")
        if self.kind == "plan" and not self.plan.strip():
            raise ValueError("A plan requires its text")
        if self.kind != "plan" and self.plan:
            raise ValueError("Only a plan may contain plan text")
        if self.kind != "clarify" and (self.question or self.options or self.secrets):
            raise ValueError("Only clarification may contain question options")
        if any(not NAME.fullmatch(name) or name in RESERVED for name in self.secrets):
            raise ValueError("Name each key in capitals, digits and underscores, like STRIPE_SECRET_KEY")
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
            "plan",
            "secrets",
            "revision_id",
            "continuation_id",
            "resolution",
        )
        if key in workflow
    }


async def select_workflow(live, model):
    if live.workflow.get("approved"):
        return live.workflow
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
    mode = live.workflow.get("mode", "auto")
    # A plan run plans whatever was asked, and an answer to a question the build asked continues that build:
    # neither is labeled.
    change = {"kind": "execute", "mode": mode, "revision_id": revision, "context": live.workflow.get("context")}
    if mode == "plan" or change["context"]:
        return change
    try:
        label = await ask_structured(
            model,
            system=ROUTING_RULES,
            payload={"request": live.prompt, "recent_context": evidence, "saved_revision_id": revision},
            schema=RouteDecision,
            name="label_request",
            description="Label the request as a change to build or a question to answer.",
            metrics=live.metrics,
            phase="routing",
            cache_scope=live.chat_id,
            what="routing",
        )
    except VerificationError:
        # A failed label must not fail the request: build, as when unsure.
        return change
    if label.kind == "question":
        # The recent messages go to the answer; the run never stores them (service.py clears the workflow).
        return {"kind": "answer", "recent": evidence}
    return change
