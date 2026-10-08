# 027 — Finish the landing strips' name reveal before the strips are fully on screen

- **Status**: DONE
- **Commit**: edf1d47 (plus the uncommitted `Strip` rows on `fix/landing-full-stack-copy`)
- **Severity**: LOW
- **Category**: Easing & duration (scroll-linked stagger)
- **Estimated scope**: 1 file, 2 numeric edits

## Problem

Under "How it builds", two `Strip` rows list names one by one: "Any stack you name" (9 names) and "Coming next" (4 names). Each name is a `.reveal` element whose scroll range is offset by its `--i`:

```css
/* frontend/components/landing/landing.module.css:153-158 — current, do not edit */
@supports (animation-timeline: view()) {
    .reveal {
        animation-timeline: view();
        animation-range-start: entry calc(10% + var(--i, 0) * 5%);
        animation-range-end: entry calc(70% + var(--i, 0) * 5%);
    }
}
```

The rows set `--i` like this:

```tsx
/* frontend/components/landing/BuildPlate.tsx:63 — current */
style={{ ["--i" as string]: at + 0.3 + index * 0.3 }}

/* frontend/components/landing/BuildPlate.tsx:144-145 — current */
<Strip label="Any stack you name" items={STACKS} at={3} border />
<Strip label="Coming next" items={NEXT} at={3 + STACKS.length * 0.3} />
```

With a 0.3 step, the last stack name has `--i` 5.7 and ends at `entry 98.5%`; the "Coming next" names reach `--i` 6.9 and end at `entry 104.5%`, past the point where the strip has fully entered the viewport. A visitor who stops scrolling with the strips low on screen sees "Reports" and "Documents" still part-faded, while reading them.

## Target

Every name finishes its fade before `entry 100%`, and the two rows still read as one sequence (stack names first, then "Coming next").

- Step per name: `0.15` (was `0.3`), so `--i = at + 0.15 + index * 0.15`.
- "Coming next" starts at `at={4.5}`.

Resulting ends: last stack name `--i` 4.35, ends `entry 91.75%`; "Coming next" label `--i` 4.5; last "Coming next" name `--i` 5.1, ends `entry 95.5%`.

Keyframe, duration and curve stay as they are: `lp-rise`, `620ms`, `var(--ease-out)` = `cubic-bezier(0.23, 1, 0.32, 1)`.

## Repo conventions to follow

- Stagger on a view timeline lives in `--i`, never in `animation-delay` (the comment at `landing.module.css:146-149` says why).
- Exemplar: the FAQ rows use `index * 0.3` for 6 items (`LandingPage.tsx`, the `QUESTIONS.map`); short lists can keep 0.3, long ones need a smaller step.

## Steps

1. In `frontend/components/landing/BuildPlate.tsx`, inside `Strip`, change
   `style={{ ["--i" as string]: at + 0.3 + index * 0.3 }}`
   to
   `style={{ ["--i" as string]: at + 0.15 + index * 0.15 }}`.
2. In the same file, change
   `<Strip label="Coming next" items={NEXT} at={3 + STACKS.length * 0.3} />`
   to
   `<Strip label="Coming next" items={NEXT} at={4.5} />`.

## Boundaries

- Do NOT touch `landing.module.css`, the `lp-rise` keyframe, or any other `.reveal` user.
- Do NOT change the strips' markup, classes or items.
- Do NOT add dependencies.
- If the code does not match the excerpts above, STOP and report instead of improvising.

## Verification

- **Mechanical**: from `frontend/`, `npx prettier --check components/landing/BuildPlate.tsx`, `npx eslint components/landing/BuildPlate.tsx`, `npx tsc --noEmit -p .`; all pass.
- **Feel check**: open `/` in Chrome (supports `animation-timeline: view()`), scroll slowly until the strips' top border is about two thirds down the viewport, and stop:
  - every name in both rows is fully opaque;
  - names still arrive left to right, stack row before "Coming next";
  - scrolling back up reverses them smoothly (it is scroll-scrubbed, not a one-shot).
  - In DevTools Rendering, set `prefers-reduced-motion: reduce`: all names are visible at once with no movement.
  - At 390px wide the same holds; the rows wrap, the order is unchanged.
- **Done when**: no name in either strip is part-faded once the strip's top border is inside the viewport.
