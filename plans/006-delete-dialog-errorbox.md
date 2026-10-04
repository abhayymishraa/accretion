# 006 — Delete dialog error through ErrorBox

- **Status**: DONE
- **Commit**: ad83e1f plus the uncommitted project-covers change (feat/project-covers)
- **Severity**: LOW
- **Category**: Cohesion & tokens / Missed opportunities
- **Estimated scope**: 1 file, about 6 changed lines

## Problem

`frontend/components/projects/ProjectDeleteDialog.tsx` rendered `{error && <p role="alert">}`:
a failed delete popped text in and pushed the buttons down in one frame, and cleared the same
way on retry. Every other error in the app uses `components/ui/ErrorBox.tsx`.

## Target

```tsx
<div className="[&>[data-error-box]]:mt-4">
    <ErrorBox message={error} />
</div>
```

`ErrorBox` stays mounted after its first error so it can leave; its motion is the shared
`[data-error-box]` rule in `frontend/app/globals.css` (enter 180ms from `opacity: 0`,
`translateY(-6px)`, `var(--ease-out)` = `cubic-bezier(0.23, 1, 0.32, 1)`; exit 140ms; none under
reduced motion). Wrapper margin follows `components/chat/ChatPage.tsx:93`.

## Verification

- Block `DELETE /projects/:id` in DevTools; confirm; the error eases in, the buttons move with it.
- Unblock and confirm again; the error eases out as the request starts.
