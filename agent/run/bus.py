"""Redis doorbells for runs: the job queue, live event fan-out and run commands.

Postgres stays the record (runs, run_events). Anything here may be lost, and every reader
recovers from Postgres. Pattern from Aegra @ 8cdf0b1 (services/redis_broker.py,
services/worker_executor.py).
"""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
from redis import RedisError
from redis.asyncio.client import PubSub

from .config import run_settings

logger = logging.getLogger("webbuilder.runs")

_PREFIX = "accretion:"
# Aegra's job list (WORKER_QUEUE_KEY): RPUSH on admit, BLPOP in a worker.
QUEUE = _PREFIX + "runs:queue"
# Run ids that are queued or running. The reaper reads Postgres only while this is non-empty.
OPEN = _PREFIX + "runs:open"
# Set after a full resync from Postgres. Missing means Redis lost its data (no persistence in
# deploy/compose.yaml), so QUEUE and OPEN are incomplete and the reaper resyncs before trusting them.
SYNCED = _PREFIX + "runs:synced"
# Aegra's cancel channel, widened to steer: every process hears it, the owner acts.
COMMANDS = _PREFIX + "runs:commands"

# A hung Redis fails a command after socket_timeout instead of stalling the caller. It must exceed
# the worker's BLPOP block (5 s). Pub/sub readers pass their own get_message timeout, which
# replaces socket_timeout for that read. health_check_interval is Aegra's REDIS_HEALTH_CHECK_INTERVAL
# (settings.py): an idle connection, the command listener's included, is PINGed before reuse.
client = redis.from_url(
    run_settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=10,
    socket_connect_timeout=5,
    health_check_interval=30,
)


def run_channel(run_id: str) -> str:
    return f"{_PREFIX}run:{run_id}"


def project_channel(chat_id: str) -> str:
    return f"{_PREFIX}project:{chat_id}"


async def publish(channel: str, message: dict[str, Any]) -> None:
    try:
        await client.publish(channel, json.dumps(message, default=str))
    except RedisError as exc:
        # At-most-once. Streams backfill from run_events on a sequence gap or when idle.
        logger.warning("Redis publish failed channel=%s error_type=%s", channel, type(exc).__name__)


@asynccontextmanager
async def subscribe(*channels: str) -> AsyncIterator[PubSub]:
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(*channels)
        yield pubsub
    finally:
        # Dify (_subscription.py) logs and drops cleanup errors: a failed close must not mask the
        # caller's exit, e.g. GeneratorExit when a client disconnects. Aegra does not guard this.
        try:
            await pubsub.aclose()
        except RedisError as exc:
            logger.warning("Redis pubsub close failed error_type=%s", type(exc).__name__)
