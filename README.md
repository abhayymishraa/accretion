# WebBuilder

Generate and edit React applications with an AI agent. The Next.js frontend uses a
FastAPI backend for authentication, chat history, and WebSocket progress. One bounded
OpenAI coding loop edits files in E2B. The backend runs production-build and browser
checks, allows two targeted repairs, and persists a final outcome. Stop and reconnect
operate on a run independently of its WebSocket connection.

See [orchestration, limits, and verification](docs/architecture/orchestration.md),
the [original audit](docs/research/2026-09-12-orchestration-audit.md), and the
[LLM Council decision](docs/council/council-transcript-2026-09-12-orchestration.md).

Project history retrieval and optional summaries are described in
[context and memory](docs/context-memory.md). Retrieval uses the existing database;
automatic compaction is disabled pending quality evaluation.

The [runtime skills](docs/runtime-skills.md) load the 13 original
Leonxlnx Taste skills, Anthropic's `frontend-design`, UI UX Pro Max, Impeccable,
Emil's `emil-design-eng`, and Vercel's React guidance and `find-skills`
on demand in the existing editing loop. Supporting references load individually;
UI UX Pro Max's search scripts and Impeccable's launcher are installed files, not runtime tools.
The skill catalog is available automatically in every editing run for every user;
the agent loads relevant instructions on demand. No activation flag is required.

## Deleting projects

Use **Delete** on a project card in the project list or workspace project drawer.
After confirmation, `DELETE /projects/{id}` checks ownership and refuses deletion
while a generation or preview-opening operation is active. The database transaction
removes the project, messages, runs, events, revisions, and derived memory, and queues
the saved revision objects, log archives, and legacy local directory for cleanup.
File deletion and sandbox termination start immediately after that transaction,
in parallel, with a 10-second cleanup wait. The response reports each independently
as `completed` or `queued`; the UI shows when cleanup is still pending. Failed or
timed-out work retains its durable records for the backend maintenance loop to retry
(60 seconds between passes). No separate queue service or new table is needed.

On the single-worker backend, file deletion waits for already-started uploads,
including uploads whose callers were cancelled. New uploads check that the project
still exists before writing. This replaces the fixed 24-hour cleanup delay. Successful
deletes remove their retry records; other queued objects continue processing after
individual failures. GCS generations and MinIO versions/delete
markers are removed by exact object name. Storage credentials need object-version
listing and deletion permissions. This does not delete the shared bucket.

Provider retention, object holds, database backups, and infrastructure access logs
have separate lifetimes. In particular, [GCS soft delete](https://cloud.google.com/storage/docs/soft-delete)
can retain recoverable objects after deletion until its retention period expires.
The application does not change bucket-wide retention policies. A successful delete
response means access is revoked. Even `completed` cleanup does not mean provider
backups or soft-deleted copies have already been permanently erased.

## Production

- Frontend: https://accretion.abhayymishraa.com (Vercel)
- Backend: https://api.accretion.abhayymishraa.com (Oracle)
- Database: PostgreSQL on Neon
- Default model: `gpt-5.6-luna`, configurable with `OPENAI_MODEL`

See [deployment configuration and rollback](deploy/README.md). Pushes to `main`
deploy the frontend through Vercel and backend changes through GitHub Actions.
The VM runs only the backend container, persistent project files, and Caddy.

## Local development

Docker Compose runs only PostgreSQL and local MinIO. The frontend and backend run on your machine.
Requires Docker Compose v2, Python 3.12+, uv, Node.js 22+, and make.

For a fresh checkout, copy `.env.example` to `.env` and
`frontend/.env.example` to `frontend/.env.local`. Fill the OpenAI and E2B
credentials and a random `SECRET_KEY` of at least 32 characters in `.env`.
Keep `DATABASE_URL` aligned with the `POSTGRES_*` values. Local frontend URLs
and `ALLOWED_ORIGINS` are already configured in these files.
Install dependencies once with `uv sync` and `npm --prefix frontend ci`.

Run these commands from the repository root:

```bash
# Dependencies: PostgreSQL on :5432 and MinIO on :9000/:9001.
docker compose up -d --build --wait
```

```bash
# Backend: localhost:8000 (in its own terminal).
make backend
```

```bash
# Frontend: localhost:3000 (in its own terminal).
make frontend
```

`make backend` runs the database migration and initializes the private local
MinIO bucket before starting Uvicorn with reload. This is a
fresh local database; it does not contain your production accounts or projects.
Open http://localhost:3000 and create a local account. AI generation still uses
the configured OpenAI and E2B services.

Use the `webbuilder-react-design-20260914` E2B template (`dwel3q1jkunk4chqfw7h`
in the existing deployment account), or build your own from `sandbox/e2b.Dockerfile`.
Templates without Playwright under `/opt/webbuilder-checks` cannot
run this backend's browser checks. The runner checks browser tooling before
calling the model and stops with a setup error if it is unavailable.
After changing `.env`, stop and restart `make backend`; Uvicorn source reload
does not reload the environment inherited from `uv run`.

Stop each app with Ctrl+C. Stop dependencies with `docker compose down`; their
named volumes preserve data. Run `docker compose logs -f postgres` for database logs.
The production stack remains in `deploy/compose.yaml`. See
[project persistence setup](docs/persistence-setup.md) for GCS, retention, recovery
and verification status. Set a private `MINIO_SECRET_KEY` when creating `.env`.

## E2B template

The sandbox contains Node LTS, React JSX, React Router, React Icons, Vite,
Tailwind CSS v4 and optional Motion for React. Python supports binary-safe
archives; Playwright and headless Chromium live outside the application.
Its server starts on port 5173. No OpenAI or database credentials are copied
into the sandbox template.

The [starter configuration](sandbox/README.md) documents exact versions,
neutral theme tokens, animation imports and upgrade policy. Starter files and
both npm lockfiles are checked in; `npm ci` replaces build-time scaffolding.
Updates use current stable releases at template release time, never floating
`latest` installs during a user's build. Generated apps only bundle Motion if
they import it. Full component kits, charts and 3D libraries remain on demand.

The [E2B Dockerfile](sandbox/e2b.Dockerfile) owns the environment. The
`template-build` Makefile target calls the pinned E2B CLI directly; there is no
custom Python template builder. It starts Vite and waits for HTTP 200 before
E2B snapshots the running process. The runtime still restarts Vite after
restoring or changing project files.

Authenticate the E2B CLI, or export `E2B_API_KEY` in your shell. The Makefile target
does not load `.env`. From the repository root, after approval for the E2B build:

```bash
make template-build TEMPLATE_NAME=webbuilder-react-design-20260917-1
```

Use a fresh release name for each build. The CLI logs `Template created with ID`
and `Build ID` during creation; those IDs alone do not prove the build succeeded.
Wait for successful completion before using the artifact. This command uses E2B
quota and does not change any backend environment.

After an approved disposable-sandbox check, set staging's private environment to
that exact successful build:

```dotenv
E2B_TEMPLATE_ID=webbuilder-react-design-20260917-1:<build-UUID-from-successful-build>
```

After staging checks pass, use the same reference in production and restart the
backend after active generations finish. Retain the previous exact reference for
rollback. No custom staging/production tag promotion is needed: the environment
pins the artifact directly. Saved revisions continue recording their template
reference. Never use a floating template name or `:latest` for a new deployment.

Existing projects keep their recorded template references and dependencies.
Legacy bare IDs remain supported; their original build pins are not backfilled.
The earlier template ID `dwel3q1jkunk4chqfw7h` remains available. An isolated
Dockerfile-built candidate passed the [2026-09-17 acceptance trial](docs/research/e2b-dockerfile-audit-2026-09-17.md);
that trial did not update staging or production.

References: [E2B start/readiness](https://docs.e2b.dev/template/start-ready-command)
and [template tags/build IDs](https://docs.e2b.dev/template/tags).

### Preview synchronization

Vite continues to serve the live app on port 5173 with HMR. After a successful
build of edited files, the backend replaces the project's Vite process once,
then checks the actual page at desktop and mobile sizes. This clears stale
server-side modules without regenerating code or creating another sandbox.
The browser check rejects the untouched `Ready to build` starter; passing it
is a smoke check, not proof that every requested feature was implemented.

Saved-file restoration stops Vite before replacing source files and installing
dependencies, then starts it once. Healthy unchanged resumes do not restart it.
An unhealthy reused preview gets one restart attempt in the same sandbox.
Failures preserve durable saved revisions and do not trigger AI repair calls
for server startup errors. A restart briefly interrupts the preview and resets
its in-memory UI state.

The host controller recognizes the existing template's Vite command and the
replacement process by project directory, executable, and explicit port. It
uses a sandbox-local lock and Linux process handles, never a public restart
endpoint or a broad `pkill`. Unknown port owners are not killed. No polling or
blanket dependency-cache deletion is enabled. The helper ships with the backend
and runs outside the archived source tree, so compatible existing templates
do not need rebuilding for this change.

OpenAI and E2B usage have their own billing or free-credit limits. Free frontend
and VM hosting do not make AI generation free.

### Optional visual observations

The existing `inspect_preview` tool accepts `screenshot=true` for a concrete visual
question. Text-only inspection remains the default. It captures one desktop or
mobile viewport as a JPEG (maximum 200 KB), masks password inputs and disables
animations during capture. There are at most two screenshot attempts per run.
The selected model must support image input; set `PREVIEW_SCREENSHOTS_ENABLED=false`
when deploying a text-only model.

Screenshots use Playwright already installed in the sandbox and native E2B file
streaming. The backend sends a real low-detail image block in the tool response,
then removes the image from context after the next model response. It reserves
4,096 estimated input tokens per image for admission; actual provider usage still
counts against the run budget. Base64 bytes are not counted as text tokens.
These are cost bounds, not a measured saving or guarantee of image understanding.

Images are not added to run events, persisted chat history or project archives.
Temporary sandbox files are removed on a best-effort basis after transfer. Public
tool details report only whether capture succeeded. Inspection blocks external
document navigation, but page scripts and third-party assets can still make network
requests. There are no click, typing or form-submission actions. Inspection does
not replace the final build/browser checks or prove feature completeness.

### Failure diagnostics

On sandbox-related run failures and run timeouts, the host collects one bounded
diagnostic snapshot before retiring the sandbox. Successful runs, ordinary build
failures, token-budget stops and normal cancellations do not trigger it. Requests
run concurrently with a four-second deadline; unavailable evidence cannot turn
the run into a success or prevent retirement. Cancellation during collection
still proceeds to cleanup.

`Run.metrics.sandbox_diagnostics` contains up to three recent CPU/memory/disk
samples and five sandbox-specific lifecycle events. Metrics use native
`AsyncSandbox.get_metrics`; E2B 2.49.1 exposes lifecycle events through its
documented REST endpoint. Only event type, timestamp and identity are retained;
raw event data, headers, metadata and exception messages are excluded. Neither
request resumes the sandbox or adds input to the generation model.

Sources: [Playwright screenshots](https://playwright.dev/docs/api/class-page#page-screenshot),
[E2B metrics](https://docs.e2b.dev/sandbox/metrics), and
[E2B lifecycle events](https://docs.e2b.dev/sandbox/lifecycle-events-api).
These observation/diagnostic additions have not yet been checked; the earlier
native-migration acceptance predates them.

## Local build

```bash
cd frontend
npm run build
```

This repository does not maintain test suites. Runtime build, preview, and
deployment readiness checks remain enabled. See AGENTS.md for contributor rules.
