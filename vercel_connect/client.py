"""The Vercel REST API, called with the user's Integration token, and the sealing of that token."""

import hashlib
import json
from typing import Any

import httpx
from sqlalchemy import select

from agent.sandbox.secrets import fernet
from db.base import AutocommitSessionLocal
from vercel_connect.config import vercel_settings
from vercel_connect.exceptions import Reconnect, SignInExpired, VercelRefused, VercelUnavailable
from vercel_connect.models import VercelAccount

API = "https://api.vercel.com"
_PURPOSE = b"accretion vercel tokens v1"


def seal(values: dict[str, Any]) -> str:
    return fernet(_PURPOSE).encrypt(json.dumps(values).encode()).decode()


def unseal(text: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(fernet(_PURPOSE).decrypt(text.encode()))
    return result


async def exchange(code: str, redirect_uri: str) -> dict[str, Any]:
    """The Integration's token for a code from its install redirect. A code works once, for 30 minutes."""
    form = {
        "client_id": vercel_settings.VERCEL_CLIENT_ID,
        "client_secret": vercel_settings.VERCEL_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            response = await http.post(f"{API}/v2/oauth/access_token", data=form)
    except httpx.HTTPError:
        raise VercelUnavailable from None
    if response.status_code in (400, 401, 403, 404):
        raise SignInExpired
    if response.status_code >= 300:
        raise VercelUnavailable
    body = response.json()
    return {"access_token": body["access_token"], "team_id": body.get("team_id")}


class Session:
    """One user's calls. The token is read once per publish, not once per call."""

    def __init__(self, tokens: dict[str, Any]) -> None:
        self._token = str(tokens["access_token"])
        team = tokens.get("team_id")
        self._team = {"teamId": team} if team else {}

    async def call(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        try:
            async with httpx.AsyncClient(base_url=API, timeout=60) as http:
                response = await http.request(
                    method,
                    path,
                    params={**(params or {}), **self._team},
                    headers={**(headers or {}), "Authorization": f"Bearer {self._token}"},
                    **kwargs,
                )
        except httpx.HTTPError:
            raise VercelUnavailable from None
        return _result(response)

    async def upload(self, data: bytes) -> str:
        """Stores one file for deployments; Vercel names a file by its SHA-1 and keeps one copy of each."""
        sha = hashlib.sha1(data, usedforsecurity=False).hexdigest()
        await self.call(
            "POST",
            "/v2/files",
            content=data,
            headers={"Content-Type": "application/octet-stream", "x-vercel-digest": sha},
        )
        return sha

    async def call_allowing_missing(self, method: str, path: str, **kwargs: Any) -> Any:
        """A call where 404 means the thing is already gone: returns None."""
        try:
            return await self.call(method, path, **kwargs)
        except VercelRefused as error:
            if error.vercel_status == 404:
                return None
            raise


def _result(response: httpx.Response) -> Any:
    if response.status_code < 400:
        return response.json() if response.content else None
    try:
        body = response.json()
    except ValueError:
        body = None
    error = body.get("error") if isinstance(body, dict) else None
    error = error if isinstance(error, dict) else {}
    code = error.get("code")
    # A removed Integration's token, or one Vercel no longer accepts: the user connects again.
    if response.status_code == 401 or code == "invalidToken":
        raise Reconnect
    message = error.get("message")
    raise VercelRefused(str(message)[:500] if message else None, vercel_status=response.status_code)


async def session(user_id: int) -> Session:
    async with AutocommitSessionLocal() as db:
        secret = await db.scalar(select(VercelAccount.secret).where(VercelAccount.user_id == user_id))
    if secret is None:
        raise Reconnect
    return Session(unseal(secret))
