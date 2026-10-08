# 018 — Open the plan card's technical details on the shared disclosure motion

- **Status**: DONE
- **Commit**: 727a267 (the plan card is uncommitted work on `fix/one-loop`; commit it first)
- **Severity**: LOW
- **Category**: Missed opportunities (state indication)
- **Estimated scope**: 1 file, one wrapper

## Problem

On a plan card, "Technical details" mounts the builder's part of the plan in one frame, and the card jumps to its full height. Hiding it removes it in one frame.

```tsx
// frontend/components/chat/PlanBody.tsx:47 — current
{open && (
    <MessageContent
        content={technical}
        className="text-[13.5px] text-muted-foreground [&_li:has(input)]:list-none [&_li:has(input)]:-ml-5 [&_input]:mr-2 [&_input]:size-3.5 [&_input]:translate-y-[2px] [&_input]:accent-foreground"
    />
)}
```

## Target

The technical part is always rendered, inside the app's shared disclosure. Opening grows its height over 260ms and fades it in over 180ms, both `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`); closing runs the same in reverse. Reduced motion opens and closes it at once (the shared rule is inside `prefers-reduced-motion: no-preference`).

```tsx
// target
<div data-disclosure={open ? "open" : ""}>
    <MessageContent
        content={technical}
        className="text-[13.5px] text-muted-foreground [&_li:has(input)]:list-none [&_li:has(input)]:-ml-5 [&_input]:mr-2 [&_input]:size-3.5 [&_input]:translate-y-[2px] [&_input]:accent-foreground"
    />
</div>
```

## Repo conventions to follow

- The rule already exists in `frontend/app/globals.css` (`[data-disclosure]`: `display: none`; `[data-disclosure="open"]`: `display: block`; inside the motion query `block-size 260ms var(--ease-out), opacity 180ms var(--ease-out), display 260ms allow-discrete` with `@starting-style { block-size: 0; opacity: 0; }`). Height to `auto` works because `globals.css:154` sets `interpolate-size: allow-keywords`.
- Exemplar: `frontend/components/chat/WorkflowCard.tsx` — `<div data-disclosure={waiting ? "open" : ""}>` around the card's actions.

## Steps

1. In `frontend/components/chat/PlanBody.tsx`, replace the `{open && ( <MessageContent … /> )}` block shown above with the target `<div data-disclosure={open ? "open" : ""}>…</div>`. Keep the `MessageContent` props exactly as they are.

## Boundaries

- Do NOT add CSS; the shared rule covers it. Do NOT touch the Button, its label, or `aria-expanded`.
- Do NOT change `globals.css`.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/chat/PlanBody.tsx`, `npx prettier --check components/chat/PlanBody.tsx` pass.
- **Feel check**: open a chat with a plan card made by the new planner (one with a "How it will be built" part), press "Technical details" and "Hide technical details".
  - The part grows open and fades in; the buttons below slide down instead of jumping.
  - Pressing the toggle twice quickly reverses from where it is, never restarting from zero.
  - In DevTools Animations at 10%, height and opacity move together and end together within 260ms.
  - With reduced motion emulated, it opens and closes at once.
- **Done when**: the technical part opens and closes like every other disclosure in the app.
