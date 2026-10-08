# 025 — Press response on the sidebar's account button and budget pill

- **Status**: DONE
- **Commit**: 727a267
- **Severity**: LOW
- **Category**: Cohesion & tokens (feedback)
- **Estimated scope**: 1 file, one class constant

## Problem

At the foot of the sidebar, the account button and the budget pill change colour on hover but do not answer a press, while every `Button` in the app dips.

```tsx
// frontend/components/layout/SidebarAccount.tsx:17 — current
const PILL =
    "flex h-9 cursor-pointer items-center rounded-[8px] border border-border bg-surface-2 text-[12.5px] [transition:background-color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-1";
```

`PILL` is used by the account `DropdownMenuTrigger` (`:40`) and the budget `PopoverTrigger` (`:97`).

## Target

Both dip to `scale: 0.97` on press over 100ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`); no dip under reduced motion.

```tsx
// target
const PILL =
    "flex h-9 cursor-pointer items-center rounded-[8px] border border-border bg-surface-2 text-[12.5px] [transition:background-color_130ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-1";
```

## Repo conventions to follow

- Exemplar: `frontend/components/ui/button.tsx:18` — the `ghost` variant: `[transition:background-color_130ms_ease,color_130ms_ease,scale_100ms_var(--ease-out)]` with `press = "[&:not(:disabled):active]:scale-[0.97] motion-reduce:[&:not(:disabled):active]:scale-100"`.
- Plan 014 made the same change on the tab close button and Download.

## Steps

1. Replace the `PILL` constant in `frontend/components/layout/SidebarAccount.tsx` with the target string.

## Boundaries

- Do NOT change the triggers, the menu, the popover, sizes or colours.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/layout/SidebarAccount.tsx`, `npx prettier --check components/layout/SidebarAccount.tsx` pass.
- **Feel check**: press and hold the account button, then the budget pill, at the sidebar's foot (desktop and a 390px phone width with the sidebar open).
  - Each dips slightly under the press and springs back within 100ms; the menu or popover still opens.
  - The collapsed sidebar's account icon (transparent background) dips the same way.
  - With reduced motion emulated, neither moves.
- **Done when**: both answer a press like the buttons around them.
