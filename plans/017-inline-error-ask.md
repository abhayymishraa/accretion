# 017 — Let the connector and skill-card errors settle in like their siblings

- **Status**: TODO
- **Commit**: 727a267
- **Severity**: LOW
- **Category**: Missed opportunities (preventing a jarring change), Cohesion & tokens
- **Estimated scope**: 3 files, 3 class strings

## Problem

Three inline error lines appear in one frame and push the buttons below them down by a line. Other
errors in the same features already settle in with the module's `ask` animation
(`frontend/components/mcp/DetailHeader.tsx:157`, `frontend/components/mcp/ServerSettings.tsx:130`),
so these three are the odd ones out.

```tsx
// frontend/components/mcp/AddByAddress.tsx:117 — current
{error && (
    <p role="alert" className="text-[12px] leading-4 text-destructive">
        {error}
    </p>
)}

// frontend/components/mcp/KeyForm.tsx:81 — current
{error && (
    <p role="alert" className="text-[12.5px] text-destructive">
        {error}
    </p>
)}

// frontend/components/skills/SkillCard.tsx:65 — current
{error && (
    <p role="alert" className="mt-2 text-[12.5px] text-destructive">
        {error}
    </p>
)}
```

## Target

Each error line enters with its module's existing `ask` class. No new CSS.

- `mcp.module.css` `.ask`: `animation: ask 160ms var(--ease-out)`, from `opacity: 0; transform: translateY(-4px)`.
  `--ease-out` is `cubic-bezier(0.23, 1, 0.32, 1)` (`frontend/app/globals.css:144`).
- `skills.module.css` `.ask`: `animation: swap 160ms var(--ease-out)`, from `opacity: 0; transform: translateY(3px)`.
- Reduced motion is already handled in both modules: `.ask` falls back to a fade only
  (`reveal 160ms ease` in mcp, `reveal 150ms ease` in skills).
- Exit stays instant, the same as the sibling errors.

```tsx
// target, AddByAddress.tsx
<p role="alert" className={`${styles.ask} text-[12px] leading-4 text-destructive`}>
// target, KeyForm.tsx
<p role="alert" className={`${styles.ask} text-[12.5px] text-destructive`}>
// target, SkillCard.tsx
<p role="alert" className={`${styles.ask} mt-2 text-[12.5px] text-destructive`}>
```

## Repo conventions to follow

- Exemplar: `frontend/components/mcp/DetailHeader.tsx:157` —
  `<p role="alert" className={`${styles.ask} mt-3 text-[13px] text-destructive`}>`.
- All three files already import their module as `styles` (`AddByAddress.tsx:10`, `KeyForm.tsx:8`,
  `SkillCard.tsx:8`). Do not add imports.

## Steps

1. `frontend/components/mcp/AddByAddress.tsx`: change the error `<p>`'s
   `className="text-[12px] leading-4 text-destructive"` to
   ``className={`${styles.ask} text-[12px] leading-4 text-destructive`}``.
2. `frontend/components/mcp/KeyForm.tsx`: change the error `<p>`'s
   `className="text-[12.5px] text-destructive"` to
   ``className={`${styles.ask} text-[12.5px] text-destructive`}``.
3. `frontend/components/skills/SkillCard.tsx`: change the error `<p>`'s
   `className="mt-2 text-[12.5px] text-destructive"` to
   ``className={`${styles.ask} mt-2 text-[12.5px] text-destructive`}``.

## Boundaries

- Do NOT touch the CSS modules, `ErrorBox`, or any other error line.
- Do NOT add exit motion or keep the element mounted to animate it out.
- Do NOT key the `<p>` on the message to replay the animation when one error replaces another
  (KeyForm can go from "Paste the key first." to a save error without unmounting). That replay is
  not wanted: the line is already in place.
- If an excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck`,
  `npx eslint components/mcp/AddByAddress.tsx components/mcp/KeyForm.tsx components/skills/SkillCard.tsx`,
  and `npx prettier --check` on the three files pass.
- **Feel check**:
  - Connectors, Add by address: submit `http://x`. The error drops in from 4px above over 160ms.
  - A connector that takes a key: press Save key with the field empty. Same motion.
  - Skills page: make a delete fail (offline in DevTools, then Delete, Delete). The error rises 3px.
  - DevTools Animations panel at 10%: only opacity and transform move; the buttons below shift once,
    with no bounce.
  - Emulate `prefers-reduced-motion: reduce`: each error fades in with no movement.
  - At 390px width the motion is the same and nothing overflows.
- **Done when**: all three errors enter like `DetailHeader.tsx:157`.
