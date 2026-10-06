# 013 — Fade status messages in like the error box beside them

- **Status**: DONE
- **Commit**: dd8207d
- **Severity**: LOW
- **Category**: Cohesion & tokens
- **Estimated scope**: 2 files, ~4 lines

## Problem

Status messages appear in one frame, while the `ErrorBox` right beside them fades.

```tsx
// frontend/components/auth/VerifyEmailPage.tsx:51 — current
{message && (
    <p
        role="status"
        className="ember-helper text-[12px] leading-[1.6] text-muted-foreground mt-4"
    >
        {message}
    </p>
)}

// frontend/components/profile/ProfilePage.tsx:136 — current (always mounted; the text changes)
<p
    className="ember-profile-status min-h-6 mt-5 text-accent-foreground text-[14px]"
    role="status"
>
    {message}
</p>
```

## Target

Each new message fades in through the shared `[data-loaded-in]` rule (`frontend/app/globals.css:386`: `animation: content-in 180ms var(--ease-out) both`, opacity from 0; `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`). A `key` of the message text makes a new message fade again.

## Repo conventions to follow

- Exemplar: `frontend/components/projects/ProjectsPage.tsx:44` uses `data-loaded-in` on content that replaces a loading state.

## Steps

1. `VerifyEmailPage.tsx:51`: on the `<p role="status">`, add `key={message}` and the attribute `data-loaded-in`.
2. `ProfilePage.tsx:136`: keep the `<p role="status">` mounted (it holds `min-h-6` so nothing shifts). Change its child `{message}` to `{message && <span key={message} data-loaded-in>{message}</span>}`.

## Boundaries

- Do NOT edit `globals.css`, `ErrorBox`, or other files. Do NOT move the `role="status"` element: a live region must stay mounted for the profile message to be announced.
- If an excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`, `npx eslint components/auth/VerifyEmailPage.tsx components/profile/ProfilePage.tsx`, `npx prettier --check` on both pass.
- **Feel check**:
  - On `/verify-email`, request a link with a test address on a local backend: the confirmation fades in over 180ms, like an error does.
  - On the profile page, save twice: each save's message fades in again.
  - A screen reader still announces the profile message.
- **Done when**: both messages fade in on the 180ms content-in.
