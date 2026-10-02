# WebBuilder frontend

Next.js App Router frontend for WebBuilder. Uses npm, React, Tailwind, and the existing Ember theme. Backend contracts and generation remain separate from the frontend.

## Development

Run dependencies with the root Compose workflow, then start the frontend separately:

```sh
npm install
npm run dev
```

The app opens at `http://localhost:3000`. Public API settings are read by `config/env.ts`; preserve the existing `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_BASE_URL` deployment configuration. Never put private credentials in public environment variables.

## Where code belongs

- `app/`: thin route adapters, metadata, layouts, global CSS.
- `components/<feature>/`: screens, presentation, and local UI interactions.
- `hooks/<feature>/`: feature state, requests, mutations, and subscriptions.
- `services/`: typed endpoint operations through `lib/http/client.ts`.
- `types/`: shared contracts, named `domain.type.ts`.
- `lib/`: session handling, file caching, chat reduction, and project helpers.
- `socket/`: incoming event handling.

See [the frontend rules](AGENTS.md) and [architecture/source evidence](../docs/frontend-architecture.md). The structure adapts TryMatcha's separation of responsibilities without introducing its package manager or state libraries.

Custom components use PascalCase filenames, hooks use `useName.ts`, and services use `service.domain.ts`. Next route filenames and shared UI primitive filenames retain their framework conventions. Authored TypeScript files are capped at 300 code lines; route pages/layouts at 80. Blank lines and comment-only lines do not count.

## Formatting and verification

```sh
npm run format
npm run format:check
npm run lint
npm run typecheck
npm run build
```

The repository requires explicit approval before verification. There is no test suite. Browser smoke checks must not silently submit generation requests. See the architecture document for the latest refactor's validation scope.

## Styling

Preserve the Ember dark/light palette and system Helvetica Neue / Helvetica / Arial stack. No runtime font download is needed.

- `app/globals.css` owns theme tokens and base styles. Prefer semantic utilities such as `bg-card`, `text-muted-foreground`, and `border-input`.
- Use shared `Button`, `buttonVariants`, and `Input` primitives. Keep repeated control styles in shared variants.
- Use Tailwind for layout, responsive behavior, typography, spacing, and interaction states. Class names must remain statically discoverable.
- Keep illustration geometry, keyframes, masks, and scroll timelines in scoped CSS modules. `app/ember.css` contains shared artwork/motion, not a parallel page-layout system.
- Preserve focus visibility, reduced-motion behavior, disabled states, and existing license attribution.
- Chat uses a viewport-sized shell and internal scroll regions. Longer content pages can scroll naturally.

The standalone profile study remains at `/prototypes/profile`; its simulated account controls are isolated from real account services.
