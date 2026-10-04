# 005 — Slide cards into a deleted project's place

- **Status**: DONE
- **Commit**: ad83e1f plus the uncommitted project-covers change (feat/project-covers)
- **Severity**: LOW
- **Category**: Missed opportunities (spatial consistency)
- **Estimated scope**: 3 files, about 35 changed lines

## Problem

`deleteProject` in `frontend/hooks/projects/useProjectCollection.ts` filtered the project out in
one frame: the card vanished and every later card jumped into the gap. Rare action, eligible.

## Target

- Each card (`ProjectCard.tsx` `<article>`) has `viewTransitionName: project-<id>` and
  `viewTransitionClass: "project"`.
- The removal (list filter plus closing the dialog) runs in
  `document.startViewTransition(() => flushSync(remove))` when the API exists and reduced motion
  is off; otherwise as before.
- `frontend/app/globals.css` (global: view-transition pseudo-elements cannot live in a CSS module):

```css
::view-transition-group(*.project) { animation-duration: 260ms; animation-timing-function: var(--ease-out); }
::view-transition-old(*.project):only-child { animation: project-out 180ms var(--ease-out) both; }
@keyframes project-out { to { opacity: 0; transform: scale(0.97); } }
```

The dialog is not named, so it cross-fades out with the root snapshot instead of its own
`dialog-out` keyframes.

## Verification

- Chrome and Safari 18.2+: delete the second of four cards; three slide, one fades.
- Firefox or older Safari: removal is instant, no errors.
- With the project sheet open over the page, names repeat; the browser skips the transition and
  the update still runs.
- Feel-check in DevTools Animations at 10% speed.
