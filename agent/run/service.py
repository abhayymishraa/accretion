"""Run admission, leased execution, durable outcomes and reconnectable activity."""

import asyncio
import json
import logging
import time
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from e2b import AsyncSandbox, SandboxException
from e2b.exceptions import ServiceBusyException
from fastapi import HTTPException
from sqlalchemy import JSON, DateTime, Insert, String, Update, cast, exists, func, insert, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from agent.sandbox.config import sandbox_settings
from agent.storage.config import storage_settings
from db.base import AsyncSessionLocal, AutocommitSessionLocal, bound
from db.models import Chat, Message, Run, RunEvent, RunScreenshot, SandboxRuntime, Skill, User, library_rows
from plans import month_window

from ..budget.budget import BudgetLimitError, BudgetSpentError, has_budget_left, month_spend, remaining_in, require_left
from ..budget.model_budget import spend_scope
from ..context.context import ContextError, ProjectContext
from ..context.transcript import stored_chars
from ..events import MAX_RUN_EVENTS, redact
from ..routing import jev
from ..routing import providers as routing_providers
from ..routing import router as routing_router
from ..sandbox import migrations, project
from ..sandbox.commands import CommandStateError
from ..sandbox.kits import KITS
from ..sandbox.preview import PROXY_PORT, PreviewError, control_preview
from ..sandbox.sandbox_runtime import RUNTIME_TIMEOUT, SandboxRuntimes
from ..storage.persistence import (
    archive_slots,
    latest_revision,
    latest_revision_in,
    put_object,
    revision_bytes,
    sandbox_archive,
    save_revision,
)
from ..storage.storage import StorageError
from ..tools.public_tools import EDIT_TOOLS, edit_summary
from ..tools.skills import RuntimeSkills
from ..tools.tools import ROOT, FileWriteError
from . import bus
from .config import run_settings
from .decisions import decision_source, prepare_continuation, resolve_decision
from .diagnostics import sandbox_diagnostics
from .runner import RunLimitError, SandboxSetupError, VerificationError, run_editor
from .title import name_project
from .worker import OPEN_STATUSES, Workers
from .workflow import public_workflow, select_workflow

logger = logging.getLogger("webbuilder.runs")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False


def gated(model, ok, **values):
    """An INSERT of one row (every value given, as anonymous binds) made only when the `ok` CTE has a row."""
    return insert(model).from_select(
        list(values), select(*bound(model, **values).values()).where(exists(select(ok.c.id)))
    )


def usable_kit(kit):
    if kit not in KITS:
        raise SandboxSetupError(f"Project kit {kit!r} is not available. No editing model request was made.")
    return kit


async def chat_kit(chat_id):
    """The kit a project started from (Chat.kit)."""
    async with AutocommitSessionLocal() as db:
        return usable_kit(await db.scalar(select(Chat.kit).where(Chat.id == chat_id)))


async def build_setup(chat_id):
    """In one query: the project's kit, and its skills (the owner's library less those turned off for the
    project or for the whole account; RuntimeSkills keeps the required ones)."""
    library = library_rows(Chat.user_id, Skill.name, Skill.description, Skill.instructions)
    account = select(User.disabled_skills).where(User.id == Chat.user_id).scalar_subquery()
    async with AutocommitSessionLocal() as db:
        kit, disabled, rows, account_off = (
            await db.execute(select(Chat.kit, Chat.disabled_skills, library, account).where(Chat.id == chat_id))
        ).one()
    return usable_kit(kit), RuntimeSkills.for_project([*disabled, *account_off], rows)


async def open_run(db: AsyncSession, chat_id: str) -> str | None:
    """A queued or running run of this chat. Any worker may claim it and open the sandbox at any moment."""
    return await db.scalar(select(Run.id).where(Run.chat_id == chat_id, Run.status.in_(OPEN_STATUSES)).limit(1))


DELETE_DATA, KEEP_DATA = "Delete the data", "Keep my data"
# Spec 4 step 3: Jev's limit is 32k tokens; about 20k tokens of input, at ~3 characters each.
_JEV_INPUT_CHARS = 60_000


def approved_data_loss(live) -> list[str]:
    """The migration files the user agreed to lose data for: only when this request answers the
    data-loss question, and only the files that question named."""
    context = live.workflow.get("context") or {}
    exchanges = context.get("exchanges") or []
    if not exchanges or exchanges[-1].get("reply") != DELETE_DATA:
        return []
    return list(context.get("data_loss_files") or [])


def original_request(live) -> str:
    context = live.workflow.get("context") or {}
    return str(context.get("original_request") or live.prompt)


async def pick_kit(live) -> None:
    """Spec 4 step 3: Jev picks a new app's kit from plain kit names; the user is never asked.
    Code falls back to DEFAULT_KIT. Jev receives the user's own words, so a named stack counts."""
    request = original_request(live)[: _JEV_INPUT_CHARS // 2]
    exchanges = (live.workflow.get("context") or {}).get("exchanges", [])
    clarifications = [exchange.get("reply", "") for exchange in exchanges]
    while clarifications and len(str([request, clarifications])) > _JEV_INPUT_CHARS:
        clarifications.pop(0)
    answers = await jev.ask(
        {"request": request, "clarifications": clarifications},
        {
            "kit": {
                "type": "choice",
                "instructions": "Which starter app is the best base for building this app?",
                "criteria": {kit.id: kit.name for kit in KITS.values()},
            }
        },
    )
    answer = (answers or {}).get("kit")
    choice = answer.get("choice") if isinstance(answer, dict) else None
    kit = choice if choice in KITS else sandbox_settings.DEFAULT_KIT
    live.metrics["kit_pick"] = {"jev": answers, "kit": kit, "fallback": None if choice in KITS else "default_kit"}
    async with AsyncSessionLocal.begin() as db:
        await db.execute(update(Chat).where(Chat.id == live.chat_id).values(kit=kit))


async def last_outcome(chat_id, *, exclude):
    """The model and verification result of the chat's previous finished run."""
    async with AutocommitSessionLocal() as db:
        run = await db.scalar(
            select(Run)
            .where(Run.chat_id == chat_id, Run.id != exclude, Run.status != "running")
            .order_by(Run.created_at.desc(), Run.id.desc())
            .limit(1)
        )
    if run is None:
        return {}
    metrics = run.metrics or {}
    return {
        "model": metrics.get("model"),
        "failed": run.status == "failed" and metrics.get("error_type") == "VerificationError",
    }


@dataclass
class LiveRun:
    id: str
    chat_id: str
    prompt: str
    events: list[Any] = field(default_factory=list[Any])
    metrics: dict[str, Any] = field(default_factory=dict[str, Any])
    task: asyncio.Task[Any] | None = None
    sandbox: AsyncSandbox | None = None
    cancelling: bool = False
    revision_id: str | None = None
    user_id: int | None = None
    message_id: str | None = None
    workflow: dict[str, Any] = field(default_factory=dict[str, Any])
    sandbox_started: bool = False
    model_choice: str = "auto"
    # Spec 5 steering: messages the user sends while this run works, drained before each model call.
    inbox: list[str] = field(default_factory=list)
    # Read-only tools run in parallel (spec 5), so their events arrive together: each takes its
    # sequence number under this lock, or two get the same number.
    emit_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # Events emitted but not yet stored, and whether metrics changed since last stored: the writer
    # task (write_events) stores them in the background, so the agent never waits on the database.
    unwritten: list[dict[str, Any]] = field(default_factory=list)
    metrics_dirty: bool = False
    writer: asyncio.Task[None] | None = None
    # The first run of a new project names it alongside the reply; finish waits for it.
    unnamed: bool = False
    naming: asyncio.Task[None] | None = None
    # When this run last reset its sandbox's provider timer (see checkpoint).
    sandbox_touched: float = 0.0


class Service:
    def __init__(self):
        self.active: dict[str, LiveRun] = {}
        self.runtimes = SandboxRuntimes()
        self.sandboxes = self.runtimes.handles
        self.admission = asyncio.Lock()
        self.stopping = False
        self.maintenance_task = None
        self.opening: set[str] = set()
        # The project each user opened last: one active sandbox per user (park_others).
        self.focus: dict[int, str] = {}
        self.workers = Workers(self)

    async def require_sandbox_capacity(self, chat_id, reserved, state, *, requesting_run=None):
        """reserved and state as SandboxRuntimes.reserved(chat_id) reads them, or a caller's own query.
        Paused rows retain ownership without occupying a running slot."""
        reserved = set(reserved) | (
            set(self.sandboxes)
            | self.opening
            | {r.chat_id for r in self.active.values() if r.sandbox_started and r.id != requesting_run}
        )
        if state in ("creating", "retiring") or (
            chat_id not in reserved and len(reserved) >= run_settings.MAX_LIVE_SANDBOXES
        ):
            raise HTTPException(
                429,
                "Live preview capacity reached or cleanup is pending. Try again after a preview closes.",
            )

    async def retire_sandbox(self, chat_id):
        async with self.admission:
            try:
                return await self.runtimes.retire(chat_id)
            except Exception as exc:
                logger.warning("Sandbox cleanup deferred chat_id=%s error_type=%s", chat_id, type(exc).__name__)
                return False

    async def busy_chats(self) -> set[str]:
        """Chats maintain() must leave alone: a preview opening here, or an open run. A run's sandbox stays
        non-reusable until the run ends, and maintain() retires non-reusable rows, so the runs come from
        Postgres: a run another process's worker owns is not in this process's memory."""
        async with AutocommitSessionLocal() as db:
            open_chats = set((await db.scalars(select(Run.chat_id).where(Run.status.in_(OPEN_STATUSES)))).all())
        return open_chats | self.opening

    async def reap_idle_sandboxes(self):
        async with self.admission:
            await self.runtimes.maintain(await self.busy_chats())

    async def preview_status(self, chat_id, user_id) -> dict[str, Any]:
        async with self.admission:
            # The project, checked as the user's, and its runtime in one query, read after acquiring
            # admission so an open that just finished is seen.
            async with AutocommitSessionLocal() as db:
                current = (
                    await db.execute(
                        select(Chat, SandboxRuntime)
                        .outerjoin(SandboxRuntime, SandboxRuntime.chat_id == Chat.id)
                        .where(Chat.id == chat_id, Chat.user_id == user_id)
                    )
                ).one_or_none()
            if current is None:
                raise HTTPException(404, "Project not found")
            chat, row = current
            status: dict[str, Any] = {"url": None, "state": "sleeping", "revision_id": chat.latest_saved_revision_id}
            if any(r.chat_id == chat_id for r in self.active.values()):
                status = {"url": None, "state": "building"}
            elif chat_id in self.opening:
                status = {"url": None, "state": "opening"}
            elif row and row.reusable and row.state != "retiring" and row.revision_id == chat.latest_saved_revision_id:
                try:
                    if await self.runtimes.state(row) == "running" and chat.app_url:
                        # Observing status must not keep an idle preview alive.
                        status = {"url": chat.app_url, "state": "active", "revision_id": row.revision_id}
                except Exception:
                    raise HTTPException(503, "Preview status temporarily unavailable") from None
        # Viewing a project is what makes it the user's active one, even when its sandbox is already up
        # and nothing is acquired. Outside admission: parking calls the provider.
        await self.park_others(chat_id, user_id)
        return status

    async def startup(self):
        if self.maintenance_task and not self.maintenance_task.done():
            self.maintenance_task.cancel()
            await asyncio.gather(self.maintenance_task, return_exceptions=True)
        self.stopping = False
        # No automatic replay of mutations after a process restart.
        async with AsyncSessionLocal.begin() as db:
            # Only running rows no lease covers. A lapsed lease is ended by the reaper below, with a
            # terminal event; a live lease belongs to another process.
            await db.execute(
                update(Run)
                .where(Run.status == "running", Run.lease_expires_at.is_(None))
                .values(
                    status="interrupted",
                    reason="Server restarted before this run finished. Submit a new request to continue.",
                    finished_at=datetime.now(UTC),
                )
            )
            await db.execute(update(Chat).values(app_url=None))
        # End runs whose lease lapsed while no process held them, with a terminal event each.
        await self.workers.reap()
        # Reconcile before admission. Unknown states stay reserved; clean runtimes sleep. Runs still open
        # here hold a live lease, so another process owns them and their sandboxes.
        await self.runtimes.maintain(await self.busy_chats(), shutdown=True)
        from ..storage.maintenance import maintain_loop

        self.maintenance_task = asyncio.create_task(maintain_loop(self), name="persistence-maintenance")
        await self.workers.start()

    async def shutdown(self):
        self.stopping = True
        await self.workers.stop()
        if self.maintenance_task:
            self.maintenance_task.cancel()
            await asyncio.gather(self.maintenance_task, return_exceptions=True)
        tasks = [r.task for r in self.active.values() if r.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        async with self.admission:
            # This process's runs were cancelled above and are no longer open; other processes' runs are.
            await self.runtimes.maintain(await self.busy_chats(), shutdown=True)

    async def admit(
        self, user_id: int, prompt: str, chat_id: str | None = None, *, mode="auto", response=None, model_choice="auto"
    ) -> dict[str, Any]:
        prompt = prompt.strip()
        if (not prompt and response is None) or len(prompt) > 12000:
            raise HTTPException(422, "Describe a change in 1–12000 characters")
        async with self.admission, AsyncExitStack() as stack:
            # Answering a decision is one transaction from here to the new run: its parent stays
            # locked throughout. Retries resolve before capacity/budget checks: no duplicate run or charge.
            if response is not None:
                decision = await stack.enter_async_context(AsyncSessionLocal.begin())
                parent, fingerprint = await decision_source(decision, user_id, *response)
                if parent.workflow.get("response_hash"):
                    child = (
                        await decision.get(Run, parent.workflow["continuation_id"])
                        if parent.workflow.get("continuation_id")
                        else None
                    )
                    return {
                        "chat_id": parent.chat_id,
                        "run_id": child.id if child else None,
                        "status": child.status if child else parent.status,
                    }
                if response[1] == "dismiss":
                    resolve_decision(parent, fingerprint, "dismiss")
                    # Commit before telling other tabs to fetch the resolved state.
                    await decision.commit()
                    await self.notify(parent.chat_id, {"e": "resync"})
                    return {"chat_id": parent.chat_id, "run_id": None, "status": "cancelled"}
                chat_id = parent.chat_id
            workflow: dict[str, Any] = {"mode": mode}
            metrics: dict[str, Any] = {}
            now = datetime.now(UTC)
            month = month_window(now)
            if self.stopping:
                raise HTTPException(429, "The builder is busy. Try again shortly.")
            if not storage_settings.configured:
                raise HTTPException(503, "Project storage is not configured.")
            if chat_id and chat_id in self.opening:
                raise HTTPException(409, "This project already has a running request.")
            new_project = not chat_id
            # Every input an admission check reads, as one row: the write is gated on it and returns it,
            # so a refused prompt names its reason with no second read.
            in_chat = select(Run.id).where(Run.chat_id == chat_id)
            facts = (
                select(
                    User,
                    select(func.count())
                    .select_from(Run)
                    .where(Run.status.in_(OPEN_STATUSES))
                    .scalar_subquery()
                    .label("running_total"),
                    month_spend(user_id, *month).scalar_subquery().label("used"),
                    select(Chat.id).where(Chat.id == chat_id, Chat.user_id == user_id).scalar_subquery().label("owned"),
                    in_chat.where(Run.status.in_(OPEN_STATUSES)).limit(1).scalar_subquery().label("running"),
                    in_chat.where(Run.status == "awaiting_input").limit(1).scalar_subquery().label("pending"),
                )
                .where(User.id == user_id)
                .cte("facts")
            )
            read = select(
                aliased(User, facts),
                facts.c.running_total,
                facts.c.used,
                facts.c.owned,
                facts.c.running,
                facts.c.pending,
            )

            def refuse(row):
                """Raise the first admission check that fails in a facts row; return its pending question."""
                if row is None:
                    # A missing account cannot hold a valid token.
                    raise HTTPException(401, "User not found")
                user, running_total, used, owned, running, pending = row[:6]
                if not new_project and not owned:
                    raise HTTPException(404, "Project not found")
                if not user.email_verified:
                    raise HTTPException(403, "Verify your email before continuing.")
                if (running_total or 0) + len(self.opening) >= run_settings.MAX_CONCURRENT_RUNS:
                    raise HTTPException(429, "The builder is busy. Try again shortly.")
                try:
                    require_left(user, used, month)
                except BudgetLimitError as exc:
                    raise HTTPException(429, str(exc)) from None
                if not new_project and running:
                    raise HTTPException(409, "This project already has a running request.")
                return pending

            check_db = await stack.enter_async_context(AutocommitSessionLocal())
            chat_id = chat_id or str(uuid.uuid4())
            message_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
            try:
                if response is None:
                    # One statement, committed by itself, gated on every admission check (the `ok` row):
                    # the remembered model choice (dyad's selectedModel, spec 4.2), the project when
                    # new, the user's message and the queued run, all or none. Postgres also refuses a
                    # second open build (uq_runs_one_open_per_chat) and a project deleted meanwhile.
                    checks = [
                        facts.c.email_verified,
                        facts.c.running_total + len(self.opening) < run_settings.MAX_CONCURRENT_RUNS,
                        has_budget_left(facts.c.plan, facts.c.used),
                    ]
                    if not new_project:
                        checks += [facts.c.owned.is_not(None), facts.c.running.is_(None), facts.c.pending.is_(None)]
                    ok = select(facts.c.id).where(*checks).cte("ok")
                    ctes = [
                        ok,
                        update(User)
                        .where(User.id.in_(select(ok.c.id)))
                        .values(bound(User, default_model_choice=model_choice))
                        .cte("choice"),
                    ]
                    if new_project:
                        # Untitled until title.py names it from this request.
                        ctes.append(
                            gated(
                                Chat, ok, id=chat_id, user_id=user_id, kit=sandbox_settings.DEFAULT_KIT, created_at=now
                            ).cte("project")
                        )
                    ctes.append(
                        gated(
                            Message, ok, id=message_id, chat_id=chat_id, role="user", content=prompt, created_at=now
                        ).cte("message")
                    )
                    queued = gated(
                        Run,
                        ok,
                        id=run_id,
                        chat_id=chat_id,
                        prompt=prompt,
                        status="queued",
                        model_choice=model_choice,
                        workflow=workflow,
                        metrics=metrics,
                        message_id=message_id,
                        cancel_requested=False,
                        created_at=now,
                    )
                    queued = queued.returning(Run.id).cte("queued")
                    row = (
                        await check_db.execute(read.add_columns(select(queued.c.id).scalar_subquery()).add_cte(*ctes))
                    ).first()
                    if row is None or row[-1] is None:
                        # Refused: the same row says why. ok and refuse read one snapshot, so a refused
                        # write has a failing check, the pending question at the latest.
                        pending = refuse(row)
                        assert pending, "a refused admission fails a check"
                        raise HTTPException(409, "Answer or dismiss the pending question or plan first.")
                else:
                    pending = refuse((await check_db.execute(read)).first())
                    # The decision's transaction, opened above with its parent locked, resolves the
                    # parent with the new run.
                    if pending and pending != parent.id:
                        raise HTTPException(409, "Answer or dismiss the pending question or plan first.")
                    workflow, metrics = await prepare_continuation(decision, parent, response[1], response[2])
                    decision.add(
                        Run(
                            id=run_id,
                            chat_id=chat_id,
                            prompt=prompt,
                            status="queued",
                            # The model is sticky across a decision: the child reuses the parent's.
                            model_choice=parent.model_choice,
                            workflow=workflow,
                            metrics=metrics,
                            message_id=message_id,
                        )
                    )
                    resolve_decision(parent, fingerprint, response[1], run_id)
                    decision.add(Message(id=message_id, chat_id=chat_id, role="user", content=prompt))
                    # Inside the try, so a refused INSERT maps below rather than at commit.
                    await decision.flush()
            except IntegrityError as exc:
                state = getattr(exc.orig, "sqlstate", None)
                if state == "23505":  # uq_runs_one_open_per_chat: another request admitted one first
                    raise HTTPException(409, "This project already has a running request.") from None
                if state == "23503":  # the project was deleted after the read
                    raise HTTPException(404, "Project not found") from None
                raise
        # Outside admission: both need only the committed row, and a slow Redis must not hold the
        # lock that previews and deletes wait on. Other tabs learn of the run; the starter opens its stream.
        await asyncio.gather(self.workers.enqueue(run_id), self.notify(chat_id, {"e": "run_created", "run_id": run_id}))
        return {
            "chat_id": chat_id,
            "run_id": run_id,
            "status": "queued",
        }

    def load_live(self, run: Run, chat: Chat) -> LiveRun:
        """The in-memory run a worker drives, rebuilt from its row."""
        return LiveRun(
            run.id,
            run.chat_id,
            run.prompt,
            metrics=dict(run.metrics),
            user_id=chat.user_id,
            message_id=run.message_id,
            workflow=dict(run.workflow),
            model_choice=run.model_choice,
            # Untitled means title.py has not named it yet; a failed naming retries next run.
            unnamed=chat.title is None,
        )

    def interrupt(self, live: LiveRun) -> None:
        if live.task and not live.cancelling:
            live.cancelling = True
            live.task.cancel()

    async def notify(self, chat_id: str, event: dict[str, Any]) -> None:
        """A project notice (new run, title, resync); live, never replayed."""
        await bus.publish(bus.project_channel(chat_id), event)

    def event(self, live, kind, **payload):
        details, diffs = payload.get("details"), None
        if isinstance(details, dict) and "diffs" in details:
            diffs = details["diffs"]
            payload["details"] = {key: value for key, value in details.items() if key != "diffs"}
        event = redact(
            {
                "e": kind,
                "run_id": live.id,
                "event_id": f"{live.id}:{len(live.events) + 1}",
                "sequence": len(live.events) + 1,
                "created_at": datetime.now(UTC).isoformat(),
                **payload,
            }
        )
        if diffs is not None:
            # The user's own code, shown whole like Codex: secrets redacted, nothing cut.
            event["details"]["diffs"] = redact(diffs, max_length=None, max_items=None)
        return event

    async def emit(self, live, kind, **payload):
        async with live.emit_lock:
            if len(live.events) >= MAX_RUN_EVENTS:
                raise RunLimitError("Activity budget reached")
            self.queue_write(live)
            event = self.event(live, kind, **payload)
            live.events.append(event)
            live.unwritten.append(event)
        record = {k: event[k] for k in ("e", "run_id", "sequence")}
        if kind == "stage":
            live.metrics["stage"] = payload.get("message")
            record["stage"] = payload.get("message")
        elif kind in ("verification", "tool_completed"):
            record["ok"] = payload.get("ok")
        logger.info(json.dumps(record))

    async def checkpoint(self, live, dirty=False):
        # A run has no clock, so a long one renews its sandbox's lease (metered, sandbox_runtime.py)
        # before E2B parks it at RUNTIME_TIMEOUT. Once a turn, at most every third of that.
        if live.sandbox and time.monotonic() - live.sandbox_touched > RUNTIME_TIMEOUT / 3:
            try:
                await self.runtimes.renew(live.chat_id, live.user_id)
                live.sandbox_touched = time.monotonic()
            except SandboxException:
                # The provider call failed; the lease is still running, so the next turn retries.
                logger.warning("Could not renew the sandbox lease run_id=%s", live.id)
        if dirty:
            await self.save_files(live)
        # Stored by the event writer with whatever it writes next: the turn does not wait for it.
        live.metrics_dirty = True
        self.queue_write(live)

    def queue_write(self, live):
        """Start the run's event writer unless it is running. A writer that failed stops the run here,
        at the next emit or checkpoint, as a failed inline write did."""
        writer = live.writer
        if writer is not None and writer.done():
            if not writer.cancelled() and (error := writer.exception()) is not None:
                raise error
            writer = None
        if writer is None:
            live.writer = asyncio.create_task(self.write_events(live), name=f"events:{live.id}")

    async def write_events(self, live):
        """Store the run's queued events, oldest first, then publish them: each round is one statement
        carrying every event queued so far, their file-edit summaries (runs.edits) and the latest
        metrics. An event is published only after it is stored, so a stream backfilling from Postgres
        on a gap always finds it. The agent never waits for this."""
        while live.unwritten or live.metrics_dirty:
            batch, live.unwritten = live.unwritten, []
            changes: dict[str, Any] = {}
            if live.metrics_dirty:
                live.metrics_dirty = False
                changes["metrics"] = literal(redact(live.metrics), JSON)
            summaries = [edit_summary(e) for e in batch if e["e"] == "tool_completed" and e.get("name") in EDIT_TOOLS]
            if summaries:
                changes["edits"] = func.coalesce(Run.edits, cast([], JSONB)).op("||")(cast(summaries, JSONB))
            now = datetime.now(UTC)
            stored = (
                insert(RunEvent).values(
                    [bound(RunEvent, run_id=live.id, sequence=e["sequence"], payload=e, created_at=now) for e in batch]
                )
                if batch
                else None
            )
            statement: Insert | Update
            if changes:
                statement = update(Run).where(Run.id == live.id).values(changes)
                if stored is not None:
                    statement = statement.add_cte(stored.cte("stored"))
            else:
                assert stored is not None, "a round has events or changes"
                statement = stored
            async with AutocommitSessionLocal() as db:
                await db.execute(statement)
            for event in batch:
                await bus.publish(bus.run_channel(live.id), event)

    async def flush_events(self, live):
        """Wait until everything emitted so far is stored and published; raise if storing failed. Any
        other writer of this run's events (a checkpoint, the terminal event) calls this first, so no
        event is stored or published ahead of an earlier one."""
        while live.writer is not None and not live.writer.done():
            await asyncio.shield(live.writer)
        if live.writer is not None and not live.writer.cancelled() and (error := live.writer.exception()) is not None:
            raise error

    async def park_others(self, chat_id, user_id):
        """One active sandbox per user, as open-lovable keeps one (firecrawl/open-lovable@69bd93b), but
        per user and paused, not killed: switching to this project parks the user's other idle sandboxes.
        One with a build or an open in progress keeps running; a build parks its own when it ends."""
        if self.focus.get(user_id) == chat_id:
            # Already this user's focus: every sandbox that started since (an open or a build of
            # another project) moved the focus away, so there is nothing new to park.
            return
        self.focus[user_id] = chat_id
        for row in await self.runtimes.running_for(user_id, chat_id):
            await self.park_left(row.chat_id)

    async def get_e2b_sandbox(self, id: str, loaded=None):
        """loaded: the project, its latest saved revision and its runtime row when the caller has just
        read them."""
        if loaded:
            chat, revision, runtime = loaded
        else:
            # The project, its owner, kit, latest saved revision and runtime row in one query;
            # latest_revision_in then finds the revision in the session.
            async with AutocommitSessionLocal() as db:
                found = (
                    await db.execute(
                        select(Chat, SandboxRuntime)
                        .outerjoin(SandboxRuntime, SandboxRuntime.chat_id == Chat.id)
                        .options(joinedload(Chat.latest_saved_revision))
                        .where(Chat.id == id)
                    )
                ).first()
                chat, runtime = found if found else (None, None)
                revision = await latest_revision_in(db, id)
        kit_id = usable_kit(chat.kit if chat else None)
        assert chat is not None, "usable_kit refuses a project that no longer exists"
        await self.park_others(id, chat.user_id)
        try:
            template = revision.template_id if revision else await project.template_ref()
        except project.KitTemplateMissing as exc:
            raise SandboxSetupError(f"{exc}. No editing model request was made.") from None
        sandbox, restore = await self.runtimes.acquire(id, chat.user_id, revision, template, runtime)
        if not restore:
            return sandbox
        try:
            await sandbox.commands.run(
                "python3 -c \"import hashlib, zipfile; assert hasattr(hashlib, 'file_digest')\"",
                timeout=10,
            )
        except Exception:
            raise SandboxSetupError(
                "Sandbox archive tools are unavailable. Rebuild the template (sandbox/templates.py)."
                " No editing model request was made."
            ) from None
        # Spec 8: restore code, dependencies and the database dump, or start from the kit
        # when the project has no saved revision yet.
        if revision:
            # Stop services before replacing their source tree or dependencies.
            await control_preview(sandbox, "stop")
            async with archive_slots:
                await sandbox_archive(sandbox, "restore", await revision_bytes(revision))
            await project.restore(sandbox, id, kit_id)
        else:
            await project.start_new(sandbox, id, kit_id)
        return sandbox

    async def preview_ready(self, sandbox, port):
        await sandbox.commands.run(
            "curl --fail --silent --retry 5 --retry-connrefused "
            f"--retry-delay 2 --max-time 5 http://localhost:{port}/ >/dev/null",
            cwd=ROOT,
            timeout=45,
        )

    async def save_screenshot(self, live, data: bytes, media_type: str) -> str | None:
        """Store an image a browser check saved; its id goes on the tool event the chat draws it from.

        None when storage refuses it: the check still counts, the chat just shows no image.
        """
        screenshot_id = uuid.uuid4().hex
        key = f"screenshots/{live.chat_id}/{live.id}/{screenshot_id}"
        try:
            await put_object(key, data, media_type, chat_id=live.chat_id)
        except StorageError:
            logger.warning("Screenshot not stored run_id=%s", live.id)
            return None
        async with AsyncSessionLocal.begin() as db:
            db.add(RunScreenshot(id=screenshot_id, run_id=live.id, object_key=key, media_type=media_type))
        return screenshot_id

    async def save_files(self, live):
        if not live.sandbox:
            return
        if len(live.events) >= MAX_RUN_EVENTS:
            raise RunLimitError("Activity budget reached before checkpoint")
        kit_id = await chat_kit(live.chat_id)
        runtime = await self.runtimes.get(live.chat_id)
        template = runtime.template_id if runtime else await project.template_ref()
        # Spec 3: the database travels with the revision.
        await project.dump(live.sandbox, kit_id)
        async with archive_slots:
            archive = await sandbox_archive(live.sandbox, "pack")
            # The checkpoint event takes a sequence number too (see LiveRun.emit_lock), and is stored
            # by promote(): every earlier event is stored and published first.
            async with live.emit_lock:
                await self.flush_events(live)
                live.revision_id, event = await save_revision(
                    live.chat_id,
                    live.id,
                    archive,
                    template,
                    lambda revision_id: self.event(
                        live, "checkpoint_saved", revision_id=revision_id, message="Project files saved"
                    ),
                )
                if event:
                    live.events.append(event)
        if event:
            await bus.publish(bus.run_channel(live.id), event)

    async def open_preview(self, chat_id, user_id) -> dict[str, Any]:
        async with self.admission:
            # Everything opening needs to know, in one query: the project (checked as the user's) and
            # its latest saved revision, whether a build is open, and sandbox capacity as
            # SandboxRuntimes.reserved reads it.
            async with AutocommitSessionLocal() as db:
                found = (
                    await db.execute(
                        select(
                            Chat,
                            select(Run.id).where(Run.chat_id == chat_id, Run.status.in_(OPEN_STATUSES)).exists(),
                            select(func.array_agg(SandboxRuntime.chat_id))
                            .where(SandboxRuntime.state != "paused")
                            .scalar_subquery(),
                            SandboxRuntime,
                        )
                        .outerjoin(SandboxRuntime, SandboxRuntime.chat_id == Chat.id)
                        .options(joinedload(Chat.latest_saved_revision))
                        .where(Chat.id == chat_id, Chat.user_id == user_id)
                    )
                ).first()
                if found is None:
                    raise HTTPException(404, "Project not found")
                chat, open_build, reserved, runtime = found
                state = runtime.state if runtime else None
                revision = await latest_revision_in(db, chat_id)
            if (
                self.stopping
                or chat_id in self.opening
                or open_build
                or len(self.active) + len(self.opening) >= run_settings.MAX_CONCURRENT_RUNS
            ):
                raise HTTPException(409, "Wait for the current operation to finish")
            if not revision:
                raise HTTPException(404, "No saved project yet")
            await self.require_sandbox_capacity(chat_id, reserved or [], state)
            self.opening.add(chat_id)
        try:
            async with asyncio.timeout(180):
                sandbox = await self.get_e2b_sandbox(chat_id, (chat, revision, runtime))
                # The navigation proxy's port; it fronts the kit's own web port (sandbox/preview.py).
                port = PROXY_PORT
                try:
                    await self.preview_ready(sandbox, port)
                except CommandStateError:
                    raise
                except Exception:
                    row = await self.runtimes.get(chat_id)
                    if not row or not row.reusable:
                        # A restored project has already received a fresh server.
                        raise
                    # Repair the server in the same sandbox before considering a
                    # future open/restore. Do not allocate a VM for a module cache.
                    await control_preview(sandbox, "restart")
                    await self.preview_ready(sandbox, port)
                url = "https://" + sandbox.get_host(port)
                # One statement: lock the project while its saved revision is still the one opened,
                # then mark the sandbox reusable and publish the URL, or write nothing at all.
                current = (
                    select(Chat.id)
                    .where(Chat.id == chat_id, Chat.latest_saved_revision_id == revision.id)
                    .with_for_update()
                    .cte("current")
                )
                reusable = self.runtimes.reusable(chat_id, revision.id, exists(select(current.c.id))).cte("reusable")
                async with AutocommitSessionLocal() as db:
                    published = await db.scalar(
                        update(Chat)
                        .where(Chat.id.in_(select(reusable.c.chat_id)))
                        .values(app_url=url)
                        .returning(Chat.id)
                        .add_cte(current, reusable),
                        # Plain SQL: the ORM's session sync would drop RETURNING from a statement with CTEs.
                        execution_options={"synchronize_session": False},
                    )
                if published is None:
                    raise StorageError("Saved project changed while opening its preview")
                return {"url": url, "revision_id": revision.id}
        except BaseException:
            await self.retire_sandbox(chat_id)
            raise
        finally:
            self.opening.discard(chat_id)

    async def finish(self, live, status, reason, result=None):
        event = self.event(
            live,
            "run_finished",
            **{
                "event_id": f"{live.id}:terminal",
                "status": status,
                "message": reason,
                "metrics": live.metrics,
                "workflow": public_workflow(live.workflow),
                "url": result["url"] if result and status == "succeeded" else None,
                "revision_id": live.revision_id,
            },
        )
        # The reply is shown whole, live as in history (Run.reason): redacted, not cut at the event bound.
        event["message"] = redact(reason, max_length=None)
        # Every event emitted so far is stored first: the terminal one takes the next sequence after them.
        try:
            await self.flush_events(live)
        except SQLAlchemyError as exc:
            # A lost batch must not also lose the outcome: the terminal sequence comes from durable state.
            logger.warning("Event batch not stored run_id=%s error_type=%s", live.id, type(exc).__name__)
        transcript = reason
        if status == "awaiting_input":
            transcript += "\nProposed, not implemented:\n" + "\n".join(live.workflow.get("steps", []))
            if live.workflow.get("question"):
                transcript += "\n" + live.workflow["question"]
        now = datetime.now(UTC)
        # One statement ends the run, updates its project, records the terminal event and the
        # transcript reply: all of it, or nothing when the run is no longer running (the reaper ended
        # it). The event takes the next sequence from durable state, since a cancelled emit may have
        # committed one the in-memory list lacks; only this run's owner writes its events.
        finished = (
            update(Run)
            .where(Run.id == live.id, Run.status == "running")
            .values(
                bound(
                    Run,
                    status=status,
                    reason=reason,
                    metrics=redact(live.metrics),
                    workflow=live.workflow,
                    finished_at=now,
                )
            )
            .returning(Run.id)
            .cte("finished")
        )
        sequence = (
            select((func.coalesce(func.max(RunEvent.sequence), 0) + 1).label("n"))
            .where(RunEvent.run_id == live.id)
            .cte("sequence")
        )
        reply = (
            insert(Message)
            .from_select(
                ["id", "chat_id", "role", "content", "event_type", "created_at"],
                select(
                    *bound(
                        Message,
                        id=live.id,
                        chat_id=live.chat_id,
                        role="assistant",
                        content=transcript,
                        event_type="run_summary",
                        created_at=now,
                    ).values()
                ).select_from(finished),
            )
            .cte("reply")
        )
        ctes = [finished, sequence, reply]
        changes = {"app_url": event["url"]} if live.sandbox_started else {}
        reusable = status == "succeeded" and live.revision_id
        if reusable:
            changes["latest_verified_revision_id"] = live.revision_id
        if result and "project_skills" in result:
            # Stored when written, so the skills list reads it from the project row, not the sandbox.
            changes["project_skills"] = result["project_skills"]
        if changes:
            ctes.append(
                update(Chat)
                .where(Chat.id == live.chat_id, exists(select(finished.c.id)))
                .values(bound(Chat, **changes))
                .cte("project")
            )
        payload = cast(
            cast(literal(event, JSON), JSONB).op("||")(func.jsonb_build_object("sequence", sequence.c.n)), JSON
        )
        terminal = (
            insert(RunEvent)
            .from_select(
                ["run_id", "sequence", "payload", "created_at"],
                select(
                    literal(live.id, String), sequence.c.n, payload, literal(now, DateTime(timezone=True))
                ).select_from(finished, sequence),
            )
            .returning(RunEvent.sequence)
            .add_cte(*ctes)
        )
        # A succeeded run also marks its sandbox reusable, which refuses (and so rolls this back)
        # when the sandbox changed hands: then one transaction; otherwise the statement alone.
        async with AsyncSessionLocal.begin() if reusable else AutocommitSessionLocal() as db:
            event["sequence"] = await db.scalar(terminal)
            if event["sequence"] is None:
                return
            if reusable:
                await self.runtimes.mark_reusable(db, live.chat_id, live.revision_id)
        live.events.append(event)
        await bus.publish(bus.run_channel(live.id), event)
        logger.info(
            json.dumps(
                {
                    "run_id": live.id,
                    "status": status,
                    **{
                        key: live.metrics.get(key)
                        for key in (
                            "turns",
                            "tool_calls",
                            "total_tokens",
                            "elapsed_ms",
                            "error_type",
                            "stage",
                            "sandbox_cleanup",
                            "token_budget",
                            "model_calls",
                            "cached_input_tokens",
                            "cache_write_tokens",
                            "uncached_input_tokens",
                            "model",
                            "router",
                            "cost_nanos",
                        )
                    },
                }
            )
        )

    async def model_for(self, live):
        """One model for every call in this run (spec 5). A continuation keeps its parent's."""
        sticky = live.metrics.get("model")
        if sticky:
            if sticky not in {entry.id for entry in routing_providers.usable_models()}:
                # Its key was removed, or screenshots were turned on for a text-only model.
                raise RunLimitError(
                    "The model this conversation uses is no longer available. Choose another model or Auto"
                )
            return routing_providers.chat_model(sticky)

        async def budget_and_size():
            # The user, this month's spend and the transcript's size in one query.
            month = month_window(datetime.now(UTC))
            async with AutocommitSessionLocal() as db:
                row = (
                    await db.execute(
                        select(
                            User,
                            month_spend(live.user_id, *month).scalar_subquery(),
                            stored_chars(live.chat_id).scalar_subquery(),
                        ).where(User.id == live.user_id)
                    )
                ).first()
            return row or (None, 0, 0)

        previous, (user, used, transcript_chars) = await asyncio.gather(
            last_outcome(live.chat_id, exclude=live.id), budget_and_size()
        )
        # An account deleted mid-run has nothing left; reserve() then refuses the call.
        remaining = remaining_in(user, used) if user else 0
        pick = await routing_router.pick_model(
            live.prompt,
            model_choice=live.model_choice,
            # About 3 characters per token, plus the system prompt, tools and the new request.
            needed_tokens=transcript_chars // 3 + 20_000,
            remaining_nanos=remaining,
            failed_model=previous.get("model") if previous.get("failed") else None,
        )
        live.metrics["model"], live.metrics["router"] = pick.model_id, pick.log
        return routing_providers.chat_model(pick.model_id)

    async def execute(self, live):
        # The hooks add each reservation and settlement to live.metrics["cost_nanos"],
        # the run's reported spend. Same dict, not a copy.
        scope = {
            "user_id": live.user_id,
            "run_id": live.id,
            "limit_error": None,
            "metrics": live.metrics,
            "settling": set(),
        }
        scope_token = spend_scope.set(scope)
        if live.unnamed:
            # Started inside the spend scope, so the naming call is metered like any other.
            live.naming = asyncio.create_task(self.name_project(live), name=f"name:{live.chat_id}")
        started = time.monotonic()
        previous_elapsed = live.metrics.get("elapsed_ms", 0)
        status, reason, result = "failed", "The run failed. Submit a new request to retry.", None
        diagnose_sandbox = False
        try:
            await self.emit(live, "run_started", message="Starting your request")
            await self.emit(live, "stage", message="Understanding your request")
            model = await self.model_for(live)
            live.workflow = await select_workflow(live, model=model)
            await self.emit(
                live,
                "approach",
                message=live.workflow["summary"],
                workflow=public_workflow(live.workflow),
            )
            if live.workflow["kind"] != "execute":
                status = "answered" if live.workflow["kind"] == "answer" else "awaiting_input"
                reason = live.workflow["summary"]
                return
            if await latest_revision(live.chat_id) is None:
                await self.emit(live, "stage", message="Choosing how to build it")
                await pick_kit(live)
            await self.open_sandbox(live)
            kit, skills = await build_setup(live.chat_id)
            stack = KITS[kit].model_dump()
            result = await run_editor(
                live.sandbox,
                live.prompt,
                lambda kind, **data: self.emit(live, kind, **data),
                lambda dirty=False: self.checkpoint(live, dirty),
                live.metrics,
                model=model,
                user_model=live.model_choice != "auto",
                inbox=live.inbox,
                request_context={
                    "continuation": live.workflow.get("context"),
                    "approach": public_workflow(live.workflow),
                    "plan_approved": live.workflow.get("approved", False),
                },
                memory=ProjectContext(live.chat_id, live.user_id, live.message_id)
                if live.user_id is not None and live.message_id is not None
                else None,
                migrate=lambda: migrations.gate(live.sandbox, stack, allow_data_loss=approved_data_loss(live)),
                save_screenshot=lambda data, media_type: self.save_screenshot(live, data, media_type),
                skills=skills,
            )
            if "decision" in result:
                current = await latest_revision(live.chat_id)
                live.workflow = {
                    **live.workflow,
                    **redact(result["decision"]),
                    "revision_id": current.id if current else None,
                    "approved": False,
                }
                status, reason = "awaiting_input", live.workflow["summary"]
                return
            await self.save_files(live)
            status, reason = (
                "succeeded",
                # The timeline's build-check row reports the build; the reply stays the model's own.
                result["summary"],
            )
        except migrations.DestructiveMigration as exc:
            # Spec 6: a change that deletes saved data waits for the user's answer.
            status, reason = await self.ask(
                live,
                "This change would delete some saved data. Delete that data, or keep it and change the approach?",
                [DELETE_DATA, KEEP_DATA],
                data_loss_files=exc.files,
            )
        except TimeoutError:
            status, reason = (
                "timed_out",
                # Commands return a timeout to the model (sandbox/commands.py); what is left is the
                # workspace itself: creating, connecting or saving the sandbox.
                "The workspace didn't respond in time. Your work so far is saved. Send another message to retry.",
            )
            diagnose_sandbox = True
        except asyncio.CancelledError:
            status = "interrupted" if self.stopping else "cancelled"
            reason = (
                "Server stopped; submit a new request to continue."
                if self.stopping
                else "Stopped at your request. The last acknowledged checkpoint remains available."
            )
        except RunLimitError as exc:
            # A limit is a stopping point, not a failure: the checkpoint holds the work and
            # the next message continues from it. Rendering this as a broken run is what
            # made users think the product itself had failed.
            status = "stopped"
            reason = f"{str(exc).rstrip('.')}. Your work so far is saved. Send another message to continue from here."
            live.metrics["error_type"] = type(exc).__name__
        except BudgetSpentError as exc:
            # Same stopping point as a run limit, but continuing waits for the monthly reset.
            status = "stopped"
            reason = f"{exc} Your work so far is saved."
            live.metrics["error_type"] = type(exc).__name__
        except (VerificationError, ContextError, PreviewError, BudgetLimitError) as exc:
            reason = str(exc)
            live.metrics["error_type"] = type(exc).__name__
            diagnose_sandbox = isinstance(exc, (SandboxSetupError, PreviewError))
        except HTTPException as exc:
            reason = str(exc.detail)
            live.metrics["error_type"] = "AdmissionError"
        except StorageError as exc:
            reason = str(exc) + ". The last acknowledged checkpoint is safe. No automatic AI retry was started."
            live.metrics["error_type"] = "StorageError"
        except (CommandStateError, FileWriteError) as exc:
            reason = str(exc) + ". The last acknowledged checkpoint remains available."
            live.metrics["error_type"] = type(exc).__name__
            diagnose_sandbox = True
        except (SandboxException, ServiceBusyException) as exc:
            reason = (
                "The build sandbox could not complete an operation. Retry the request; if it"
                " keeps failing, check the E2B template and service availability."
            )
            live.metrics["error_type"] = type(exc).__name__
            diagnose_sandbox = True
            logger.error(
                "Sandbox operation failed run_id=%s error_type=%s stage=%s",
                live.id,
                type(exc).__name__,
                live.metrics.get("stage"),
            )
        except Exception as exc:
            # Exception text can include provider requests or secrets. Log safe identity only.
            live.metrics["error_type"] = type(exc).__name__
            logger.error("Run failed run_id=%s error_type=%s", live.id, type(exc).__name__)
        finally:
            if live.naming:
                # Its cost lands in live.metrics, which finish() persists; bounded by title.py's timeout.
                await live.naming
            # Creation registers ownership before restoring files; cancellation can interrupt restoration.
            if live.sandbox_started:
                live.sandbox = live.sandbox or self.sandboxes.get(live.chat_id)
            live.metrics["elapsed_ms"] = previous_elapsed + round((time.monotonic() - started) * 1000)
            if status != "succeeded" and live.sandbox_started:
                # Completed mutation batches are already saved. Never archive a half-finished command.
                if live.sandbox:
                    self.sandboxes[live.chat_id] = live.sandbox
                    if diagnose_sandbox:
                        # At most four seconds before retirement. No periodic polling or model input.
                        try:
                            live.metrics["sandbox_diagnostics"] = await sandbox_diagnostics(live.sandbox.sandbox_id)
                        except asyncio.CancelledError:
                            # Cancellation during optional evidence collection must still retire the sandbox.
                            status = "interrupted" if self.stopping else "cancelled"
                            reason = (
                                "Stopped while collecting diagnostics."
                                " The last acknowledged checkpoint remains available."
                            )
                if await self.retire_sandbox(live.chat_id):
                    live.metrics["sandbox_cleanup"] = "killed"
                else:
                    live.metrics["sandbox_cleanup"] = "pending"
                    reason += " Sandbox cleanup is pending. Reopening is blocked until ownership is resolved."
                    logger.warning("Sandbox cleanup remains reserved run_id=%s", live.id)
            # Settlements run in the background (model_budget.settle_later); the run's spend is
            # final only once they have landed.
            await asyncio.gather(*scope["settling"], return_exceptions=True)
            try:
                await self.finish(live, status, reason, result)
            except Exception:
                if live.sandbox_started:
                    await self.retire_sandbox(live.chat_id)
                logger.error("Could not persist terminal state run_id=%s", live.id)
                await self.notify(live.chat_id, {"e": "resync"})
            self.active.pop(live.id, None)
            spend_scope.reset(scope_token)
            if live.user_id is not None and self.focus.get(live.user_id, live.chat_id) != live.chat_id:
                # The user moved to another project while this built: park its sandbox now.
                await self.park_left(live.chat_id)

    async def name_project(self, live):
        try:
            title = await name_project(live.chat_id, live.prompt, live.metrics)
        except SQLAlchemyError:
            logger.warning("Could not save the project name chat_id=%s", live.chat_id)
            return
        if title:
            # Not a run event: the name belongs to the project, so it is pushed and never replayed.
            await self.notify(live.chat_id, {"e": "project_title", "title": title})

    async def park_left(self, chat_id):
        """Pause a project's sandbox the user has moved away from, unless a build or an open uses it."""
        if chat_id in self.opening:
            return
        async with AutocommitSessionLocal() as db:
            # A queued run is about to acquire this sandbox, and a running one may belong to another
            # process's worker: neither is in self.active, so the row decides.
            if await open_run(db, chat_id):
                return
        row = await self.runtimes.get(chat_id)
        if not row or row.state != "running":
            return
        try:
            await self.runtimes.pause(row)
        except (SandboxException, StorageError, TimeoutError):
            # Never blocks the project being opened; this one still parks at its own timeout.
            logger.warning("Could not park the sandbox left behind chat_id=%s", chat_id)

    async def open_sandbox(self, live):
        async with self.admission:
            await self.require_sandbox_capacity(
                live.chat_id, *await self.runtimes.reserved(live.chat_id), requesting_run=live.id
            )
            live.sandbox_started = True
        live.sandbox = await self.get_e2b_sandbox(live.chat_id)
        # Commit unsafe state before the first possible mutation.
        await self.runtimes.invalidate(live.chat_id)

    async def ask(self, live, question, options, data_loss_files=None):
        """Pause with one question. The continuation carries the original request, plus the
        migration files a data-loss question is about, so the answer approves exactly those."""
        current = await latest_revision(live.chat_id)
        context: dict[str, Any] = {"original_request": original_request(live), "exchanges": []}
        if data_loss_files:
            context["data_loss_files"] = data_loss_files
        live.workflow = {
            "kind": "clarify",
            "summary": question[:700],
            "steps": [],
            "question": question[:500],
            "options": options,
            "revision_id": current.id if current else None,
            "context": context,
        }
        await self.emit(live, "approach", message=question, workflow=public_workflow(live.workflow))
        return "awaiting_input", question

    async def steer(self, run_id: str, user_id: int, text: str) -> tuple[int | None, bool]:
        """Queue a user message for a running build (Pi's steering queue), in one statement: it is
        stored only if the run is the user's, running and not stopping. Returns the run's owner (None:
        no such run) and whether it was stored, so a refusal needs no second read."""
        target = (
            select(Run.chat_id, Run.status, Run.cancel_requested, Chat.user_id)
            .join(Chat, Chat.id == Run.chat_id)
            .where(Run.id == run_id)
            .cte("target")
        )
        message = bound(Message, id=str(uuid.uuid4()), role="user", content=text, created_at=datetime.now(UTC))
        stored = (
            insert(Message)
            .from_select(
                [*message, "chat_id"],
                select(*message.values(), target.c.chat_id).where(
                    target.c.user_id == user_id, target.c.status == "running", target.c.cancel_requested.is_(False)
                ),
            )
            .returning(Message.chat_id)
            .cte("stored")
        )
        async with AutocommitSessionLocal() as db:
            row = (await db.execute(select(target.c.user_id, select(stored.c.chat_id).scalar_subquery()))).first()
        owner, chat_id = row if row else (None, None)
        if chat_id is None:
            return owner, False
        await bus.publish(bus.COMMANDS, {"type": "steer", "run_id": run_id, "text": text})
        await self.notify(chat_id, {"e": "resync"})
        return owner, True

    async def cancel(self, run_id: str, user_id: int) -> int | None:
        """Request a stop in one statement, only for the user's open run. Returns the run's owner (None:
        no such run), so a refusal needs no second read; a finished run of the user's is a no-op."""
        target = select(Chat.user_id).join(Run, Run.chat_id == Chat.id).where(Run.id == run_id).cte("target")
        requested = (
            update(Run)
            .where(
                Run.id == run_id,
                Run.status.in_(OPEN_STATUSES),
                Run.chat_id.in_(select(Chat.id).where(Chat.user_id == user_id)),
            )
            .values(cancel_requested=True)
            .returning(Run.status)
            .cte("requested")
        )
        async with AutocommitSessionLocal() as db:
            row = (await db.execute(select(target.c.user_id, select(requested.c.status).scalar_subquery()))).first()
        owner, status = row if row else (None, None)
        if status == "queued":
            # Never executed: take it off the queue by claiming it, then record the stop.
            live = await self.workers.claim(run_id)
            if live is not None:
                await self.workers.finish_unstarted(live)
                return owner
        if status is not None:
            # Running, or a worker claimed it between our update and claim. The command is
            # immediate; the flag reaches the owner at its next heartbeat if the command is lost.
            await bus.publish(bus.COMMANDS, {"type": "cancel", "run_id": run_id})
        return owner


agent_service = Service()
