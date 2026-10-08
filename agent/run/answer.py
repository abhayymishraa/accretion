"""Answers a question about the project from its saved files: the same model, read-only tools, no sandbox.

A question never needs the app running, so it reads the latest saved revision from storage. It wakes no
sandbox, parks no other project and holds no lease; its model calls are metered like any other.
"""

import asyncio
import io
import json
import zipfile
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ValidationError

from ..budget.usage import invoke_with_usage, prompt_cache_key, record_usage
from ..routing.providers import bind_tools, cache_options, limit_output
from ..storage.persistence import latest_revision, revision_bytes

# A question is answered in a few reads; this stops a model that keeps reading.
MAX_TURNS = 6
MAX_FILE_CHARS = 20_000
MAX_FILES_PER_READ = 6
MAX_LISTED = 400

ANSWER_RULES = """You answer a question about the user's app, which you built. You can read its saved files with
list_files and read_files; you cannot change anything. Read the files the answer depends on before answering,
and answer only from what they show; if they do not show it, say you are not sure. Never guess.
Answer in the language the user writes in, in plain words for someone who does not code: say what the app does
or uses, not file paths or code. When the user asks about a tool, library or technology by name, name it and
say plainly whether the app uses it, and if not, what it uses instead. If the answer suggests a change, end
by offering it in one short question, for example "Want me to switch it?". Keep it short."""


def _archive_reader(data: bytes | None):
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


async def answer_question(model, chat_id: str, question: str, recent: list[dict[str, str]], metrics) -> str:
    """The model's answer to `question`, after reading what it needs from the latest saved revision."""
    revision = await latest_revision(chat_id)
    data = await revision_bytes(revision) if revision else None
    tools = await asyncio.to_thread(_archive_reader, data)
    schemas = [convert_to_openai_tool(item) for item in tools.values()]
    payload = {"question": question, "recent_conversation": recent, "app_saved": revision is not None}
    messages: list[Any] = [SystemMessage(content=ANSWER_RULES), HumanMessage(content=json.dumps(payload))]
    bound = bind_tools(limit_output(model, 2048), schemas)
    options = cache_options(model, prompt_cache_key(ANSWER_RULES, schemas, chat_id))
    for _ in range(MAX_TURNS):
        response = await invoke_with_usage(bound, messages, **options)
        record_usage(metrics, response, phase="answer")
        messages.append(response)
        if not response.tool_calls:
            return str(response.text or "").strip() or "I could not find an answer in the app's files."
        for call in response.tool_calls:
            chosen = tools.get(call["name"])
            try:
                output = await asyncio.to_thread(chosen.invoke, call["args"]) if chosen else {"error": "Unknown tool."}
            except ValidationError:
                # Bad arguments are the model's mistake to correct, not a failed question.
                output = {"error": "Invalid arguments for this tool."}
            messages.append(ToolMessage(content=json.dumps(output), tool_call_id=call["id"]))
    return "I could not find an answer in the app's files."
