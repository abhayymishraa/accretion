# Repository rules

## Karpathy guidelines (MUST)

Every change MUST follow the Karpathy guidelines (`karpathy-guidelines` skill, source `forrestchang/andrej-karpathy-skills`).

- Skill not installed: agent MUST tell the user before starting work, and give the install command: `npx skills add forrestchang/andrej-karpathy-skills --skill karpathy-guidelines -g`. Until installed, follow the summary below.
- **Think before coding.** State assumptions. Several readings: list them, don't pick silently. Unclear: stop and ask. Simpler way exists: say so.
- **Simplicity first.** Minimum code that solves the ask. No speculative features, single-use abstractions, unasked config, or handling for impossible cases.
- **Surgical changes.** Touch only what the ask needs. Match existing style. No drive-by refactors. Remove orphans your change made. Dead code outside the change: mention, don't delete.
- **Goal-driven.** Define success first; verify within the approval rule under No test suites.

Exception, for now: skip the skill's test-first step; no test suites here.

## No test suites

- No tests in repo: Python, TypeScript, JavaScript, or other languages.
- Do not add, restore, or generate test files, fixtures, test-only dependencies, test scripts, or CI test jobs.
- Applies to bundled skills too. Excludes installed dependencies and external tool caches.
- Preserve runtime validation, build checks, preview checks, and deployment health checks.
- Run lint, typecheck, build, or manual browser checks only with explicit user approval. Never claim unrun checks passed.

## Branches and pull requests

Every change reaches `main` through a pull request. Only a hotfix goes to `main` direct.

- Never commit, push or open a pull request until the user explicitly asks for it. Edit freely; leave changes uncommitted and report them. Approval covers only what was asked: a request to commit is not a request to push.
- One branch per request, cut from fresh `origin/main`. Name: `<type>/<short-kebab-topic>`, e.g. `feat/at-file-mentions`, `fix/preview-proxy-tmp`.
- Types match commit types: `feat` feature, `fix` bug fix, `refactor` no behaviour change, `perf`, `docs`, `chore` tooling or deps, `hotfix` production down or broken now.
- `hotfix/*` only: may push to `main` direct. Still open a PR after, so the change has a record.
- Commits: Conventional Commits, `<type>(<scope>): <summary>`, imperative, describe the change only. Same type as branch. `prompts.md` change = own commit.
- PR: title = main commit summary. Body says what changed, why, how verified, what not verified. One concern per PR; unrelated fix = own branch.
- Never push feature work to `main`. Never force-push `main`. Never merge own PR: owner merges, merge deploys.

`agent/sandbox/sandbox_runtime.py` owns E2B sandboxes; `agent/run/service.py` drives it.

- `lifecycle` is create-time and immutable. `AsyncSandbox.create` accepts it, `connect` does not, and no setter exists. A change to it reaches new sandboxes only.
- E2B defaults `on_timeout` to `kill`. A sandbox created without `lifecycle` is destroyed at timeout, not parked.
- Pausing belongs to the provider, through `on_timeout: 'pause'`. Do not reintroduce an idle reaper. Paused sandboxes are unbilled and do not count toward the concurrency limit.
- `SandboxRuntimes.state()` is not a getter. It drops rows whose sandbox is gone, syncs the row to the provider, and settles spend once a sandbox has paused. `maintain()` must call it on every pass, unconditionally. Put it behind a short-circuit and it stops running, leaving rows stuck at `running`.
- `reserved(chat_id)` counts every row whose state is not `paused`, and returns that chat's row state from the same query. A stale `running` row holds capacity forever, and `require_sandbox_capacity` then refuses previews with a 429.
- `retire` ends every row it can prove is gone. A row with no `sandbox_id` (the create's response was lost) is removed once its creation tag lists nothing and `CREATE_GRACE` (10 minutes) has passed since the create began; before that an empty list proves nothing. A missing spend reservation does not block removal (`SpendMissing`); `settle` still raises it for every other caller, because a missing record must never release money.
- A run has no clock, so a long one renews its lease through `SandboxRuntimes.renew`, which reserves before it extends. Never call `set_timeout` directly: an extension without a reservation is unmetered.
- One active sandbox per user. Viewing a project (`preview_status`) or acquiring its sandbox calls `Service.park_others`, which pauses the user's other running sandboxes; one with a build in progress keeps running and is parked when its build ends. `park_others` returns at once when the project is already the user's `focus`: every sandbox started since (an open or a build of another project) moved the focus away. `preview_status` checks ownership in its one query and parks only after that check.
- Sandboxes are created without `auto_resume`. A paused one wakes only through `acquire`, which reserves its lease first; the builder opens a sleeping preview itself. Turning `auto_resume` back on makes preview traffic resume a sandbox unmetered, and lets a stale tab undo the one-sandbox rule. A `lifecycle` change reaches existing sandboxes only after `E2B_RUNTIME_GENERATION` is raised.

## Context compaction

`agent/context/compaction.py` trims context, `agent/context/transcript.py` stores it,
`agent/run/runner.py` calls both.

- Always on. There is no enable flag. The run's model window (`agent/routing/models.toml`) and `COMPACTION_RESERVE_TOKENS` size it, they do not switch it off.
- The transcript is append-only per chat, not per run. A chat is one conversation; a later request reads what earlier ones did.
- Never separate a tool call from its result. Every `AIMessage.tool_calls` entry must keep its matching `ToolMessage.tool_call_id`. An orphan is a provider 400, so each cut path rechecks the pairing.
- Summarize with `model.model_copy(...)`, never `bind()` or a call kwarg: both put `reasoning: null` on the wire. `model_copy` also leaves the caller's model untouched, so a failed summary cannot misconfigure the live loop.
- Constants trace to named upstream harnesses and carry that attribution in comments. Change a value and change its comment with it.
- Old transcripts still hold calls to removed tools, and the model copies them. The unknown-tool error lists the tools that exist. Never rewrite a transcript to remove them: it is append-only and the provider caches its prefix.

## Changing runtime code

- Verify the path that runs, not the path you edited. A reused sandbox goes through `connect`, not `create`. Maintenance runs through `maintain`, not through import. A successful import proves neither.
- Before deleting a call, list everything it did. `state()` reads as a status check and also reconciles rows and settles spend.
- Edit Python with exact string replacement, not regex. Removing a statement that is the sole body of an `if` leaves an orphaned block and an `IndentationError`.

## Round trips and chat loading

API and database sit in different regions: each database round trip costs ~120 ms. Count trips, not queries. Measure through a delay proxy in front of local Postgres; local timing hides the cost.

- `pool_pre_ping` off: saves one trip per request. A database or pooler restart fails one request, then SQLAlchemy replaces the pool. `pool_recycle` retires idle connections first.
- Route that never writes, or writes in exactly one statement: `dependencies=[Autocommit, ...]`, `Autocommit` first. Session runs in autocommit, no `BEGIN`/`COMMIT`; a single statement commits by itself (rename and profile save are one `UPDATE ... RETURNING`). Background code uses `AutocommitSessionLocal` the same way, for reads and one-statement writes (each batch of build events, transcript save, lease update). A route with two writes that must land together keeps the transaction.
- Reuse rows the ownership dependency already loaded: same session, identity map, no query. Never close the session and reopen one to load them again (`latest_revision_in`).
- History never ships run steps. Folded run carries `edits` for its edited-files card: `runs.edits`, appended by the event writer as each edit is stored, diff hunks stripped (`edit_summary`). Steps load on expand or menu open. Open run: its stream replays every event, no `/events` fetch.
- A read route answers in one query with ownership joined into it: `/messages` (project, live runs and page), run events, screenshots. An unknown row and someone else's keep their separate errors. Data a page shows is stored on its row at write time, not gathered from other tables at read time.
- Auth reads the access token only: `CurrentUser` is a `TokenUser` (id, role, approved), no query. A route that needs the account row takes `SignedInUser`. Role, waitlist and removal changes reach a caller when the token renews, within 30 minutes; a token still marked waitlisted is rechecked against the database, so an approval lets the user in at once.
- The daily storage transfer budget lives in Redis (`reserve_transfer`), like a rate limit: reading a file costs no database trip. It resets if Redis restarts and is unchecked while Redis is down; it guards provider allowances, it is not billing. `storage_usage` is no longer written; drop it in a later deploy.
- Lookups by owner and by address use indexes: `ix_chats_user_id`, and `ix_users_email_lower` for every `lower(email)` match (migration-owned, not unique). Add an index with the query that filters on a new column.
- File routes check ownership with `owned_project_files`, which loads the latest revision in the same query. Its relationship is `lazy="raise"`: load it explicitly or not at all.
- Let Postgres enforce a rule instead of reading before writing. One queued or running build per project is the partial unique index `uq_runs_one_open_per_chat`: a prompt's admission is one statement whose `ok` CTE carries every check (verified, builder capacity, budget, ownership, no open build or pending question), and a lost race fails the INSERT as a 409. A refused write names its reason from the same statement: admission returns the `facts` row its checks read, steer and cancel return the run's owner. Do not reintroduce a locked read to guard it, or a second read to explain a refusal.
- A model call's spend reservation is one call to `reserve_model_spend` (alembic `f1a2b3c4d5e6`): it locks the user, sums each month under that lock with a fresh snapshot, and inserts. A single SQL statement cannot do this (its sums would be read before the lock); change the limit logic there and in `budget.reserve` together. Settlement runs in the background (`settle_later`); the run awaits it before it finishes.
- Sandbox leases never count against the model budget, so their reserve, confirm and settle take no user lock and are one statement each. `runtime_amount` is SQL over the row being updated.
- Finishing a run is one statement (run, project, terminal event, reply), plus `mark_reusable` in the same transaction only when the run succeeded.
- `emit` never waits on the database. It numbers the event under `emit_lock` and queues it; one writer task per run (`write_events`) stores each batch of events, edit summaries and metrics in one statement, then publishes them in order. `checkpoint` marks metrics dirty for the writer. `flush_events` drains the writer before a revision is saved and before finish; a failed write is raised at the next emit or flush.
- Email and rate limits stay off the database. Register, verification request and confirm are one statement each; the verification limits (five per caller per 15 minutes, one per address per minute) live in Redis (`limit_caller`, `first_link`) and fail open while it is down; register marks the address only once the account exists. Emails go out after the response (`BackgroundTasks`): a lost one is logged, and the user asks for another.
- Deleting a project replies once the project row is gone and the retry intents are stored; storage and sandbox cleanup run after the reply, and the intents retry what they leave.
- `/runs/{id}/events` is paged at `EVENT_PAGE`. Client follows `has_more`. One page truncates long runs.
- Refresh bumps a run's `details_version` only when its status or end changed. Bumping every run refetches every loaded log.
- One stream per project (`/projects/{id}/stream`) carries its notices and the events of its runs. A run event's id is `run_id:sequence`; a reconnect sends it and that run resumes after it, even if it ended meanwhile. No per-run stream.
- Project stream `ready` carries `latest_run_id` and `title`, read after subscribing. Client reloads history only when that run is missing. Read before subscribing opens a gap. `resync`, or Redis down: full reload.
- The stream opens in its dependency (`opened_stream`), before the response starts: subscribe, then one query checks ownership and reads the ready frame and a resumed run's status. Not the user's: the subscription is dropped and it is a real 404. Subscribing costs no database trip, so this order is free and the only one without a gap.
- After a deploy every tab reconnects at once. Catch-up must cost one query per tab, not a history load per tab.

## Performance work: lessons that held up

General rules, learned cutting round trips across this app. The section above records what was built; this one records how to decide.

Measure, don't guess:

- Count statements with SQLAlchemy `before_cursor_execute`. Time through a delay proxy. The `begin` event fires under AUTOCOMMIT too, but nothing goes on the wire.
- Rewrote a read? Diff its output against the old code on real data, including error cases. Trip counts miss wrong answers.
- Before adding machinery, check how mature open-source apps solve the same path. Match the best; stop there.

When to cut, when to stop:

- Cut trips on paths a user waits on: page load, prompt, stream connect, auth. Background work (lease renew, settlement, cleanup) and paths dominated by a slow provider call (sandbox start) are not worth extra complexity.
- An error path may cost one extra read. Fold it in only when free (the write returns what refused it).
- Correctness beats trips. Keep a lock when one statement would read stale data. Keep a transaction when two writes must land together.
- Trips are half of it. Index every foreign key and every expression a query filters on (`lower(email)`). Add the index in the same change as the query.
- Reply first, clean up after: a durable intent row in the reply's statement, provider calls in `BackgroundTasks`, retries from the row.

Postgres and SQLAlchemy traps hit here:

- One statement, one snapshot, taken before any lock wait. Its subqueries miss rows committed while it waited. A fresh read after a lock needs separate statements, e.g. a `VOLATILE` plpgsql function.
- A data-modifying CTE must sit at the top level. It runs even when nothing references it.
- Statements joined by CTEs share bind names: use anonymous literals (`db.base.bound`). INSERT ... SELECT and CTE inserts skip Python column defaults: give every value.
- An ORM UPDATE carrying CTEs drops RETURNING without `synchronize_session=False`. INSERT ... SELECT reports rowcount -1: read RETURNING.
- The session identity map holds rows weakly. A row loaded for a later `db.get` is collected unless something keeps a reference, e.g. the dependency's return value.
- A unique index fails the deploy if existing rows break it: check production first. `CREATE INDEX CONCURRENTLY` runs outside the transaction (`autocommit_block`), and a failed build leaves an invalid index that `IF NOT EXISTS` keeps.

Async traps hit here:

- A closure reads a variable when called, not when defined. A name reassigned in between gives the wrong answer (a refused new project once answered 404).
- Start a task only inside the block that cancels it, and after any cursor it depends on is applied.
- A background writer publishes only after commit, in order. It raises its failure at the next call. The final write must still land after a failed batch.

Process:

- Check every review finding against the code. Reproduce it, fix it, re-measure. Decline with the exact code path that rules it out; reviewers withdraw when shown it.
- Check that a suggested fix actually works: a `storage` event listener hears other tabs only.
- Fail-open or fail-closed for a limit is a product decision. Record it here.
- Scripted edits: back up first, replace exact strings, assert the match count. Never `open(p, "w").write(open(p).read())`: the write truncates before the read.

## Frontend architecture

- Read `frontend/AGENTS.md` before changing frontend code. It defines the feature folders, request boundaries, naming, formatting, and enforced file limits.
- Keep frontend restructuring scoped to the frontend; do not transplant backend controller classes, change API contracts, or add state libraries solely to match a folder layout.

## Mobile and webviews first (MUST)

Most users on phone, often inside app browser (Instagram, X, LinkedIn, Gmail), not Safari/Chrome. Every user-facing feature MUST be built and checked there first. Desktop = wider case, not default.

- MUST start 390px wide, then widen. Full-height = `dvh`, not `vh`. Clear notch and home bar: `env(safe-area-inset-*)`.
- MUST be touch-first. Targets ≥44px. No action or label hover-only. No keyboard shortcut as only path.
- MUST NOT rely on what webviews block: popups/new windows (`window.open`), file downloads, third-party cookies. Google sign-in refuses embedded webviews: every sign-in path MUST have a webview-safe fallback.
- Heavy editors/canvases (Monaco, previews) MUST stay usable on phone, or degrade to readable view.
- UI work is NOT done until checked, after approval, at phone width + in an in-app webview, beside the device and theme checks in `frontend/AGENTS.md`.

## Bundled skills

Loader: `agent/tools/skills.py`. Files: `agent/skills/<dir>/SKILL.md`. Registry: `SKILL_DIRECTORIES`.

Three levels, do not collapse them:

- Catalog in system prompt: name + description only. Every run.
- Body: model calls `read_skill(name)`. On demand.
- References: `read_skill(name, resource)`. Allowlisted per skill in `REFERENCE_DIRECTORIES`.

`REQUIRED_SKILLS` lists the platform skills a user cannot turn off, in a project or for the account. The API refuses the change (`SkillRequired`) and `for_project` ignores an older stored one. A name there must be a bundled skill; an import-time assert checks it.

A skill is off in a project when it is in the project's `chats.disabled_skills` or the account's `users.disabled_skills`; the build reads both in its one query. Turning a skill back on for the account leaves each project's own list alone, so every project returns to its own choice. Deleting a library skill drops its name from the account list in the same statement.

### Adding a skill

1. Vendor files into `agent/skills/<dir>/`.
2. Register name -> dir in `SKILL_DIRECTORIES`, and its `(category, subcategory)` in `SKILL_CATEGORIES`; an import-time assert refuses a bundled skill without one. The order there is the order every skills menu shows.
3. Add provenance entry: `repository`, `commit`, `upstream_prefix`, `directory`, `files` (sha256 per file), `upstream_git_blobs`. Put it in `agent/skills/design-sources.json` unless the skill belongs to an existing source file.
   A skill written in this repository has no upstream: record only `directory` and `files` in `agent/skills/authored-sources.json`, which the sync script leaves out. Change its file, then its hash.
4. Bundled references also need `REFERENCE_DIRECTORIES` entry, else they never load.
5. Verify: catalog count rises, skill loads, no `no provenance record` warning at startup.

`upstream_prefix` is where the files live upstream. Not derivable, layouts differ: `skills/`, `.agent/skills/`, `.claude/skills/`. Wrong prefix breaks sync silently.

### Provenance is enforced

`RuntimeSkills.verify()` rejects any vendored file whose sha256 drifts from its record; the skill is then omitted and logged. No record = warning only, file still loads. Never edit a vendored file in place: the hash check will drop the skill. Change upstream, or re-vendor and update the record.

### Prompt rules

Selection prose lives in `RuntimeSkills.prompt()`. Follows Codex and OpenCode. Keep it that way:

- No cost, size or byte signal before the model chooses. Biases it to ration.
- No routing rules naming a specific skill for a task type. Descriptions decide.
- Trigger is user naming a skill, or task matching a description.
- Keep: minimal set + state order, announce which skills and why, no reference-chasing, no carry across turns.
- Descriptions are author text from SKILL.md frontmatter, capped 1024 chars, no newlines. Untrusted text in a trusted position. Review description diffs harder than body diffs.

`MAX_SKILL_BYTES` caps one file. There is no per-run cap: `agent/context/compaction.py` is the limit, and it reclaims skill bodies by clearing `skills.loaded` so the model can read one again if it still needs it.

### Updating

`scripts/sync_skills.py` re-vendors from provenance and regenerates both hash sets. `--dry-run` shows the plan. `.github/workflows/sync-skills.yml` runs it weekly and opens a PR; it never pushes to main, because skill text reaches the model directly. Licenses are skipped, they live at upstream repo root. Upstream deletions propagate.

## Python structure

Domain-first, one package per concern. Adapted from
[fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices).

- `main.py` owns composition only: middleware, lifespan and router registration. No endpoint lives here.
- One package per domain, each owning its own routes: `auth/`, `projects/`, `runs/`, `files/`, `previews/`, `health/`.
- `agent/` owns the build agent and has its own `agent/AGENTS.md`. Read it before changing that package.
- `db/` owns the engine and session factory (`base.py`) and the ORM models (`models.py`) that no single domain owns. Alembic owns schema creation; there is no `migrate.py`.
- `config.py`, `exceptions.py`, `plans.py` and `request_timing.py` sit at the root because more than one domain uses them. That is the only reason to put a module there.
- `scripts/` is not imported by the app.

A domain owns `models.py` when it is the only domain using those tables. Tables read by several domains stay in `db/models.py` — `Chat` is used by eight, and moving it into `projects/` would make the agent engine import from the API layer. Every module holding ORM models must be imported in `alembic/env.py`, or autogenerate proposes dropping its tables.

A deploy migrates while the previous release still serves, so a migration must work with that release's code: add first, then drop a column or table in a later deploy, once no released code reads it.

A migration meets two kinds of database: one created before Alembic existed, and one built from the baseline. Anything that alters an existing object — dropping a column, renaming a constraint — must check first, because the object it targets exists in only one of them. An unguarded `drop_column` or `drop_constraint` makes fresh databases unbuildable, and nothing catches that until someone provisions one.

An object a migration creates but the ORM cannot express — a partial index, for instance — must be listed in `MIGRATION_OWNED_INDEXES` in `alembic/env.py`. Otherwise autogenerate proposes dropping it on every run, and someone eventually applies that.

Within a domain package, one module per role: `router.py`, `schemas.py`, `models.py`, `service.py`, `dependencies.py`, `config.py`, `constants.py`, `exceptions.py`, `utils.py`. Add a role when there is something to put in it, not to complete the set.

Settings are one `BaseSettings` per domain in `<domain>/config.py`, never one app-wide object: a single settings class makes every domain depend on every variable. Only what two domains share belongs in the root `config.py`. Nothing reads `os.getenv` directly, so a bad value fails at boot rather than mid-request.

Raise a named exception from `<domain>/exceptions.py` instead of an `HTTPException` with a literal status and message, so the status and wording for one failure live in one place. Base classes are in the root `exceptions.py`.

Inject dependencies with `Annotated`: `user: CurrentUser`, `db: DbSession`, never `= Depends(...)` as a default argument. When a route already has defaulted query parameters, make the dependencies keyword-only with `*` rather than reordering the signature, which would change the published parameter order.

Where the tree and these rules disagree, the rules win and the tree moves. There was no established Python convention here to defend.

Responses are Pydantic models inheriting `CustomModel` from the root `models.py`, declared as the handler's return annotation. That is the single place deciding how a value crosses the wire: every timestamp is UTC ISO-8601 with a `Z` suffix, because two endpoints rendering the same column differently is a bug the client pays for. Do not also pass `response_model=` when the return type already says it.

REST naming is consistent and plural: one resource is `projects`, its path parameter is `{project_id}`, and nested collections hang off it (`/projects/{project_id}/runs`). A resource is never reachable under two names. This rule outranks URL stability: when the two conflict, the URL moves and every caller in this repository moves with it.

The database schema is owned by Alembic in `alembic/versions/`. `make backend` and the deploy script both run `alembic upgrade head`; nothing calls `create_all` any more. Constraint and index names come from the convention on `Base.metadata`, so a migration can name the object it alters. A migration that adds an object `create_all` cannot express — a partial index, a data backfill — must say so, because autogenerate cannot see it and a metadata-only baseline would drop it.

Each domain keeps its routes in `router.py` and everything else in `service.py`: a router resolves dependencies and hands off, and holds no database query of its own. Ownership is a dependency (`OwnedProject`, `OwnedRun`), not a call repeated as the first line of each handler — a route that forgets the call is a route that leaks another user's project.

Generated project checkouts live in `var/projects`, not `projects/`, which is a domain package. The deployed bind mount would otherwise shadow the package and the application would not import.

Cross-domain imports name the module, never a star import:

```python
from auth import constants as auth_constants
from agent import service as agent_service
```

New code goes in the package that already owns the concern. A new package is for a concern with no owner, not for an owner that is inconvenient.

## Python coding rules

Adapted from [pydantic-ai](https://github.com/pydantic/pydantic-ai)'s
`agent_docs/index.md`, which its maintainers extracted from their own PR reviews.

Style:

- Scope a change to the problem it solves. For a bug fix, the narrowest change that fixes the reproduced behaviour. A hunch that siblings are affected is not evidence; reproduce it or file it.
- Validate at one layer. Duplicate validation drifts the moment the requirement changes.
- Extract a shared helper on the second occurrence, by refactoring the first, not by adding a parallel path.
- Inline a single-use helper that only wraps attribute access or forwards one call. The jump costs the reader and returns nothing.
- Scope helpers and constants to their use site. A module-level name invites reuse of something not designed for it.
- Delete commented-out code, unused definitions, superseded implementations. Git remembers; the next reader should not have to work out which version is live.
- Compile static regex at module level.

Types:

- `isinstance()` for type checks. Not `hasattr()`, `getattr()`, or `type(obj).__name__`: only `isinstance()` narrows, the others break silently on rename.
- `Literal` for a fixed set of string values, in parameters, fields and returns.
- Annotate to runtime reality. Drop `| None` when the value is always set; narrow a union when control flow already excludes a member.
- Fix a type error instead of silencing it. If a suppression is unavoidable, name the error code and the reason.
- Guard optional-dependency imports with `if TYPE_CHECKING:` and quoted hints.

Errors:

- `assert` for invariants that cannot fail. `RuntimeError("internal error")` disguises a programming mistake as a runtime one.
- Catch the types you expect. Bare `except Exception` swallows what should propagate.
- `!r` for identifiers in messages, so empty and whitespace values stay visible: `f"Tool {name!r}"`.
- Fail fast on a conflict the caller configured explicitly. Fall back quietly only on conflicts the code inferred itself.
- Validate inputs before expensive work: a sandbox, a model call, an upload.

Naming:

- Drop a prefix the context supplies: `ToolConfig.description`, not `ToolConfig.tool_description`.
- Rename a function when its behaviour changes. A name describing the old scope is worse than none.
- Names carry meaning: `revision_id` over `id`.
- No type suffixes (`_dict`, `_list`, `Value`, `Type`) when the annotation says it.
- `UPPER_CASE` for module constants, `_LEADING_UNDERSCORE` when internal.

Imports and async:

- Imports at the top. Inside a function only to defer an optional dependency or break a real cycle, and say which in a comment. Remove unused and duplicate imports.
- The app is async end to end. Never call a blocking function from an `async def` path: it stalls the loop for every other request on the worker. Use the async client, or `run_in_threadpool` where none exists.
- Preserve cancellation. When work spans an `await`, check that a cancelled or failed task cannot leave a sandbox, upload, or row half-owned.

Ruff owns formatting and linting, replacing black, isort and flake8. mypy runs in `strict` mode with the three annotation-demanding flags off — openai-agents' profile: every check that finds a bug, none that only demand signatures on existing code. It is clean; keep it that way rather than adding a suppression. Line length is 120, with no per-file exemption. Model-facing prose stays out of the rule's way instead of being excused from it: the system prompt lives in `agent/run/prompts.md`, and a tool description too long for one line is passed as `@tool(description=...)` rather than written as a docstring. There is no `noqa`, no `type: ignore` and no mypy override in authored code; removing the last one is the goal, adding one needs a reason and the user's agreement.

- `make check` — the gate: `format-check`, `lint`, then `typecheck`.
- `make format` — `ruff format`, then `ruff check --fix`.

Run these with the user's approval, and never claim an unrun check passed.
