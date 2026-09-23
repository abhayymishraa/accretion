"""Reserve each HTTP attempt, including SDK retries and context compaction."""
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import os

from .budget import BudgetLimitError, dollar_nanos, reserve, settle

spend_scope = ContextVar('spend_scope', default=None)


def model_rates(model):
    # Changing models requires explicitly updating the matching rate configuration.
    if model != os.getenv('COST_MODEL', 'gpt-5.6-luna'):
        raise BudgetLimitError('The selected model has no configured cost rates. Contact support.')
    rates = {key: dollar_nanos(env, default) for key, env, default in (
        ('input', 'MODEL_INPUT_USD_PER_MILLION', '0.20'),
        ('cached', 'MODEL_CACHED_INPUT_USD_PER_MILLION', '0.02'),
        ('write', 'MODEL_CACHE_WRITE_USD_PER_MILLION', '0.25'),
        ('output', 'MODEL_OUTPUT_USD_PER_MILLION', '1.20'),
    )}
    if min(rates.values()) <= 0:
        raise BudgetLimitError('Model cost rates must be positive. Contact support.')
    return rates


def model_cost(rates, inputs, outputs, cached=0, written=None):
    # Unknown cache creation is conservatively charged at the higher input rate.
    input_rate = max(rates['input'], rates['write']) if written is None else rates['input']
    written = written or 0
    numerator = (inputs - cached - written) * input_rate + cached * rates['cached'] + written * rates['write']
    # Current Luna long-context rates. Rates/config must change with model policy.
    if inputs > 272_000:
        numerator *= 2
        numerator += outputs * rates['output'] * 3 // 2
    else:
        numerator += outputs * rates['output']
    return (numerator + 999_999) // 1_000_000


async def reserve_model_request(request):
    scope = spend_scope.get()
    if scope is None:
        raise BudgetLimitError('Model spending requires an authenticated run scope.')
    if scope.get('limit_error'):
        raise scope['limit_error']
    try:
        if not request.url.path.rstrip('/').endswith('/responses'):
            raise BudgetLimitError('This model endpoint has no cost accounting configured.')
        body = json.loads(request.content)
        rates = model_rates(body['model'])
        output_limit = body.get('max_output_tokens')
        if type(output_limit) is not int or not 1 <= output_limit <= 8192 or body.get('stream'):
            raise BudgetLimitError('Model request needs a supported bounded output limit.')
        if body.get('previous_response_id') or body.get('conversation') or body.get('prompt'):
            raise BudgetLimitError('Server-held model history requires separate cost accounting.')
        if any(tool.get('type') != 'function' for tool in body.get('tools', [])):
            raise BudgetLimitError('Hosted model tools require separate cost accounting.')
        # Bound the transmitted body, not just a tokenizer estimate. This includes
        # tool definitions, Unicode, and image payloads (intentionally conservative).
        inputs = len(request.content) + 2000
        reservation_rates = {**rates, 'input': max(rates['input'], rates['cached'], rates['write'])}
        amount = model_cost(reservation_rates, inputs, output_limit)
        entry = await reserve(scope['user_id'], 'model', amount, 690,
            {'model': body['model'], 'rates_nanos_per_million': rates,
             'input_bound': inputs, 'output_limit': output_limit}, run_id=scope['run_id'])
        request.extensions['webbuilder_spend'] = entry
    except BudgetLimitError as exc:
        # OpenAI may wrap hook exceptions as APIConnectionError; preserve the cause
        # in this run's task-local scope so the UI receives an actionable message.
        scope['limit_error'] = exc
        raise
    except Exception:
        scope['limit_error'] = BudgetLimitError('Usage accounting is temporarily unavailable. No new model request was sent.')
        raise scope['limit_error'] from None


async def settle_model_response(response):
    try:
        entry = response.request.extensions.get('webbuilder_spend')
        if entry is None:
            return
        # Only explicit rejections are released. Timeouts, server errors and transport
        # failures can hide billable work; retain those reservations for reconciliation.
        if response.status_code in {400, 401, 403, 404, 413, 422, 429}:
            await settle(entry.id, 0, {'outcome': 'rejected'})
            return
        if not response.is_success:
            return
        await response.aread()
        try:
            usage = response.json().get('usage') or {}
            inputs, outputs = usage.get('input_tokens'), usage.get('output_tokens')
            if any(type(value) is not int or value < 0 for value in (inputs, outputs)):
                return
            details = usage.get('input_tokens_details') or {}
            cached, written = details.get('cached_tokens'), details.get('cache_write_tokens')
            cached_known = type(cached) is int and 0 <= cached <= inputs
            cached = cached if cached_known else 0
            written = written if type(written) is int and 0 <= written <= inputs - cached else None
            amount = model_cost(entry.details['rates_nanos_per_million'], inputs, outputs, cached, written)
        except (ValueError, TypeError, AttributeError):
            return
        await settle(entry.id, amount, {'input_tokens': inputs, 'output_tokens': outputs,
            'cached_input_tokens': cached if cached_known else None, 'cache_write_tokens': written,
            'usage_recorded_at': datetime.now(timezone.utc).isoformat(),
            'cost_is_estimate': written is None or not cached_known})
        if amount > entry.reserved_nanos:
            # Record the actual overage, stop further calls, and expose configuration drift.
            raise BudgetLimitError('Provider usage exceeded its cost reservation. Saved files remain available; contact support.')
    except Exception as exc:
        scope = spend_scope.get()
        error = exc if isinstance(exc, BudgetLimitError) else BudgetLimitError(
            'Usage accounting could not confirm the model response. Its cost remains reserved; retry later.')
        if scope is not None:
            scope['limit_error'] = error
        raise error from None

