"""The project tools the model calls: their schemas and results. The sandbox work is agent/sandbox/workspace.py."""

import asyncio
from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..sandbox.workspace import MAX_FILE_BYTES, FileEdit, Workspace
from .public_tools import file_diffs


class FileChange(BaseModel):
    path: str
    content: str = Field(max_length=MAX_FILE_BYTES)


def definitions(workspace: Workspace):
    @tool(
        description=(
            "Read relevant project files together. Unchanged files are cached; avoid repeat reads."
            " Images (png, jpg, gif, webp) are shown to the user, and to you when you can read images."
        )
    )
    async def read_files(paths: Annotated[list[str], Field(min_length=1, max_length=12)]) -> dict[str, Any]:
        return await workspace.read_many(paths)

    @tool
    async def write_files(
        files: Annotated[list[FileChange], Field(min_length=1, max_length=12)],
    ) -> dict[str, Any]:
        """Create or replace source files. Pass typed objects; content is written exactly as supplied."""
        before, changes = await workspace.write_files([(f.path, f.content) for f in files])
        diffs = await asyncio.to_thread(file_diffs, before, changes)
        return {"ok": True, "changed_files": list(changes), "_diffs": diffs}

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
        originals, updated = await workspace.edit(edits)
        # `_diffs` is for the chat; the runner removes it before the result reaches the model.
        diffs = await asyncio.to_thread(file_diffs, originals, updated)
        return {"ok": True, "changed_files": list(updated), "edits": len(edits), "_diffs": diffs}

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
        return await workspace.run(command)

    return [read_files, write_files, edit_files, execute_command]
