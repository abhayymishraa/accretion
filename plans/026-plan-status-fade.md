# 026 — Fade in a card's new status when the user answers it

- **Status**: DONE
- **Commit**: 727a267 (the plan card is uncommitted work on `fix/one-loop`; commit it first)
- **Severity**: LOW
- **Category**: Missed opportunities (state indication)
- **Estimated scope**: 1 file, one element
- **Feel-check gate**: this plan has a stop condition; read Verification before starting.

## Problem

After Approve, Revise or Dismiss, the card's status in its top-right corner changes in one frame ("Awaiting approval" becomes "Approved", "Changes requested" or "Dismissed"). It is the only text on the card that confirms the answer was taken.

```tsx
// frontend/components/chat/WorkflowCard.tsx:78 — current
{status && !(question && pending) && <span>{status}</span>}
```

## Target

The new word fades in over 180ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`) from `opacity: 0`. `key={status}` remounts the span on each change, so the shared fade plays on every new word; under reduced motion it changes at once.

```tsx
// target
{status && !(question && pending) && (
    <span key={status} data-loaded-in="">
        {status}
    </span>
)}
```

## Repo conventions to follow

- The shared rule lives in `frontend/app/globals.css`, inside `@media (prefers-reduced-motion: no-preference)`: `[data-loaded-in] { animation: content-in 180ms var(--ease-out) both; }`, `@keyframes content-in { from { opacity: 0; } }`.
- Exemplar: `frontend/components/profile/ProfilePage.tsx:141` — `<span key={message} data-loaded-in>` (plan 013, status messages).

## Steps

1. In `frontend/components/chat/WorkflowCard.tsx`, replace `<span>{status}</span>` (in the line shown above) with `<span key={status} data-loaded-in="">{status}</span>`.

## Boundaries

- One element. Do NOT change the status words or the condition.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/chat/WorkflowCard.tsx`, `npx prettier --check components/chat/WorkflowCard.tsx` pass.
- **Feel check**: open a chat with plan cards, then make a new plan in Plan mode and Dismiss it.
  - On Dismiss, "Dismissed" fades in where "Awaiting approval" was.
  - **Stop condition:** `content-in` also plays when a card first renders, so on a page load every card's status fades in once. Reload a chat with several cards. If that reads as noise rather than as part of the page load, revert this change, mark the plan DROPPED, and report.
  - With reduced motion emulated, the word changes at once.
- **Done when**: the answered status fades in, and a page load does not look noisy.
