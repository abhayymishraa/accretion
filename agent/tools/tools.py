"""Typed, source-preserving tools. Sandbox code never receives API credentials."""
import json
import re
from pathlib import PurePosixPath
from typing import Annotated, Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..sandbox.commands import run_command
from ..sandbox.browser import PreviewStep

ROOT = '/home/user/react-app'
MAX_FILE_BYTES = 200_000


class FileWriteError(Exception):
    """A native upload failed; retire the sandbox rather than checkpoint partial writes."""


def project_path(path: str) -> str:
    p = PurePosixPath(path)
    if not path or p.is_absolute() or '..' in p.parts or '\\' in path:
        raise ValueError('Use a relative project path without traversal')
    if any(part in {'.git', '.env', 'node_modules', '.venv'} for part in p.parts):
        raise ValueError('That path is outside editable project files')
    if any(part.startswith('.env.') for part in p.parts):
        raise ValueError('Environment files are not editable')
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
            info = await self.sandbox.files.get_info(f'{ROOT}/{path}', request_timeout=10)
            if info.size > MAX_FILE_BYTES:
                raise ValueError('File exceeds the source-size limit')
            reader = await self.sandbox.files.read(f'{ROOT}/{path}', format='stream', gzip=True,
                request_timeout=20, stream_idle_timeout=10)
            data = bytearray()
            async with reader:
                async for chunk in reader:
                    # Metadata can race a file change; enforce the bound on decoded transfer bytes too.
                    if len(data) + len(chunk) > MAX_FILE_BYTES:
                        raise ValueError('File exceeds the source-size limit')
                    data.extend(chunk)
            content = data.decode('utf-8')
            self.cache[path] = content
        return self.cache[path]

    async def command(self, command: str, timeout: int = 60) -> dict:
        return await run_command(self.sandbox, command, cwd=ROOT, timeout=timeout)

    def definitions(self):
        @tool
        async def read_files(paths: Annotated[list[str], Field(min_length=1, max_length=12)]) -> dict:
            """Read relevant project files together. Unchanged files are cached; avoid repeat reads."""
            result = {}
            for path in paths:
                result[path] = await self.read(path)
            return {'ok': True, 'files': result}

        @tool
        async def write_files(files: Annotated[list[FileChange], Field(min_length=1, max_length=12)]) -> dict:
            """Create or replace source files. Pass typed objects; content is written exactly as supplied."""
            paths = [project_path(f.path) for f in files]
            if len(set(paths)) != len(paths):
                raise ValueError('A batch must not write the same path twice')
            if sum(len(f.content.encode()) for f in files) > 500_000:
                raise ValueError('Batch is too large')
            self.cache.clear()
            self.revision += 1
            try:
                # E2B owns batching, compression and version fallback. Uploads are
                # not atomic: an error must stop the run before any checkpoint.
                await self.sandbox.files.write_files(
                    [{'path': f'{ROOT}/{path}', 'data': item.content} for path, item in zip(paths, files)],
                    gzip=True, request_timeout=20)
            except Exception:
                raise FileWriteError('File upload did not complete; sandbox cleanup is required') from None
            self.cache.update({path: item.content for path, item in zip(paths, files)})
            return {'ok': True, 'changed_files': paths}

        @tool
        async def execute_command(command: str) -> dict:
            """Run a bounded shell command in the project for concrete diagnostics or requested skill discovery. The dev server is already running: never start it again. Do not install relative paths as packages."""
            if len(command) > 2000:
                raise ValueError('Command is too long')
            if re.search(r'npm\s+(?:i|install)\s+(?:\.{1,2})(?:\s|$)', command):
                raise ValueError('Relative imports are not npm packages')
            if re.search(r'npm\s+run\s+(?:dev|start)\b', command):
                raise ValueError('The template already runs the dev server')
            try:
                return await self.command(command)
            finally:
                self.cache.clear()
                # Shell can modify files even on failed commands.
                self.revision += 1

        @tool
        async def inspect_preview(viewport: Literal['desktop', 'mobile'] = 'desktop', path: str = '/', screenshot: bool = False,
                                  steps: Annotated[list[PreviewStep], Field(max_length=8)] = []) -> dict:
            """Inspect the page or exercise its main workflow with up to eight CSS-selector steps ending in an expect_* assertion. Supply a meaningful sequence for desktop and mobile before finishing; the host replays the latest sequence for each after the final edit. Fresh isolated browser state each call. Only local UI interactions: network writes and external navigation are blocked. Optional screenshot returns one viewport image, at most twice per run. Does not replace final build checks."""
            from ..sandbox.browser import inspect_preview as inspect
            return await inspect(self, viewport=viewport, path=path, screenshot=screenshot, steps=steps)

        return [read_files, write_files, execute_command, inspect_preview]


LIST_FILES_JS = r"""
const fs=require('fs'),path=require('path');const out=[];
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){
 if(['node_modules','.git','dist','.next','.env'].includes(e.name)||e.name.startsWith('.env.'))continue;
 const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else if(e.isFile())out.push(p);
 if(out.length>250)throw Error('Project file limit exceeded');
}}walk('.');console.log(JSON.stringify(out));
"""


async def list_files(sandbox) -> list[str]:
    import shlex
    result = await sandbox.commands.run('node -e ' + shlex.quote(LIST_FILES_JS), cwd=ROOT, timeout=20)
    return [project_path(p) for p in json.loads(result.stdout)]
