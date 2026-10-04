# Animation plans

Written by `improve-animations` from the `find-animation-opportunities` pass on the sidebar,
project title and preview toolbar (2026-10-01). Each plan is self-contained; run one with any
agent, or with `improve-animations execute plans/<file>`.

| # | Plan | Severity | Status |
| --- | --- | --- | --- |
| 001 | [Fade in the AI's project name when it arrives](001-fade-in-ai-project-name.md) | LOW | DONE |
| 002 | [Fade out the rename status instead of blinking it away](002-fade-out-rename-status.md) | LOW | DONE |
| 003 | [Press response on project cards](003-project-card-press.md) | MEDIUM | DONE |
| 004 | [Fade the cover in over its placeholder](004-cover-load-fade.md) | LOW | DONE |
| 005 | [Slide cards into a deleted project's place](005-delete-reflow-view-transition.md) | LOW | DONE |
| 006 | [Delete dialog error through ErrorBox](006-delete-dialog-errorbox.md) | LOW | DONE |
| 007 | [First-run empty state rises in](007-first-run-empty-state.md) | LOW | DONE |
| 008 | [Stop lifting cards on keyboard focus](008-no-keyboard-focus-lift.md) | LOW | DONE |

## Order and dependencies

1. **001 first.** It has the most leverage: the name arriving is the only change on these screens the user does not cause.
2. **002 next.** Both edit `frontend/components/chat/ProjectTitle.tsx` in different spots (the `<h1>` and the status `<span>`). They don't depend on each other, but running them one after the other avoids edit conflicts.

Both plans describe code that was uncommitted at commit `4260670` (AI naming and the
rename-width fix). Commit that work before executing them.

003-005 come from the projects-page pass (2026-10-04, project covers). They are independent;
003 has the most leverage, since it is the only press response a phone gets on a card.

006-008 come from the second projects-page pass. 008 edits the same `.card` block as 003; run it after.
