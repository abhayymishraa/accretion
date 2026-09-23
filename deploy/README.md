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
   NEXT_PUBLIC_WS_URL=wss://BACKEND_DOMAIN
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

One API worker is required: execution ownership, WebSocket subscribers and sandbox
handles are in memory. Run outcomes and bounded activity checkpoints are in PostgreSQL.
Startup marks unfinished runs `interrupted`; it never replays mutations automatically.
Restarting the API interrupts active generations. This setup does not provide
zero-downtime failover, and adding workers would violate admission/ownership assumptions.

## Upgrade the generated-app template

Follow the [SDK build and promotion commands](../README.md#e2b-template).
Build a fresh version label, promote its exact `name:build-UUID` to staging,
and smoke-check a disposable sandbox with approval before production promotion.
Check the starter production build, desktop/mobile browser rendering, and a
source restore followed by the existing Vite restart. Template HTTP readiness
alone does not establish that these paths work.

Set the repository's `E2B_TEMPLATE_ID` secret to the returned exact `build_ref`.
The backend deploy workflow validates the reference and writes it to the VM's
private runtime file before migrating and restarting the API. Retain the old
value for rollback. Do not configure a moving `:production` tag or bare name for
new releases: saved revisions must retain a reproducible build reference.
Tag promotion does not change the VM environment or deploy the backend.
Deploy accompanying agent guidance with the backend when needed.

Saved revisions retain their recorded template references; this does not migrate
them. Legacy IDs such as `dwel3q1jkunk4chqfw7h` still work. For rollback, restore
the previous backend environment reference and optionally reassign the production
tag to that exact prior build. Adding the SDK release command does not establish
a new built, smoke-checked, or deployed template.

## Roll out the orchestration change

The 12 September implementation has been checked locally with real OpenAI/E2B,
but that does not establish deployment of this revision.

1. Set `E2B_TEMPLATE_ID=xjklh0xbjh3wpgu0w306` in the VM's private runtime file.
   This `webbuilder-react-verified` template includes the browser checker dependencies.
   Keep the old value with the previous release configuration for rollback.
2. Allow current generations to finish, then release backend and frontend together.
   The workflow creates the additive `runs` table before API startup. The new first-frame
   WebSocket authentication and HTTP follow-up protocol require both sides to be updated;
   old browser tabs must reload. Independently completing Vercel/GitHub deploys can leave
   a short incompatible interval. Use a maintenance window for this first transition.
3. Confirm readiness, login, snapshot recovery and Stop. Generation checks use paid
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
