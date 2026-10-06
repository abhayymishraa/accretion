# 010 — Let the waitlist confirmation rise in after sign-up

- **Status**: DONE
- **Commit**: dd8207d
- **Severity**: LOW
- **Category**: Missed opportunities (delight, a once-per-user moment)
- **Estimated scope**: 1 file, ~8 lines

## Problem

After sign-up the whole form is replaced in one frame by the confirmation. It is the one moment every user sees once, and it lands flat.

```tsx
// frontend/components/auth/SignUpPage.tsx:28 — current
if (registered)
    return (
        <AuthFrame signup>
            <p role="status">
                You&apos;re on the waitlist. We sent a link to {email}: open it within 30
                minutes to confirm your spot. We&apos;ll email you again when you&apos;re in.
            </p>
            <p className={AUTH_SWITCH_LINK}>
                <Link href="/verify-email">Resend verification email</Link>
            </p>
        </AuthFrame>
    );
```

## Target

The two paragraphs use the auth pages' existing entrance, `.rise` in `frontend/components/auth/auth.module.css`: `animation: auth-rise 460ms var(--ease-drawer) both; animation-delay: calc(var(--i, 0) * 70ms);` with `--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1)`. Under reduced motion the file already swaps it for `auth-fade 180ms ease` (`auth.module.css:81`). The first paragraph takes `--i: 0`, the second `--i: 1`.

## Repo conventions to follow

- Exemplar: `frontend/components/auth/AuthFrame.tsx:68` — `<div style={{ ["--i" as string]: 0 }} className={styles.rise}>`.

## Steps

1. Add `import styles from "@/components/auth/auth.module.css";` to `SignUpPage.tsx` with the other imports.
2. On the first `<p role="status">`, add `style={{ ["--i" as string]: 0 }} className={styles.rise}`.
3. On the second `<p>`, set `style={{ ["--i" as string]: 1 }}` and ``className={`${AUTH_SWITCH_LINK} ${styles.rise}`}``.

## Boundaries

- Do NOT edit `auth.module.css` or `AuthFrame.tsx`.
- Do NOT change the text or the link.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`, `npx eslint components/auth/SignUpPage.tsx`, `npx prettier --check components/auth/SignUpPage.tsx` pass.
- **Feel check**: on `/signup`, with a test address on a local backend, submit the form.
  - The confirmation rises into place, the link 70ms after it, matching the page's own entrance.
  - At 10% playback, nothing travels further than the page header's rise does.
  - With reduced motion emulated, both fade in over 180ms without moving.
- **Done when**: the success swap uses `.rise` with a 70ms stagger.
