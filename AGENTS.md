# Repository rules

## No test suites

- No tests in repo: Python, TypeScript, JavaScript, or other languages.
- Do not add, restore, or generate test files, fixtures, test-only dependencies, test scripts, or CI test jobs.
- Applies to bundled skills too. Excludes installed dependencies and external tool caches.
- Preserve runtime validation, build checks, preview checks, and deployment health checks.
- Run lint, typecheck, build, or manual browser checks only with explicit user approval. Never claim unrun checks passed.

## Sandbox runtimes

`agent/sandbox_runtime.py` owns E2B sandboxes; `agent/service.py` drives it.

- `lifecycle` is create-time and immutable. `AsyncSandbox.create` accepts it, `connect` does not, and no setter exists. A change to it reaches new sandboxes only.
- E2B defaults `on_timeout` to `kill`. A sandbox created without `lifecycle` is destroyed at timeout, not parked.
- Pausing belongs to the provider, through `on_timeout: 'pause'`. Do not reintroduce an idle reaper. Paused sandboxes are unbilled and do not count toward the concurrency limit.
- `SandboxRuntimes.state()` is not a getter. It drops rows whose sandbox is gone, syncs the row to the provider, and settles spend once a sandbox has paused. `maintain()` must call it on every pass, unconditionally. Put it behind a short-circuit and it stops running, leaving rows stuck at `running`.
- `reserved()` counts every row whose state is not `paused`. A stale `running` row holds capacity forever, and `require_sandbox_capacity` then refuses previews with a 429.
- `auto_resume` wakes a sandbox from preview traffic without passing `reserve_runtime`. That resume is unmetered; treat billing as an open item (edit this when billing covers this edge case).

## Context compaction

`agent/compaction.py` trims context, `agent/transcript.py` stores it, `agent/runner.py` calls both.

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

Loader: `agent/skills.py`. Files: `agent/skills/<dir>/SKILL.md`. Registry: `SKILL_DIRECTORIES`.

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

`MAX_SKILL_BYTES` caps one file. There is no per-run cap: `agent/compaction.py` is the limit, and it reclaims skill bodies by clearing `skills.loaded` so the model can read one again if it still needs it.

### Updating

`scripts/sync_skills.py` re-vendors from provenance and regenerates both hash sets. `--dry-run` shows the plan. `.github/workflows/sync-skills.yml` runs it weekly and opens a PR; it never pushes to main, because skill text reaches the model directly. Licenses are skipped, they live at upstream repo root. Upstream deletions propagate.

## Python structure

Domain-first, one package per concern. Adapted from
[fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices).

- `main.py` owns the app: routing, middleware, lifespan, `/ws/{id}`. Request handling here, the work it calls in the owning package.
- `auth/` owns authentication. `db/` owns engine (`base.py`), ORM models (`models.py`), schema creation (`migrate.py`).
- `agent/` owns the build agent and has its own `agent/AGENTS.md`. Read it before changing that package.
- `plans.py` and `request_timing.py` sit at the root because more than one package uses them. That is the only reason to put a module there.
- `scripts/` is not imported by the app.

Within a domain package, one module per role: `router.py`, `schema.py`, `models.py`, `service.py`, `dependencies.py`, `constants.py`, `exceptions.py`, `utils.py`. Add a role when there is something to put in it, not to complete the set. `auth/` currently has four of the eight.

Where the tree and these rules disagree, the rules win and the tree moves. There was no established Python convention here to defend.

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

No formatter, linter, or type checker is configured. Match the file you are editing; do not introduce a tool as a side effect of an unrelated change.
