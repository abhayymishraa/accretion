# 008 — Stop lifting cards on keyboard focus

- **Status**: DONE
- **Commit**: ad83e1f plus the uncommitted project-covers change (feat/project-covers)
- **Severity**: LOW
- **Category**: Purpose & frequency
- **Estimated scope**: 1 file, 3 removed lines

## Problem

`frontend/components/projects/project-shelf.module.css` lifted `.card:focus-within` by 2px over
220ms. Tabbing through the grid animated every stop; keyboard focus jumps should not animate.
The card link already shows a focus ring (`focus-visible:outline-2 ... outline-offset-4`), and
a mouse click that focused the link left the card lifted after the pointer left.

## Target

Delete the `.card:focus-within { transform: translateY(-2px); }` rule. Keep the hover lift
(gated to `(hover: hover) and (pointer: fine)`) and the `:active` press from plan 003.

## Verification

- Tab through the grid: the ring moves, cards stay still.
- Mouse hover still lifts; click-and-return leaves nothing lifted.
