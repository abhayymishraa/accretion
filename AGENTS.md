# Repository rules

## No test suites

- No tests in repo: Python, TypeScript, JavaScript, or other languages.
- Do not add, restore, or generate test files, fixtures, test-only dependencies, test scripts, or CI test jobs.
- Applies to bundled skills too. Excludes installed dependencies and external tool caches.
- Preserve runtime validation, build checks, preview checks, and deployment health checks.
- Run lint, typecheck, build, or manual browser checks only with explicit user approval. Never claim unrun checks passed.

## Sandbox runtimes

`agent/sandbox/sandbox_runtime.py` owns E2B sandboxes; `agent/run/service.py` drives it.

- `lifecycle` is create-time and immutable. `AsyncSandbox.create` accepts it, `connect` does not, and no setter exists. A change to it reaches new sandboxes only.
- E2B defaults `on_timeout` to `kill`. A sandbox created without `lifecycle` is destroyed at timeout, not parked.
- Pausing belongs to the provider, through `on_timeout: 'pause'`. Do not reintroduce an idle reaper. Paused sandboxes are unbilled and do not count toward the concurrency limit.
- `SandboxRuntimes.state()` is not a getter. It drops rows whose sandbox is gone, syncs the row to the provider, and settles spend once a sandbox has paused. `maintain()` must call it on every pass, unconditionally. Put it behind a short-circuit and it stops running, leaving rows stuck at `running`.
- `reserved()` counts every row whose state is not `paused`. A stale `running` row holds capacity forever, and `require_sandbox_capacity` then refuses previews with a 429.
- `auto_resume` wakes a sandbox from preview traffic without passing `reserve_runtime`. That resume is unmetered; treat billing as an open item (edit this when billing covers this edge case).

## Context compaction

`agent/context/compaction.py` trims context, `agent/context/transcript.py` stores it,
`agent/run/runner.py` calls both.

- Always on. There is no enable flag. `MODEL_CONTEXT_WINDOW` and `COMPACTION_RESERVE_TOKENS` size it, they do not switch it off.
- The transcript is append-only per chat, not per run. A chat is one conversation; a later request reads what earlier ones did.
- Never separate a tool call from its result. Every `AIMessage.tool_calls` entry must keep its matching `ToolMessage.tool_call_id`. An orphan is a provider 400, so each cut path rechecks the pairing.
- Summarize with `model.model_copy(...)`, never `bind()` or a call kwarg: both put `reasoning: null` on the wire. `model_copy` also leaves the caller's model untouched, so a failed summary cannot misconfigure the live loop.
- Constants trace to named upstream harnesses and carry that attribution in comments. Change a value and change its comment with it.

## Changing runtime code

- Verify the path that runs, not the path you edited. A reused sandbox goes through `connect`, not `create`. Maintenance runs through `maintain`, not through import. A successful import proves neither.
- Before deleting a call, list everything it did. `state()` reads as a status check and also reconciles rows and settles spend.
- Edit Python with exact string replacement, not regex. Removing a statement that is the sole body of an `if` leaves an orphaned block and an `IndentationError`.

## Frontend architecture

- Read `frontend/AGENTS.md` before changing frontend code. It defines the feature folders, request boundaries, naming, formatting, and enforced file limits.
- The structure is adapted from the sibling TryMatcha repository. Evidence and deliberate differences are recorded in `docs/frontend-architecture.md`.
- Keep frontend restructuring scoped to the frontend; do not transplant backend controller classes, change API contracts, or add state libraries solely to match a folder layout.

## Bundled skills

Loader: `agent/tools/skills.py`. Files: `agent/skills/<dir>/SKILL.md`. Registry: `SKILL_DIRECTORIES`.

Three levels, do not collapse them:

- Catalog in system prompt: name + description only. Every run.
- Body: model calls `read_skill(name)`. On demand.
- References: `read_skill(name, resource)`. Allowlisted per skill in `REFERENCE_DIRECTORIES`.

### Adding a skill

1. Vendor files into `agent/skills/<dir>/`.
2. Register name -> dir in `SKILL_DIRECTORIES`.
3. Add provenance entry: `repository`, `commit`, `upstream_prefix`, `directory`, `files` (sha256 per file), `upstream_git_blobs`. Put it in `agent/skills/design-sources.json` unless the skill belongs to an existing source file.
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
