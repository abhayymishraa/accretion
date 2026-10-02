"""Run workers: claim queued runs under a Postgres lease, keep the lease alive, end expired ones.

Ported from Aegra @ 8cdf0b1b7d004c7700bfc255be18d5d496a2e97d: services/worker_executor.py
(queue, semaphore, lease, heartbeat) and services/lease_reaper.py (expired and stuck runs).
Deliberate differences:
- An expired lease ends the run as interrupted instead of re-queueing it: agent/AGENTS.md,
  "Recovery makes no model calls".
- Cancel is durable: Run.cancel_requested is read by every heartbeat; the Redis command
  only makes it immediate.
- The reaper and the queue fallback read Postgres only while bus.OPEN is non-empty, so an
  idle Neon database can suspend.
"""

import asyncio
import json
import logging
import os
import socket
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from redis import RedisError
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from db.base import AsyncSessionLocal
from db.models import Chat, Run

from . import bus
from .config import run_settings

if TYPE_CHECKING:
    from .service import LiveRun, Service

logger = logging.getLogger("webbuilder.runs")

# Aegra lease_reaper.py STUCK_PENDING_THRESHOLD_SECONDS: a queued run this old that is missing
# from the Redis list lost its wake-up (Redis restarted) and is pushed again.
_STUCK_QUEUED_SECONDS = 120
# Aegra's lease timings (settings.py): 30 s lease renewed every 10 s, so it outlives two missed
# heartbeats; swept every 15 s; a 5 s Postgres poll while Redis is unreachable.
_LEASE_SECONDS = 30
_HEARTBEAT_SECONDS = 10
_REAPER_SECONDS = 15
_QUEUE_POLL_SECONDS = 5

# A run in either state holds a worker slot or waits for one.
OPEN_STATUSES = ("queued", "running")


def _lease_end() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=_LEASE_SECONDS)


class Workers:
    def __init__(self, service: "Service"):
        self.service = service
        self.name = f"{socket.gethostname()}-{os.getpid()}"
        self.tasks: list[asyncio.Task[None]] = []
        # Aegra worker_executor.py _job_tasks: asyncio holds tasks weakly, and stop() must cancel the
        # runs too, or one still claiming at shutdown starts executing after the pool is disposed.
        self.jobs: set[asyncio.Task[None]] = set()
        # Redis may be missing open ids (a refused enqueue or bus.OPEN write, or a restarted
        # Redis), so the next reaper pass reads Postgres without the bus.OPEN gate.
        self.unsynced = False

    async def start(self) -> None:
        # Redis has no persistence: put every open row back. Queued rows made no model call yet,
        # so ringing for them again is safe; running ones go back in bus.OPEN for the reaper.
        await self.sync(datetime.now(UTC))
        self.tasks = [
            asyncio.create_task(self.loop(), name=f"worker:{index}") for index in range(run_settings.WORKER_COUNT)
        ]
        self.tasks.append(asyncio.create_task(self.reap_loop(), name="lease-reaper"))
        self.tasks.append(asyncio.create_task(self.listen_commands(), name="run-commands"))

    async def stop(self) -> None:
        # A cancelled job cancels its execute task; execute then records interrupted (stopping is set)
        # and the job's finally releases the lease.
        for task in [*self.tasks, *self.jobs]:
            task.cancel()
        await asyncio.gather(*self.tasks, *self.jobs, return_exceptions=True)

    async def loop(self) -> None:
        slots = asyncio.Semaphore(run_settings.RUN_JOBS_PER_WORKER)
        while True:
            await slots.acquire()
            run_id = await self.dequeue()
            if run_id is None or self.service.stopping:
                if run_id is not None:
                    # Aegra _push_back: dequeued during shutdown, hand it to the next process.
                    await self.enqueue(run_id)
                slots.release()
                continue
            task = asyncio.create_task(self.run(run_id), name=f"job:{run_id}")
            self.jobs.add(task)
            task.add_done_callback(self.jobs.discard)
            task.add_done_callback(lambda _: slots.release())

    async def dequeue(self) -> str | None:
        try:
            # An idle BLPOP returns None at 5 s, before the client's 10 s socket_timeout (bus.py), so
            # a TimeoutError here means a hung Redis, not an empty queue: it takes the branch below.
            item = await bus.client.blpop([bus.QUEUE], timeout=5)
            return item[1] if item else None
        except RedisError as exc:
            # Aegra _dequeue: Redis down, so poll Postgres for the oldest queued run. A restarted Redis
            # has lost QUEUE and OPEN, so the reaper resyncs every open row from Postgres too.
            logger.warning("Redis dequeue failed, polling Postgres error_type=%s", type(exc).__name__)
            self.unsynced = True
            await asyncio.sleep(_QUEUE_POLL_SECONDS)
            try:
                async with AsyncSessionLocal() as db:
                    return await db.scalar(
                        select(Run.id).where(Run.status == "queued").order_by(Run.created_at).limit(1)
                    )
            except SQLAlchemyError as db_exc:
                # Aegra _worker_loop logs and re-loops; a dead loop would stop this process taking runs.
                logger.warning("Queue poll failed error_type=%s", type(db_exc).__name__)
                return None

    async def claim(self, run_id: str) -> "LiveRun | None":
        """Take a queued run. None when another worker won it or it was cancelled first."""
        async with AsyncSessionLocal.begin() as db:
            run = await db.scalar(
                update(Run)
                .where(Run.id == run_id, Run.status == "queued")
                .values(status="running", claimed_by=self.name, lease_expires_at=_lease_end())
                .returning(Run)
            )
            if run is None:
                return None
            # The claimed row is locked, so its chat cannot be deleted under it (runs cascade on chat).
            chat = await db.get_one(Chat, run.chat_id)
        live = self.service.load_live(run, chat)
        # Cancelled while still queued, after the canceller's own claim lost to this one.
        live.cancelling = run.cancel_requested
        return live

    async def enqueue(self, run_id: str) -> None:
        # A refused push leaves the row queued in Postgres; unsynced makes the reaper resync it.
        try:
            async with bus.client.pipeline() as pipe:
                pipe.sadd(bus.OPEN, run_id)
                pipe.rpush(bus.QUEUE, run_id)
                await pipe.execute()
        except RedisError as exc:
            logger.warning("Redis enqueue failed run_id=%s error_type=%s", run_id, type(exc).__name__)
            self.unsynced = True

    async def sync(self, cutoff: datetime) -> None:
        """Make Redis match Postgres: bus.OPEN holds exactly the open rows, and queued rows created before
        cutoff that are missing from the queue are pushed again (Aegra lease_reaper.py _missing_from_queue).
        bus.SYNCED then marks Redis complete. A refusal or a failed read leaves unsynced set."""
        # Cleared first, so a refusal during this pass, or a failed enqueue meanwhile, sets it again.
        self.unsynced = False
        try:
            # Listed before Postgres is read: an id admitted in between is in the rows, never dropped.
            listed = await bus.client.smembers(bus.OPEN)
            async with AsyncSessionLocal() as db:
                open_rows = select(Run.id, Run.status, Run.created_at).where(Run.status.in_(OPEN_STATUSES))
                rows = (await db.execute(open_rows)).all()
            open_ids = {row.id for row in rows}
            if closed := listed - open_ids:
                await bus.client.srem(bus.OPEN, *closed)
            if open_ids:
                await bus.client.sadd(bus.OPEN, *open_ids)
            stuck = {row.id for row in rows if row.status == "queued" and row.created_at < cutoff}
            if stuck:
                stuck -= set(await bus.client.lrange(bus.QUEUE, 0, -1))
        except (RedisError, SQLAlchemyError) as exc:
            logger.warning("Open-run sync failed error_type=%s", type(exc).__name__)
            self.unsynced = True
            return
        for run_id in stuck:
            await self.enqueue(run_id)
        if not self.unsynced:
            try:
                await bus.client.set(bus.SYNCED, self.name)
            except RedisError:
                self.unsynced = True

    async def release(self, run_id: str) -> None:
        async with AsyncSessionLocal.begin() as db:
            # A row still running here lost its terminal write. It keeps its lease and its place in
            # bus.OPEN, so the lease lapses and the reaper ends it; a null lease no pass looks at.
            released = await db.scalar(
                update(Run)
                .where(Run.id == run_id, Run.claimed_by == self.name, Run.status != "running")
                .values(claimed_by=None, lease_expires_at=None)
                .returning(Run.id)
            )
        if released is not None:
            with suppress(RedisError):  # Missed here, sync drops ids whose row is no longer open.
                await bus.client.srem(bus.OPEN, run_id)

    async def run(self, run_id: str) -> None:
        live = await self.claim(run_id)
        if live is None:
            return
        if live.cancelling:
            await self.finish_unstarted(live)
            return
        # A cancel committed before the claim is in cancelling above. One committed after it publishes a
        # command that from here finds the run in active with its task; only one landing during the claim's
        # commit round trip can still miss, and the heartbeat's cancel_requested read covers that.
        self.service.active[live.id] = live
        live.task = asyncio.create_task(self.service.execute(live), name=f"run:{live.id}")
        heartbeat = asyncio.create_task(self.heartbeat(live), name=f"lease:{live.id}")
        try:
            try:
                # Idempotent: a run claimed through the Postgres poll may never have reached bus.OPEN.
                await bus.client.sadd(bus.OPEN, live.id)
            except RedisError:
                self.unsynced = True
            await asyncio.gather(live.task, return_exceptions=True)
            if live.id in self.service.active:
                # Cancelled before execute's first instruction, so its finally never ran.
                await self.finish_unstarted(live)
                self.service.active.pop(live.id, None)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await self.release(live.id)

    async def finish_unstarted(self, live: "LiveRun") -> None:
        """End a claimed run cancelled before it did any work, then give up its lease."""
        await self.service.finish(live, "cancelled", "Stopped before generation started.")
        await self.release(live.id)

    async def heartbeat(self, live: "LiveRun") -> None:
        while True:
            await asyncio.sleep(_HEARTBEAT_SECONDS)
            try:
                async with AsyncSessionLocal.begin() as db:
                    # status: this process's own reaper may have ended the run under the same name.
                    cancel_requested = await db.scalar(
                        update(Run)
                        .where(Run.id == live.id, Run.claimed_by == self.name, Run.status == "running")
                        .values(lease_expires_at=_lease_end())
                        .returning(Run.cancel_requested)
                    )
            except SQLAlchemyError as exc:
                logger.warning("Lease renewal failed run_id=%s error_type=%s", live.id, type(exc).__name__)
                continue
            if cancel_requested is None:
                # Aegra _heartbeat_loop: the lease is gone, so stop before two owners write. A run
                # already stopping has usually just saved its terminal state, which also ends the match.
                if not live.cancelling:
                    logger.warning("Lease lost, stopping run_id=%s", live.id)
                    self.service.interrupt(live)
                return
            if cancel_requested:
                self.service.interrupt(live)

    async def listen_commands(self) -> None:
        # Aegra redis_broker.py _listen_for_cancel_commands: while Redis is down, retry with a doubling
        # delay capped at 30 s, not every second. A lost command still lands through the heartbeat.
        delay = 1
        while True:
            try:
                async with bus.subscribe(bus.COMMANDS) as pubsub:
                    delay = 1
                    while True:
                        # Aegra redis_broker.py _subscribe_and_handle_cancels: a bounded read returns
                        # None when idle. timeout=None would read under socket_timeout and raise.
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                        if message is None:
                            continue
                        command = json.loads(message["data"])
                        live = self.service.active.get(command["run_id"])
                        if live is None:
                            continue
                        if command["type"] == "cancel":
                            self.service.interrupt(live)
                        elif command["type"] == "steer":
                            # ponytail: a steer lost with Redis is still in the chat, not in this
                            # run's inbox. Add a durable inbox read if Redis loss is ever seen.
                            live.inbox.append(command["text"])
            except RedisError as exc:
                logger.warning("Run command listener lost Redis error_type=%s retry_in=%ss", type(exc).__name__, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    async def reap_loop(self) -> None:
        while True:
            await asyncio.sleep(_REAPER_SECONDS)
            try:
                if not self.unsynced and not await bus.client.exists(bus.SYNCED):
                    # Redis restarted or was flushed while this process kept running: QUEUE and
                    # OPEN went with it, and nothing else in this process need have seen an error.
                    self.unsynced = True
                if not self.unsynced and not await bus.client.scard(bus.OPEN):
                    continue  # Nothing open: leave Postgres alone so an idle Neon can suspend.
                await self.reap()
                # Aegra lease_reaper.py _find_recoverable: stuck queued runs straight from Postgres.
                await self.sync(datetime.now(UTC) - timedelta(seconds=_STUCK_QUEUED_SECONDS))
            except (RedisError, SQLAlchemyError) as exc:
                logger.warning("Lease reaper pass failed error_type=%s", type(exc).__name__)

    async def reap(self) -> None:
        async with AsyncSessionLocal.begin() as db:
            # Taking the lease first makes one process the finisher; a slow original owner then
            # finds its lease gone at its next heartbeat and stops.
            expired = (
                await db.scalars(
                    update(Run)
                    .where(Run.status == "running", Run.lease_expires_at < datetime.now(UTC))
                    .values(claimed_by=self.name, lease_expires_at=_lease_end())
                    .returning(Run)
                )
            ).all()
            chat_rows = await db.scalars(select(Chat).where(Chat.id.in_([run.chat_id for run in expired])))
            chats = {chat.id: chat for chat in chat_rows}
        for run in expired:
            logger.warning("Lease expired, ending run_id=%s", run.id)
            await self.service.finish(
                self.service.load_live(run, chats[run.chat_id]),
                "interrupted",
                "The worker running this request stopped. Your work so far is saved. Send another message to continue.",
            )
            await self.release(run.id)
