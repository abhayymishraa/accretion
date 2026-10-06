# 011 — Open the waitlist FAQ on the shared disclosure motion

- **Status**: DONE
- **Commit**: dd8207d
- **Severity**: LOW
- **Category**: Cohesion & tokens
- **Estimated scope**: 1 file, 2 attribute changes

## Problem

The waitlist FAQ `<details>` snap open; only the "+" turns, on its own 200ms Tailwind `ease-out`. The landing page's FAQ already glides open through a shared rule.

```tsx
// frontend/components/auth/WaitlistPage.tsx:193 — current
<details
    key={q}
    className="group border-b border-[var(--hairline)]"
>
    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-[15px] font-medium [&::-webkit-details-marker]:hidden">
        {q}
        <span
            aria-hidden
            className="text-[var(--ink-tertiary)] transition-transform duration-200 ease-out group-open:rotate-45"
        >
            +
        </span>
    </summary>
```

## Target

The `<details>` opt into the shared rule at `frontend/app/globals.css:299-322`, which applies only under `prefers-reduced-motion: no-preference`: the panel's `block-size` 0 → auto over 260ms `var(--ease-out)` (`cubic-bezier(0.23, 1, 0.32, 1)`), the glyph's `transform` on the same 260ms, and `scale: 0.9` on press over 140ms.

## Repo conventions to follow

- Exemplar: `frontend/components/landing/FaqItem.tsx` — `<details data-faq><summary>{question}<span aria-hidden="true">+</span></summary><p>{answer}</p></details>`. The rule targets `details[data-faq] summary > span`; this markup already matches.

## Steps

1. Add the attribute `data-faq` to the `<details>` at `WaitlistPage.tsx:193`.
2. On the "+" `<span>`, remove `transition-transform duration-200 ease-out`; keep `text-[var(--ink-tertiary)]` and `group-open:rotate-45`.

## Boundaries

- Do NOT edit `globals.css`. Do NOT touch any other `<details>` (tool output in chat must stay instant, see `globals.css:296`).
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`, `npx eslint components/auth/WaitlistPage.tsx`, `npx prettier --check components/auth/WaitlistPage.tsx` pass.
- **Feel check**: on the waitlist page, open and close each question.
  - The answer's height grows over 260ms and the "+" turns on the same beat, not before it.
  - Pressing the question dips the "+" to 0.9.
  - Opening and closing rapidly reverses smoothly, never restarting from closed.
  - With reduced motion emulated, the panel opens at once.
- **Done when**: the waitlist FAQ and the landing FAQ open identically.
