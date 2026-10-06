# 014 — Press response on the tab close button and Download

- **Status**: DONE
- **Commit**: dd8207d
- **Severity**: LOW
- **Category**: Cohesion & tokens (feedback)
- **Estimated scope**: 2 files, 2 class strings

## Problem

Two small buttons give no response to a press, while the buttons beside them dip to 0.97.

```tsx
// frontend/components/chat/PreviewToolbar.tsx:104 — the tab close button (current)
className="grid size-6 cursor-pointer place-items-center rounded-[6px] text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground"

// frontend/components/files/FileViewer.tsx:85 — Download (current)
className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-[6px] bg-surface-2 px-2.5 text-[11.5px] text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] pointer-fine:hover:bg-accent pointer-fine:hover:text-accent-foreground"
```

## Target

Both dip to `scale: 0.97` on press over 100ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`); no dip under reduced motion. The existing transitions stay; `scale` is added to them.

## Repo conventions to follow

- Exemplar: `frontend/components/ui/button.tsx:17-18` — `press = "[&:not(:disabled):active]:scale-[0.97] motion-reduce:[&:not(:disabled):active]:scale-100"` and `[transition:background-color_130ms_ease,color_130ms_ease,scale_100ms_var(--ease-out)]`.

## Steps

1. In both class strings, change `[transition:background-color_130ms_ease,color_130ms_ease]` to `[transition:background-color_130ms_ease,color_130ms_ease,scale_100ms_var(--ease-out)]`.
2. In both, add `active:scale-[0.97] motion-reduce:active:scale-100` after it.

## Boundaries

- Do NOT replace these with the `Button` component, and do NOT change sizes or colors.
- If an excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`, `npx eslint components/chat/PreviewToolbar.tsx components/files/FileViewer.tsx`, `npx prettier --check` on both pass.
- **Feel check**: open a Code tab and press its ✕; open a file and press Download (or hold the press without releasing).
  - Each dips like the tab button beside it, and springs back within 100ms on release.
  - On a phone, the dip is visible under the finger.
  - With reduced motion emulated, neither moves.
- **Done when**: both buttons answer a press like their neighbours.
