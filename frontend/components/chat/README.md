# Inline chat activity

Tool activity lives in each assistant run, using the existing Ember theme. There is no separate Activity view.

The loading grid, collapsible steps, tool rows, file context, and searchable composer adapt interaction patterns from [Beautiful UI](https://www.beautifului.dev/) ([source](https://github.com/slev12397/beautiful-ui)). MIT attribution is in `../ember/BEAUTIFUL-UI-LICENSE`.

- Run status, elapsed time, tool results, and verification details come from websocket events and their persisted replay.
- Build steps display public stage messages, never invented model reasoning.
- File cards display paths returned by tools. They do not claim to contain retrieved document chunks.
- The backend currently sends complete answers. Content updates render as received; there is no simulated token streaming.
- File references and prompt commands insert editable text without starting a run. Expanded tool results now provide copy-result and stable plain-text run/call reference actions. Model selection, attachments, and dictation are not exposed by this implementation.
- Motion respects reduced-motion settings. Live timers clean up on completion and unmount. Updates follow the conversation only while the user remains near the bottom.

The focused browser check uses intercepted HTTP/websocket fixtures in an isolated context. It does not authenticate to the backend, generate apps, or resume E2B sandboxes.

## Tool presentation research (2026-09-13)

Patterns were inspected directly in these repositories; this is a tailored implementation, not a claim that any one design is universally best:

- [OpenCode BasicTool](https://github.com/anomalyco/opencode/blob/dev/packages/session-ui/src/components/basic-tool.tsx): structured action titles/subtitles, pending feedback, collapsible details, and deferred heavy content.
- [Cline ToolOutput](https://github.com/cline/cline/blob/main/apps/cli/src/tui/components/tool-output.tsx): different presentations for reads, edits, terminal output, and errors; concise output before full diagnostics.
- [bolt.diy ToolInvocations](https://github.com/stackblitz-labs/bolt.diy/blob/main/app/components/chat/ToolInvocations.tsx): clear call/result states and expandable tool results within the chat.

Our rows show returned filenames/counts, command exit codes and stdout/stderr, matched history identifiers, and visible error summaries. Errors open by default, with user expansion choices respected. Earlier consecutive successful calls collapse on long runs; failures and running calls remain visible and calls retain their order. Closed tool details and older groups do not mount their output listings. Plain-text/truncated output is preserved as text.

The backend publishes command text only for a small exact allowlist of commands. Other command inputs are explicitly omitted. Before/after source contents are not published, so this view cannot calculate real tool edit diffs. It does not invent them or expose unrestricted arguments.

## Structured event contract

`tool_started` and `tool_completed` carry optional `details` with `version: 1`. Existing run/call/event IDs and sequence remain authoritative. A started file operation reports target `paths`; completed reads report `files`, and completed writes report `changed_files`. Counts describe the original list even if the public list is shortened. Commands report available exit code and stdout/stderr; retrieval reports message IDs, and skills report metadata only.

`agent/tools/public_tools.py` projects an allowlist and bounds the serialized details to 4,000 UTF-8 bytes; events are redacted when emitted. `truncated_fields` identifies shortened values. Commands publish the command text; edits publish a bounded line diff (`diffs`); agent-browser commands publish the ids of stored screenshots (`screenshots`, served by `GET /runs/{run_id}/screenshots/{id}`). A valid JSON `output` string, without diffs, is retained for legacy clients. Read bodies and skill text are never copied to public events.

The existing service persists each event before publishing it to its authenticated WebSocket subscribers. The frontend updates as start/completion/stage/verification events arrive; reconnecting replays those saved events. This adds no provider requests and no new broker or database schema. It does not stream terminal chunks or model tokens. Tool completion is distinct from checkpoint persistence and final build verification.
