"""The project's files and shell in its sandbox: the one place the model's tools reach E2B, with its limits."""

import asyncio
import json
import re
import shlex
from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from typing import Any

import httpx
from e2b import FileNotFoundException, SandboxException
from pydantic import BaseModel, Field

from . import command_policy
from .commands import MAX_OUTPUT, run_command

ROOT = "/home/user/react-app"
# About 25k tokens. Bounds reads, writes and edits alike, so a file the model
# can write it can also read back and edit; lockfile-sized reads are refused rather than resent every turn.
MAX_FILE_BYTES = 100_000

# The model checks the running app with agent-browser (installed by sandbox/templates.py) through
# execute_command. Before such a command the host brings the preview and database up to date; after
# it, the screenshots the CLI reports saving go to the chat and, when the model reads images, to it.
BROWSER = re.compile(r"\bagent-browser\b")
# Subcommands that do not touch a page (docs, session management) skip the host's page preparation.
_BROWSER_CALL = re.compile(r"\bagent-browser((?:\s+--?\S+)*)\s+([a-z][\w-]*)")
_NOT_PAGE = frozenset({"skills", "close", "install", "session", "profiles", "help", "dashboard", "upgrade"})
# Under the tool's 60s deadline, so a hung browser exits 124 from `timeout` itself before that.
BROWSER_TIMEOUT = 50
_PROJECT_ENV = "set -a; [ -f .env ] && . ./.env; set +a; "
_SCREENSHOT = re.compile(r"Screenshot saved to (\S+)")
MAX_SCREENSHOTS = 4
MAX_SCREENSHOT_BYTES = 3_000_000
_IMAGE_TYPES = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg", b"GIF8": "image/gif", b"RIFF": "image/webp"}
# Project images read_files hands over as pictures, not text.
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
# An edit whose old_string matches nowhere exactly matches again with typographic quotes, dashes and spaces made
# plain, then line by line ignoring trailing whitespace. Each plain character replaces one, so offsets hold.
_PLAIN = str.maketrans(
    {
        **dict.fromkeys(map(ord, "\u2018\u2019\u201a\u201b"), "'"),
        **dict.fromkeys(map(ord, "\u201c\u201d\u201e\u201f"), '"'),
        **dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-"),
        **dict.fromkeys(
            map(ord, "\u00a0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000"), " "
        ),
    }
)
_LINE = re.compile(r"[^\n]*(?:\n|$)")


def _occurrences(content: str, search: str) -> list[tuple[int, int]]:
    """Each non-overlapping (start, end) of `search` in `content`."""
    found, offset = [], content.find(search)
    while offset != -1:
        found.append((offset, offset + len(search)))
        offset = content.find(search, offset + len(search))
    return found


def _line_occurrences(content: str, search: str) -> list[tuple[int, int]]:
    """Whole-line runs of `content` equal to the lines of `search` once each is made plain and loses trailing
    whitespace; a run that would overlap an earlier one is skipped."""
    trailing_newline = search.endswith("\n")
    expected = search.split("\n")
    if trailing_newline:
        expected.pop()
    lines = []
    for match in _LINE.finditer(content):
        if not match[0]:
            continue
        newline = match[0].endswith("\n")
        text = match[0][:-1] if newline else match[0]
        lines.append((match.start(), match.end(), text, match.start() + len(text) - text.endswith("\r"), newline))
    found: list[tuple[int, int]] = []
    for index in range(len(lines)):
        actual = lines[index : index + len(expected)]
        if len(actual) != len(expected):
            continue
        if any(
            line[2].rstrip().translate(_PLAIN) != want.rstrip().translate(_PLAIN)
            for line, want in zip(actual, expected, strict=True)
        ):
            continue
        if trailing_newline and not actual[-1][4]:
            continue
        start, end = actual[0][0], actual[-1][1] if trailing_newline else actual[-1][3]
        if not any(other_end > start and other_start < end for other_start, other_end in found):
            found.append((start, end))
    return found


# What the model sees in place of a key (events.hide_secrets). Defined here, where writes are guarded, because
# events imports this module through storage.
HIDDEN = "<secret-hidden>"


def _refuse_hidden(before: dict[str, str | None], after: dict[str, str]) -> None:
    """A key the model was shown as HIDDEN must never be written back as that text: it would replace the key."""
    for path, content in after.items():
        if HIDDEN in content and HIDDEN not in (before.get(path) or ""):
            raise ValueError(
                f"{path}: {HIDDEN} stands for a key hidden from you; writing it would replace the key."
                " Read keys from the environment (process.env.NAME) instead of copying them."
            )


class FileWriteError(Exception):
    """A native upload failed; retire the sandbox rather than checkpoint partial writes."""


def project_path(path: str) -> str:
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts or "\\" in path:
        raise ValueError("Use a relative project path without traversal")
    if any(part in {".git", ".env", "node_modules", ".venv"} for part in p.parts):
        raise ValueError("That path is outside editable project files")
    if any(part.startswith(".env.") for part in p.parts):
        raise ValueError("Environment files are not editable")
    return str(p)


class FileEdit(BaseModel):
    path: str = Field(description="Path relative to the project root.")
    old_string: str = Field(description="Exact text to replace, unique in the file unless replace_all is set.")
    new_string: str = Field(description="The replacement text.")
    replace_all: bool = Field(default=False, description="Replace every match of old_string.")


class Workspace:
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.cache: dict[str, str] = {}
        self.revision = 0
        self.preview_revision = 0
        # Set by the runner: what must be true before agent-browser looks at the app.
        self.before_browser: Callable[[], Awaitable[None]] | None = None
        self.browser_timeouts = 0
        # agent-browser's page-error log only grows (its --clear leaves it, 0.38.1): count what was reported.
        self.page_errors_reported = 0

    async def read(self, path: str) -> str:
        path = project_path(path)
        if path not in self.cache:
            try:
                info = await self.sandbox.files.get_info(f"{ROOT}/{path}", request_timeout=10)
            except FileNotFoundException:
                raise ValueError(f"{path} does not exist; the request lists every project path") from None
            if info.size > MAX_FILE_BYTES:
                raise ValueError(
                    f"{path} is over {MAX_FILE_BYTES:,} bytes; read part of it with execute_command,"
                    f" such as sed -n '1,200p' {path}"
                )
            reader = await self.sandbox.files.read(
                f"{ROOT}/{path}",
                format="stream",
                gzip=True,
                request_timeout=20,
                stream_idle_timeout=10,
            )
            data = bytearray()
            async with reader:
                async for chunk in reader:
                    # Metadata can race a file change; enforce the bound on decoded transfer bytes too.
                    if len(data) + len(chunk) > MAX_FILE_BYTES:
                        raise ValueError(
                            f"{path} is over {MAX_FILE_BYTES:,} bytes; read part of it with execute_command,"
                            f" such as sed -n '1,200p' {path}"
                        )
                    data.extend(chunk)
            content = data.decode("utf-8")
            self.cache[path] = content
        return self.cache[path]

    async def write(self, changes: dict[str, str]) -> None:
        """Upload files as one batch; every edit goes through here so revision and cache stay in step."""
        self.cache.clear()
        self.revision += 1
        try:
            # E2B owns batching, compression and version fallback. Uploads are
            # not atomic: an error must stop the run before any checkpoint.
            await self.sandbox.files.write_files(
                [{"path": f"{ROOT}/{path}", "data": content} for path, content in changes.items()],
                gzip=True,
                request_timeout=20,
            )
        except Exception:
            raise FileWriteError("File upload did not complete; sandbox cleanup is required") from None
        self.cache.update(changes)

    async def write_files(self, files: list[tuple[str, str]]) -> tuple[dict[str, str | None], dict[str, str]]:
        """Create or replace whole files: the text each one replaced, and what was written."""
        paths = [project_path(path) for path, _ in files]
        if len(set(paths)) != len(paths):
            raise ValueError("A batch must not write the same path twice")
        if sum(len(content.encode()) for _, content in files) > 500_000:
            raise ValueError("The files in one write_files call total over 500,000 bytes; split them across calls")
        changes = {path: content for path, (_, content) in zip(paths, files, strict=True)}
        before = dict(zip(paths, await asyncio.gather(*(self.previous(path) for path in paths)), strict=True))
        _refuse_hidden(before, changes)
        await self.write(changes)
        return before, changes

    async def read_many(self, paths: list[str]) -> dict[str, Any]:
        """Text files as text; images take the screenshot path: stored, shown, attached for the model."""
        result = {}
        images = []
        for path in paths:
            if PurePosixPath(path).suffix.lower() not in IMAGE_SUFFIXES:
                result[path] = await self.read(path)
                continue
            image = await self.image(f"{ROOT}/{project_path(path)}")
            result[path] = "[image, shown to the user]" if image else "[not a readable image under 3 MB]"
            if image:
                images.append(image)
        return {"ok": True, "files": result, **({"_screenshots": images} if images else {})}

    async def image(self, path: str) -> tuple[bytes, str] | None:
        """An image file as (bytes, media type); None when it is missing, too large or not an image."""
        try:
            info = await self.sandbox.files.get_info(path, request_timeout=10)
            if info.size > MAX_SCREENSHOT_BYTES:
                return None
            data = bytes(await self.sandbox.files.read(path, format="bytes", request_timeout=20))
        except (SandboxException, httpx.HTTPError):
            return None
        media = next((kind for magic, kind in _IMAGE_TYPES.items() if data.startswith(magic)), None)
        return (data, media) if media else None

    async def screenshots(self, output: str) -> list[tuple[bytes, str]]:
        """The images a browser command reported saving; unreadable ones are skipped."""
        paths = list(dict.fromkeys(_SCREENSHOT.findall(output)))[:MAX_SCREENSHOTS]
        images = [await self.image(path if path.startswith("/") else f"{ROOT}/{path}") for path in paths]
        return [image for image in images if image]

    async def run(self, command: str) -> dict[str, Any]:
        """A command the model asked for, once the host's policy allows it; agent-browser goes through browse."""
        if reason := command_policy.refusal(command):
            raise ValueError(reason)
        if command_policy.installs_at_root(command) and not await self.sandbox.files.exists(f"{ROOT}/package.json"):
            raise ValueError(
                "The project root has no package.json, so npm would create a stray project here. Run it"
                " in the folder that owns the package (workspace.packages): cd <folder> && npm install ..."
            )
        if BROWSER.search(command):
            return await self.browse(command)
        try:
            # The kit's own instructions (alembic revision) need DATABASE_URL, as project._run provides.
            return await self.command(_PROJECT_ENV + command)
        finally:
            self.cache.clear()
            # Shell can modify files even on failed commands.
            self.revision += 1

    async def browse(self, command: str) -> dict[str, Any]:
        """Run a command using agent-browser; add what the page reported and the screenshots it saved."""
        drives_page = any(verb not in _NOT_PAGE for _, verb in _BROWSER_CALL.findall(command))
        if drives_page and self.before_browser is not None:
            await self.before_browser()
        try:
            result = await self.command(f"{_PROJECT_ENV}timeout -k 5 {BROWSER_TIMEOUT} bash -c {shlex.quote(command)}")
        finally:
            self.cache.clear()
            self.revision += 1
            # A browser command reads the app; it does not make the next one restart the preview.
            self.preview_revision = self.revision
        timed_out = result.get("exit_code") == 124
        self.browser_timeouts = self.browser_timeouts + 1 if timed_out else 0
        if timed_out:
            result["error"] = f"agent-browser did not finish within {BROWSER_TIMEOUT}s"
        if self.browser_timeouts >= 2:
            # A wedged browser session does not recover alone: restart it after repeated timeouts.
            await self.command("agent-browser close --all", timeout_seconds=20)
            self.browser_timeouts = 0
            result["browser_restarted"] = "The browser stopped responding twice and was restarted. Open the page again."
        elif drives_page and not timed_out:
            result["page_check"] = await self.page_check()
        # `_screenshots` is for the runner, which stores them; it never reaches the model as JSON.
        result["_screenshots"] = await self.screenshots(result.get("stdout", ""))
        return result

    async def page_check(self) -> dict[str, Any]:
        """What the page reported since the last check: a page can look right and still throw."""
        result = await self.command("timeout 25 python3 -c " + shlex.quote(_PAGE_CHECK), timeout_seconds=30)
        try:
            found = json.loads(result["stdout"])
        except ValueError:
            return {"summary": "The page's errors could not be read"}
        counts = found.pop("counts")
        total = found.pop("page_errors_total")
        # A shorter log means a new browser session, whose errors are all new.
        new = total - self.page_errors_reported if total >= self.page_errors_reported else total
        self.page_errors_reported = total
        found["page_errors"] = found["page_errors"][-new:] if new else []
        parts = [
            (new, "new uncaught error"),
            (counts["console_errors"], "console error"),
            (counts["warnings"], "warning"),
            (counts["failed_requests"], "failed request"),
        ]
        summary = ", ".join(f"{count} {label}{'' if count == 1 else 's'}" for count, label in parts)
        return {"summary": summary, **{key: value for key, value in found.items() if value}}

    async def command(self, command: str, timeout_seconds: int = 60, max_output: int = MAX_OUTPUT) -> dict[str, Any]:
        return await run_command(
            self.sandbox, command, cwd=ROOT, timeout_seconds=timeout_seconds, max_output=max_output
        )

    async def edit(self, edits: list[FileEdit]) -> tuple[dict[str, str | None], dict[str, str], list[tuple[str, int]]]:
        """Apply exact-text edits in order, several to one file allowed; all validate before any is written.
        Returns each file's text before and after, and where each edit landed: the file's text just after it and the
        offset of its first replacement."""
        updated: dict[str, str] = {}
        originals: dict[str, str | None] = {}
        landed: list[tuple[str, int]] = []
        for number, item in enumerate(edits, 1):
            path = project_path(item.path)
            if not item.old_string or item.old_string == item.new_string:
                raise ValueError(f"Edit {number}: old_string must be non-empty and differ from new_string")
            if path in updated:
                content = updated[path]
            else:
                content = originals[path] = await self.read(path)
            spans = (
                _occurrences(content, item.old_string)
                or _occurrences(content.translate(_PLAIN), item.old_string.translate(_PLAIN))
                or _line_occurrences(content, item.old_string)
            )
            if not spans:
                raise ValueError(f"Edit {number} ({path}): old_string was not found; copy the text exactly")
            if len(spans) > 1 and not item.replace_all:
                raise ValueError(
                    f"Edit {number} ({path}): old_string matches {len(spans)} places; add context or set replace_all"
                )
            pieces, kept = [], 0
            for start, end in spans:
                pieces += [content[kept:start], item.new_string]
                kept = end
            updated[path] = content = "".join(pieces) + content[kept:]
            landed.append((content, spans[0][0]))
            if len(updated[path].encode()) > MAX_FILE_BYTES:
                raise ValueError(
                    f"Edit {number} ({path}): the file would be over {MAX_FILE_BYTES:,} bytes; split it into smaller"
                    " files"
                )
        _refuse_hidden(originals, updated)
        await self.write(updated)
        return originals, updated, landed

    async def previous(self, path: str) -> str | None:
        """Text a write is about to replace: "" for a new file, None when it cannot be read."""
        if not await self.sandbox.files.exists(f"{ROOT}/{path}"):
            return ""
        try:
            return await self.read(path)
        except (ValueError, UnicodeDecodeError):
            return None


# Skips what checkpoints skip (agent/sandbox/archive.py EXCLUDED) and shares their limit.
LIST_FILES_JS = r"""
const fs=require('fs'),path=require('path');const out=[];
const skip=['node_modules','.git','.venv','dist','.next','.cache','__pycache__','.env'];
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){
 if(skip.includes(e.name)||e.name.startsWith('.env.'))continue;
 const p=path.join(dir,e.name);
 if(e.isDirectory())walk(p);else if(e.isFile())out.push(p);
 if(out.length>600)throw Error('Project file limit exceeded');
}}walk('.');console.log(JSON.stringify(out));
"""


async def list_files(sandbox) -> list[str]:
    result = await sandbox.commands.run("node -e " + shlex.quote(LIST_FILES_JS), cwd=ROOT, timeout=20)
    return [project_path(p) for p in json.loads(result.stdout)]


# Runs in the sandbox after a page command. agent-browser 0.38.1 prints uncaught errors as empty
# lines in its text output, so this reads --json. Console and request logs are cleared, so the next
# check sees only new entries; the page-error log cannot be, so the host counts it (page_check).
_PAGE_CHECK = r"""
import json, subprocess
def read(*command):
    try:
        out = subprocess.run(["agent-browser", *command, "--json"], capture_output=True, text=True, timeout=8)
        return json.loads(out.stdout).get("data") or {}
    except Exception:
        return {}
errors = [str(e.get("text", ""))[:500] for e in read("errors").get("errors", [])]
messages = read("console").get("messages", [])
failed = [
    f"{r.get('method')} {r.get('url')} {r.get('status')}"[:300]
    for r in read("network", "requests").get("requests", [])
    if isinstance(r.get("status"), int) and r["status"] >= 400 and not str(r.get("url", "")).endswith("/favicon.ico")
]
for command in (["errors"], ["console"], ["network", "requests"]):
    subprocess.run(["agent-browser", *command, "--clear"], capture_output=True, timeout=8)
print(json.dumps({
    "page_errors_total": len(errors),
    "counts": {
        "console_errors": sum(m.get("type") == "error" for m in messages),
        "warnings": sum(m.get("type") == "warning" for m in messages),
        "failed_requests": len(failed),
    },
    "page_errors": errors[-10:],
    "console": [
        f"[{m.get('type')}] {m.get('text', '')}"[:500] for m in messages if m.get("type") in ("error", "warning")
    ][-20:],
    "failed_requests": failed[-10:],
}))
"""
