# 019 — Let the plan card's actions and its revise form settle in when they swap

- **Status**: DONE
- **Commit**: 727a267 (the plan card is uncommitted work on `fix/one-loop`; commit it first)
- **Severity**: LOW
- **Category**: Missed opportunities (preventing a jarring change)
- **Estimated scope**: 1 file, 2 class strings

## Problem

On a plan or question card, "Revise plan" swaps the Approve / Revise / Dismiss row for the "What should change?" form in one frame, and "Back to plan" swaps it back the same way.

```tsx
// frontend/components/chat/WorkflowCard.tsx:150 — current
{plan && !revising ? (
    <div className="space-y-3">
        …the Approve / Revise / Dismiss row…
    </div>
) : (
    <form
        className="space-y-3"
        …
```

## Target

Whichever branch mounts settles in: from `opacity: 0` and `translate: 0 0.25rem` to rest, over 180ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`). The leaving branch unmounts at once, so a quick Back / Revise never waits. Reduced motion keeps the fade and drops the movement.

```tsx
// target: the same addition on both roots
<div className="space-y-3 starting:translate-y-1 starting:opacity-0 motion-reduce:starting:translate-y-0 [transition:opacity_180ms_var(--ease-out),translate_180ms_var(--ease-out)]">
<form className="space-y-3 starting:translate-y-1 starting:opacity-0 motion-reduce:starting:translate-y-0 [transition:opacity_180ms_var(--ease-out),translate_180ms_var(--ease-out)]" …>
```

## Repo conventions to follow

- `starting:` is Tailwind v4's `@starting-style` variant; it animates an element's first frame without JavaScript.
- Exemplar: `frontend/components/chat/ChatInput.tsx` — the Stop button: `starting:scale-[0.97] starting:opacity-0 motion-reduce:starting:scale-100 [transition:…opacity_120ms_var(--ease-out),scale_120ms_var(--ease-out)]`.

## Steps

1. In `frontend/components/chat/WorkflowCard.tsx`, on the `<div className="space-y-3">` directly after `{plan && !revising ? (`, append the target classes.
2. On the `<form className="space-y-3"` in the other branch, append the same classes.

## Boundaries

- Motion classes only. Do NOT change markup, buttons, labels or the `data-disclosure` wrapper above.
- Do NOT add an exit animation.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/chat/WorkflowCard.tsx`, `npx prettier --check components/chat/WorkflowCard.tsx` pass.
- **Feel check**: on a pending plan card, press "Revise plan", then "Back to plan", several times, also quickly.
  - Each swap rises 4px into place and fades in; nothing slides out.
  - Fast switching never stalls or flickers.
  - On a question card (no plan), "Dismiss" and "Continue" behave as before.
  - With reduced motion emulated, the swap fades without moving.
- **Done when**: the swap no longer lands in one frame.
