# React + FastAPI + Postgres

## Stack
- Frontend: Vite 8.3, React 19.3, TypeScript 7.0, Tailwind CSS 4.3 (`@tailwindcss/vite`).
- Backend: Python 3.11, FastAPI 0.141, SQLAlchemy 2.1 (sync, psycopg 3), Alembic 1.20, pydantic-settings 2.15.
- Database: Postgres, reached through `DATABASE_URL` (read by `app/db.py`).

## Layout
- `frontend/src/App.tsx` home page; `frontend/src/main.tsx` entry; `frontend/src/index.css` Tailwind import.
- `frontend/vite.config.ts` dev server (0.0.0.0:5173), `/api` proxy to 127.0.0.1:8000, and `allowedHosts: [".e2b.app", ".e2b.dev"]`. Don't remove any of these: the preview breaks without them.
- `backend/app/main.py` routes; `app/models.py` tables; `app/schemas.py` request/response models; `app/db.py` engine, `Base`, `get_db`.
- `backend/alembic/versions/` migrations.

## Conventions
- The frontend calls the API with relative URLs: `fetch("/api/...")`. Never hardcode a host or port.
- Every backend route lives under `/api`.
- Tables go in `app/models.py`, request/response shapes in `app/schemas.py`. Validate input with pydantic `Field` constraints; FastAPI returns 422 on bad input.
- Get a DB session with the `Db` dependency in `main.py`.

## How to
- Add a page: create a component in `frontend/src/`, render it from `App.tsx`. No router is installed; switch views with state, or add `react-router` if the app truly needs URLs.
- Add an API route: add a function in `backend/app/main.py` with `@app.get("/api/...")` (or post/put/delete), typed with schemas from `app/schemas.py`.
- Add or change a table: edit `app/models.py`, then
  `cd backend && .venv/bin/alembic revision --autogenerate -m "describe change"` and review the generated file. Do not run `alembic upgrade`: the host applies new migrations when it checks your work, and asks the user first if one would delete data. Never edit the database by hand. If autogenerate says the database is not up to date (an earlier new revision is not applied yet), write the next revision by hand with `.venv/bin/alembic revision -m "..."`.

## Tailwind v4
- Configured in CSS only: `@import "tailwindcss";` in `index.css`. There is no `tailwind.config.js`; don't create one.
- Customize with `@theme { --color-brand: ...; }` in `index.css`. Use utility classes in JSX.

## Installed libraries
Frontend: react, react-dom, tailwindcss. Backend: fastapi, uvicorn, sqlalchemy, alembic, psycopg, pydantic-settings. Add others only when needed (`npm install` in `frontend/`, or add a pinned line to `backend/requirements.txt` and `.venv/bin/pip install -r requirements.txt`).

## Running
Both services are already running (API on 8000, web on 5173); never start another server.

## Current condition
Keep this section up to date whenever you add or remove a page, route, or table.
- Pages: `/` (notes list and add form)
- Routes: `GET /api/health`, `GET /api/notes` (newest first), `POST /api/notes` (`{text}` 1..500 chars)
- Tables: `notes` (id, text, created_at)
