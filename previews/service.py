"""Business logic for the project preview."""

from typing import Any

from fastapi import HTTPException

from agent.budget.budget import BudgetLimitError
from agent.run.service import agent_service
from db.models import Chat
from exceptions import TooManyRequests
from previews.exceptions import PreviewUnavailable
from request_timing import measure


async def open_preview(project_id: str) -> dict[str, Any]:
    try:
        with measure("preview_open"):
            return await agent_service.open_preview(project_id)
    except HTTPException:
        # A status the agent service chose deliberately, e.g. 429 or 503.
        raise
    except BudgetLimitError as exc:
        raise TooManyRequests(str(exc)) from None
    except Exception:
        raise PreviewUnavailable from None


async def preview_status(project: Chat) -> dict[str, Any]:
    with measure("preview_status"):
        return await agent_service.preview_status(project)
