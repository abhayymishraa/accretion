# 021 — Fade in the build check's output like the tool rows beside it

- **Status**: DROPPED — `ShellBlock` already fades in through `FRAME` (`frontend/components/chat/ToolBlocks.tsx:59`), the same 150ms fade as the tool rows; the wrapper added a second fade and was removed.
- **Commit**: 727a267
- **Severity**: LOW
- **Category**: Cohesion & tokens
- **Estimated scope**: 1 file, one wrapper

## Problem

Opening a run's build-check row shows its output in one frame, while opening a tool row fades its contents in.

```tsx
// frontend/components/chat/TimelineNotes.tsx:54 — current
{open && (
    <ShellBlock
        command=""
        …
    />
)}

// frontend/components/chat/RunTimeline.tsx:160 — the tool rows (exemplar)
<div className="grid min-w-0 animate-in fade-in duration-150 ease-out motion-reduce:animate-none">
```

## Target

```tsx
// target
{open && (
    <div className="animate-in fade-in duration-150 ease-out motion-reduce:animate-none">
        <ShellBlock … />
    </div>
)}
```

A 150ms fade, the same values the tool rows use; none under reduced motion.

## Repo conventions to follow

- Exemplar: `frontend/components/chat/RunTimeline.tsx:160` (above).

## Steps

1. In `frontend/components/chat/TimelineNotes.tsx`, wrap the `<ShellBlock … />` inside `{open && ( … )}` in `<div className="animate-in fade-in duration-150 ease-out motion-reduce:animate-none">`. Keep every `ShellBlock` prop unchanged.

## Boundaries

- Do NOT add motion to the row itself, the chevron, or other notes.
- If the excerpt does not match, STOP and report.

## Verification

- **Mechanical**: from `frontend/`: `npx tsc --noEmit -p .`, `npx eslint components/chat/TimelineNotes.tsx`, `npx prettier --check components/chat/TimelineNotes.tsx` pass.
- **Feel check**: expand a finished run, then open its "Checked the build" row.
  - The output fades in over about 150ms, the same as opening a tool row.
  - With reduced motion emulated, it appears at once.
- **Done when**: both kinds of row open the same way.
