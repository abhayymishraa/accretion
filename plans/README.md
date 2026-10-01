# Animation plans

Written by `improve-animations` from the `find-animation-opportunities` pass on the sidebar,
project title and preview toolbar (2026-10-01). Each plan is self-contained; run one with any
agent, or with `improve-animations execute plans/<file>`.

| # | Plan | Severity | Status |
| --- | --- | --- | --- |
| 001 | [Fade in the AI's project name when it arrives](001-fade-in-ai-project-name.md) | LOW | DONE |
| 002 | [Fade out the rename status instead of blinking it away](002-fade-out-rename-status.md) | LOW | DONE |

## Order and dependencies

1. **001 first.** It has the most leverage: the name arriving is the only change on these screens the user does not cause.
2. **002 next.** Both edit `frontend/components/chat/ProjectTitle.tsx` in different spots (the `<h1>` and the status `<span>`). They don't depend on each other, but running them one after the other avoids edit conflicts.

Both plans describe code that was uncommitted at commit `4260670` (AI naming and the
rename-width fix). Commit that work before executing them.
