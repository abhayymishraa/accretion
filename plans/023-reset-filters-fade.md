# 023 — Fade in "Reset filters" when the first filter is set

- **Status**: DONE
- **Commit**: 727a267
- **Severity**: LOW
- **Category**: Missed opportunities (preventing a jarring change)
- **Estimated scope**: 1 file, one class string

## Problem

On the projects page, "Reset filters" appears in one frame beside the project count as soon as a search or filter changes.

```tsx
// frontend/components/projects/ProjectCollection.tsx:140 — current
{changed && (
    <Button variant="utility" onClick={resetFilters}>
        Reset filters
    </Button>
)}
```

## Target

It fades in from `opacity: 0` over 150ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`). Opacity only, so the count beside it does not move. It leaves at once when pressed, because the user asked for that.

```tsx
// target
<Button
    variant="utility"
    className="starting:opacity-0 [transition:opacity_150ms_var(--ease-out),background-color_130ms_ease,color_130ms_ease,scale_100ms_var(--ease-out)]"
    onClick={resetFilters}
>
```

## Repo conventions to follow

- The `utility` variant in `frontend/components/ui/button.tsx` already transitions `background-color 130ms ease, color 130ms ease, scale 100ms var(--ease-out)` for its press dip; the target keeps those and adds opacity. Check the variant's current transition string first and keep its values exactly.

## Steps

1. Read the `utility` variant's transition in `frontend/components/ui/button.tsx`.
2. Add `className` to the "Reset filters" Button: `starting:opacity-0` plus a `[transition:…]` that lists the variant's own transitions and `opacity_150ms_var(--ease-out)`.

## Boundaries

- Do NOT edit `button.tsx`. Do NOT add an exit animation.
- If the variant's transition differs from the values above, use its real values and add only opacity.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/projects/ProjectCollection.tsx`, `npx prettier --check components/projects/ProjectCollection.tsx` pass.
- **Feel check**: on the projects page, type a search letter, then press "Reset filters".
  - The button fades in; the count beside it does not move.
  - Its press dip still works.
  - With reduced motion emulated, the fade is acceptable (opacity only).
- **Done when**: "Reset filters" no longer appears in one frame.
