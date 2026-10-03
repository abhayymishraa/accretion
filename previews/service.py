"""Business logic for the project preview."""

from fastapi import HTTPException

from agent.budget.budget import BudgetLimitError
from agent.run.service import agent_service
from auth.schemas import TokenUser
from exceptions import TooManyRequests
from previews.exceptions import PreviewUnavailable
from previews.schemas import PreviewState
from request_timing import measure


async def open_preview(project_id: str, user: TokenUser) -> PreviewState:
    try:
        with measure("preview_open"):
            return PreviewState.model_validate(await agent_service.open_preview(project_id, user.id))
    except HTTPException:
        # A status the agent service chose deliberately, e.g. 429 or 503.
        raise
    except BudgetLimitError as exc:
        raise TooManyRequests(str(exc)) from None
    except Exception:
        raise PreviewUnavailable from None


async def preview_status(project_id: str, user: TokenUser) -> PreviewState:
    with measure("preview_status"):
        return PreviewState.model_validate(await agent_service.preview_status(project_id, user.id))
