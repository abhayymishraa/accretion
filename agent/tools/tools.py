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
    r"|\b(?:tsx|node)\b[^|;&]*\bsrc/index\.ts\b|\bmongod\b|\bpg_ctl\b|\bsystemctl\b|\btail\s+-f\b"
)
# Spec 6 migration gate: the host applies migrations, after checking they keep saved data.
MIGRATE = re.compile(
    r"\balembic\s+(?:upgrade|downgrade|stamp)\b|\bnpm\s+run\s+migrate\b|\bdrizzle-kit\s+(?:migrate|push)\b"
    r"|\b(?:tsx|node)\s+(?:\S*/)?(?:db/migrate|src/db)\.ts\b|\bmongosh\b|\bpsql\b"
)
MAX_FILE_BYTES = 200_000


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

    async def command(self, command: str, timeout_seconds: int = 60, max_output: int = MAX_OUTPUT) -> dict[str, Any]:
        return await run_command(self.sandbox, command, cwd=ROOT, timeout=timeout_seconds, max_output=max_output)

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
            self.cache.clear()
            self.revision += 1
            try:
                # E2B owns batching, compression and version fallback. Uploads are
                # not atomic: an error must stop the run before any checkpoint.
                await self.sandbox.files.write_files(
                    [{"path": f"{ROOT}/{path}", "data": item.content} for path, item in zip(paths, files, strict=True)],
                    gzip=True,
                    request_timeout=20,
                )
            except Exception:
                raise FileWriteError("File upload did not complete; sandbox cleanup is required") from None
            self.cache.update({path: item.content for path, item in zip(paths, files, strict=True)})
            return {"ok": True, "changed_files": paths}

        @tool(
            description=(
                "Run a bounded shell command in the project for concrete diagnostics or"
                " requested skill discovery. The project's services are already running:"
                " never start a dev server. Do not install relative paths as packages."
            )
        )
        async def execute_command(command: str) -> dict[str, Any]:
            if len(command) > 2000:
                raise ValueError("Command is too long")
            if re.search(r"npm\s+(?:i|install)\s+(?:\.{1,2})(?:\s|$)", command):
                raise ValueError("Relative imports are not npm packages")
            if DEV_SERVER.search(command):
                raise ValueError("The project's services are already running; do not start another server")
            if MIGRATE.search(command):
                raise ValueError(
                    "Do not migrate or edit the database directly: write the migration file and finish."
                    " The host applies new migrations when it checks your work."
                )
            try:
                return await self.command(command)
            finally:
                self.cache.clear()
                # Shell can modify files even on failed commands.
                self.revision += 1

        @tool(
            description=(
                "Inspect the page or exercise its main workflow with up to eight CSS-selector"
                " steps ending in an expect_* assertion. Supply a meaningful sequence for"
                " desktop and mobile before finishing; the host replays the latest sequence"
                " for each after the final edit. Fresh isolated browser state each call. Only"
                " local UI interactions: network writes and external navigation are blocked."
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

        return [read_files, write_files, execute_command, inspect_preview]


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
