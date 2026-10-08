# 024 — Fade the workspace Skills tab's content in over its skeleton

- **Status**: DONE
- **Commit**: 727a267
- **Severity**: LOW
- **Category**: Cohesion & tokens (entry)
- **Estimated scope**: 1 file, one fragment becomes a div

## Problem

In a project's workspace, the Skills tab swaps its five skeleton rows for the skill sections in one frame. The pages beside it fade their content in over the skeleton (the Projects and Profile pages), and the Connectors tab's rows fade in one after another.

```tsx
// frontend/components/skills/ProjectSkillsPanel.tsx:155 — current
) : skills ? (
    <>
        <Section
            title="In this project"
        …
        )}
    </>
) : (
    <div className="flex flex-col gap-1.5 p-4" aria-label="Loading skills">
```

## Target

The loaded branch is a `div` with the shared `data-loaded-in` attribute, so it fades in over 180ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`) from `opacity: 0` when it replaces the skeleton. No movement; under reduced motion it appears at once.

```tsx
// target
) : skills ? (
    <div data-loaded-in="">
        <Section
        …
        )}
    </div>
) : (
```

## Repo conventions to follow

- The rule lives in `frontend/app/globals.css`, inside `@media (prefers-reduced-motion: no-preference)`: `[data-loaded-in] { animation: content-in 180ms var(--ease-out) both; }` with `@keyframes content-in { from { opacity: 0; } }`.
- Exemplar: `frontend/components/projects/ProjectsPage.tsx:44` — `<div data-loaded-in="">` around content that replaces a skeleton.

## Steps

1. In `frontend/components/skills/ProjectSkillsPanel.tsx`, in the `) : skills ? (` branch, replace the opening `<>` with `<div data-loaded-in="">` and its matching closing `</>` (just before `) : (` and the "Loading skills" skeleton) with `</div>`.

## Boundaries

- Only that fragment. Do NOT touch the error, "No skills match" or skeleton branches, or the `Section` component.
- Do NOT add CSS.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/skills/ProjectSkillsPanel.tsx`, `npx prettier --check components/skills/ProjectSkillsPanel.tsx` pass.
- **Feel check**: in a project's workspace, open the Skills tab (from "+"), and reload the page with it open.
  - The sections fade in over the skeleton in about 180ms; nothing moves.
  - Typing in its search box does not replay the fade (the div stays mounted); clearing a "No skills match" search fades the list back in, which is fine.
  - With reduced motion emulated, the content appears at once.
- **Done when**: the Skills tab loads like the Projects page and the Connectors tab.
