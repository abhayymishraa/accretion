"""One server-sent event stream per project: its notices, and the events of the runs it follows.

Each run is followed by subscribing first, then backfilling from the log, then live, dropping
anything already sent. Replaying before subscribing could lose an event published in between.
A run event's id is `run_id:sequence`, so a reconnect resumes the run it was watching.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, nullcontext, suppress
from typing import Any

from fastapi.sse import ServerSentEvent
from redis import RedisError
from redis.asyncio.client import PubSub
from sqlalchemy import Row, select
from sqlalchemy.exc import SQLAlchemyError

from agent.events import EVENT_PAGE, run_events
from agent.run import bus
from agent.run.worker import OPEN_STATUSES
from db.base import AutocommitSessionLocal
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
            async with AutocommitSessionLocal() as db:
                status = await db.scalar(select(Run.status).where(Run.id == run_id))
                events = await run_events(db, run_id, sent)
            for event in events:
                sent = event["sequence"]
                yield ServerSentEvent(data=event, id=f"{run_id}:{sent}")
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
                yield ServerSentEvent(data=event, id=f"{run_id}:{sent}")
                if event["e"] == "run_finished":
                    return


class ProjectStream:
    """The project's notices and, interleaved, the events of every run it follows: the run a
    reconnect names in `resume` (its remaining events, even if it ended meanwhile), the open run
    and each run created while connected. Every source feeds one queue; a failed run read closes
    the stream, and the client reconnects and resumes."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.queue: asyncio.Queue[ServerSentEvent | None] = asyncio.Queue()
        self.followed: dict[str, asyncio.Task[None]] = {}
        # Set by open(): the subscription taken before the response starts, the row the first ready
        # frame is built from, and the resumed run with its status.
        self.pubsub: PubSub | None = None
        self.found: Row[Any] | None = None
        self.resume: str | None = None
        self.resume_status: str | None = None

    def ready_query(self, user_id: int | None = None, resume_run: str | None = None):
        """The project's title and newest run with its status, plus a resumed run's status: what a
        ready frame carries. With user_id, only the user's project matches."""
        newest = select(Run).where(Run.chat_id == self.project_id).order_by(Run.created_at.desc()).limit(1)
        resumed = select(Run.status).where(Run.id == resume_run, Run.chat_id == self.project_id)
        query = select(
            Chat.title,
            newest.with_only_columns(Run.id).scalar_subquery(),
            newest.with_only_columns(Run.status).scalar_subquery(),
            resumed.scalar_subquery(),
        ).where(Chat.id == self.project_id)
        return query.where(Chat.user_id == user_id) if user_id is not None else query

    def frame(self, found, subscribed: bool) -> dict[str, object]:
        frame: dict[str, object] = {"e": "ready"}
        if found:
            title, run_id, status = found[:3]
            if run_id and status in OPEN_STATUSES:
                self.follow(run_id)
            if subscribed:
                frame |= {"latest_run_id": run_id, "title": title}
        return frame

    async def open(self, stack: AsyncExitStack, user_id: int, resume: str | None) -> bool:
        """Before the response starts: subscribe to the project's notices, then read, in one query,
        whether the project is the user's and what the ready frame and a resumed run need. Read after
        subscribing, so a change made in between arrives as a notice. False when it is not theirs;
        the caller's stack then drops the subscription and nothing has been sent."""
        with suppress(RedisError):
            self.pubsub = await stack.enter_async_context(bus.subscribe(bus.project_channel(self.project_id)))
        resume_run = resume.split(":")[0] if resume else None
        async with AutocommitSessionLocal() as db:
            found = (await db.execute(self.ready_query(user_id, resume_run))).first()
        if found is None:
            return False
        # The frame, which starts following the newest open run, is built once the stream runs: after
        # the resume cursor is applied, and inside the block that cancels what it follows.
        self.resume, self.resume_status, self.found = resume, found[3], found
        return True

    async def events(self) -> AsyncIterator[ServerSentEvent]:
        if self.resume:
            # Before the notices start. An open run is followed from here, not from its start. An
            # ended run's remaining events are sent first and in full: were a later run's events
            # interleaved, a second reconnect would resume that run and skip the rest of this one.
            run_id, after = self.resume.split(":")
            status = self.resume_status
            if status in OPEN_STATUSES:
                self.follow(run_id, int(after))
            elif status is not None:
                async for event in run_stream(run_id, int(after)):
                    yield event
        notices = asyncio.create_task(self.notices())
        try:
            while (item := await self.queue.get()) is not None:
                yield item
        finally:
            tasks = [notices, *self.followed.values()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    def follow(self, run_id: str, after: int = 0) -> None:
        if run_id not in self.followed:
            self.followed[run_id] = asyncio.create_task(self.pump(run_id, after))

    async def pump(self, run_id: str, after: int) -> None:
        try:
            async for event in run_stream(run_id, after):
                await self.queue.put(event)
        except SQLAlchemyError:
            await self.queue.put(None)

    async def announce(self, subscribed: bool) -> None:
        # Read after subscribing: a run or title committed before the read is in this frame, one
        # committed after it arrives as a notice. The client then reloads history only when it
        # lacks that run. Without a subscription the frame stays bare and the client reloads.
        try:
            async with AutocommitSessionLocal() as db:
                found = (await db.execute(self.ready_query())).first()
        except SQLAlchemyError:
            found = None
        await self.queue.put(ServerSentEvent(data=self.frame(found, subscribed)))

    async def notices(self) -> None:
        ready = False
        # The first round uses the subscription and ready frame open() took before the response
        # started; a round after Redis failed subscribes and reads again.
        opened = self.pubsub
        while True:
            try:
                async with (
                    nullcontext(opened) if opened else bus.subscribe(bus.project_channel(self.project_id)) as pubsub
                ):
                    # Sent after every subscribe, so notices missed while Redis was down are caught up.
                    if ready:
                        await self.announce(subscribed=True)
                    else:
                        await self.queue.put(ServerSentEvent(data=self.frame(self.found, self.pubsub is not None)))
                    ready, opened = True, None
                    while True:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=STREAM_IDLE_SECONDS)
                        if message is None:
                            continue
                        notice = json.loads(message["data"])
                        if notice.get("e") == "run_created":
                            self.follow(notice["run_id"])
                        await self.queue.put(ServerSentEvent(data=notice))
            except RedisError:
                # Notices are only doorbells: without Redis the client still composes, and runs still
                # stream from Postgres. FastAPI's 15 s ping keeps this stream open until Redis returns.
                if not ready:
                    # Redis was down when the stream opened: the first frame goes out bare.
                    ready, opened = True, None
                    await self.queue.put(ServerSentEvent(data=self.frame(self.found, self.pubsub is not None)))
                await asyncio.sleep(STREAM_IDLE_SECONDS)
