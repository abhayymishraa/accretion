# 022 — Let a skill card's delete error settle in

- **Status**: DONE
- **Commit**: 727a267
- **Severity**: LOW
- **Category**: Cohesion & tokens (entry)
- **Estimated scope**: 1 file, one attribute

## Problem

When deleting a skill fails, its error line appears in one frame on the card.

```tsx
// frontend/components/skills/SkillCard.tsx:64 — current
{error && (
    <p role="alert" className="mt-2 text-[12.5px] text-destructive">
        {error}
    </p>
)}
```

## Target

The line enters on the app's shared error motion: from `opacity: 0` and `translateY(-6px)` to rest over 180ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`); without movement under reduced motion. It still leaves at once when the error clears. Its look does not change.

```tsx
// target
<p data-error-box="shown" role="alert" className="mt-2 text-[12.5px] text-destructive">
```

## Repo conventions to follow

- The rule lives in `frontend/app/globals.css`: `[data-error-box="shown"]` is `display: block`, and inside the motion query it transitions `opacity` and `transform` 180ms `var(--ease-out)` with `@starting-style { opacity: 0; transform: translateY(-6px); }`.
- Do NOT use the `ErrorBox` component here: it draws a bordered box, which would change the card's look.

## Steps

1. Add `data-error-box="shown"` to the `<p role="alert">` shown above.

## Boundaries

- One attribute. Do NOT change the text, classes or condition.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/skills/SkillCard.tsx`, `npx prettier --check components/skills/SkillCard.tsx` pass.
- **Feel check**: make a delete fail (for example, stop the backend, then delete a library skill).
  - The error drops 6px into place and fades in; the card's size change is the only jump.
  - It looks exactly as before once settled.
  - With reduced motion emulated, it fades without moving.
- **Done when**: the error enters like every other error in the app.
