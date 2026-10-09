"""Typed, source-preserving tools. Sandbox code never receives API credentials."""

import asyncio
import difflib
import json
import re
import shlex
from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from typing import Annotated, Any

import httpx
from e2b import SandboxException
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..sandbox.commands import MAX_OUTPUT, run_command

ROOT = "/home/user/react-app"
# Starting a second dev server breaks the host-owned preview (spec 8: services are started
# by the host from stack.json). Builds (`vite build`, `next build`) stay allowed.
# Long-running processes the kits already run (sandbox/kits/*/stack.json services) or that never exit.
DEV_SERVER = re.compile(
    r"npm\s+run\s+(?:dev|start)\b|\buvicorn\b|\bnext\s+(?:dev|start)\b|\bvite(?:\.js)?(?!\s+build)(?:\s|$)"
    r"|\b(?:tsx|node)\b[^|;&]*\bsrc/index\.ts\b|\bmongod\b|\bpg_ctl\b|\bsystemctl\s+(?:start|restart)\b|\btail\s+-f\b"
)
# A search names a server without starting one: `ps aux | grep uvicorn` is diagnosis. Quoted
# patterns are kept whole, so a `|` inside `grep -E "a|uvicorn"` does not end the segment.
_SEARCH = re.compile(r"\b(?:grep|egrep|pgrep)\b(?:\s+(?:\"[^\"]*\"|'[^']*'|[^\s|;&]+))*")
# Spec 6 migration gate: the host applies migrations, after checking they keep saved data.
MIGRATE = re.compile(
    r"\balembic\s+(?:upgrade|downgrade|stamp)\b|\bnpm\s+run\s+migrate\b|\bdrizzle-kit\s+(?:migrate|push)\b"
    r"|\b(?:tsx|node)\s+(?:\S*/)?(?:db/migrate|src/db)\.ts\b|\bmongosh\b|\bpsql\b|\b(?:create|drop)_all\b"
)
# An install run where no package.json exists creates a stray project there (a second copy of React,
# for one). Only the no-directory form is checked: `cd <dir> &&` and `--prefix` name a directory.
_NPM_INSTALL = re.compile(r"\bnpm\s+(?:i|install|add)\b")
_NAMES_DIR = re.compile(r"\bcd\s+\S|--prefix\b")
_RELATIVE_INSTALL = re.compile(r"npm\s+(?:i|install)\s+(?:\.{1,2})(?:\s|$)")
# About 25k tokens. Bounds reads, writes and edits alike, so a file the model
# can write it can also read back and edit; lockfile-sized reads are refused rather than resent every turn.
MAX_FILE_BYTES = 100_000
# What the chat shows of an edit, never what the model sees: one line of context around each change
# and the whole diff, uncapped.
_DIFF_CONTEXT = 1


def file_diffs(before: dict[str, str | None], after: dict[str, str]) -> list[dict[str, Any]]:
    """Line diffs for the chat, one per file, whole. A None `before` is a file whose old text was
    unreadable: it gets counts but no hunks, marked truncated."""
    diffs = []
    for path, new_text in after.items():
        old_text = before.get(path)
        old, new = (old_text or "").splitlines(), new_text.splitlines()
        matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
        opcodes = matcher.get_opcodes()
        added = sum(j2 - j1 for tag, _, _, j1, j2 in opcodes if tag in {"replace", "insert"})
        removed = sum(i2 - i1 for tag, i1, i2, _, _ in opcodes if tag in {"replace", "delete"})
        hunks: list[list[list[Any]]] = []
        truncated = old_text is None
        for group in [] if truncated else matcher.get_grouped_opcodes(_DIFF_CONTEXT):
            lines: list[list[Any]] = []
            for tag, i1, i2, j1, j2 in group:
                if tag == "equal":
                    lines += [[" ", j1 + k + 1, new[j1 + k]] for k in range(j2 - j1)]
                    continue
                lines += [["-", i + 1, old[i]] for i in range(i1, i2)]
                lines += [["+", j + 1, new[j]] for j in range(j1, j2)]
            hunks.append(lines)
        diffs.append(
            {
                "path": path,
                "created": old_text == "",
                "added": added,
                "removed": removed,
                "hunks": hunks,
                "truncated": truncated,
            }
        )
    return diffs


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


class FileChange(BaseModel):
    path: str
    content: str = Field(max_length=MAX_FILE_BYTES)


class FileEdit(BaseModel):
    path: str
    old_string: str
    new_string: str
    replace_all: bool = False


class WorkspaceTools:
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
            info = await self.sandbox.files.get_info(f"{ROOT}/{path}", request_timeout=10)
            if info.size > MAX_FILE_BYTES:
                raise ValueError("File exceeds the source-size limit")
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
                        raise ValueError("File exceeds the source-size limit")
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

    async def edit(self, edits: list[FileEdit]) -> dict[str, Any]:
        """Apply exact-text edits in order, several to one file allowed; all validate before any is written."""
        updated: dict[str, str] = {}
        originals: dict[str, str | None] = {}
        for number, item in enumerate(edits, 1):
            path = project_path(item.path)
            if not item.old_string or item.old_string == item.new_string:
                raise ValueError(f"Edit {number}: old_string must be non-empty and differ from new_string")
            if path in updated:
                content = updated[path]
            else:
                content = originals[path] = await self.read(path)
            count = content.count(item.old_string)
            if count == 0:
                raise ValueError(f"Edit {number} ({path}): old_string was not found; copy the text exactly")
            if count > 1 and not item.replace_all:
                raise ValueError(
                    f"Edit {number} ({path}): old_string matches {count} places; add context or set replace_all"
                )
            updated[path] = content.replace(item.old_string, item.new_string, -1 if item.replace_all else 1)
            if len(updated[path].encode()) > MAX_FILE_BYTES:
                raise ValueError(f"Edit {number} ({path}): file exceeds the source-size limit")
        await self.write(updated)
        # `_diffs` is for the chat; the runner removes it before the result reaches the model.
        diffs = await asyncio.to_thread(file_diffs, originals, updated)
        return {"ok": True, "changed_files": list(updated), "edits": len(edits), "_diffs": diffs}

    async def previous(self, path: str) -> str | None:
        """Text a write is about to replace: "" for a new file, None when it cannot be read."""
        if not await self.sandbox.files.exists(f"{ROOT}/{path}"):
            return ""
        try:
            return await self.read(path)
        except (ValueError, UnicodeDecodeError):
            return None

    def definitions(self):
        @tool
        async def read_files(
            paths: Annotated[list[str], Field(min_length=1, max_length=12)],
        ) -> dict[str, Any]:
            """Read relevant project files together. Unchanged files are cached; avoid repeat reads.
            Images (png, jpg, gif, webp) are shown to the user, and to you when you can read images."""
            return await self.read_many(paths)

        @tool
        async def write_files(
            files: Annotated[list[FileChange], Field(min_length=1, max_length=12)],
        ) -> dict[str, Any]:
            """Create or replace source files. Pass typed objects; content is written exactly as supplied."""
            paths = [project_path(f.path) for f in files]
            if len(set(paths)) != len(paths):
                raise ValueError("A batch must not write the same path twice")
            if sum(len(f.content.encode()) for f in files) > 500_000:
                raise ValueError("Batch is too large")
            changes = {path: item.content for path, item in zip(paths, files, strict=True)}
            before = dict(zip(paths, await asyncio.gather(*(self.previous(path) for path in paths)), strict=True))
            await self.write(changes)
            return {"ok": True, "changed_files": paths, "_diffs": await asyncio.to_thread(file_diffs, before, changes)}

        # Edit in place: a rewrite pays for the whole file as output, then resends it on every later turn.
        @tool(
            description=(
                "Replace exact text in existing files, several edits and files per call, applied in order."
                " Prefer this to write_files for changes to part of a file. Each old_string must match"
                " exactly once, whitespace included; add surrounding lines to make it unique, or set"
                " replace_all. Nothing is written unless every edit applies."
            )
        )
        async def edit_files(edits: Annotated[list[FileEdit], Field(min_length=1, max_length=20)]) -> dict[str, Any]:
            return await self.edit(edits)

        @tool(
            description=(
                "Run a bounded shell command in the project: diagnostics, skill discovery, and checking the"
                " running app in a browser with the agent-browser CLI. The project's services are already"
                " running and reload when files change: never start a dev server. Do not install relative"
                " paths as packages. Screenshots saved by agent-browser are shown to the user."
            )
        )
        async def execute_command(command: str) -> dict[str, Any]:
            if len(command) > 2000:
                raise ValueError("Command is too long")
            if _RELATIVE_INSTALL.search(command):
                raise ValueError("Relative imports are not npm packages")
            if DEV_SERVER.search(_SEARCH.sub("", command)):
                raise ValueError("The project's services are already running; do not start another server")
            if (
                _NPM_INSTALL.search(command)
                and not _NAMES_DIR.search(command)
                and not await self.sandbox.files.exists(f"{ROOT}/package.json")
            ):
                raise ValueError(
                    "The project root has no package.json, so npm would create a stray project here. Run it"
                    " in the folder that owns the package (workspace.packages): cd <folder> && npm install ..."
                )
            if MIGRATE.search(command):
                raise ValueError(
                    "Do not migrate or edit the database directly: write the migration file."
                    " The host applies new migrations before each agent-browser command and when you finish."
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

        return [read_files, write_files, edit_files, execute_command]


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
    import shlex

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
