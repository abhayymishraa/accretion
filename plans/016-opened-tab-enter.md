# 016 — Let a newly opened workspace tab settle into the toolbar

- **Status**: TODO
- **Commit**: dd8207d (the file has uncommitted changes on branch `feat/mcp-servers`; line numbers below are from that working tree)
- **Severity**: LOW
- **Category**: Missed opportunities (spatial consistency)
- **Estimated scope**: 1 file, 1 class string

## Problem

A tab opened from the toolbar's "+" menu (Code, Skills, Connectors) appears in one frame, at the moment the panel switches to it, so nothing ties the new tab to the action.

```tsx
// frontend/components/chat/PreviewToolbar.tsx:90 — current
<span key={tab} className="flex items-center">
```

## Target

On mount only, the tab fades and settles from `scale: 0.97` over 150ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`), growing from its left edge. Closing stays instant. Under reduced motion it only fades.

```tsx
<span
    key={tab}
    className="flex origin-left items-center [transition:opacity_150ms_var(--ease-out),scale_150ms_var(--ease-out)] starting:scale-[0.97] starting:opacity-0 motion-reduce:starting:scale-100"
>
```

## Repo conventions to follow

- `starting:` is Tailwind's `@starting-style` variant. Exemplar: `frontend/components/chat/ToolList.tsx:42` — `[transition:opacity_200ms_var(--ease-out),translate_200ms_var(--ease-out)] starting:translate-y-1 starting:opacity-0 motion-reduce:starting:translate-y-0`.
- Tailwind v4's `scale-*` writes the `scale` property, so the transition lists `scale`, not `transform`.

## Steps

1. In `frontend/components/chat/PreviewToolbar.tsx` line 90, replace `className="flex items-center"` on the `<span key={tab}>` with the className in Target.

## Boundaries

- Do NOT add an exit animation. Do NOT change the tab `Button` or the close button inside the span.
- If line 90 does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`, `npx eslint components/chat/PreviewToolbar.tsx`, `npx prettier --check components/chat/PreviewToolbar.tsx` pass.
- **Feel check**: in a project's workspace, open Code, Skills and Connectors from "+", then close them.
  - Each new tab fades and grows slightly from its left edge in 150ms; the tabs to its left do not move.
  - Reloading the page with tabs open: `@starting-style` also plays on first render, so the open tabs fade once. Confirm it reads as part of the page load; if it reads as noise, STOP and report.
  - Closing a tab removes it at once.
  - With reduced motion emulated, a new tab only fades.
- **Done when**: an opened tab enters with the 150ms settle and leaves instantly.
