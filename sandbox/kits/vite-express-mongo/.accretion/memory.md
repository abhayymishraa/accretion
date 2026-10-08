# React + Express + MongoDB

## Stack
- Frontend: Vite 8, React 19, TypeScript 7, Tailwind CSS 4 (`@tailwindcss/vite`).
- Backend: Express 5, official `mongodb` driver 7 (no ORM), TypeScript run by `tsx` 4.
- Database: MongoDB 8 at `MONGO_URL` (from `.env`). Secrets: `APP_SECRET` in `.env`, read via `process.env`.

## Layout
```
frontend/            web app, dev server on :5173 (the preview)
  vite.config.ts     proxies /api -> http://127.0.0.1:4000
  src/main.tsx       React entry
  src/App.tsx        home page (/)
  src/index.css      Tailwind entry
backend/             API on :4000
  src/index.ts       Express app, mounts routers
  src/db.ts          Mongo client, collections, migrate()
  src/routes/*.ts    one router per resource
db/                  database dumps (managed by the platform)
```

## Rules
- Both services are already running with hot reload; never start another server.
- The frontend calls relative `/api/...` URLs only. Never hardcode a host or port.
- Every API route lives under `/api` in `backend/src/routes/`.
- Collections are declared and accessed only through `backend/src/db.ts`.
- Validate request bodies in the route; answer bad input with 400 and `{ "error": "..." }`.
- `server.allowedHosts` in `vite.config.ts` lets the preview load through E2B hostnames. Don't remove it.
- Backend imports use the `.ts` extension (`import { notes } from "../db.ts"`).
- Add a library only when needed: `cd frontend && npm install <pkg>` or `cd backend && npm install <pkg>`.

## How to
- **Add a page:** create a component in `frontend/src/`, render it from `App.tsx`. There is no router; if you need several URLs, install `react-router` and set routes up in `App.tsx`.
- **Add an API route:** create `backend/src/routes/<name>.ts` exporting an Express `Router`, then `app.use("/api/<name>", router)` in `backend/src/index.ts`.
- **Add a collection or index:** in `db.ts`, add a type and `export const things = db.collection<Thing>("things")`, then add its `createIndex` calls to `migrate()`. The host runs `npm run migrate` when it checks your work (do not run it yourself, and never call `migrate()` at startup); it must stay idempotent.

## Tailwind v4
- No `tailwind.config.js` and no `postcss.config.js`. `src/index.css` holds `@import "tailwindcss";`.
- Customize in CSS with `@theme { --color-brand: #...; }`, which yields classes like `bg-brand`.
- Use utility classes in JSX. v4 names: `shadow-xs` (old `shadow-sm`), `rounded-xs`, `outline-hidden`, `bg-linear-to-r`.
- Dark styles (`dark:`) apply under the `dark` class on `<html>`, not the device setting (`@custom-variant dark` in `src/index.css`; keep it). A theme switch sets that class on `<html>` and saves the choice in `localStorage`; to follow the device, read `prefers-color-scheme` once and set the class from it.

## Installed libraries
- Frontend: react, react-dom, vite, @vitejs/plugin-react, tailwindcss, @tailwindcss/vite, typescript.
- Backend: express, mongodb, tsx, typescript, @types/express, @types/node.

## Checks
- Check your work: `cd frontend && npm run typecheck`, `cd backend && npm run typecheck`. The host runs the production build when you finish; do not run it yourself.

## Current condition
Keep this section up to date whenever you add or remove a page, route, or collection.
- Pages: `/` (notes list and add form).
- Routes: `GET /api/health`, `GET /api/notes` (newest first), `POST /api/notes` (`{ text }`, 1-500 chars).
- Collections: `notes` (`text`, `createdAt`; index on `createdAt`).
