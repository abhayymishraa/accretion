# 003 — Press response on project cards

- **Status**: DONE
- **Commit**: ad83e1f plus the uncommitted project-covers change (feat/project-covers)
- **Severity**: MEDIUM
- **Category**: Missed opportunities (feedback)
- **Estimated scope**: 1 file, about 20 changed lines

## Problem

The project card link (`frontend/components/projects/ProjectCard.tsx`, class `styles.card`) lifts
`translateY(-2px)` on hover, gated to `(hover: hover) and (pointer: fine)`. A phone has no hover,
so a tap shows nothing until the next page renders. Most users are on phones.

## Target

In `frontend/components/projects/project-shelf.module.css`, inside the existing
`@media (prefers-reduced-motion: no-preference)` block and **after** the hover rule (equal
specificity; the later rule wins, so a mouse press is not overridden by the lift):

```css
.card:active {
    transform: scale(0.985);
    transition-duration: 140ms;
}
```

Matches the app's `control` button press (`frontend/components/ui/button.tsx:6`: `scale(0.985)`,
`140ms var(--ease-out)`, where `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`). The release uses
the card's own `transform 220ms var(--ease-out)`.

Reduced motion keeps feedback without movement:

```css
@media (prefers-reduced-motion: reduce) {
    .card { transition: opacity 100ms ease; }
    .card:active { opacity: 0.92; }
}
```

## Verification

- iOS only applies `:active` when the element has a touch listener; Next's `Link` adds one for
  prefetch. Check on a real phone and inside an in-app webview (Instagram, Gmail).
- Desktop: hover lifts, press scales, release returns without a jump.
