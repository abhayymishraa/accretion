# 007 — First-run empty state rises in

- **Status**: DONE
- **Commit**: ad83e1f plus the uncommitted project-covers change (feat/project-covers)
- **Severity**: LOW
- **Category**: Missed opportunities (delight, first-time only)
- **Estimated scope**: 2 files, about 30 changed lines

## Problem

A new user's projects page swapped the skeleton for "A blank canvas, just for you." in one frame.
The same container shows "No matching projects." while filtering, which must stay still.

## Target

In `frontend/components/projects/ProjectCollection.tsx`, add `styles.firstRun` to the empty-state
container only when `projects.length === 0`. In `project-shelf.module.css`:

```css
.firstRun {
    transition: opacity 260ms var(--ease-out), translate 260ms var(--ease-out);
    @starting-style { opacity: 0; translate: 0 8px; }
}
@media (prefers-reduced-motion: reduce) {
    .firstRun { transition-property: opacity; }
}
```

Reduced motion keeps the fade; the 8px rise snaps, so nothing moves.

## Verification

- New account: the empty state fades and rises 8px once after the skeleton.
- Account with projects, search for nonsense: "No matching projects." appears with no motion.
