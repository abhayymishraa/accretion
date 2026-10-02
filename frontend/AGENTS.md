<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Styling rules

- Use Tailwind for layout, spacing, typography, responsive rules, and interaction states.
- Put utilities on their element. Use descendant variants only for structured content or deliberate component overrides.
- Reuse `components/ui` controls. Actions use `Button`; styled links use `buttonVariants`; ordinary form fields use `Input`.
- Extend shared variants for repeated styles. Avoid duplicate control styling across pages.
- Keep theme tokens and base styles in `app/globals.css`. Prefer semantic colors: `bg-card`, `text-muted-foreground`, `border-input`.
- Keep complex artwork, keyframes, masks, and scroll timelines in scoped CSS modules. Use `@layer components` when utilities must override them.
- Keep `app/ember.css` focused on artwork and shared motion behavior. Do not restore global page-layout rules.
- Keep Tailwind class names statically discoverable. Do not construct partial class names at runtime.
- Preserve Ember design, keyboard focus, disabled states, and reduced-motion support.
- Prevent horizontal page overflow. Keep chat viewport-sized with internal scrolling; let long content pages scroll naturally.
- After verification approval, check phone, tablet, desktop, short landscape, and both themes. Include menus, dialogs, and loading/error states.
- Claim performance gains only with measurements. Styling cleanup does not fix repeated API calls or downloads.

## Structure and ownership

Adapted from TryMatcha at `98c030584a1e1e383b58c567e7693e9982e1e04d`. These are repository rules, not runtime design skills.

- `app/` owns Next.js route adapters, metadata, layouts, and global styles. Put page implementation in its feature component; keep the route small. Preserve server components unless client behavior requires a boundary.
- `components/<feature>/` owns rendered UI and local interaction state. Features include `auth`, `chat`, `files`, `landing`, `layout`, `profile`, and `projects`.
- `hooks/<feature>/useName.ts` owns feature orchestration: requests, loading/error state, mutations, subscriptions, and lifecycle cleanup. This is the frontend equivalent of a controller; do not wrap React state in static classes.
- `services/service.<domain>.ts` owns typed HTTP operations. Use the single client in `lib/http/client.ts`; return domain data rather than Axios responses. The one exception is `lib/http/eventStream.ts`, which uses `fetch` because Axios cannot read a streaming body in the browser. Preserve paths, timeout/abort behavior, and response contracts when moving operations.
- `lib/` owns reusable non-rendering logic grouped by concern: auth sessions, HTTP refresh/error handling, chat reduction, file cache/tree helpers, and project filtering/drafts. Use `config/` for public environment configuration and `socket/` for stream event translation.
- `types/<domain>.type.ts` owns contracts shared across features/layers. Keep one-use Props and implementation types beside their owner. Do not introduce circular imports from types to components.
- Keep the session-refresh interceptor centralized. Retain session identity checks, single-flight refresh, file-cache isolation, stream reconnect guards, and preview startup ownership.
- Components call feature hooks; hooks call services. Do not issue HTTP requests from page/view components. ESLint rejects direct service/client/Axios imports there. Do not bypass this with relative imports or `fetch`.
- Import from the owning module with `@/`; use relative imports within a feature when clearer. Avoid catch-all barrels that mix unrelated features or client/server boundaries.

## Names and file size

- Custom React components use PascalCase filenames and component names. Hooks use `useName.ts`; services use `service.domain.ts`; shared types use `domain.type.ts`; ordinary helpers use descriptive camelCase names.
- Next.js reserved filenames (`page.tsx`, `layout.tsx`, `route.ts`) and existing shadcn-style primitives in `components/ui` retain their framework conventions. CSS modules retain descriptive kebab-case names.
- One file owns one cohesive concern. Share an abstraction only when it has real callers; do not create an empty controller/service/type file for every component.
- **Maximum 300 code lines per authored `.ts`/`.tsx` file; 80 for route pages/layouts.** ESLint excludes blank lines and comment-only lines. Generated output and dependency directories are excluded.
- This is a new WebBuilder guardrail: TryMatcha had no enforced word or line cap. We use code lines, not word count, so names and prose cannot distort the limit.
- Split at meaningful boundaries (page/hook, socket/lifecycle, dialog/list, file tree/viewer, artwork layer). Do not compress statements, delete useful comments, or add lint suppressions to fit.
- Keep artwork styles scoped. The TypeScript line cap does not count CSS, documentation, lockfiles, or third-party licenses.

## Formatting and change discipline

- Prettier owns formatting: four spaces, double quotes, semicolons, trailing commas, 100-column print width, LF, and parentheses around arrow parameters.
- Use `npm run format` to format and, with verification approval, `npm run format:check`, `npm run lint`, `npm run typecheck`, and `npm run build` to check.
- Preserve useful rationale, third-party attribution, and behavioral guards. Prefer clear names over comments that merely repeat the code.
- Structural refactors preserve copy, theme, interaction behavior, network frequency, and persistent storage keys. API URLs are not on that list: the backend owns REST naming (see ../AGENTS.md), and when it renames a resource the services in `services/` move with it in the same change. Next.js page routes are unaffected by that rule. Treat functional changes as separate, explicit work.
- Keep the root no-test-suite rule. Do not add test fixtures or test frameworks. Authorized browser smoke checks must not submit a generation request or touch live accounts without scope-specific permission.
- Do not introduce Zustand, React Query, inheritance, a monorepo tool, or a new package manager just because TryMatcha uses it. The existing hooks and npm setup remain the default.
