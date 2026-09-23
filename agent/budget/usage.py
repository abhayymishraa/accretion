"""Content-free provider usage, including fields older LangChain adapters omit."""
import hashlib
import json
from contextvars import ContextVar
from .model_budget import spend_scope

_provider_usage = ContextVar('provider_usage', default=None)


async def capture_provider_usage(response):
    """HTTPX response hook for our non-streaming Responses API calls only."""
    holder = _provider_usage.get()
    if holder is None:
        return
    if not response.is_success or response.request.url.path.rstrip('/') != '/v1/responses':
        return
    if 'application/json' not in response.headers.get('content-type', ''):
        return
    await response.aread()
    try:
        usage = response.json().get('usage')
    except (ValueError, AttributeError):
        return
    if isinstance(usage, dict):
        # Never retain raw response content, headers, IDs, or credentials.
        # LangChain may create child tasks: mutate this call's holder so usage reaches its caller.
        holder.update({key: usage[key] for key in
            ('input_tokens', 'output_tokens', 'total_tokens', 'input_tokens_details') if key in usage})


async def invoke_with_usage(model, messages, **kwargs):
    holder = {}
    token = _provider_usage.set(holder)
    try:
        response = await model.ainvoke(messages, **kwargs)
        if holder:
            response.response_metadata['provider_usage'] = holder
        return response
    except Exception:
        scope = spend_scope.get()
        if scope and scope.get('limit_error'):
            raise scope['limit_error'] from None
        raise
    finally:
        _provider_usage.reset(token)


def prompt_cache_key(instructions, tools, scope=''):
    """Opaque, stable routing key; never include user text or identifiers verbatim."""
    payload = json.dumps([instructions, tools, str(scope)], ensure_ascii=False, sort_keys=True)
    return 'webbuilder-' + hashlib.sha256(payload.encode()).hexdigest()[:32]


def record_usage(metrics, response, *, phase, estimated_input=None):
    usage = response.usage_metadata or {}
    for key in ('input_tokens', 'output_tokens', 'total_tokens'):
        metrics[key] = metrics.get(key, 0) + usage.get(key, 0)
    raw = response.response_metadata.get('provider_usage') or {}
    details = raw.get('input_tokens_details') or {}
    normalized = usage.get('input_token_details') or {}

    def count(value):
        return value if type(value) is int and value >= 0 else None

    cached = count(details.get('cached_tokens', normalized.get('cache_read')))
    written = count(details.get('cache_write_tokens', normalized.get('cache_creation')))
    input_tokens = usage.get('input_tokens', 0)
    uncached = (input_tokens - cached - written
                if cached is not None and written is not None and cached + written <= input_tokens else None)
    calls = metrics.setdefault('model_calls', [])
    calls.append({'phase': phase, 'input_tokens': input_tokens,
        'output_tokens': usage.get('output_tokens', 0), 'cached_input_tokens': cached,
        'cache_write_tokens': written, 'uncached_input_tokens': uncached,
        'estimated_input_tokens': estimated_input})
    # Missing provider fields stay unknown, not zero. These totals cover the reported calls only.
    for key in ('cached_input_tokens', 'cache_write_tokens', 'uncached_input_tokens'):
        known = [call[key] for call in calls if call[key] is not None]
        metrics[key] = sum(known) if len(known) == len(calls) else None
