# WebBuilder React starter

React TypeScript/TSX and Vite, with Tailwind CSS v4 already connected. Edit
`src/pages/Home.tsx`; add routes in `src/App.tsx` only when needed.
`src/main.tsx` imports the global stylesheet. Keep that entry point intact.
Use `.tsx` for React components and `.ts` for hooks, services and helpers.
Keep strict type checking enabled; type props and data boundaries instead of
using `any` or suppression comments to bypass errors.

## Installed tools

| Purpose              | Package                    | Pinned version |
| -------------------- | -------------------------- | -------------- |
| Runtime              | Node LTS                   | 24.21.0        |
| UI                   | React / React DOM          | 19.3.0         |
| Type checking        | TypeScript                 | 7.0.2          |
| React types          | @types/react / react-dom   | 19.3.0         |
| Node types           | @types/node                | 24.13.5        |
| Dev server and build | Vite / React plugin        | 8.3.0 / 6.1.1  |
| Styling              | Tailwind CSS / Vite plugin | 4.3.3          |
| Routing              | react-router-dom           | 7.18.3         |
| Icons                | react-icons                | 5.7.0          |
| Optional animation   | motion                     | 13.2.0         |
| Lint                 | oxlint                     | 1.82.0         |

Use `npm ci` to reproduce the lockfile, `npm run lint` for lint checks,
and `npm run typecheck` for TypeScript checks. `npm run build` runs type checking
before creating the production bundle; Vite alone only transpiles TypeScript.
The hosted workspace already
runs Vite at port 5173; do not start another server there. To run a downloaded
project locally, use `npm run dev`.

## Styling conventions

Keep `@import "tailwindcss"` at the top of `src/index.css`. This is Tailwind v4:
do not add v3 `@tailwind` directives, a v3 config, or a second PostCSS pipeline.
Keep custom element defaults inside `@layer base` so utility classes can win.
Use complete, statically discoverable class names, not constructed fragments.

The starter supplies neutral `bg-background`, `text-foreground`, `bg-surface`,
`text-muted-foreground`, `bg-primary`, `text-primary-foreground`, `border-border`
and `ring-ring` tokens. Change their values to match the requested design.
The `.dark` class on `<html>` activates the dark palette and `dark:` utilities;
no theme-switch UI or persistence is imposed on generated apps.

Use Tailwind for layout, spacing, typography and states. Keep complex custom
artwork in scoped CSS. Preserve visible keyboard focus. Use `motion-reduce:`
or media queries for CSS motion. Do not hide page overflow to conceal layout
bugs, and keep controls usable on narrow screens.

## Animation and icons

Motion is preinstalled but not imported by the starter. For requested complex
animation, import from `motion/react`, not an assumed `framer-motion` package:

```tsx
import { MotionConfig, motion } from "motion/react";

<MotionConfig reducedMotion="user">
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
    Your content
  </motion.div>
</MotionConfig>;
```

`reducedMotion="user"` suppresses transform/layout animation, not every opacity
transition. Use `useReducedMotion` to disable other distracting effects when
needed. Simple hover/focus feedback usually needs only CSS.

Import named icons from one React Icons family, for example `FiArrowRight`
from `react-icons/fi`. Label icon-only controls. Install missing UI kits, charts,
3D tools, or state libraries only when a requested feature needs them.

## Template maintenance

Stable versions were resolved from the npm registry and Node release index on
2026-09-14; TypeScript and type dependencies were added on 2026-09-16.
Application and browser-tool dependencies have separate lockfiles.
Playwright 1.63.0 and Chromium live outside the app at `/opt/webbuilder-checks`
and `/opt/pw-browsers`; they do not enter generated application bundles.

For a release, review current stable versions, update exact manifest versions,
regenerate both lockfiles, and run lint/build plus desktop/mobile browser checks
with approval. From the repository root, build the single `sandbox/e2b.Dockerfile`
using the pinned native E2B CLI:

```bash
make template-build TEMPLATE_NAME=webbuilder-react-design-20260917-1
```

Authenticate the CLI or export `E2B_API_KEY` first; this target does not read `.env`.
Choose a fresh release name, wait for build success, and record its logged Build ID.
The Makefile preserves the Vite start command, HTTP-200 readiness check, 1 CPU,
and 1024 MB memory. Each readiness request has a 2-second connect timeout and a
5-second total timeout. The build requests 2048 MiB of free disk space after
installation; this is a best-effort target, not a disk quota or guarantee.
It does not change backend environments.

Smoke-check an approved disposable sandbox, then configure staging's private
`E2B_TEMPLATE_ID` as `<release-name>:<build-UUID>`. After staging validation, use
that same exact reference in production and restart the backend. Keep the previous
reference for rollback. Do not resolve `latest` during user runs. Node tags and
Debian system packages are not digest locked, so the entire operating-system image
is not bit-for-bit reproducible.

Existing saved projects retain their recorded template IDs and package files.
They are not automatically upgraded. No generation-speed or design-quality
improvement is claimed without representative generation measurements.

The minimal hooks/Fast Refresh lint rules follow the published create-vite
9.2.1 React preset. No test suite is bundled, per repository policy.
