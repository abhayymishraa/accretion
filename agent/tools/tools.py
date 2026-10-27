"""The tools the model calls: their schemas and results. The sandbox work is agent/sandbox/workspace.py."""

import asyncio
import io
import re
import zipfile
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..sandbox.workspace import MAX_FILE_BYTES, FileEdit, Workspace
from .public_tools import file_diffs

# The plan the user approves; it lives in the project, so every revision keeps it.
PLAN_FILE = ".accretion/plan.md"
# A title or part heading a model starts a plan part with: the host writes those itself.
_LEADING_HEADING = re.compile(r"\A\s*#{1,2} [^\n]*\n")
# What a question's reads of the saved app may return.
MAX_FILE_CHARS = 20_000
MAX_FILES_PER_READ = 6
MAX_LISTED = 400


class FileChange(BaseModel):
    path: str
    content: str = Field(max_length=MAX_FILE_BYTES)


def definitions(workspace: Workspace, read_database: Callable[[str], Awaitable[dict[str, Any]]], *, planning: bool):
    # Imported here, not at the top: workflow imports the runner, which imports this module.
    from ..run.workflow import WorkflowDecision

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

    @tool
    async def request_decision(
        summary: str,
        question: str,
        options: list[str] = Field(default=[]),
        secrets: list[str] = Field(default=[]),
    ) -> dict[str, Any]:
        """Ask the user one question, only for a newly discovered choice that changes the result or a key the app
        needs. Never combine with other calls. Supply the question and up to three suggested answers, each within
        300 characters. To get keys the app needs from the user, name them in secrets: the user types each value
        into a field on the card that only the app receives. Never ask for a key's value in the question or the
        options.
        """
        decision = WorkflowDecision(
            kind="clarify", summary=summary, question=question, options=options, secrets=secrets
        )
        return {"ok": True, "decision": decision.model_dump()}

    @tool
    async def query_database(sql: str) -> dict[str, Any]:
        """Run one read-only SQL query on the app's Supabase database and get the rows back, to check its tables,
        columns, policies and data. It cannot change anything: schema changes go in migration files, which the host
        applies. Only works once the user has connected Supabase."""
        # Present in every build, so connecting Supabase never changes the tool list, the start of the cached prefix.
        return await read_database(sql)

    if planning:
        # Plan mode reads, and changes one file, the plan, through write_plan: no commands and no connected
        # services, since either can change files.
        @tool
        async def write_plan(title: str, summary: str, for_user: str, for_builder: str) -> dict[str, Any]:
            """Save the plan for the user to approve, replacing any earlier one, and stop. title names the app or the
            change; summary is one or two plain sentences on what will be built; for_user and for_builder are the two
            parts the plan rules describe, in markdown, without headings. Never combine with other calls."""
            # The host writes the headings, so every plan splits the same way whatever earlier plans looked like.
            user, builder = (_LEADING_HEADING.sub("", part).strip() for part in (for_user, for_builder))
            # The chat card folds the builder's part, found by its heading.
            plan = f"# {title.strip()}\n\n## What you'll get\n{user}\n\n## How it will be built\n{builder}\n"
            decision = WorkflowDecision(kind="plan", summary=summary, plan=plan)
            await workspace.write({PLAN_FILE: decision.plan})
            return {"ok": True, "changed_files": [PLAN_FILE], "decision": decision.model_dump()}

        return [read_files, request_decision, write_plan]
    return [read_files, write_files, edit_files, execute_command, request_decision, query_database]


def history_search(search: Callable[[str], Awaitable[dict[str, Any]]]):
    @tool
    async def search_project_history(query: str) -> dict[str, Any]:
        """Find earlier user decisions and run outcomes in this project. Use specific words or file names."""
        if not 1 <= len(query.strip()) <= 200:
            return {"ok": False, "error": "Use a history query of 1–200 characters"}
        return await search(query)

    return search_project_history


def saved_files(data: bytes | None):
    """A question's read-only tools over the saved revision's archive, which `data` holds."""
    names = []
    archive = None
    if data is not None:
        archive = zipfile.ZipFile(io.BytesIO(data))
        names = sorted(name for name in archive.namelist() if not name.endswith("/"))

    @tool
    def list_files(prefix: str = "") -> dict[str, Any]:
        """List the app's saved files, optionally only those under a folder prefix such as "backend/"."""
        found = [name for name in names if name.startswith(prefix)]
        return {"files": found[:MAX_LISTED], "more": max(0, len(found) - MAX_LISTED)}

    @tool
    def read_files(paths: list[str]) -> dict[str, Any]:
        """Read up to six saved files by their exact paths from list_files."""
        result: dict[str, dict[str, Any]] = {}
        for path in paths[:MAX_FILES_PER_READ]:
            if archive is None or path not in names:
                result[path] = {"error": "No such file in the saved app."}
                continue
            text = archive.read(path).decode("utf-8", errors="replace")
            result[path] = {"content": text[:MAX_FILE_CHARS], "truncated": len(text) > MAX_FILE_CHARS}
        return result

    return {list_files.name: list_files, read_files.name: read_files}
