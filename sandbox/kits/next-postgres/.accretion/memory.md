# Next.js + Postgres app

## Stack
- Next.js 16.3.6 (App Router, Turbopack), React 19.3.0, TypeScript 7.0.2
- Tailwind CSS 4.3.3 via `@tailwindcss/postcss`
- Postgres, reached through `DATABASE_URL` (set in `.env`). Drizzle ORM 0.45.3 + drizzle-kit 0.31.11, pg (node-postgres) 8.23.0
- One service on port 3000. No other libraries are installed; do not add one when a few lines of code will do.

Next.js 16 differs from older versions you may know. Before using a Next.js API, read its guide in `node_modules/next/dist/docs/`.

The dev server is already running with hot reload; never start another.

## Layout
- `app/**/page.tsx`: pages. `app/layout.tsx`: shared shell. `app/globals.css`: global styles.
- `app/api/**/route.ts`: route handlers (export `GET`, `POST`, ...; return `Response.json(...)`).
- `db/schema.ts`: tables. `db/index.ts`: the `db` client (server only). `db/migrate.ts`: applies `drizzle/` (run by `npm run migrate`). `drizzle/`: generated SQL migrations, never edit by hand.
- Import with the `@/` alias and the `.ts` extension: `import { db } from "@/db/index.ts"`.

## Conventions
- Components are server components by default. Add `"use client"` only for state, effects or event handlers.
- Only server code (route handlers, server components) may import `@/db/*`. Client components call the API with `fetch`.
- Validate request bodies in the route handler; answer bad input with status 400 and `{ error }`.
- Tailwind v4: `app/globals.css` starts with `@import "tailwindcss"`. There is no `tailwind.config.js`; customise with `@theme` in CSS. Do not add v3 config or `@tailwind` directives.
- Dark styles (`dark:`) apply under the `dark` class on `<html>`, not the device setting (`@custom-variant dark` in `app/globals.css`; keep it). For a theme switch install `next-themes` and wrap the app in `<ThemeProvider attribute="class" defaultTheme="system" enableSystem>`, with `suppressHydrationWarning` on `<html>`.
- `next.config.ts` sets `allowedDevOrigins` for the E2B preview hostnames. Don't remove it: the preview breaks without it. Keep `agentRules: false` too.

## How to
- Add a page: create `app/<name>/page.tsx` exporting a default component.
- Add an API route: create `app/api/<name>/route.ts` exporting `GET`/`POST`.
- Add or change a table: edit `db/schema.ts`, then run `npx drizzle-kit generate`. Do not run `npm run migrate`: the host applies new migrations when it checks your work, and asks the user first if one would delete data. Never change the database by hand.

## Checks
- Check your work: `npm run typecheck`. The host runs the production build when you finish; do not run it yourself.

## Current condition
Keep this section up to date whenever you add or remove a page, route or table.
- Pages: `/` (lists notes, form to add one)
- Routes: `GET /api/health`, `GET /api/notes` (newest first), `POST /api/notes` (`{text}`, 1..500 chars)
- Tables: `notes` (id, text, created_at)
