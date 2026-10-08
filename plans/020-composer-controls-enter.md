# 020 — Fade the composer's mode toggle back in, and let "Send update" enter like Stop

- **Status**: DONE
- **Commit**: 727a267 (the hidden toggle is uncommitted work on `fix/one-loop`; commit it first)
- **Severity**: LOW
- **Category**: Cohesion & tokens (entry)
- **Estimated scope**: 1 file, 2 class strings

## Problem

The Build/Plan toggle is hidden while a build runs or waits for an answer, and comes back in one frame when it ends. During a build, the "Send update" arrow pops in when the user types, while Stop and Send beside it already enter with a dip and a fade.

```tsx
// frontend/components/chat/ChatInput.tsx:195 — current
<fieldset className="relative flex rounded-[8px] bg-surface-3 p-[3px] disabled:opacity-40">

// frontend/components/chat/ChatInput.tsx:240-243 — current
<Button
    type="submit"
    variant="send"
    className="rounded-full"
```

## Target

- The toggle fades in from `opacity: 0` over 120ms `var(--ease-out)`. Opacity only: it returns many times a day, and movement would make the row wobble. It leaves at once.
- "Send update" enters exactly like the Send button it replaces: from `scale: 0.97` and `opacity: 0`, 120ms `var(--ease-out)`; no scale under reduced motion. It is the same `send` variant, so it copies that button's class string.

```tsx
// target
<fieldset className="relative flex rounded-[8px] bg-surface-3 p-[3px] disabled:opacity-40 starting:opacity-0 [transition:opacity_120ms_var(--ease-out)]">

<Button
    type="submit"
    variant="send"
    className="rounded-full starting:scale-[0.97] starting:opacity-0 motion-reduce:starting:scale-100 [transition:background-color_140ms_ease,border-color_140ms_ease,opacity_120ms_var(--ease-out),transform_140ms_var(--ease-out),scale_120ms_var(--ease-out)]"
```

## Repo conventions to follow

- Exemplar for "Send update": the Send button in the same file (`ChatInput.tsx:267`, same `send` variant): `rounded-full … starting:scale-[0.97] starting:opacity-0 motion-reduce:starting:scale-100 [transition:background-color_140ms_ease,border-color_140ms_ease,opacity_120ms_var(--ease-out),transform_140ms_var(--ease-out),scale_120ms_var(--ease-out)]` (it also has `disabled:` colours, which "Send update" does not need).
- Exemplar for the fade: the Stop button in the same file: `starting:scale-[0.97] starting:opacity-0 motion-reduce:starting:scale-100 [transition:background-color_130ms_ease,color_130ms_ease,opacity_120ms_var(--ease-out),scale_120ms_var(--ease-out)]`.
- `var(--ease-out)` is `cubic-bezier(0.23, 1, 0.32, 1)`, defined in `frontend/app/globals.css`.

## Steps

1. Append `starting:opacity-0 [transition:opacity_120ms_var(--ease-out)]` to the `<fieldset>` class string.
2. Change the "Send update" Button's `className="rounded-full"` to the target string.

## Boundaries

- Do NOT change the `!isBuilding && !awaitingInput` condition, the sliding pill's own transition, or any other button.
- If an excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/chat/ChatInput.tsx`, `npx prettier --check components/chat/ChatInput.tsx` pass.
- **Feel check**: send a small change and watch the composer; while it builds, type in the box; when it ends, watch the toggle.
  - "Send update" dips and fades in like Stop; the toggle fades back in at the end without moving.
  - The row's width does not wobble at 390px.
  - With reduced motion emulated, "Send update" fades without scaling.
- **Done when**: nothing in the composer row appears in one frame.
