"""Request-local phase timings, without recording URLs, headers or payloads."""

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])

_timings: ContextVar[dict[str, float] | None] = ContextVar("request_timings", default=None)


@contextmanager
def measure(name):
    started = perf_counter()
    try:
        yield
    finally:
        spans = _timings.get()
        if spans is not None:
            spans[name] = spans.get(name, 0) + (perf_counter() - started) * 1000


def timed(name: str) -> Callable[[F], F]:
    """Record how long a handler spends, without changing its signature."""

    def decorate(function: F) -> F:
        @wraps(function)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            with measure(name):
                return await function(*args, **kwargs)

        return cast(F, wrapped)

    return decorate


async def request_timing(request, call_next):
    spans: dict[str, float] = {}
    token = _timings.set(spans)
    try:
        with measure("app"):
            response = await call_next(request)
        response.headers["Server-Timing"] = ", ".join(f"{name};dur={duration:.1f}" for name, duration in spans.items())
        return response
    finally:
        _timings.reset(token)
