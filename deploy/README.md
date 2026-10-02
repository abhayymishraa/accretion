# Production deployment

The Next.js frontend runs on Vercel Hobby. One Oracle Always Free AMD Micro runs the
Python API and Caddy HTTPS proxy. GitHub Actions builds a Linux AMD64 container and
transfers the image over SSH; the VM needs no compiler, Git checkout, frontend, or
development dependencies. Python requires its interpreter and installed libraries;
the deployable artifact is a container, not a standalone native binary.

Frontend: `https://accretion.abhayymishraa.com`.
Backend: `https://api.accretion.abhayymishraa.com`.

## One-time configuration

1. On the Ubuntu VM, install Docker and Docker Compose 2.30 or newer. Allow TCP 80/443 to the VM.
2. Save backend credentials in `/opt/webbuilder/runtime.env` with mode `600`, using
   `runtime.env.example` as the key list. Use the intended PostgreSQL database. The deployment brings the schema to
   head with `alembic upgrade head`. A database that predates Alembic is adopted rather than
   rebuilt, so no existing data is dropped. Generate a strong
   `SECRET_KEY`; never use the application's development fallback in production.
3. Create a DNS A record for the backend domain pointing at the VM. Caddy obtains and
   renews its certificate. Keep the API's port 8000 private.
4. Configure GitHub repository secrets `DEPLOY_HOST`, `DEPLOY_SSH_KEY` (a dedicated
   deployment key for Ubuntu), and `DEPLOY_KNOWN_HOSTS` (the host key verified against
   the VM). Configure repository variable `BACKEND_DOMAIN` with the backend hostname.
5. Configure the existing Vercel frontend project with root directory `frontend`,
   production branch `main`, and these production environment variables:

   ```text
   NEXT_PUBLIC_API_URL=https://BACKEND_DOMAIN
   NEXT_PUBLIC_BASE_URL=https://FRONTEND_DOMAIN
   ```

   Attach the frontend domain in Vercel and use the DNS record Vercel specifies.
   Put that exact HTTPS origin in the backend's `ALLOWED_ORIGINS`.

## Automatic deployments

Pushing backend changes to `main` runs `.github/workflows/deploy-backend.yml`.
Vercel's Git integration deploys frontend changes. The backend workflow can also
be started manually for `main` in GitHub Actions.

Each backend image is tagged with the full Git commit SHA. Deployments serialize,
run provider-free orchestration regressions before packaging, load the new image,
check database readiness, and verify HTTPS before marking the
release current. A failed rollout restores the previous image and Compose files.
The VM retains the current and previous image; logs have bounded rotation.
The API runs as a non-root user with a read-only root filesystem and capped memory.
Docker's periodic check uses the process-only `/` endpoint so it does not keep
Neon awake. Database readiness is checked during deployment and on demand, allowing
an idle Neon database to suspend and conserve its free compute allowance.

Runs are claimed from a Redis-woken queue by leased workers (agent/run/worker.py). Postgres holds
the queue row, the lease and every event; Redis on the same VM only wakes workers and fans events
out. Browsers follow runs over resumable SSE (`GET /runs/{run_id}/stream`, `Last-Event-ID`), so a
reload or reconnect loses no activity. A run whose worker dies, including on a deploy restart, ends
as `interrupted` within about 45 s, by the reaper or at startup; model calls are never replayed.

Workers run inside the API process (WORKER_COUNT=1, RUN_JOBS_PER_WORKER=10). Preview opening and
sandbox handles are still held in that process, so keep one API process until those move to the
database; splitting workers out is then WORKER_COUNT=0 on the API plus a worker service.

## Upgrade the sandbox template

Build it as described in [sandbox/README.md](../sandbox/README.md#release): `make template-build`
tags the new build with its date and moves `production` to it. The backend follows
`E2B_TEMPLATE` (`accretion:production`), and every new project records the exact build it
started on, so a tag move never changes an existing project. `deploy.sh` refuses to deploy
without `E2B_TEMPLATE` in `name:tag` form. Roll back by moving the tag to an earlier dated build.

## Roll out the orchestration change

The 12 September implementation has been checked locally with real OpenAI/E2B,
but that does not establish deployment of this revision.

1. Allow current generations to finish, then release backend and frontend together.
   The workflow runs `alembic upgrade head` before API startup, including migration
   `0a9ff048c441` (run worker lease), and `deploy.sh` starts the Compose `redis` service before the API. Live
   updates moved from the WebSocket to resumable SSE, so both sides must be updated;
   open browser tabs must reload. Independently completing Vercel/GitHub deploys can leave
   a short incompatible interval. Use a maintenance window for this first transition.
2. Confirm readiness, login, snapshot recovery and Stop. Generation checks use paid
   providers; the routine health check does not generate an application.

For rollback, restore both frontend and backend revisions. Leave the additive `runs`
table in place. The old backend cannot read version-2 project snapshots written by
this release: back up `/opt/webbuilder/projects` before rollout and restore that backup
if rolling back. This loses edits made after the backup, so retain the newer files too.
The [architecture document](../docs/architecture/orchestration.md) describes the limits
and snapshot semantics.

## Operations

```bash
cd /opt/webbuilder/current
sudo docker compose -p webbuilder --env-file deployment.env ps
curl --fail https://BACKEND_DOMAIN/health/ready
```

To roll back to the retained release:

```bash
previous=$(sudo cat /opt/webbuilder/previous-release)
sudo docker compose -p webbuilder --env-file "$previous/deployment.env" \
  -f "$previous/compose.yaml" up -d
sudo ln -sfn "$previous" /opt/webbuilder/current
```

Hosting is intended to stay within free allowances. Oracle may reclaim idle free
instances, and Vercel Hobby has usage limits. OpenAI, E2B, and the existing database
have independent quotas or billing; free hosting does not make generation free.
No AI generation is needed for deployment health and login checks.
