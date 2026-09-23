"""Read-only request routing and immutable, bounded proposals for user decisions."""
import json
import logging
import os
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select

from db.base import AsyncSessionLocal
from db.models import Chat, Message
from ..events import redact
from .runner import RunLimitError, VerificationError, estimate_input_tokens
from ..budget.usage import invoke_with_usage, prompt_cache_key, record_usage

ROUTING_RULES = '''Choose the next action for a React app-building request. You cannot edit or run commands here.
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
Use only the select_workflow function. No markdown fences.'''


class WorkflowDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['execute', 'clarify', 'plan', 'answer']
    summary: str = Field(min_length=1, max_length=700)
    steps: list[str] = Field(default_factory=list, max_length=5,
        description='Up to five milestones, each 1–300 characters. Required for plan; empty for answer.')
    question: str = Field(default='', max_length=500,
        description='Required for clarify. Empty string for all other kinds, including plan approval.')
    options: list[str] = Field(default_factory=list, max_length=3,
        description='Suggested clarification answers, each 1–300 characters. Empty list unless kind is clarify.')

    @model_validator(mode='after')
    def valid_content(self):
        if not self.summary.strip() or any(not s.strip() or len(s) > 300 for s in self.steps + self.options):
            raise ValueError('Use nonempty, bounded proposal text')
        if self.kind == 'clarify' and not self.question.strip():
            raise ValueError('Clarification requires one question')
        if self.kind == 'plan' and not self.steps:
            raise ValueError('A plan requires steps')
        if self.kind == 'answer' and self.steps:
            raise ValueError('An informational response must not propose implementation steps')
        if self.kind != 'clarify' and (self.question or self.options):
            raise ValueError('Only clarification may contain question options')
        return self


def public_workflow(workflow):
    """Expose the decision, never its private continuation prompt or usage counters."""
    if not workflow or 'kind' not in workflow:
        return None
    return {key: workflow[key] for key in ('kind', 'summary', 'steps', 'question', 'options',
        'revision_id', 'continuation_id', 'resolution') if key in workflow}


async def select_workflow(live, model=None):
    if live.workflow.get('approved'):
        return live.workflow
    if model is None:
        from .agent import llm
        model = llm
    async with AsyncSessionLocal() as db:
        chat = await db.get(Chat, live.chat_id)
        # No sandbox, compaction, or unbounded source reads just to choose a route.
        rows = (await db.scalars(select(Message).where(Message.chat_id == live.chat_id,
            Message.id != live.message_id).order_by(Message.created_at.desc(), Message.id.desc()).limit(4))).all()
        evidence = [{'role': row.role, 'content': row.content[:1500]} for row in reversed(rows)]
        revision = chat.latest_saved_revision_id
    schema = convert_to_openai_tool(WorkflowDecision)
    schema['function']['name'] = 'select_workflow'
    schema['function']['description'] = 'Choose execution, clarification, an approval-required plan, or an informational answer.'
    messages = [SystemMessage(content=ROUTING_RULES), HumanMessage(content=json.dumps({
        'request': live.prompt, 'mode': live.workflow.get('mode', 'auto'),
        'continuation': live.workflow.get('context'),
        'recent_context': evidence, 'saved_revision_id': revision}, ensure_ascii=False))]
    estimate, _ = estimate_input_tokens(model, messages, json.dumps(schema))
    budget = int(os.getenv('RUN_MAX_TOKENS', '1000000'))
    if live.metrics.get('total_tokens', 0) + live.metrics.get('reserved_tokens', 0) + estimate + 2048 >= budget:
        raise RunLimitError('Token budget reached before request routing')
    response = await invoke_with_usage(model.bind_tools([schema], tool_choice='select_workflow',
        parallel_tool_calls=False), messages, max_tokens=2048,
        prompt_cache_key=prompt_cache_key(ROUTING_RULES, [schema], live.chat_id))
    record_usage(live.metrics, response, phase='routing', estimated_input=estimate)
    if live.metrics.get('total_tokens', 0) + live.metrics.get('reserved_tokens', 0) >= budget:
        raise RunLimitError('Token budget reached during request routing')
    metadata = response.response_metadata
    if metadata.get('finish_reason') == 'length' or (metadata.get('incomplete_details') or {}).get('reason') == 'max_output_tokens':
        raise VerificationError('The routing response was incomplete. No files were edited.')
    if response.invalid_tool_calls or len(response.tool_calls) != 1 or response.tool_calls[0]['name'] != 'select_workflow':
        raise VerificationError('Could not select a safe workflow. No files were edited.')
    try:
        decision = WorkflowDecision.model_validate(response.tool_calls[0]['args']).model_dump()
    except ValidationError as exc:
        # Keep validator diagnostics, never the user's prompt or model arguments.
        errors = exc.errors(include_input=False, include_context=False, include_url=False)
        logging.getLogger('webbuilder.runs').warning('Workflow validation failed run_id=%s errors=%s',
            live.id, json.dumps([{'type': error['type'], 'message': error['msg']} for error in errors]))
        raise VerificationError('The proposed workflow was incomplete. No files were edited.') from None
    if live.workflow.get('mode') == 'plan' and decision['kind'] != 'plan':
        raise VerificationError('Planning was requested but no plan was returned. No files were edited.')
    return {**redact(decision), 'revision_id': revision,
            'context': live.workflow.get('context')}
