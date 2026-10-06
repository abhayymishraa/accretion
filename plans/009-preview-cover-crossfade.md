# 009 — Fade the preview's loading cover out as the app fades in

- **Status**: DONE
- **Commit**: dd8207d (the file is unchanged on the uncommitted branch `feat/mcp-servers`)
- **Severity**: MEDIUM
- **Category**: Missed opportunities (preventing a jarring change)
- **Estimated scope**: 1 file, ~6 lines

## Problem

When the preview iframe paints, it fades in over 200ms, but the loading cover on top of it unmounts in one frame. The user sees a hard cut, not a crossfade, on every preview open and refresh.

```tsx
// frontend/components/chat/PreviewPanel.tsx:169 — the iframe (current)
className={`${mobile ? "max-w-[375px]" : "max-w-full"} [transition:opacity_200ms_var(--ease-out),max-width_300ms_var(--ease-in-out)] motion-reduce:[transition:opacity_120ms_var(--ease-out)]`}

// frontend/components/chat/PreviewPanel.tsx:173 — the cover (current)
{paintedKey !== frameKey && (
    <div
        className={`${STATE_CLASS} pointer-events-none absolute inset-0`}
    >
        {BUILD_LOADER}
        <h2>{LOADING_TITLE}</h2>
        <p role="status">{LOADING_DESCRIPTION}</p>
    </div>
)}
```

## Target

The cover stays mounted while the frame exists and fades out on the iframe's own curve: opacity 1 → 0, 200ms, `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`; with reduced motion, 120ms. Its status text leaves the accessibility tree once painted.

```tsx
<div
    aria-hidden={paintedKey === frameKey}
    className={`${STATE_CLASS} pointer-events-none absolute inset-0 [transition:opacity_200ms_var(--ease-out)] motion-reduce:[transition:opacity_120ms_var(--ease-out)] ${paintedKey === frameKey ? "opacity-0" : ""}`}
>
    {BUILD_LOADER}
    <h2>{LOADING_TITLE}</h2>
    <p role={paintedKey === frameKey ? undefined : "status"}>{LOADING_DESCRIPTION}</p>
</div>
```

## Repo conventions to follow

- Easing tokens: `frontend/app/globals.css:144` `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`. Use `var(--ease-out)`, never a literal.
- Exemplar: the iframe's own class at `PreviewPanel.tsx:169` (same duration, curve and reduced-motion form).

## Steps

1. In `frontend/components/chat/PreviewPanel.tsx`, replace the conditional `{paintedKey !== frameKey && (<div …>…</div>)}` at line 173 with the always-mounted `<div>` shown in Target. Keep `BUILD_LOADER`, `LOADING_TITLE` and `LOADING_DESCRIPTION` as they are.
2. Change nothing else. The cover already has `pointer-events-none`, so it never blocks the app.

## Boundaries

- Do NOT touch the iframe, the empty-state branch below it, or any other file.
- Do NOT add dependencies.
- If line 173 does not match the excerpt, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npm run typecheck` and `npx eslint components/chat/PreviewPanel.tsx` pass; `npx prettier --check components/chat/PreviewPanel.tsx` passes.
- **Feel check**: open a project with a saved preview and press refresh in the preview toolbar.
  - The loader and the app crossfade; no frame shows both at full strength, and none is blank.
  - In DevTools Animations at 10%, the cover's opacity falls over the same 200ms the iframe rises.
  - With `prefers-reduced-motion` emulated, the crossfade still happens, over 120ms.
  - A screen reader does not announce "Your saved project will appear here shortly" after the app shows.
- **Done when**: the cover is never unmounted mid-frame and fades with the iframe.
