"""Failure-only provider evidence. No sandbox resume, model calls or raw event data."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import math
import os
from urllib.parse import quote

from e2b import AsyncSandbox
import httpx


async def recent_metrics(sandbox_id):
    end = datetime.now(timezone.utc)
    samples = await AsyncSandbox.get_metrics(sandbox_id, start=end - timedelta(seconds=60),
                                             end=end, request_timeout=3)
    result = []
    for sample in samples[-3:]:
        values = {'timestamp': str(sample.timestamp)[:64]}
        for key in ('cpu_count', 'cpu_used_pct', 'mem_used', 'mem_total', 'disk_used', 'disk_total'):
            value = getattr(sample, key, None)
            if type(value) in (int, float) and math.isfinite(value):
                values[key] = value
        result.append(values)
    return {'available': True, 'samples': result}


async def lifecycle_events(sandbox_id):
    # E2B 2.49.1 has no public lifecycle-event SDK method. Use its documented
    # sandbox-scoped REST endpoint, never the all-projects event feed.
    key = os.getenv('E2B_API_KEY')
    if not key:
        return {'available': False, 'reason': 'not_configured'}
    url = 'https://api.e2b.app/events/sandboxes/' + quote(sandbox_id, safe='')
    async with httpx.AsyncClient(timeout=3, follow_redirects=False, trust_env=False) as client:
        async with client.stream('GET', url, headers={'X-API-Key': key}) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                if len(body) + len(chunk) > 65_536:
                    raise ValueError('Lifecycle response exceeds the diagnostic bound')
                body.extend(chunk)
    events = json.loads(body)
    if not isinstance(events, list):
        raise ValueError('Unexpected lifecycle response')
    owned = [event for event in events if isinstance(event, dict)
             and event.get('sandboxId') == sandbox_id]
    # eventData and metadata may contain user values. Only retain type/time/identity.
    return {'available': True, 'events': [
        {key: event[key][:80] for key in ('id', 'type', 'timestamp') if isinstance(event.get(key), str)}
        for event in owned[:5]]}


async def sandbox_diagnostics(sandbox_id):
    async def capture(fetch):
        try:
            async with asyncio.timeout(4):
                return await fetch(sandbox_id)
        except Exception as exc:
            # Failure to inspect must never replace the run failure or prevent cleanup.
            return {'available': False, 'error_type': type(exc).__name__}

    metrics, events = await asyncio.gather(capture(recent_metrics), capture(lifecycle_events))
    return {'sandbox_id': sandbox_id, 'metrics': metrics, 'lifecycle': events}
