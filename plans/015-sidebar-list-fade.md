# 015 — Fade the sidebar's project list with the collapse

- **Status**: DONE
- **Commit**: dd8207d (the file has uncommitted changes on branch `feat/mcp-servers`; line numbers below are from that working tree)
- **Severity**: LOW
- **Category**: Missed opportunities (preventing a jarring change)
- **Estimated scope**: 1 file, 1 class string

## Problem

The sidebar's width animates over 200ms, but its project list switches visibility in one frame. On collapse the list vanishes at once; on expand it shows at once inside a column that is still narrow, so truncated labels are visible while the width grows.

```tsx
// frontend/components/layout/WorkspaceSidebar.tsx:127 — current
<div className="-mx-1 min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 pt-2 group-data-[collapsed=true]/sidebar:invisible group-data-[collapsed=true]/sidebar:overflow-hidden">

// frontend/components/layout/WorkspaceSidebar.tsx:41 — the width transition it should keep pace with
[transition:width_200ms_var(--ease-out)] … motion-reduce:[transition:none] data-[resizing]:[transition:none]
```

## Target

The list fades: opacity 1 → 0 over 150ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`). `visibility` transitions with it, so on collapse the list stays visible until the fade ends and on expand it becomes visible at once and fades in. `invisible` stays: focus and screen readers must still leave a collapsed list. No transition under reduced motion, matching the width.

```tsx
<div className="-mx-1 min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 pt-2 [transition:opacity_150ms_var(--ease-out),visibility_150ms] motion-reduce:[transition:none] group-data-[collapsed=true]/sidebar:invisible group-data-[collapsed=true]/sidebar:opacity-0 group-data-[collapsed=true]/sidebar:overflow-hidden">
```

## Repo conventions to follow

- Easing token: `frontend/app/globals.css:144` `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`.
- Exemplar: the sidebar's own width transition at `WorkspaceSidebar.tsx:41` (same token, same `motion-reduce:[transition:none]` form).

## Steps

1. In `frontend/components/layout/WorkspaceSidebar.tsx` line 127, replace the `className` with the one in Target. The added classes are `[transition:opacity_150ms_var(--ease-out),visibility_150ms]`, `motion-reduce:[transition:none]` and `group-data-[collapsed=true]/sidebar:opacity-0`.

## Boundaries

- Do NOT change the labels (`LABEL`, `sr-only`), the brand text, or the width transition.
- Do NOT remove `invisible`.
- If line 127 does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`, `npx eslint components/layout/WorkspaceSidebar.tsx`, `npx prettier --check components/layout/WorkspaceSidebar.tsx` pass.
- **Feel check**: on a desktop-width window, press the logo to collapse and expand the sidebar several times.
  - Collapsing: the list fades out within the width's 200ms; no clipped project names show in the narrow strip.
  - Expanding: the list fades in as the column widens. At 10% playback, judge whether names clipped in the first frames still read as wrong; if they do, STOP and report rather than adding a delay.
  - Dragging the sidebar edge (`data-resizing`) is unaffected.
  - Tab through a collapsed sidebar: no project row takes focus.
  - With reduced motion emulated, the list switches at once, as the width does.
- **Done when**: the list never switches visibility mid-width-animation without a fade.
