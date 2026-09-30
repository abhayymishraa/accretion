"""Typed, source-preserving tools. Sandbox code never receives API credentials."""

import json
import re
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..sandbox.browser import PreviewStep
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
# About 25k tokens, Claude Code's Read limit. Bounds reads, writes and edits alike, so a file the model
# can write it can also read back and edit; lockfile-sized reads are refused rather than resent every turn.
MAX_FILE_BYTES = 100_000


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


class WorkspaceTools:
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.cache: dict[str, str] = {}
        self.revision = 0
        self.preview_revision = 0
        self.screenshot_attempts = 0
        self.preview_checks = {}

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

    async def command(self, command: str, timeout_seconds: int = 60, max_output: int = MAX_OUTPUT) -> dict[str, Any]:
        return await run_command(self.sandbox, command, cwd=ROOT, timeout=timeout_seconds, max_output=max_output)

    async def edit(self, path: str, old_string: str, new_string: str, replace_all: bool) -> dict[str, Any]:
        """Exact-text replacement for edit_file; kept here so the tool list stays declarative."""
        path = project_path(path)
        if not old_string or old_string == new_string:
            raise ValueError("old_string must be non-empty and differ from new_string")
        content = await self.read(path)
        count = content.count(old_string)
        if count == 0:
            raise ValueError("old_string was not found; read the file and copy the text exactly")
        if count > 1 and not replace_all:
            raise ValueError(f"old_string matches {count} places; include more surrounding text or set replace_all")
        updated = content.replace(old_string, new_string, -1 if replace_all else 1)
        if len(updated.encode()) > MAX_FILE_BYTES:
            raise ValueError("File exceeds the source-size limit")
        await self.write({path: updated})
        return {"ok": True, "changed_files": [path], "replacements": count if replace_all else 1}

    def definitions(self):
        @tool
        async def read_files(
            paths: Annotated[list[str], Field(min_length=1, max_length=12)],
        ) -> dict[str, Any]:
            """Read relevant project files together. Unchanged files are cached; avoid repeat reads."""
            result = {}
            for path in paths:
                result[path] = await self.read(path)
            return {"ok": True, "files": result}

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
            await self.write({path: item.content for path, item in zip(paths, files, strict=True)})
            return {"ok": True, "changed_files": paths}

        # Every surveyed harness edits in place (Claude Code Edit, Codex apply_patch, OpenCode edit):
        # a rewrite pays for the whole file as output, then resends it on every later turn.
        @tool(
            description=(
                "Replace exact text in one existing file. Prefer this to write_files for changes to part of"
                " a file. old_string must match exactly once, whitespace included; add surrounding lines to"
                " make it unique, or set replace_all to change every match."
            )
        )
        async def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict[str, Any]:
            return await self.edit(path, old_string, new_string, replace_all)

        @tool(
            description=(
                "Run a bounded shell command in the project for concrete diagnostics or"
                " requested skill discovery. The project's services are already running and reload"
                " when files change: never start a dev server. Do not install relative paths as packages."
            )
        )
        async def execute_command(command: str) -> dict[str, Any]:
            if len(command) > 2000:
                raise ValueError("Command is too long")
            if re.search(r"npm\s+(?:i|install)\s+(?:\.{1,2})(?:\s|$)", command):
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
                    "Do not migrate or edit the database directly: write the migration file and finish."
                    " The host applies new migrations when it checks your work."
                )
            try:
                # The kit's own instructions (alembic revision) need DATABASE_URL, as project._run provides.
                return await self.command(f"set -a; [ -f .env ] && . ./.env; set +a; {command}")
            finally:
                self.cache.clear()
                # Shell can modify files even on failed commands.
                self.revision += 1

        @tool(
            description=(
                "Inspect the page or exercise its main workflow with up to eight CSS-selector"
                " steps ending in an expect_* assertion. Supply a meaningful sequence for"
                " desktop and mobile before finishing; the host replays the latest sequence"
                " for each after the final edit. Fresh isolated browser state each call. Steps may"
                " create or change data through this app's own API; the database is restored after"
                " each check. Writes to other sites and external navigation are blocked."
                " Optional screenshot returns one viewport image, at most twice per run. Does"
                " not replace final build checks."
            )
        )
        async def inspect_preview(
            viewport: Literal["desktop", "mobile"] = "desktop",
            path: str = "/",
            screenshot: bool = False,
            steps: Annotated[list[PreviewStep], Field(max_length=8)] = Field(default=[]),
        ) -> dict[str, Any]:
            from ..sandbox.browser import inspect_preview as inspect

            return await inspect(self, viewport=viewport, path=path, screenshot=screenshot, steps=steps)

        return [read_files, write_files, edit_file, execute_command, inspect_preview]


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
