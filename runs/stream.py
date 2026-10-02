"""Server-sent event streams: one run's events with resume, and a project's notices.

Subscribe first, then backfill from the log, then live, dropping anything already sent.
Replaying before subscribing could lose an event published in between.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, suppress

from fastapi.sse import ServerSentEvent
from redis import RedisError
from redis.asyncio.client import PubSub
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from agent.events import EVENT_PAGE, run_events
from agent.run import bus
from agent.run.worker import OPEN_STATUSES
from db.base import AsyncSessionLocal, ReadSessionLocal
from db.models import Chat, Run
from runs.constants import STREAM_IDLE_SECONDS


async def run_stream(run_id: str, after: int) -> AsyncIterator[ServerSentEvent]:
    async with AsyncExitStack() as stack:
        pubsub: PubSub | None = None
        sent = after
        while True:
            if pubsub is None:
                # Redis down: serve from Postgres below and try again before the next read.
                with suppress(RedisError):
                    pubsub = await stack.enter_async_context(bus.subscribe(bus.run_channel(run_id)))
            # Status before events: a run that finishes in between still has its terminal
            # event in the rows read next, or arrives live on the channel we already hold.
            async with AsyncSessionLocal() as db:
                status = await db.scalar(select(Run.status).where(Run.id == run_id))
                events = await run_events(db, run_id, sent)
            for event in events:
                sent = event["sequence"]
                yield ServerSentEvent(data=event, id=str(sent))
            if len(events) == EVENT_PAGE:
                continue
            if status not in OPEN_STATUSES:
                return
            if pubsub is None:
                await asyncio.sleep(STREAM_IDLE_SECONDS)
                continue
            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=STREAM_IDLE_SECONDS)
                except RedisError:
                    # Redis is down: Postgres has every event, so poll it at the idle cadence. The
                    # next get_message reconnects and resubscribes by itself once Redis is back.
                    await asyncio.sleep(STREAM_IDLE_SECONDS)
                    break
                if message is None:
                    # Idle: re-read Postgres in case Redis dropped a message. FastAPI's
                    # EventSourceResponse sends the keep-alive ping itself, every 15 s.
                    break
                event = json.loads(message["data"])
                if event["sequence"] <= sent:
                    continue
                if event["sequence"] != sent + 1:
                    break  # A message was lost: backfill the gap from Postgres.
                sent = event["sequence"]
                yield ServerSentEvent(data=event, id=str(sent))
                if event["e"] == "run_finished":
                    return


async def ready_frame(project_id: str) -> ServerSentEvent:
    """`ready`, carrying the project's newest run and its title. Read after subscribing: a run or
    title committed before the read is in this frame, one committed after it arrives as a notice.
    The client reloads history only when it lacks that run, so a reconnect costs one query here
    instead of a history load per tab. Without the read it reloads everything, as before."""
    newest = select(Run.id).where(Run.chat_id == project_id).order_by(Run.created_at.desc()).limit(1).scalar_subquery()
    try:
        async with ReadSessionLocal() as db:
            row = (await db.execute(select(Chat.title, newest).where(Chat.id == project_id))).first()
    except SQLAlchemyError:
        row = None
    if row is None:
        return ServerSentEvent(data={"e": "ready"})
    title, latest_run_id = row
    return ServerSentEvent(data={"e": "ready", "latest_run_id": latest_run_id, "title": title})


async def project_stream(project_id: str) -> AsyncIterator[ServerSentEvent]:
    ready = False
    while True:
        try:
            async with bus.subscribe(bus.project_channel(project_id)) as pubsub:
                # Sent after every subscribe, so notices missed while Redis was down are caught up.
                ready = True
                yield await ready_frame(project_id)
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=STREAM_IDLE_SECONDS)
                    if message is not None:
                        yield ServerSentEvent(data=json.loads(message["data"]))
        except RedisError:
            # Notices are only doorbells: without Redis the client still composes, and runs still
            # stream from Postgres. FastAPI's 15 s ping keeps this stream open until Redis returns.
            if not ready:
                ready = True
                yield ServerSentEvent(data={"e": "ready"})
            await asyncio.sleep(STREAM_IDLE_SECONDS)
