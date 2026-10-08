# React + Express + Postgres

## Stack
- Frontend: Vite 8, React 19, TypeScript 7, Tailwind CSS 4 (`@tailwindcss/vite`).
- Backend: Express 5, Drizzle ORM 0.45 + drizzle-kit 0.31 over `pg` (node-postgres) 8, TypeScript run by `tsx` 4.
- Database: Postgres at `DATABASE_URL` (from `.env`). Secrets: `APP_SECRET` in `.env`, read via `process.env`.

## Layout
```
frontend/              web app, dev server on :5173 (the preview)
  vite.config.ts       proxies /api -> http://127.0.0.1:4000
  src/main.tsx         React entry
  src/App.tsx          home page (/)
  src/index.css        Tailwind entry
backend/               API on :4000
  src/index.ts         Express app, mounts routers
  src/routes/*.ts      one router per resource
  src/db/schema.ts     tables
  src/db/index.ts      the `db` client
  src/db/migrate.ts    applies drizzle/ (run by `npm run migrate`)
  drizzle/             generated SQL migrations, never edit by hand
  drizzle.config.ts    drizzle-kit config
db/                    database dumps (managed by the platform)
```

## Rules
- Both services are already running with hot reload; never start another server.
- The frontend calls relative `/api/...` URLs only. Never hardcode a host or port.
- Every API route lives under `/api` in `backend/src/routes/`.
- Tables are declared only in `backend/src/db/schema.ts` and queried only through `db` from `backend/src/db/index.ts`.
- Validate request bodies in the route; answer bad input with 400 and `{ "error": "..." }`.
- `server.allowedHosts` in `vite.config.ts` lets the preview load through E2B hostnames. Don't remove it.
- Backend imports use the `.ts` extension (`import { db } from "../db/index.ts"`).
- Add a library only when needed: `cd frontend && npm install <pkg>` or `cd backend && npm install <pkg>`.

## How to
- **Add a page:** create a component in `frontend/src/`, render it from `App.tsx`. There is no router; if you need several URLs, install `react-router` and set routes up in `App.tsx`.
- **Add an API route:** create `backend/src/routes/<name>.ts` exporting an Express `Router`, then `app.use("/api/<name>", router)` in `backend/src/index.ts`.
- **Add or change a table:** edit `backend/src/db/schema.ts`, then run `npx drizzle-kit generate` in `backend/`. Do not run `npm run migrate` and never apply migrations at startup: the host applies new migrations when it checks your work, and asks the user first if one would delete data. Never change the database by hand.

## Tailwind v4
- No `tailwind.config.js` and no `postcss.config.js`. `src/index.css` holds `@import "tailwindcss";`.
- Customize in CSS with `@theme { --color-brand: #...; }`, which yields classes like `bg-brand`.
- Use utility classes in JSX. v4 names: `shadow-xs` (old `shadow-sm`), `rounded-xs`, `outline-hidden`, `bg-linear-to-r`.
- Dark styles (`dark:`) apply under the `dark` class on `<html>`, not the device setting (`@custom-variant dark` in `src/index.css`; keep it). A theme switch sets that class on `<html>` and saves the choice in `localStorage`; to follow the device, read `prefers-color-scheme` once and set the class from it.

## Installed libraries
- Frontend: react, react-dom, vite, @vitejs/plugin-react, tailwindcss, @tailwindcss/vite, typescript.
- Backend: express, drizzle-orm, pg, tsx, drizzle-kit, typescript, @types/express, @types/node, @types/pg.

## Checks
- Check your work: `cd frontend && npm run typecheck`, `cd backend && npm run typecheck`. The host runs the production build when you finish; do not run it yourself.

## Current condition
Keep this section up to date whenever you add or remove a page, route, or table.
- Pages: `/` (notes list and add form).
- Routes: `GET /api/health`, `GET /api/notes` (newest first), `POST /api/notes` (`{ text }`, 1-500 chars).
- Tables: `notes` (`id`, `text`, `created_at`).
