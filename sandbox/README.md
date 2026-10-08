# Sandbox templates and kits

A project starts from a **kit**: a working full-stack app in `kits/<id>/`. Its
frontend calls its backend API, and the API reads and writes a real database
server. There is no SQLite and no frontend-only starter.

| Kit                     | Frontend               | Backend                               | Database   |
| ----------------------- | ---------------------- | ------------------------------------- | ---------- |
| `vite-fastapi-postgres` | React + Vite           | FastAPI, SQLAlchemy, Alembic, psycopg | Postgres   |
| `vite-express-postgres` | React + Vite           | Express, Drizzle, pg                  | Postgres   |
| `next-postgres`         | Next.js (App Router)   | Next route handlers, Drizzle, pg      | Postgres   |
| `vite-express-mongo`    | React + Vite           | Express, official mongodb driver      | MongoDB    |

Each kit holds `stack.json` (services, ports, install, build, typecheck, migrate,
seed, dump, restore, env), and `.accretion/memory.md`, the notes the build agent keeps current.
The Vite frontends proxy `/api` to the backend, so a project has one preview URL.

## Template

`templates.py` builds one E2B template, `accretion`, with the E2B Template SDK. It holds every
kit and both database servers (Postgres 18 and MongoDB 8.3). Neither database runs at boot:
`accretion-db start postgres|mongo` starts the one a kit declares, so an unused server costs no
RAM (E2B bills CPU and RAM, not disk).

The base is `node:24.21.0-bookworm-slim` (Node 24 LTS), Python 3 with venv, Chromium's headless
shell (downloaded by the pinned Playwright package in `/opt/webbuilder-checks`) and the
agent-browser CLI, configured in `~/.agent-browser/config.json` to drive that Chromium. The model
checks apps with it through its command tool. The base stays on
bookworm because MongoDB publishes server packages for bookworm only. Kits are copied to
`/opt/accretion/kits/<id>` with dependencies installed; a new project copies its kit into
`/home/user/react-app`.

Every kit is gated during the build by `kit-gate.mjs`: install, typecheck, build, migrate, then
every service must answer its ready path. The kit's database is reset after its gate, so
projects start empty. A failing kit fails the build.

## Release

Update kit dependencies to their latest stable versions first (`@types/node` stays on the newest
24.x), then from the repository root, with `E2B_API_KEY` in `.env`:

```bash
make template-build            # tags the build v<date> and production
make template-build TAG=staging
```

The backend reads `E2B_TEMPLATE` (default `accretion:production`). A new project resolves the
tag to its exact build and stores that, so moving a tag never changes an existing project.
Roll back by pointing the tag at an earlier dated build (`Template.assign_tags`).
