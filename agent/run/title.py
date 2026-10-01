"""Project naming: a short title from the first request, written once while the project has none.

After Vercel's ai-chatbot (generateTitleFromUserMessage, vercel/ai-chatbot@c2f8235): the chat starts
untitled, a fast model names it alongside the first reply, and the name is saved and pushed to the page.
"""

import asyncio
import logging
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import update

from db.base import AsyncSessionLocal
from db.models import Chat

from ..budget.usage import invoke_with_usage, record_usage
from ..routing import providers

logger = logging.getLogger(__name__)

# Vercel ai-chatbot's titlePrompt (lib/ai/prompts.ts) with Open WebUI's "accuracy over creativity"
# (DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE), and examples from this product instead of a chat app.
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
# Five words fit in well under this; the cap only bounds what the call reserves.
_MAX_OUTPUT_TOKENS = 24
_TIMEOUT_SECONDS = 15
# Vercel trims leading markdown and wrapping quotes the same way.
_WRAPPING = re.compile(r"""^[\s#*"'`]+|[\s"'`.]+$""")
# The title before naming existed, kept as the fallback so no project stays nameless.
_FALLBACK_LENGTH = 100


def _naming_model() -> BaseChatModel | None:
    """The cheapest Auto model this deployment can call, as Vercel keeps a separate fast title model."""
    entries = [entry for entry in providers.usable_models() if entry.auto]
    if not entries:
        return None
    cheapest = min(entries, key=lambda entry: entry.cost.input + entry.cost.output)
    return providers.limit_output(providers.chat_model(cheapest.id), _MAX_OUTPUT_TOKENS, reasoning=False)


async def _generate(prompt: str, metrics: dict[str, Any]) -> str | None:
    model = _naming_model()
    if model is None:
        return None
    try:
        response = await asyncio.wait_for(
            invoke_with_usage(model, [SystemMessage(content=_PROMPT), HumanMessage(content=prompt)]),
            timeout=_TIMEOUT_SECONDS,
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
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Chat).where(Chat.id == chat_id, Chat.title.is_(None)).values(title=title).returning(Chat.id)
        )
        await db.commit()
    return title if result.first() else None
