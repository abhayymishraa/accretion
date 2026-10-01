# 001 — Fade in the AI's project name when it arrives

- **Status**: DONE
- **Commit**: 4260670 plus the uncommitted AI-naming change (agent/run/title.py; `projectName()` in frontend/lib/projects/filters.ts)
- **Severity**: LOW
- **Category**: Missed opportunities
- **Estimated scope**: 3 files, about 10 changed lines

## Problem

A new project is untitled; its title reads "New project" until the server pushes the AI's name
over the socket (`project_title` event). The name then replaces "New project" in a single frame,
in two places at once, with nothing on screen having caused it. It reads as a glitch rather
than a deliberate update. It happens once per project, so it is a rare moment and eligible for
a short entrance.

```tsx
// frontend/components/chat/ProjectTitle.tsx:90-96 — current
<h1
    onDoubleClick={startEditing}
    title="Double-click to rename"
    className={`${TITLE_TEXT} m-0 min-w-0 cursor-text truncate [transition:background-color_130ms_ease] pointer-fine:hover:bg-surface-2`}
>
    {title}
</h1>
```

```tsx
// frontend/components/layout/SidebarProjects.tsx:40 — current
<span className="min-w-0 truncate">{projectName(project)}</span>
```

```ts
// frontend/hooks/projects/useProjectTitle.ts:13-15 — current
const project = projects?.find((item) => item.id === projectId);
// Null only while the list loads; an unnamed project reads "New project" until it is named.
const title = project ? projectName(project) : null;
```

## Target

When a title changes from untitled (`project.title === null`) to named, the name fades in and
rises 2px into place over 200ms with the strong ease-out. Nothing else animates. In particular,
a rename the user types must **not** replay it.

- Trigger: a React `key` that changes **only** on the untitled → named flip:
  `key={project.title ? "named" : "pending"}`. A new key remounts the element, and
  `@starting-style` (Tailwind v4's `starting:` variant) supplies the from-state.
- From: `opacity: 0`, `translate: 0 2px` (Tailwind `starting:opacity-0 starting:translate-y-0.5`).
- To: the element's normal resting state.
- Transition: `opacity 200ms var(--ease-out), translate 200ms var(--ease-out)`, where
  `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)` is already defined in `frontend/app/globals.css`.
  The property is `translate`, not `transform`: Tailwind v4's `translate-y-*` sets the
  standalone `translate` property.
- Reduced motion: keep the fade, drop the movement: `motion-reduce:starting:translate-y-0`.

## Repo conventions to follow

- Easing tokens live in `frontend/app/globals.css` (`--ease-out`, `--ease-in-out`, `--ease-drawer`). Use `var(--ease-out)`; do not add a new curve.
- Transitions are written as Tailwind arbitrary properties listing exact properties, never `all`: `[transition:opacity_120ms_var(--ease-out),scale_120ms_var(--ease-out)]`.
- Exemplar of a `starting:` entrance with a reduced-motion override: `frontend/components/chat/ChatInput.tsx:246`
  `starting:scale-[0.97] starting:opacity-0 motion-reduce:starting:scale-100 [transition:...,opacity_120ms_var(--ease-out),scale_120ms_var(--ease-out)]`.
- Prettier formats the frontend (4 spaces, 100 columns): run `npm run format` in `frontend/` after editing.

## Steps

1. `frontend/hooks/projects/useProjectTitle.ts`: expose whether the project has a real name.
   After the `const title = ...` line add:
   ```ts
   // Flips once, when the AI's name replaces "New project"; keys the title's entrance.
   const named = Boolean(project?.title);
   ```
   and change the return to `return { title, named, projects, status, save, saveSoon };`.
2. `frontend/components/chat/ProjectTitle.tsx`: destructure `named` from `useProjectTitle(projectId)`.
   On the `<h1>` add `key={named ? "named" : "pending"}`. Then replace its transition so the
   existing hover transition is kept and the entrance is added:
   ```tsx
   className={`${TITLE_TEXT} m-0 min-w-0 cursor-text truncate starting:translate-y-0.5 starting:opacity-0 motion-reduce:starting:translate-y-0 [transition:background-color_130ms_ease,opacity_200ms_var(--ease-out),translate_200ms_var(--ease-out)] pointer-fine:hover:bg-surface-2`}
   ```
3. `frontend/components/layout/SidebarProjects.tsx:40`: replace the span with
   ```tsx
   <span
       key={project.title ? "named" : "pending"}
       className="min-w-0 truncate starting:translate-y-0.5 starting:opacity-0 motion-reduce:starting:translate-y-0 [transition:opacity_200ms_var(--ease-out),translate_200ms_var(--ease-out)]"
   >
       {projectName(project)}
   </span>
   ```
4. Run `npm run format` in `frontend/`.

## Boundaries

- Do NOT touch the rename input, the dropdown menu, or `useProjectList.ts`.
- Do NOT animate on every title change: the key must depend only on `project.title` being null or not.
- Do NOT add dependencies (no Motion import for this); CSS only.
- If the code at the cited lines differs from the excerpts above, STOP and report instead of improvising.

## Verification

- **Mechanical**: in `frontend/`, `npx tsc --noEmit -p .` prints nothing and `npm run lint` reports no errors.
- **Feel check**:
  - Create a new project. The title bar and the sidebar row show "New project". When the name arrives (about a second), both fade in and settle 2px upward, together.
  - Double-click the title, rename it, press Enter: the new name appears instantly with **no** fade.
  - Reload the page on an already-named project: no fade (the element mounts already named; `@starting-style` applies on first paint too, so if a fade is visible on every load, use the key alone and report it).
  - DevTools → Animations panel → playback 10%: confirm opacity and the 2px rise both run 200ms with a fast start and a long settle, and nothing scales.
  - DevTools → Rendering → emulate `prefers-reduced-motion: reduce`: the name still fades, but does not move.
- **Done when**: the only motion on the name is the one-time untitled → named entrance, in both places.

Note for the reviewer: `@starting-style` also runs when an element first renders. If the fade
shows on every page load (not only on arrival), that is the known trade-off of a CSS-only
entrance. Judge whether a 200ms fade on load is acceptable; if not, gate the classes on a
"was pending in this session" flag. Feel can't be settled from code, so check it in the browser.

## Outcome

Done. One deviation from the steps: keying on `project.title` alone was not enough. `@starting-style`
also fires whenever the title element mounts, so the fade replayed after every rename (the input
swaps back to the heading) and on every page load. Arrival is now tracked in React state: each
component remembers projects it saw untitled (`useProjectTitle`'s `watchedUntitled`,
`SidebarProjects`' `watched`), applies the entrance classes (`NAME_ARRIVES` in `ProjectTitle.tsx`)
only after such a project gets a name, and clears the memory on `transitionend`. A module-level
flag was tried first and failed: React Compiler memoised `nameArrived(projectId)` because its
argument never changes.

Verified in the browser: arrival fades title and sidebar row together (opacity 0 to 1, translate
2px to 0, about 200ms, strong ease-out); a typed rename and a page load never drop below opacity 1;
with reduced motion the name fades with 0px movement.
