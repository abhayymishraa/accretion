# 012 — Fade the build's label when the build ends

- **Status**: DONE
- **Commit**: dd8207d
- **Severity**: LOW
- **Category**: Missed opportunities (state indication)
- **Estimated scope**: 1 file, 2 class additions

## Problem

When a build ends, the row's "working" label (orb, text, timer) is replaced in one frame by the folded "done" button. It is the moment the user waits for, and it lands as a cut.

```tsx
// frontend/components/chat/RunActivity.tsx:81 — current
{running ? (
    <span
        role="status"
        className="flex min-w-0 flex-1 items-center gap-2 text-[13.5px] text-muted-foreground"
    >
        …
    </span>
) : (
    <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        className={`group flex min-w-0 cursor-pointer items-center gap-1.5 rounded-[6px] text-left text-[13.5px] [transition:color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring ${ … }`}
    >
```

## Target

The done button fades in over 180ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`) through Tailwind's `starting:` variant (`@starting-style`), opacity only, so the row does not move. Its existing color transition stays.

```tsx
className={`group flex min-w-0 cursor-pointer items-center gap-1.5 rounded-[6px] text-left text-[13.5px] [transition:color_130ms_ease,opacity_180ms_var(--ease-out)] starting:opacity-0 focus-visible:outline-2 focus-visible:outline-ring ${ … }`}
```

## Repo conventions to follow

- Exemplar: `frontend/components/chat/ToolList.tsx:42` — `[transition:opacity_200ms_var(--ease-out),translate_200ms_var(--ease-out)] starting:translate-y-1 starting:opacity-0`.

## Steps

1. In `RunActivity.tsx`, in the `<button>` of the `:` branch, change `[transition:color_130ms_ease]` to `[transition:color_130ms_ease,opacity_180ms_var(--ease-out)]` and add `starting:opacity-0` after it.
2. Leave the `running` branch as it is: a starting build should appear at once.

## Boundaries

- Do NOT change the markup, the label text, or other files.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`, `npx eslint components/chat/RunActivity.tsx`, `npx prettier --check components/chat/RunActivity.tsx` pass.
- **Feel check**: run a short build and watch its row as it ends.
  - The done label fades in over 180ms; the row height and the time on the right do not move.
  - Reload the chat. `@starting-style` also plays on first render, so a history load fades every done label once, over 180ms. Confirm this reads as one quiet fade with the rest of the page (`data-loaded-in` already fades the page in 180ms). If it reads as noise, STOP and report.
  - With reduced motion emulated, the fade still happens; nothing moves.
- **Done when**: a build's end crossfades its label.
