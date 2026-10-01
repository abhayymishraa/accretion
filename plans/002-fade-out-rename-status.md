# 002 — Fade out the rename status instead of blinking it away

- **Status**: DONE
- **Commit**: 4260670 plus the uncommitted rename-width change in frontend/components/chat/ProjectTitle.tsx
- **Severity**: LOW
- **Category**: Missed opportunities
- **Estimated scope**: 1 file, about 10 changed lines

## Problem

After a rename the title bar shows "Saved", and 1.5s later it disappears in a single frame. The
hook clears the status to `idle`, whose message is the empty string, so the text is removed
rather than faded. Feedback that steps aside smoothly reads as confirmation; text that blinks
out reads as something vanishing.

```tsx
// frontend/components/chat/ProjectTitle.tsx:148-153 — current
<span
    aria-live="polite"
    className={`shrink-0 text-[11.5px] ${status === "error" ? "text-destructive" : "text-muted-foreground"}`}
>
    {STATUS[status]}
</span>
```

```ts
// frontend/components/chat/ProjectTitle.tsx — STATUS map near the top of the file
const STATUS = { idle: "", saving: "Saving…", saved: "Saved", error: "Couldn't save the name" };
```

```ts
// frontend/hooks/projects/useProjectTitle.ts:37-41 — current, unchanged by this plan
useEffect(() => {
    if (status !== "saved") return;
    const fade = setTimeout(() => setStatus("idle"), 1500);
    return () => clearTimeout(fade);
}, [status]);
```

## Target

- The status text stays on screen while it fades: going to `idle` drops opacity to 0 over 200ms
  instead of removing the words.
- Appearing ("Saving…", "Saved", the error) is instant at full opacity, because it confirms
  something the user just did.
- Transition: `opacity 200ms var(--ease-out)` with `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`
  from `frontend/app/globals.css`. Opacity only, so no reduced-motion override is needed.
- Screen readers: the text must not change when it fades, so `aria-live` does not announce
  anything new on the fade.

## Repo conventions to follow

- Exact-property transitions as Tailwind arbitrary values, e.g. `[transition:opacity_200ms_var(--ease-out)]` (see `frontend/components/chat/ChatInput.tsx:246`).
- Derived state is adjusted during render, not in an effect; this file already does that for the rename draft, and the repo's ESLint config rejects `setState` inside effects (`react-hooks/set-state-in-effect`).

## Steps

1. `frontend/components/chat/ProjectTitle.tsx`: inside `ProjectTitle`, after the
   `useProjectTitle(...)` line, keep the last non-empty message:
   ```tsx
   // The words stay while the status fades out, so nothing blinks and aria-live hears no change.
   const [message, setMessage] = useState("");
   if (STATUS[status] && STATUS[status] !== message) setMessage(STATUS[status]);
   ```
   (`useState` is already imported from "react" in this file.)
2. Replace the status span with:
   ```tsx
   <span
       aria-live="polite"
       className={`shrink-0 text-[11.5px] [transition:opacity_200ms_var(--ease-out)] ${status === "idle" ? "opacity-0" : "opacity-100 [transition-duration:0ms]"} ${status === "error" ? "text-destructive" : "text-muted-foreground"}`}
   >
       {message}
   </span>
   ```
   The `0ms` override makes appearing instant while disappearing takes 200ms.
3. Run `npm run format` in `frontend/`.

## Boundaries

- Do NOT change `useProjectTitle.ts`; the 1500ms hold stays as it is.
- Do NOT touch the title, the rename input or the dropdown.
- Do NOT add dependencies or keyframes.
- If the excerpts above don't match the file, STOP and report.

## Verification

- **Mechanical**: in `frontend/`, `npx tsc --noEmit -p .` prints nothing and `npm run lint` reports no errors (watch for `react-hooks` rules on the render-time `setMessage`).
- **Feel check**:
  - Rename a project and press Enter: "Saving…" then "Saved" appear instantly; about 1.5s later "Saved" fades out over 200ms instead of vanishing.
  - Rename twice quickly: the second "Saving…" appears at full opacity immediately, even mid-fade.
  - DevTools → Animations at 10%: only opacity changes, and the words stay "Saved" for the whole fade.
  - With a screen reader on (VoiceOver), "Saved" is announced once; the fade announces nothing.
- **Done when**: the status never disappears in a single frame and never fades in.

## Outcome

Done as written. Verified in the browser: "Saved" appears at full opacity, then fades 1 to 0 in about
200ms with the word kept on screen throughout.
