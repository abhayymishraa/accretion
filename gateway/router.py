"""App services: sign-in for generated apps, and the owner's panel for them."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db.base import Autocommit, DbSession
from gateway import service, signin
from gateway.dependencies import AppOf
from gateway.exceptions import AppTokenInvalid
from gateway.schemas import AppServices, EmailSent, EmailSignIn, SignInSession
from projects.dependencies import OwnedProject

router = APIRouter()


@router.get("/apps/auth/jwks.json")
async def jwks() -> dict[str, Any]:
    return signin.jwks()


@router.get("/apps/{app_id}/auth/google", dependencies=[Autocommit])
async def google_start(app_id: str, redirect_uri: str, db: DbSession) -> RedirectResponse:
    return await signin.google_start(db, app_id, redirect_uri)


@router.get("/apps/auth/google/callback")
async def google_finish(state: str = "", code: str = "", error: str = "") -> RedirectResponse:
    return await signin.google_finish(state, code, error)


@router.post("/apps/{app_id}/auth/email", status_code=202, dependencies=[Autocommit])
async def email_start(app_id: str, payload: EmailSignIn, app: AppOf, db: DbSession) -> EmailSent:
    """Called by the app's server with its app key, never its browser code: the app id is public, and without the
    key anyone could send sign-in mail from our domain and use up the app's daily email."""
    if app != app_id:
        raise AppTokenInvalid
    await signin.email_start(db, app_id, payload)
    return EmailSent()


@router.get("/apps/auth/email/verify")
async def email_confirm(t: str) -> HTMLResponse:
    """A page with one button. Mail scanners open links on their own; only the button's POST uses the link."""
    return signin.email_confirm(t)


@router.post("/apps/auth/email/verify")
async def email_finish(t: str) -> Response:
    return await signin.email_finish(t)


@router.get("/apps/{app_id}/auth/session")
async def session(
    app_id: str, credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]
) -> SignInSession:
    """Called by the app's server, not its browser code: there is no CORS for app origins."""
    return signin.session(app_id, credentials.credentials)


@router.get("/projects/{project_id}/app-services", dependencies=[Autocommit])
async def app_services(_: OwnedProject) -> AppServices:
    """Owners only, though no answer depends on the project yet."""
    return service.app_services()
