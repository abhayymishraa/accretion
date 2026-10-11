"""GitHub REST calls: the App's JWT, installation tokens, and each user's token, refreshed under a row lock.

Tokens never leave this module except as the bearer of a request to GitHub.
"""

import json
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
from cryptography.fernet import Fernet
from sqlalchemy import select

from agent.sandbox.secrets import fernet
from db.base import AsyncSessionLocal, AutocommitSessionLocal
from github_sync.config import github_settings
from github_sync.models import GithubAccount

_TOKEN_URL = "https://github.com/login/oauth/access_token"
# A token this close to expiry is renewed first, so a call never starts with one that dies mid-request.
_MARGIN = 300

http = httpx.AsyncClient(
    base_url="https://api.github.com",
    headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Accretion",
    },
    timeout=httpx.Timeout(30, connect=10),
)
# ponytail: per process; each process asks GitHub for its own token, which GitHub allows.
_installation_tokens: dict[int, tuple[str, float]] = {}


class GithubError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub answered {status}: {message}")
        self.status = status


class Reconnect(Exception):
    """The user's token or the App installation is gone: only a new sign-in fixes it."""


def _sealer() -> Fernet:
    return fernet(b"accretion github tokens v1")


def seal(credentials: dict[str, Any]) -> str:
    return _sealer().encrypt(json.dumps(credentials).encode()).decode()


def _unseal(secret: str) -> dict[str, Any]:
    credentials: dict[str, Any] = json.loads(_sealer().decrypt(secret.encode()))
    return credentials


def _message(response: httpx.Response) -> str:
    try:
        return str(response.json().get("message", ""))[:300]
    except ValueError:
        return response.text[:300]


async def call(method: str, path: str, token: str, **kwargs: Any) -> Any:
    response = await http.request(method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs)
    if response.status_code >= 400:
        raise GithubError(response.status_code, _message(response))
    return response.json() if response.content else None


async def download(path: str, token: str, limit: int) -> bytes:
    """A tarball, read up to limit bytes. GitHub redirects to its download host; httpx drops the token on the way."""
    async with http.stream("GET", path, headers={"Authorization": f"Bearer {token}"}, follow_redirects=True) as reply:
        if reply.status_code >= 400:
            await reply.aread()
            raise GithubError(reply.status_code, _message(reply))
        data = bytearray()
        async for chunk in reply.aiter_bytes():
            data += chunk
            if len(data) > limit:
                raise ValueError("Repository download exceeds the project size limit")
    return bytes(data)


def _app_jwt() -> str:
    now = int(time.time())
    # Backdated for clock drift; GitHub refuses a JWT that lives longer than ten minutes.
    claims = {"iat": now - 60, "exp": now + 540, "iss": github_settings.GITHUB_APP_ID}
    return jwt.encode(claims, github_settings.GITHUB_APP_PRIVATE_KEY, algorithm="RS256")


async def installation_token(installation_id: int) -> str:
    """The token that reads and writes the repositories the user gave the App. It lives an hour."""
    cached = _installation_tokens.get(installation_id)
    if cached and cached[1] - time.time() > _MARGIN:
        return cached[0]
    try:
        body = await call("POST", f"/app/installations/{installation_id}/access_tokens", _app_jwt())
    except GithubError as exc:
        # Uninstalled or suspended.
        if exc.status in (401, 403, 404):
            raise Reconnect from None
        raise
    _installation_tokens[installation_id] = (body["token"], datetime.fromisoformat(body["expires_at"]).timestamp())
    return str(body["token"])


async def oauth(**params: str) -> dict[str, Any] | None:
    """A token response as stored credentials, or None when GitHub refused the code or refresh token. GitHub
    answers 200 with an `error` field for a refusal."""
    response = await http.post(
        _TOKEN_URL,
        data={
            "client_id": github_settings.GITHUB_APP_CLIENT_ID,
            "client_secret": github_settings.GITHUB_APP_CLIENT_SECRET,
            **params,
        },
        headers={"Accept": "application/json"},
    )
    if response.status_code >= 400:
        raise GithubError(response.status_code, _message(response))
    body = response.json()
    if "access_token" not in body:
        return None
    now = time.time()
    # An App that opted out of expiring user tokens returns neither expiry nor refresh token.
    return {
        "access_token": body["access_token"],
        "refresh_token": body.get("refresh_token"),
        "expires_at": now + body["expires_in"] if body.get("expires_in") else None,
        "refresh_expires_at": now + body["refresh_token_expires_in"] if body.get("refresh_token_expires_in") else None,
    }


def _expiring(credentials: dict[str, Any]) -> bool:
    expires_at = credentials.get("expires_at")
    return expires_at is not None and expires_at - time.time() < _MARGIN


async def user_token(user_id: int) -> str:
    """The user's own token: it creates repositories and lists what the App can reach for them."""
    async with AutocommitSessionLocal() as db:
        secret = await db.scalar(select(GithubAccount.secret).where(GithubAccount.user_id == user_id))
    if secret is None:
        raise Reconnect
    credentials = _unseal(secret)
    if not _expiring(credentials):
        return str(credentials["access_token"])
    # GitHub rotates the refresh token on use: two refreshes at once would leave one caller holding a dead token,
    # so the second waits on the row and finds the first one's result.
    async with AsyncSessionLocal.begin() as db:
        account = await db.scalar(select(GithubAccount).where(GithubAccount.user_id == user_id).with_for_update())
        if account is None or account.secret is None:
            raise Reconnect
        credentials = _unseal(account.secret)
        if not _expiring(credentials):
            return str(credentials["access_token"])
        refreshed = await oauth(grant_type="refresh_token", refresh_token=credentials.get("refresh_token") or "")
        account.secret = seal(refreshed) if refreshed else None
        account.updated_at = datetime.now(UTC)
    if refreshed is None:
        raise Reconnect
    return str(refreshed["access_token"])
