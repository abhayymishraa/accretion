"""Small, versioned public projections: what ran and what changed, never read bodies or skill text."""

import json

from ..events import redact

# Room for a readable slice of command output in the chat's shell block.
MAX_PUBLIC_BYTES = 4000
MAX_COMMAND_CHARS = 600


def encode_public(details):
    return json.dumps(details, ensure_ascii=False, separators=(",", ":"))


def _bounded(fields):
    """Redact structured fields first, then shrink values without breaking JSON."""
    result = redact(fields, max_length=None)
    truncated = set()
    while len(encode_public(result).encode()) > MAX_PUBLIC_BYTES:
        candidates = [
            (len(encode_public(value).encode()), key)
            for key, value in result.items()
            if key not in {"version", "kind", "error_category", "truncated_fields"}
            and isinstance(value, (str, list))
            and value
        ]
        if not candidates:
            break
        _, key = max(candidates)
        value = result[key]
        result[key] = value[: len(value) // 2]
        truncated.add(key)
        result["truncated_fields"] = sorted(truncated)
    return result


def public_tool_details(name, *, args=None, result=None, diffs=None, screenshots=None):
    """Same projection feeds durable history, websocket updates and copy actions.

    `diffs` is the user's own project text, shown back to them in the chat; the command is published so
    the chat can show what ran. Both are redacted with the rest of the event (RunService.event).
    `screenshots` are ids of stored images (RunService.save_screenshot) the chat shows after the command.
    """
    fields = {"version": 1, "kind": name[:80]}
    args = args if isinstance(args, dict) else {}
    changes = args.get("files") if isinstance(args.get("files"), list) else []
    if result is None:
        paths = []
        if name == "read_files":
            paths = args.get("paths", [])
        elif name == "write_files":
            paths = [item.get("path") for item in changes if isinstance(item, dict)]
        elif name == "edit_file":
            paths = [args.get("path")]
        elif name == "edit_files":
            edits = args.get("edits") if isinstance(args.get("edits"), list) else []
            paths = list(dict.fromkeys(item.get("path") for item in edits if isinstance(item, dict)))
        paths = [path for path in paths if isinstance(path, str)] if isinstance(paths, list) else []
        if paths:
            fields.update(paths=paths, file_count=len(paths))
    else:
        fields["ok"] = bool(result.get("ok"))
        # Results contain source/skill bodies: allowlist by tool before any serialization.
        if name == "read_files" and isinstance(result.get("files"), (dict, list)):
            paths = [path for path in result["files"] if isinstance(path, str)]
            fields.update(files=paths, file_count=len(paths))
        elif name in {"write_files", "edit_file", "edit_files"} and isinstance(result.get("changed_files"), list):
            paths = [path for path in result["changed_files"] if isinstance(path, str)]
            fields.update(changed_files=paths, file_count=len(paths))
        elif name == "search_project_history":
            messages = result.get("messages") if isinstance(result.get("messages"), list) else []
            refs = [item["id"] for item in messages if isinstance(item, dict) and isinstance(item.get("id"), str)]
            fields.update(message_ids=refs, match_count=len(refs))
        elif name == "read_skill":
            fields.update(
                {
                    key: result[key]
                    for key in ("name", "resource", "sha256", "bytes", "status")
                    if isinstance(result.get(key), (str, int, bool))
                }
            )
        elif name == "execute_command":
            fields.update(
                {
                    key: result[key]
                    for key in (
                        "stdout",
                        "stderr",
                        "exit_code",
                        "pid",
                        "status",
                        "reconnected",
                        "output_may_be_incomplete",
                    )
                    if isinstance(result.get(key), (str, int))
                }
            )
            check = result.get("page_check")
            if isinstance(check, dict):
                # Flat, so the byte bound above can shorten it like any other field.
                fields["page_summary"] = str(check.get("summary", ""))
                fields["page_problems"] = [
                    str(item) for key in ("page_errors", "console", "failed_requests") for item in check.get(key, [])
                ]
            if isinstance(result.get("browser_restarted"), str):
                fields["browser_restarted"] = result["browser_restarted"]
        if isinstance(result.get("error"), str):
            fields["error"] = result["error"]
        if isinstance(result.get("error_type"), str):
            fields["error_type"] = result["error_type"]
    if name == "execute_command" and isinstance(args.get("command"), str):
        fields["command"] = args["command"].strip()[:MAX_COMMAND_CHARS]
    bounded = _bounded(fields)
    if screenshots:
        bounded["screenshots"] = list(screenshots)
    if diffs:
        # Whole, like Codex: kept apart from the bounded fields above, never cut.
        bounded["diffs"] = list(diffs)
    return bounded
