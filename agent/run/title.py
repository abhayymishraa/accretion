"""Project naming: a short title from the first request, written once while the project has none.

The chat starts untitled, a fast model names it alongside the first reply, and the name is saved and
pushed to the page.
"""

import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import update

from db.base import AutocommitSessionLocal
from db.models import Chat

from ..budget.usage import record_usage
from ..routing import providers

logger = logging.getLogger(__name__)

# Examples from this product, not a chat app.
_PROMPT = (
    "Name this app project from the user's request, in 2-5 words.\n"
    'Output ONLY the name. No quotes, no prefixes like "Title:", no emojis, no trailing punctuation.\n'
    "Prefer accuracy over creativity.\n"
    "\n"
    "Examples:\n"
    '- "Build a notes app where I can add a note and delete it" -> Notes App\n'
    '- "a landing page for my coffee shop with the menu and hours" -> Coffee Shop Landing Page\n'
    '- "track my gym workouts and show weekly progress" -> Workout Tracker\n'
    '- "hi" -> New Project'
)
# Thinking counts against the cap: Gemini 3.1 Pro measured 215 reasoning tokens before a 2-word name,
# and at 24 it stopped with no name at all. The cap only bounds what the call reserves.
_MAX_OUTPUT_TOKENS = 512
# Per model: a hung provider is benched and the next one tried.
_TIMEOUT_SECONDS = 15
# Leading markdown and wrapping quotes.
_WRAPPING = re.compile(r"""^[\s#*"'`]+|[\s"'`.]+$""")
# The title before naming existed, kept as the fallback so no project stays nameless.
_FALLBACK_LENGTH = 100


async def _generate(prompt: str, metrics: dict[str, Any]) -> str | None:
    """The cheapest Auto model names it."""
    try:
        response = await providers.invoke_auto(
            [SystemMessage(content=_PROMPT), HumanMessage(content=prompt)], _MAX_OUTPUT_TOKENS, _TIMEOUT_SECONDS
        )
    except Exception:
        # Best effort, budget refusals included: the fallback title below still names the project.
        logger.warning("Project naming failed; using the request as the title")
        return None
    record_usage(metrics, response, phase="naming")
    first_line = response.text.strip().split("\n", 1)[0]
    return _WRAPPING.sub("", first_line)[:60] or None


async def name_project(chat_id: str, prompt: str, metrics: dict[str, Any]) -> str | None:
    """Title a project that has none; returns the title it wrote, or None if it already had one.

    The write is conditional, so a name the user typed meanwhile is never overwritten.
    """
    title = await _generate(prompt, metrics) or prompt.strip()[:_FALLBACK_LENGTH]
    async with AutocommitSessionLocal() as db:
        written = await db.scalar(
            update(Chat).where(Chat.id == chat_id, Chat.title.is_(None)).values(title=title).returning(Chat.id)
        )
    return title if written else None
