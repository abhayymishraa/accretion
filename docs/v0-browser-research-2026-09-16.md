# v0 browser research: chat, files, preview, and generation

Observed on September 16, 2026 using the authenticated `agent-browser` session `v0-research`. Research only; no WebBuilder application code changed. Browser observations describe this account and session, not a universal v0 architecture or performance benchmark.

## Scope and evidence limits

- Opened a recent existing portfolio chat, its preview and Code tab, and `app/page.tsx` in the embedded editor.
- Returned to that chat after visiting another chat.
- Opened a legacy chat marked 315 days old. Its UI offered an Update action and said to start a new chat to continue. Did not update or modify it.
- Created one new chat, “Minimal todo list app,” using v0 Mini. Requested a simple local-state todo page without integrations. No deployment or publishing was requested.
- Used its preview to add a temporary task and click its completion checkbox.
- Inspected request methods, paths, response shapes, content types, and browser Resource Timing. No credentials, raw HAR, cookies, auth headers, or private source bodies are retained in this report.
- Inspected WebBuilder source for comparison. Did not run WebBuilder lint, tests, type checks, builds, or browser checks.
- Network capture does not establish private prompts, backend queues, model routing, cache internals, billing, or the absence of WebSockets in every v0 subsystem.

## Observed endpoints

IDs, workspace slugs, and query values are omitted. These are private website endpoints observed through normal UI actions, not supported APIs for us to integrate with.

| Action | Observed request | Observation |
| --- | --- | --- |
| Navigate to an existing chat | `GET /<scope>/chat/<slug>` | `text/x-component` response; React Server Component navigation alongside JSON requests. Full initial-history serialization was not established. |
| Synchronize conversation | `GET /api/chat/chat/latest?chatId=…&lastSyncedAt=…` | JSON envelope with `newMessages`, `deletedMessageIds`, `resumeUserMessageMap`, and `syncedAt`. One response contained four messages; later unchanged responses contained zero. |
| Populate navigation | `GET /api/chat/scoped/chats`, `GET /chat/api/history` | Separate sidebar/history requests. Do not confuse their names with the active conversation’s message transport. |
| Inspect preview runtime | `GET /chat/api/vm/status` | Runtime status is separate from chat history. Includes status/substatus and preview/editor metadata. Sensitive fields omitted. |
| Fetch saved preview | `GET /chat/api/snapshots/proxy` | Returned HTML, not a source-file manifest. Existing preview response was about 108 KB encoded. |
| Open live preview | `GET /chat/api/vm/open` | Observed redirect chain to a `*.v0.build` page. Legacy chat used `*.vusercontent.net`. |
| Request runtime pipeline | `POST /chat/api/vm/actions/run-pipeline` | Returned 403 in this session, while live previews ultimately rendered. Cause not established; not evidence that this endpoint is unnecessary. |
| Open Code tab | `GET /chat/api/blocks/source` | JSON `source` string, containing a generated code block. Not evidence that it supplies the entire editor filesystem. |
| Use code editor | Embedded `*.vercel.run` editor | VS Code-style explorer/editor and `vscode-remote-resource` requests. Exact file-content transport was not isolated; do not claim every file is read through REST. |
| Submit new prompt | `POST /chat/api/chat` | Long-running `text/plain; charset=utf-8` response. Completed body contained newline-separated JSON arrays/objects; not `text/event-stream`. |
| Track new conversation | `POST /chat/api/chat/leaf`, route GET/POST requests | Separate JSON and RSC requests accompanied generation. Their full backend roles were not established. |

The new-chat request’s top-level fields included chat/message IDs, `messageContent`, `modelConfiguration`, `permissionsMode`, `mcpServers`, and team information. These field names do not reveal the internal model prompt or full orchestration design.

## Loading behavior and measurements

1. Chat synchronization and preview-runtime requests occurred separately; conversation display did not depend on completing the Code editor startup.
2. A saved HTML preview was fetched before the live preview navigation completed. On revisiting the new demo, an iframe labelled **Loading preview** already contained the todo heading/input/Add button. This supports a saved-preview placeholder interpretation; exact snapshot swap logic is not exposed.
3. The Code tab opened a sandbox-hosted VS Code-style editor. Returning to the portfolio restored the Code tab and selected file. Whether this comes from retained components or another client cache is not established.
4. Unchanged chat-sync responses measured **97–99 encoded body bytes**. A populated response measured about **11.8 KB**. These are response body measurements, not whole-page bandwidth or provider token usage.
5. The portfolio RSC navigation measured about **131 KB encoded** and **1.55 seconds** on one visit; a later navigation measured **3.26 seconds**. These are request durations, not time to first visible chat. v0 is not uniformly instant.
6. The new generation response lasted **46.98 seconds**, with **9,146 encoded body bytes** and **9,446 transfer bytes** in Resource Timing. Captured decoded body length was 33,260 characters. This does not measure LLM context size or cost.
7. During new generation, VM status checks started roughly every **3 seconds**, later roughly **6 seconds**. Do not infer a fixed polling interval across all states.
8. Repeated sidebar, plan, attributes, template, and status requests were visible. Copying v0’s entire request pattern would not inherently reduce our bandwidth.

## Visible agent workflow

The new run exposed this sequence:

```text
Submit prompt
  → load shadcn guidance / find visual direction
  → inspect project files
  → edit todo page and metadata
  → load agent-browser guidance
  → open local preview
  → add a task and check its checkbox
  → capture screenshot
  → present completion summary
```

Expanded “Tested todo interactions” showed an actual command combining `agent-browser open`, snapshot, fill, click, wait, check, and screenshot, with recorded output. UI duration initially said 45 seconds and said 48 seconds after reopening. Use “about 47 seconds,” not a benchmark claim.

The existing portfolio run exposed multiple screenshot checks and repair steps for CSS and icon errors. This demonstrates observable edit/check/repair behavior, not proof that every run uses identical tools or catches all visual problems.

## Comparison with current local WebBuilder source

| Concern | v0 observation | WebBuilder source | Decision |
| --- | --- | --- | --- |
| Initial history | HTTP/RSC navigation and JSON synchronization | Cached messages plus `GET /chats/{id}/messages?limit=50` | Keep HTTP history. We already moved away from loading history through the socket. |
| Catch-up | `lastSyncedAt` with changed/deleted messages | Latest-page refresh on socket ready/resync/run-started; merges and buffers events during fetch | Incremental catch-up is worth evaluating if repeated page payloads are material. |
| Live generation | Streaming HTTP text response | HTTP run submission plus WebSocket events | No demonstrated reason to change transport. SSE/HTTP streaming is not automatically faster. |
| File browsing | Separate sandbox editor plus source-block endpoint | Persisted file manifest and revision-keyed on-demand file reads | Keep our lightweight file APIs. Full IDE complexity is not justified by this research. |
| Preview startup | Saved HTML and live runtime handled separately | File metadata supplies revision ID; preview GET/POST manages E2B readiness | Preserve separation. Consider a labelled last-successful screenshot while live preview starts. |
| Runtime polling | Frequent VM checks in observed generation | Files poll every 10 seconds while building; preview polling depends on startup/visibility state | Do not copy more frequent polling without evidence. |
| Verification | Task-specific browser actions and screenshots visible in tool output | Existing preview/browser verification capabilities | Audit whether our checks exercise the requested interaction, not only whether a page loads. |

Relevant local files: `frontend/hooks/chat/useChatHistory.ts`, `frontend/hooks/chat/useChatConnection.ts`, `frontend/services/service.history.ts`, `frontend/hooks/files/useProjectFiles.ts`, `frontend/hooks/files/useFileViewer.ts`, `frontend/hooks/preview/usePreviewLifecycle.ts`, `frontend/components/chat/PreviewPanel.tsx`, `agent/service.py`, and `main.py`.

## Recommended next steps, not implemented

1. **Measure our open-chat path first:** time to first visible cached/history message, file metadata, first preview placeholder, and interactive preview. Trace mount/ready refresh duplication before changing the architecture.
2. **Optimize catch-up if payloads justify it:** use a server-owned change cursor or revision, return changed message/run summaries, and retain full snapshot fallback after gaps. If deletion is supported, include deletion markers. Preserve current event/snapshot race handling and owner authorization. Do not simply trust a client timestamp.
3. **Improve perceived preview startup:** show a last-successful, revision-labelled screenshot while E2B resumes, then swap to the live iframe. Never present the screenshot as interactive or as proof the latest edit succeeded. Reuse any existing screenshot pipeline before adding capture/storage work. A screenshot is a simpler proposal than cloning v0’s executable HTML snapshot mechanism.
4. **Make completion evidence task-specific:** for a todo app, verify adding/completing a task; for a form, validate submission behavior. Reuse current browser tooling and budgets rather than adding another tool layer by default.

No transport migration, full IDE integration, private v0 API dependency, app code change, or production performance claim follows from this research alone.
