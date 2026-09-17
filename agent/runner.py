"""One editing conversation with shared budgets and host-controlled verification."""
import json
import os
import time
from collections import Counter

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_core.tools import tool
from typing import Literal
from .prompts import SYSTEM_PROMPT
from .tools import FileWriteError, WorkspaceTools, list_files
from .context import CONTEXT_RULES, choose_files
from .skills import RuntimeSkills
from .public_tools import encode_public, public_tool_details, preflight_failure
from .usage import invoke_with_usage, prompt_cache_key, record_usage
from .browser import check_browser, ensure_preview_current
from .commands import CommandStateError


class RunLimitError(Exception):
    pass


class VerificationError(Exception):
    pass


class SandboxSetupError(VerificationError):
    pass


def without_preview_images(messages):
    """Keep observations' text, but do not resend screenshots on later turns."""
    text_messages = []
    for message in messages:
        if isinstance(message, ToolMessage) and isinstance(message.content, list):
            content = [
                block for block in message.content
                if not isinstance(block, dict) or block.get('type') != 'image_url'
            ]
            message = message.model_copy(update={'content': content})
        text_messages.append(message)
    return text_messages


def estimate_input_tokens(model, messages, tool_schema: str) -> tuple[int, str]:
    images = sum(1 for message in messages if isinstance(message, ToolMessage)
                 and isinstance(message.content, list) for block in message.content
                 if isinstance(block, dict) and block.get('type') == 'image_url')
    messages = without_preview_images(messages)
    try:
        # LangChain counts message/tool-call text but not bound tool definitions.
        count = model.get_num_tokens_from_messages(messages) + model.get_num_tokens(tool_schema)
        estimator = 'tokenizer'
    except (NotImplementedError, ValueError):
        # Unsupported tokenizers or special-token literals must still have a bound.
        count = sum(len(str(m.content).encode()) +
                    len(str(getattr(m, 'tool_calls', '')).encode()) + 100 for m in messages)
        count += len(tool_schema.encode())
        estimator = 'bytes_fallback'
    # Allow for provider-specific message and tool framing; this is an estimate.
    # Low-detail image accounting is model-specific. Reserve conservatively without
    # tokenizing base64; measured provider usage still enforces the shared run budget.
    return count + 2000 + images * 4096, estimator


async def verify(workspace: WorkspaceTools) -> dict:
    missing = [view for view in ('desktop', 'mobile') if view not in workspace.preview_checks]
    if missing:
        return {'ok': False, 'browser': {'checked': False, 'errors': [
            'Use inspect_preview with steps ending in an assertion for: ' + ', '.join(missing) +
            '. Exercise the requested workflow (including mobile controls). For static content, assert its visibility.']}}
    build = await workspace.command('npm run build', timeout=90)
    if not build['ok']:
        return {'ok': False, 'build': build, 'browser': {'checked': False}}
    # Flush only after a successful build; infrastructure failures escape repair.
    await ensure_preview_current(workspace)
    browser = await check_browser(workspace, checks=workspace.preview_checks)
    return {'ok': browser['ok'], 'build': build, 'browser': browser}


async def run_editor(sandbox, prompt, emit, checkpoint, metrics, model=None, memory=None, request_context=None):
    workspace = WorkspaceTools(sandbox)
    workspace.screenshot_attempts = metrics.get('preview_screenshot_attempts', 0)
    await emit('stage', message='Checking sandbox browser tools')
    metrics['sandbox_check'] = await check_browser(workspace, preflight=True)
    if not metrics['sandbox_check']['ok']:
        category, explanation = preflight_failure(metrics['sandbox_check'])
        diagnostic = public_tool_details('browser_preflight', result=metrics['sandbox_check'])
        diagnostic['error_category'] = category
        await emit('verification', ok=False, message=explanation, checks=diagnostic)
        raise SandboxSetupError(explanation)
    await emit('verification', ok=True, message='Sandbox browser startup check passed')
    if model is None:
        from .agent import llm
        model = llm
    tools = {t.name: t for t in workspace.definitions()}
    @tool
    async def request_decision(kind: Literal['clarify', 'plan'], summary: str,
                               steps: list[str], question: str = '', options: list[str] = []) -> dict:
        """Pause only for a newly discovered material user choice. Never combine with other calls.

        For clarify, supply one nonempty question and up to three suggested options.
        For plan, supply a summary and 1–5 steps; question must be "" and options [].
        The UI supplies plan approval controls. Keep each step or option within 300 characters.
        """
        from .workflow import WorkflowDecision
        decision = WorkflowDecision(kind=kind, summary=summary, steps=steps,
                                    question=question, options=options)
        return {'ok': True, 'decision': decision.model_dump()}
    tools[request_decision.name] = request_decision
    skills = RuntimeSkills()
    skill_prompt = skills.prompt()
    if skill_prompt:
        skill_tool = skills.tool()
        tools[skill_tool.name] = skill_tool
    if memory is not None:
        history_tool = memory.tool()
        tools[history_tool.name] = history_tool
    max_turns = int(os.getenv('RUN_MAX_TURNS', '16'))
    max_calls = int(os.getenv('RUN_MAX_TOOL_CALLS', '32'))
    token_budget = int(os.getenv('RUN_MAX_TOKENS', '200000'))
    max_repairs = 2
    context = await memory.build(prompt, model, metrics, token_budget) if memory is not None else {}
    paths = await list_files(sandbox)
    initial = {}
    for path in choose_files(paths, prompt, context):
        try:
            content = await workspace.read(path)
            encoded = content.encode()
            initial[path] = {'content': encoded[:4000].decode('utf-8', errors='ignore'),
                             'truncated': len(encoded) > 4000}
        except Exception:
            initial[path] = {'error': 'Unable to read; inspect with tools before editing'}
    formatted_tools = [convert_to_openai_tool(t) for t in tools.values()]
    bound = model.bind_tools(formatted_tools, parallel_tool_calls=False)
    tool_schema = json.dumps(formatted_tools, ensure_ascii=False)
    messages = [SystemMessage(content=SYSTEM_PROMPT + '\n' + CONTEXT_RULES + skill_prompt +
        '\nInitial files may be excerpts. Read complete files before replacing them.'),
        HumanMessage(content=json.dumps({'project_context': context, 'request': prompt,
                                        'request_context': request_context,
                                        'files': initial, 'paths': paths}, ensure_ascii=False))]
    cache_key = prompt_cache_key(messages[0].content, formatted_tools, getattr(memory, 'chat_id', ''))
    repeated = Counter()
    repairs = metrics.get('repairs', 0)
    for turn in range(metrics.get('turns', 0), max_turns):
        metrics['turns'] = turn + 1
        if repairs:
            await emit('stage', message='Repairing verification errors')
        await checkpoint()
        # Bound growing conversation inputs as well as measured provider usage.
        if sum(len(str(m.content)) for m in without_preview_images(messages)) > 180_000:
            raise RunLimitError('Context budget reached; request a smaller change')
        estimated_input, estimator = estimate_input_tokens(model, messages, tool_schema)
        # Keep room for a useful response without always demanding the full 8k output ceiling.
        output_limit = min(8192, token_budget - metrics.get('total_tokens', 0) -
                           metrics.get('reserved_tokens', 0) - estimated_input - 1)
        if output_limit < 1024:
            metrics['token_budget'] = {'stage': 'preflight', 'limit': token_budget,
                'used': metrics.get('total_tokens', 0), 'reserved': metrics.get('reserved_tokens', 0),
                'estimated_input': estimated_input, 'output_reserve': 1024, 'estimator': estimator}
            raise RunLimitError('Token budget reached')
        response = await invoke_with_usage(bound, messages, max_tokens=output_limit,
                                           prompt_cache_key=cache_key)
        messages = without_preview_images(messages)
        record_usage(metrics, response, phase='editor', estimated_input=estimated_input)
        if metrics.get('total_tokens', 0) + metrics.get('reserved_tokens', 0) >= token_budget:
            metrics['token_budget'] = {'stage': 'provider_usage', 'limit': token_budget,
                'used': metrics.get('total_tokens', 0), 'reserved': metrics.get('reserved_tokens', 0)}
            raise RunLimitError('Token budget reached')
        metadata = response.response_metadata
        if (metadata.get('incomplete_details') or {}).get('reason') == 'max_output_tokens' or metadata.get('finish_reason') == 'length':
            metrics['token_budget'] = {'stage': 'model_output', 'limit': token_budget,
                'used': metrics.get('total_tokens', 0), 'output_limit': output_limit}
            raise RunLimitError('Model output budget reached; request a smaller change')
        messages.append(response)
        if response.invalid_tool_calls:
            raise VerificationError('Model returned an invalid tool call')
        if any(call['name'] == 'request_decision' for call in response.tool_calls) and len(response.tool_calls) != 1:
            raise VerificationError('A decision request cannot be combined with editing tools. No calls in this batch were executed.')
        if not response.tool_calls:
            await emit('stage', message='Checking production build and browser')
            checks = await verify(workspace)
            metrics['checks'] = checks
            await emit('verification', ok=checks['ok'], message='Build and selected desktop/mobile acceptance checks passed' if checks['ok'] else 'Verification failed', checks=checks)
            await checkpoint()
            if checks['ok']:
                return {'summary': response.text()[:1500] or 'Application updated.',
                        'url': 'https://' + sandbox.get_host(5173)}
            if repairs >= max_repairs:
                raise VerificationError('Build or browser checks still fail after two repair passes')
            repairs += 1
            metrics['repairs'] = repairs
            messages.append(HumanMessage(content='Fix only these verification errors: ' + json.dumps(checks)))
            continue
        before_revision = workspace.revision
        for call in response.tool_calls:
            metrics['tool_calls'] = metrics.get('tool_calls', 0) + 1
            if metrics['tool_calls'] > max_calls:
                raise RunLimitError('Tool-call budget reached')
            fingerprint = (call['name'], json.dumps(call['args'], sort_keys=True))
            # Reads are deduplicated until a mutation; other repeated operations are bounded globally.
            key = (*fingerprint, workspace.revision if call['name'] in {'read_files', 'inspect_preview'} else 0)
            repeated[key] += 1
            if repeated[key] >= 3:
                raise RunLimitError('Stopped repetitive tool calls without progress')
            call_id = call['id']
            stage = {'read_files': 'Inspecting existing files', 'read_skill': 'Loading relevant guidance',
                     'write_files': 'Editing project files', 'execute_command': 'Running a workspace command',
                     'inspect_preview': 'Checking the requested interactions'}.get(call['name'])
            if stage:
                await emit('stage', message=stage)
            await emit('tool_started', call_id=call_id, name=call['name'],
                       details=public_tool_details(call['name'], args=call['args']))
            started = time.monotonic()
            fatal_error = None
            try:
                if call['name'] not in tools:
                    raise ValueError('Unknown tool')
                result = await tools[call['name']].ainvoke(call['args'])
            except Exception as exc:
                result = {'ok': False, 'error': str(exc)[:2000]}
                if isinstance(exc, (CommandStateError, FileWriteError)):
                    fatal_error = exc
                    result.update(error_type=type(exc).__name__, status='unknown')
            duration = round((time.monotonic() - started) * 1000)
            metrics['preview_screenshot_attempts'] = workspace.screenshot_attempts
            image = result.pop('_image', None) if call['name'] == 'inspect_preview' else None
            serialized = json.dumps(result, ensure_ascii=False)
            detail = public_tool_details(call['name'], args=call['args'], result=result)
            # Keep valid JSON for old clients; new clients consume the structured projection.
            await emit('tool_completed', call_id=call_id, name=call['name'], ok=bool(result.get('ok')),
                       duration_ms=duration, details=detail, output=encode_public(detail))
            if fatal_error is not None:
                # Never checkpoint or edit while a command/upload may still mutate files.
                raise fatal_error
            content = serialized
            if image is not None:
                content = [{'type': 'text', 'text': serialized}, image]
                metrics['preview_screenshots'] = metrics.get('preview_screenshots', 0) + 1
            messages.append(ToolMessage(content=content, tool_call_id=call_id, status='success' if result.get('ok') else 'error'))
            if call['name'] == 'request_decision' and result.get('ok'):
                await checkpoint()
                return {'decision': result['decision']}
        await checkpoint(workspace.revision != before_revision)
    raise RunLimitError('Model-turn budget reached')
