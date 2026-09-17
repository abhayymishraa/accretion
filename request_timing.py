"""Request-local phase timings, without recording URLs, headers or payloads."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter

_timings = ContextVar('request_timings', default=None)


@contextmanager
def measure(name):
    started = perf_counter()
    try:
        yield
    finally:
        spans = _timings.get()
        if spans is not None:
            spans[name] = spans.get(name, 0) + (perf_counter() - started) * 1000


def timed(name):
    def decorate(function):
        @wraps(function)
        async def wrapped(*args, **kwargs):
            with measure(name):
                return await function(*args, **kwargs)
        return wrapped
    return decorate


async def request_timing(request, call_next):
    spans = {}
    token = _timings.set(spans)
    try:
        with measure('app'):
            response = await call_next(request)
        response.headers['Server-Timing'] = ', '.join(
            f'{name};dur={duration:.1f}' for name, duration in spans.items())
        return response
    finally:
        _timings.reset(token)
