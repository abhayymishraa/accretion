# Accretion

Talk an idea into a running React app. Describe it, watch it build, keep shaping
it by chat, with a live preview the whole way.

A Next.js frontend, a FastAPI backend, and one bounded agent loop that edits
files inside an E2B sandbox. The backend runs a production build plus browser
checks, allows two targeted repairs, then persists the outcome. Stop and
reconnect work on a run independently of its WebSocket.

## Stack

| | |
|---|---|
| Frontend | Next.js, deployed on Vercel |
| Backend | FastAPI, one container on a VM behind Caddy |
| Database | PostgreSQL |
| Sandbox | E2B, Vite on port 5173 |
| Model | `gpt-5.6-luna`, set with `OPENAI_MODEL` |

## Quickstart

Needs Docker Compose v2, Python 3.12+, uv, Node.js 22+, make.

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env.local
# fill OPENAI_API_KEY, E2B_API_KEY, and a 32+ char SECRET_KEY in .env

uv sync
npm --prefix frontend ci
```

Three terminals from the repo root:

```bash
docker compose up -d --build --wait   # PostgreSQL + MinIO
make backend                          # localhost:8000
make frontend                         # localhost:3000
```

`make backend` migrates the database and creates the local bucket before
starting Uvicorn. This is a fresh local database, separate from production.
Open http://localhost:3000 and make an account.

After editing `.env`, restart `make backend`. Uvicorn's reload does not pick up
a changed environment.

## How it works

A run is one bounded agent loop. It reads and edits files in the sandbox, then
the backend builds the project and drives a browser over the result at desktop
and mobile sizes. A failed check earns at most two targeted repairs before the
run ends with a recorded outcome.

Context is compacted rather than summarized first: superseded file reads are
dropped, long tool output keeps only its head and tail, and loaded reference
material is released before any summarizing model call is made.

- [Sandbox template](sandbox/README.md), pinned versions and build policy
- [Deployment and rollback](deploy/README.md)

## Notes

Pushes to `main` deploy the frontend through Vercel and the backend through
GitHub Actions.

The sandbox template must carry Playwright under `/opt/webbuilder-checks`, or
the browser checks cannot run. The runner fails fast with a setup error when it
is missing.

OpenAI and E2B bill separately. Free hosting does not make generation free.

This repository keeps no test suites. Build, preview and deployment checks stay
enabled. Contributor rules are in [AGENTS.md](AGENTS.md).
