"""Redis doorbells for runs: the job queue, live event fan-out and run commands.

Postgres stays the record (runs, run_events). Anything here may be lost, and every reader
recovers from Postgres.
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
# Job list: RPUSH on admit, BLPOP in a worker.
QUEUE = _PREFIX + "runs:queue"
# Run ids that are queued or running. The reaper reads Postgres only while this is non-empty.
OPEN = _PREFIX + "runs:open"
# Set after a full resync from Postgres. Missing means Redis lost its data (no persistence in
# deploy/compose.yaml), so QUEUE and OPEN are incomplete and the reaper resyncs before trusting them.
SYNCED = _PREFIX + "runs:synced"
# Cancel and steer: every process hears it, the owner acts.
COMMANDS = _PREFIX + "runs:commands"

# A hung Redis fails a command after socket_timeout instead of stalling the caller. It must exceed
# the worker's BLPOP block (5 s). Pub/sub readers pass their own get_message timeout, which
# replaces socket_timeout for that read. With health_check_interval an idle connection, the
# command listener's included, is PINGed before reuse.
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
        # Log and drop cleanup errors: a failed close must not mask the caller's exit,
        # e.g. GeneratorExit when a client disconnects.
        try:
            await pubsub.aclose()
        except RedisError as exc:
            logger.warning("Redis pubsub close failed error_type=%s", type(exc).__name__)
