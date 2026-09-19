"""Single-worker run ownership, durable outcomes and reconnectable activity."""
import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from e2b import AsyncSandbox, SandboxException
from e2b.exceptions import ServiceBusyException
from fastapi import HTTPException
from sqlalchemy import select, update, func

from db.base import AsyncSessionLocal
from db.models import Chat, Message, Run, RunEvent, User, SandboxRuntime
from .runner import run_editor, RunLimitError, VerificationError, SandboxSetupError
from .browser import check_browser
from .commands import CommandStateError
from .tools import ROOT, FileWriteError, WorkspaceTools
from .preview import control_preview, PreviewError
from .persistence import archive_slots, ensure_revision, latest_revision, revision_bytes, sandbox_archive, save_revision
from .storage import StorageError
from .events import redact, run_events
from .context import ContextError, ProjectContext
from .sandbox_runtime import SandboxRuntimes
from .diagnostics import sandbox_diagnostics
from .budget import BudgetLimitError, require_allowance
from .model_budget import spend_scope
from .workflow import select_workflow, public_workflow
from .decisions import decision_source, prepare_continuation, resolve_decision

logger = logging.getLogger('webbuilder.runs')
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False


@dataclass
class LiveRun:
    id: str
    chat_id: str
    prompt: str
    events: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    task: asyncio.Task | None = None
    sandbox: AsyncSandbox | None = None
    cancelling: bool = False
    revision_id: str | None = None
    user_id: int | None = None
    message_id: str | None = None
    workflow: dict = field(default_factory=dict)
    sandbox_started: bool = False


class Service:
    def __init__(self):
        self.active: dict[str, LiveRun] = {}
        self.runtimes = SandboxRuntimes()
        self.sandboxes = self.runtimes.handles
        self.subscribers: dict[str, set[asyncio.Queue]] = {}
        self.admission = asyncio.Lock()
        self.stopping = False
        self.maintenance_task = None
        self.opening: set[str] = set()

    async def require_sandbox_capacity(self, chat_id, *, requesting_run=None):
        # Paused rows retain ownership without occupying a running slot.
        reserved = await self.runtimes.reserved()
        reserved |= set(self.sandboxes) | self.opening | {r.chat_id for r in self.active.values()
            if r.sandbox_started and r.id != requesting_run}
        row = await self.runtimes.get(chat_id) if chat_id else None
        if (row and row.state in ('creating', 'retiring')) or (chat_id not in reserved and
                len(reserved) >= int(os.getenv('MAX_LIVE_SANDBOXES', '2'))):
            raise HTTPException(429, 'Live preview capacity reached or cleanup is pending. Try again after a preview closes.')

    async def retire_sandbox(self, chat_id):
        async with self.admission:
            try:
                return await self.runtimes.retire(chat_id)
            except Exception as exc:
                logger.warning('Sandbox cleanup deferred chat_id=%s error_type=%s', chat_id, type(exc).__name__)
                return False

    async def reap_idle_sandboxes(self):
        async with self.admission:
            await self.runtimes.maintain(self.opening | {r.chat_id for r in self.active.values()})

    async def preview_status(self, chat):
        async with self.admission:
            if any(r.chat_id == chat.id for r in self.active.values()):
                return {'url': None, 'state': 'building'}
            if chat.id in self.opening:
                return {'url': None, 'state': 'opening'}
            # Ownership was checked by the route. Refresh revision and runtime together
            # after acquiring admission; its original Chat snapshot may predate a build.
            async with AsyncSessionLocal() as db:
                current = (await db.execute(select(Chat, SandboxRuntime).outerjoin(
                    SandboxRuntime, SandboxRuntime.chat_id == Chat.id).where(Chat.id == chat.id))).one_or_none()
            if current is None:
                raise HTTPException(404, 'Project not found')
            chat, row = current
            if row and row.reusable and row.state != 'retiring' and row.revision_id == chat.latest_saved_revision_id:
                try:
                    if await self.runtimes.state(row) == 'running' and chat.app_url:
                        # Observing status must not keep an idle preview alive.
                        return {'url': chat.app_url, 'state': 'active', 'revision_id': row.revision_id}
                except Exception:
                    raise HTTPException(503, 'Preview status temporarily unavailable') from None
            return {'url': None, 'state': 'sleeping', 'revision_id': chat.latest_saved_revision_id}

    async def startup(self):
        if self.maintenance_task and not self.maintenance_task.done():
            self.maintenance_task.cancel()
            await asyncio.gather(self.maintenance_task, return_exceptions=True)
        self.stopping = False
        # No automatic replay of mutations after a process restart.
        async with AsyncSessionLocal.begin() as db:
            await db.execute(update(Run).where(Run.status == 'running').values(
                status='interrupted', reason='Server restarted before this run finished. Submit a new request to continue.',
                finished_at=datetime.now(timezone.utc)))
            await db.execute(update(Chat).values(app_url=None))
        # Reconcile before admission. Unknown states stay reserved; clean runtimes sleep.
        await self.runtimes.maintain(set(), shutdown=True)
        from .maintenance import maintain_loop
        self.maintenance_task = asyncio.create_task(maintain_loop(self), name='persistence-maintenance')

    async def shutdown(self):
        self.stopping = True
        if self.maintenance_task:
            self.maintenance_task.cancel()
            await asyncio.gather(self.maintenance_task, return_exceptions=True)
        tasks = [r.task for r in self.active.values() if r.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        async with self.admission:
            await self.runtimes.maintain(set(), shutdown=True)

    async def admit(self, user_id: int, prompt: str, chat_id: str | None = None, *, mode='auto', response=None):
        prompt = prompt.strip()
        if (not prompt and response is None) or len(prompt) > 12000:
            raise HTTPException(422, 'Describe a change in 1–12000 characters')
        async with self.admission:
            # Resolve retries before capacity/credit checks: no duplicate run or charge.
            if response is not None:
                async with AsyncSessionLocal.begin() as db:
                    parent, fingerprint = await decision_source(db, user_id, *response)
                    if parent.workflow.get('response_hash'):
                        child = await db.get(Run, parent.workflow['continuation_id']) if parent.workflow.get('continuation_id') else None
                        return {'chat_id': parent.chat_id, 'run_id': child.id if child else None,
                                'status': child.status if child else parent.status}
                    if response[1] == 'dismiss':
                        resolve_decision(parent, fingerprint, 'dismiss')
                        # Commit before telling other tabs to fetch the resolved state.
                        await db.commit()
                        self.publish(parent.chat_id, {'e': 'resync'})
                        return {'chat_id': parent.chat_id, 'run_id': None, 'status': 'cancelled'}
                    chat_id = parent.chat_id
            if self.stopping or len(self.active) + len(self.opening) >= int(os.getenv('MAX_CONCURRENT_RUNS', '2')):
                raise HTTPException(429, 'The builder is busy. Try again shortly; no credit was used.')
            workflow, metrics = {'mode': mode}, {}
            async with AsyncSessionLocal.begin() as db:
                user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
                if not user:
                    raise HTTPException(401, 'User not found')
                if not user.email_verified:
                    raise HTTPException(403, 'Verify your email before continuing.')
                parent = None
                if response is not None:
                    parent, fingerprint = await decision_source(db, user_id, *response)
                    workflow, metrics = await prepare_continuation(db, parent, response[1], response[2])
                try:
                    await require_allowance(db, user)
                except BudgetLimitError as exc:
                    raise HTTPException(429, str(exc)) from None
                required = ('STORAGE_BUCKET',) + (('MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY')
                    if os.getenv('STORAGE_PROVIDER', 'minio') == 'minio' else ())
                if any(not os.getenv(name) for name in required):
                    raise HTTPException(503, 'Project storage is not configured; no credit was used.')
                if chat_id:
                    chat = await db.scalar(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).with_for_update())
                    if not chat:
                        raise HTTPException(404, 'Project not found')
                    if chat_id in self.opening or any(r.chat_id == chat_id for r in self.active.values()):
                        raise HTTPException(409, 'This project already has a running request; no credit was used.')
                    pending = await db.scalar(select(Run.id).where(Run.chat_id == chat_id,
                        Run.status == 'awaiting_input').limit(1))
                    if pending and (not parent or pending != parent.id):
                        raise HTTPException(409, 'Answer or dismiss the pending question or plan first.')
                else:
                    chat_id = str(uuid.uuid4())
                    db.add(Chat(id=chat_id, user_id=user_id, title=prompt[:100]))
                    await db.flush()
                if parent is None:
                    if not user.use_token():
                        raise HTTPException(403, f'You have used all {user.credits_limit} credits '
                            f'for this month. They reset on {user.tokens_reset_at:%-d %B} UTC. '
                            'Saved projects and previews remain available.')
                    # Recorded only once the credit is actually taken, so a refund
                    # cannot return one that was never spent.
                    metrics['credit_spent'] = True
                run_id = str(uuid.uuid4())
                db.add(Run(id=run_id, chat_id=chat_id, prompt=prompt, status='running', workflow=workflow, metrics=metrics))
                if parent is not None:
                    resolve_decision(parent, fingerprint, response[1], run_id)
                message_id = str(uuid.uuid4())
                db.add(Message(id=message_id, chat_id=chat_id, role='user', content=prompt))
                credits = user.tokens_remaining
            live = LiveRun(run_id, chat_id, prompt, user_id=user_id, message_id=message_id,
                           workflow=workflow, metrics=metrics)
            self.active[run_id] = live
            if parent is not None:
                self.publish(chat_id, {'e': 'resync'})
            live.task = asyncio.create_task(self.execute(live), name=f'run:{run_id}')
            return {'chat_id': chat_id, 'run_id': run_id, 'status': 'running', 'tokens_remaining': credits}

    async def refund_credit(self, live):
        if not live.metrics.get('credit_spent') or live.metrics.get('credit_refunded'):
            return
        async with AsyncSessionLocal.begin() as db:
            user = await db.get(User, live.user_id, with_for_update=True)
            if user:
                user.refund_token()
        live.metrics['credit_refunded'] = True
        logger.warning('Refunded a credit after an infrastructure fault run_id=%s', live.id)

    def publish(self, chat_id, event):
        for queue in list(self.subscribers.get(chat_id, set())):
            if queue.full():
                # A slow observer reloads a snapshot rather than blocking generation.
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait({'e': 'resync'})
            else:
                queue.put_nowait(event)

    def event(self, live, kind, **payload):
        return redact({'e': kind, 'run_id': live.id, 'event_id': f'{live.id}:{len(live.events) + 1}',
                 'sequence': len(live.events) + 1, 'created_at': datetime.now(timezone.utc).isoformat(), **payload}
        )

    async def emit(self, live, kind, **payload):
        if len(live.events) >= 200:
            raise RunLimitError('Activity budget reached')
        event = self.event(live, kind, **payload)
        async with AsyncSessionLocal.begin() as db:
            db.add(RunEvent(run_id=live.id, sequence=event['sequence'], payload=event))
        live.events.append(event)
        self.publish(live.chat_id, event)
        record = {k: event[k] for k in ('e', 'run_id', 'sequence')}
        if kind == 'stage':
            live.metrics['stage'] = payload.get('message')
            record['stage'] = payload.get('message')
        elif kind in ('verification', 'tool_completed'):
            record['ok'] = payload.get('ok')
        logger.info(json.dumps(record))

    async def checkpoint(self, live, dirty=False):
        if dirty:
            await self.save_files(live)
        async with AsyncSessionLocal.begin() as db:
            await db.execute(update(Run).where(Run.id == live.id).values(metrics=redact(live.metrics)))

    async def get_e2b_sandbox(self, id: str):
        revision = await ensure_revision(id)
        sandbox, restore = await self.runtimes.acquire(id, revision)
        if not restore:
            return sandbox
        try:
            await sandbox.commands.run('python3 -c "import hashlib, zipfile; assert hasattr(hashlib, \'file_digest\')"', timeout=10)
        except Exception:
            raise SandboxSetupError('Sandbox archive tools are unavailable. Rebuild sandbox/e2b.Dockerfile with Python 3.11 or later. No editing model request was made.') from None
        if revision:
            # Stop watchers before replacing their source tree or dependencies.
            await control_preview(sandbox, 'stop')
            async with archive_slots:
                await sandbox_archive(sandbox, 'restore', await revision_bytes(revision))
            if 'package-lock.json' not in revision.manifest:
                raise StorageError('Saved project needs package-lock.json before preview can be restored')
            await sandbox.commands.run('npm ci --ignore-scripts --no-audit --no-fund', cwd=ROOT, timeout=90)
            await control_preview(sandbox, 'start')
        return sandbox

    async def preview_ready(self, sandbox):
        await sandbox.commands.run('curl --fail --silent --retry 5 --retry-connrefused '
            '--retry-delay 2 --max-time 5 http://localhost:5173/ >/dev/null', cwd=ROOT, timeout=45)
        if not (await check_browser(WorkspaceTools(sandbox)))['ok']:
            raise PreviewError('Saved preview did not pass browser checks')

    async def save_files(self, live):
        if not live.sandbox:
            return
        if len(live.events) >= 200:
            raise RunLimitError('Activity budget reached before checkpoint')
        current = await latest_revision(live.chat_id)
        async with archive_slots:
            archive = await sandbox_archive(live.sandbox, 'pack')
            live.revision_id, event = await save_revision(live.chat_id, live.id, archive,
                current.template_id if current else os.environ['E2B_TEMPLATE_ID'],
                lambda revision_id: self.event(live, 'checkpoint_saved', revision_id=revision_id,
                                               message='Project files saved'))
        if event:
            live.events.append(event)
            self.publish(live.chat_id, event)

    async def open_preview(self, chat_id):
        async with self.admission:
            if (self.stopping or chat_id in self.opening or any(r.chat_id == chat_id for r in self.active.values())
                    or len(self.active) + len(self.opening) >= int(os.getenv('MAX_CONCURRENT_RUNS', '2'))):
                raise HTTPException(409, 'Wait for the current operation to finish')
            await self.require_sandbox_capacity(chat_id)
            self.opening.add(chat_id)
        try:
            revision = await ensure_revision(chat_id)
            if not revision:
                raise HTTPException(404, 'No saved project yet')
            async with asyncio.timeout(180):
                sandbox = await self.get_e2b_sandbox(chat_id)
                try:
                    await self.preview_ready(sandbox)
                except CommandStateError:
                    raise
                except Exception:
                    row = await self.runtimes.get(chat_id)
                    if not row or not row.reusable:
                        # A restored project has already received a fresh server.
                        raise
                    # Repair the server in the same sandbox before considering a
                    # future open/restore. Do not allocate a VM for a module cache.
                    await control_preview(sandbox, 'restart')
                    await self.preview_ready(sandbox)
                url = 'https://' + sandbox.get_host(5173)
                async with AsyncSessionLocal.begin() as db:
                    chat = await db.get(Chat, chat_id, with_for_update=True)
                    if not chat or chat.latest_saved_revision_id != revision.id:
                        raise StorageError('Saved project changed while opening its preview')
                    await self.runtimes.mark_reusable(db, chat_id, revision.id)
                    chat.app_url = url
                return {'url': url, 'revision_id': revision.id}
        except BaseException:
            await self.retire_sandbox(chat_id)
            raise
        finally:
            self.opening.discard(chat_id)

    async def finish(self, live, status, reason, result=None):
        event = self.event(live, 'run_finished', **{'event_id': f'{live.id}:terminal',
                 'status': status, 'message': reason, 'metrics': live.metrics,
                 'workflow': public_workflow(live.workflow),
                 'url': result['url'] if result and status == 'succeeded' else None,
                 'revision_id': live.revision_id})
        async with AsyncSessionLocal.begin() as db:
            run = await db.get(Run, live.id, with_for_update=True)
            if not run or run.status != 'running':
                return
            # A cancelled DB await may have committed an event before updating LiveRun.
            # Allocate terminal sequence from durable state rather than the in-memory length.
            last_sequence = await db.scalar(select(func.coalesce(func.max(RunEvent.sequence), 0))
                                           .where(RunEvent.run_id == live.id))
            event['sequence'] = last_sequence + 1
            await db.execute(update(Run).where(Run.id == live.id).values(status=status, reason=reason,
                metrics=redact(live.metrics), workflow=live.workflow, finished_at=datetime.now(timezone.utc)))
            changes = {'app_url': event['url']} if live.sandbox_started else {}
            if status == 'succeeded' and live.revision_id:
                await self.runtimes.mark_reusable(db, live.chat_id, live.revision_id)
                changes['latest_verified_revision_id'] = live.revision_id
            if changes:
                await db.execute(update(Chat).where(Chat.id == live.chat_id).values(**changes))
            db.add(RunEvent(run_id=live.id, sequence=event['sequence'], payload=event))
            transcript = reason
            if status == 'awaiting_input':
                transcript += '\nProposed, not implemented:\n' + '\n'.join(live.workflow.get('steps', []))
                if live.workflow.get('question'):
                    transcript += '\n' + live.workflow['question']
            db.add(Message(id=live.id, chat_id=live.chat_id, role='assistant', content=transcript, event_type='run_summary'))
        live.events.append(event)
        self.publish(live.chat_id, event)
        logger.info(json.dumps({'run_id': live.id, 'status': status, **{
            key: live.metrics.get(key) for key in ('turns', 'tool_calls', 'total_tokens', 'elapsed_ms', 'error_type', 'stage', 'sandbox_cleanup', 'token_budget', 'model_calls', 'cached_input_tokens', 'cache_write_tokens', 'uncached_input_tokens')}}))

    async def execute(self, live):
        scope_token = spend_scope.set({'user_id': live.user_id, 'run_id': live.id, 'limit_error': None})
        started = time.monotonic()
        previous_elapsed = live.metrics.get('elapsed_ms', 0)
        status, reason, result = 'failed', 'The run failed. Submit a new request to retry.', None
        diagnose_sandbox = False
        try:
            remaining_time = int(os.getenv('RUN_TIMEOUT_SECONDS', '600')) - previous_elapsed / 1000
            if remaining_time <= 0:
                raise RunLimitError('The request reached its active time limit')
            async with asyncio.timeout(remaining_time):
                await self.emit(live, 'run_started', message='Starting your request')
                await self.emit(live, 'stage', message='Understanding your request')
                live.workflow = await select_workflow(live)
                await self.emit(live, 'approach', message=live.workflow['summary'],
                                workflow=public_workflow(live.workflow))
                if live.workflow['kind'] != 'execute':
                    status = 'answered' if live.workflow['kind'] == 'answer' else 'awaiting_input'
                    reason = live.workflow['summary']
                    return
                async with self.admission:
                    await self.require_sandbox_capacity(live.chat_id, requesting_run=live.id)
                    live.sandbox_started = True
                live.sandbox = await self.get_e2b_sandbox(live.chat_id)
                # Commit unsafe state before the first possible mutation.
                await self.runtimes.invalidate(live.chat_id)
                result = await run_editor(live.sandbox, live.prompt,
                    lambda kind, **data: self.emit(live, kind, **data),
                    lambda dirty=False: self.checkpoint(live, dirty), live.metrics,
                    request_context={'continuation': live.workflow.get('context'),
                        'approach': public_workflow(live.workflow),
                        'plan_approved': live.workflow.get('approved', False)},
                    memory=ProjectContext(live.chat_id, live.user_id, live.message_id)
                    if live.user_id is not None and live.message_id is not None else None)
                if 'decision' in result:
                    current = await latest_revision(live.chat_id)
                    live.workflow = {**live.workflow, **redact(result['decision']),
                        'revision_id': current.id if current else None, 'approved': False}
                    status, reason = 'awaiting_input', live.workflow['summary']
                    return
                await self.save_files(live)
                status, reason = 'succeeded', result['summary'] + '\n\nProduction build and the selected desktop/mobile acceptance checks passed.'
        except TimeoutError:
            status, reason = 'timed_out', 'The run reached its time limit. Partial changes may remain; submit a smaller request.'
            diagnose_sandbox = True
        except asyncio.CancelledError:
            status = 'interrupted' if self.stopping else 'cancelled'
            reason = 'Server stopped; submit a new request to continue.' if self.stopping else 'Stopped at your request. The last acknowledged checkpoint remains available.'
        except RunLimitError as exc:
            # A limit is a stopping point, not a failure: the checkpoint holds the work and
            # the next message continues from it. Rendering this as a broken run is what
            # made users think the product itself had failed.
            status = 'stopped'
            reason = (f'{str(exc).rstrip(".")}. Your work so far is saved. '
                      'Send another message to continue from here.')
            live.metrics['error_type'] = type(exc).__name__
        except (VerificationError, ContextError, PreviewError, BudgetLimitError) as exc:
            reason = str(exc)
            live.metrics['error_type'] = type(exc).__name__
            diagnose_sandbox = isinstance(exc, (SandboxSetupError, PreviewError))
        except HTTPException as exc:
            reason = str(exc.detail)
            live.metrics['error_type'] = 'AdmissionError'
        except StorageError as exc:
            reason = str(exc) + '. The last acknowledged checkpoint is safe. No automatic AI retry was started.'
            live.metrics['error_type'] = 'StorageError'
        except (CommandStateError, FileWriteError) as exc:
            reason = str(exc) + '. The last acknowledged checkpoint remains available.'
            live.metrics['error_type'] = type(exc).__name__
            diagnose_sandbox = True
        except (SandboxException, ServiceBusyException) as exc:
            reason = 'The build sandbox could not complete an operation. Retry the request; if it keeps failing, check the E2B template and service availability.'
            live.metrics['error_type'] = type(exc).__name__
            diagnose_sandbox = True
            # The provider never gave this run a machine, so the credit buys nothing.
            # Deliberately not done for RunLimitError: that run spent real compute.
            await self.refund_credit(live)
            logger.error('Sandbox operation failed run_id=%s error_type=%s stage=%s',
                         live.id, type(exc).__name__, live.metrics.get('stage'))
        except Exception as exc:
            # Exception text can include provider requests or secrets. Log safe identity only.
            live.metrics['error_type'] = type(exc).__name__
            logger.error('Run failed run_id=%s error_type=%s', live.id, type(exc).__name__)
        finally:
            # Creation registers ownership before restoring files; cancellation can interrupt restoration.
            if live.sandbox_started:
                live.sandbox = live.sandbox or self.sandboxes.get(live.chat_id)
            live.metrics['elapsed_ms'] = previous_elapsed + round((time.monotonic() - started) * 1000)
            if status != 'succeeded' and live.sandbox_started:
                # Completed mutation batches are already saved. Never archive a half-finished command.
                if live.sandbox:
                    self.sandboxes[live.chat_id] = live.sandbox
                    if diagnose_sandbox:
                        # At most four seconds before retirement. No periodic polling or model input.
                        try:
                            live.metrics['sandbox_diagnostics'] = await sandbox_diagnostics(live.sandbox.sandbox_id)
                        except asyncio.CancelledError:
                            # Cancellation during optional evidence collection must still retire the sandbox.
                            status = 'interrupted' if self.stopping else 'cancelled'
                            reason = 'Stopped while collecting diagnostics. The last acknowledged checkpoint remains available.'
                if await self.retire_sandbox(live.chat_id):
                    live.metrics['sandbox_cleanup'] = 'killed'
                else:
                    live.metrics['sandbox_cleanup'] = 'pending'
                    reason += ' Sandbox cleanup is pending. Reopening is blocked until ownership is resolved.'
                    logger.warning('Sandbox cleanup remains reserved run_id=%s', live.id)
            try:
                await self.finish(live, status, reason, result)
            except Exception:
                if live.sandbox_started:
                    await self.retire_sandbox(live.chat_id)
                logger.error('Could not persist terminal state run_id=%s', live.id)
                self.publish(live.chat_id, {'e': 'resync'})
            self.active.pop(live.id, None)
            spend_scope.reset(scope_token)

    async def cancel(self, run_id):
        live = self.active.get(run_id)
        if live and live.task and not live.cancelling:
            live.cancelling = True
            live.task.cancel()
            await asyncio.gather(live.task, return_exceptions=True)
            # Cancellation before the coroutine's first instruction still gets a terminal record.
            if run_id in self.active:
                await self.finish(live, 'cancelled', 'Stopped before generation started.')
                self.active.pop(run_id, None)

    async def snapshot(self, chat_id, offset=0, limit=10):
        async with AsyncSessionLocal.begin() as db:
            rows = (await db.scalars(select(Run).where(Run.chat_id == chat_id).order_by(Run.created_at.desc(), Run.id.desc())
                                    .offset(offset).limit(limit))).all()
            runs = []
            for row in reversed(rows):
                live = self.active.get(row.id)
                if row.status == 'running' and not live:
                    row.status, row.reason = 'interrupted', 'Run stopped before a final state was saved. Submit a new request to continue.'
                    row.finished_at = datetime.now(timezone.utc)
                runs.append({'id': row.id, 'status': row.status, 'reason': row.reason, 'created_at': row.created_at.isoformat(),
                    'workflow': public_workflow(row.workflow),
                    'events': await run_events(db, row.id), 'metrics': redact(live.metrics) if live else row.metrics})
            return runs


agent_service = Service()
