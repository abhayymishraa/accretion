# 004 — Fade the cover in over its placeholder

- **Status**: DONE
- **Commit**: ad83e1f plus the uncommitted project-covers change (feat/project-covers)
- **Severity**: LOW
- **Category**: Missed opportunities (preventing a jarring change)
- **Estimated scope**: 2 files, about 30 changed lines

## Problem

`frontend/components/projects/ProjectCover.tsx` unmounted the pulsing placeholder in the same
frame the image mounted with `animate-in fade-in`. For ~200ms the card showed its bare
`bg-surface-2`: pulse, gap, image. The fade also began on mount, before the image decoded.

## Target

- The `bg-surface-3` placeholder stays mounted under the image; it pulses only while loading.
- The image carries `styles.cover` and `data-loaded` set from `onLoad`:

```css
.cover { opacity: 0; transition: opacity 200ms var(--ease-out); }
.cover[data-loaded] { opacity: 1; }
```

No reduced-motion override: an opacity fade does not move anything.

Opacity only: the screenshot is content, it should not move. No cache-hit shortcut: a blob
object URL is decoded fresh by each new `<img>`, so `img.complete` is never true at mount.

## Verification

- Throttle the network; each card goes pulse, then a 200ms fade, with no dark frame between.
- A project without a cover still shows the grid banner with no flash.
