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
| 009 | [Fade the preview's loading cover out as the app fades in](009-preview-cover-crossfade.md) | MEDIUM | DONE |
| 010 | [Let the waitlist confirmation rise in after sign-up](010-signup-success-rise.md) | LOW | DONE |
| 011 | [Open the waitlist FAQ on the shared disclosure motion](011-waitlist-faq-height.md) | LOW | DONE |
| 012 | [Fade the build's label when the build ends](012-run-label-fade.md) | LOW | DONE |
| 013 | [Fade status messages in like the error box beside them](013-status-message-fade.md) | LOW | DONE |
| 014 | [Press response on the tab close button and Download](014-press-close-download.md) | LOW | DONE |
| 015 | [Fade the sidebar's project list with the collapse](015-sidebar-list-fade.md) | LOW | TODO |
| 016 | [Let a newly opened workspace tab settle into the toolbar](016-opened-tab-enter.md) | LOW | TODO |
| 017 | [Let the connector and skill-card errors settle in like their siblings](017-inline-error-ask.md) | LOW | TODO |

## Order and dependencies

1. **001 first.** It has the most leverage: the name arriving is the only change on these screens the user does not cause.
2. **002 next.** Both edit `frontend/components/chat/ProjectTitle.tsx` in different spots (the `<h1>` and the status `<span>`). They don't depend on each other, but running them one after the other avoids edit conflicts.

Both plans describe code that was uncommitted at commit `4260670` (AI naming and the
rename-width fix). Commit that work before executing them.

003-005 come from the projects-page pass (2026-10-04, project covers). They are independent;
003 has the most leverage, since it is the only press response a phone gets on a card.

006-008 come from the second projects-page pass. 008 edits the same `.card` block as 003; run it after.

009-014 come from the whole-frontend pass (2026-10-07). They touch different files and are independent. 009 has the most leverage: every preview open ends on a hard cut today. 012 needs a feel check first, since `@starting-style` also fades done labels once on a history load.

015-016 come from the third whole-frontend pass (2026-10-07). They are independent. 015 first: clipped names in a widening sidebar are the one visibly wrong frame left. Both carry a feel-check stop condition. After this pass, further motion would be motion for its own sake.

017 comes from the fourth pass (2026-10-08), on the connector and skill screens added since. It is independent of 015-016; run it after them. It reuses each module's `ask` class and adds no CSS.
