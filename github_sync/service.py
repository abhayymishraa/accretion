"""GitHub routes' logic: connecting an account, linking a project to a repository, importing one, webhooks."""

import hashlib
import hmac
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from fastapi import BackgroundTasks
from redis import RedisError
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent.run import bus
from auth.schemas import TokenUser
from db.models import Chat
from github_sync import client, sync
from github_sync.config import github_settings
from github_sync.exceptions import (
    BranchExists,
    BranchNameInvalid,
    BranchNotFound,
    GithubNotConfigured,
    GithubNotConnected,
    GithubReconnect,
    GithubUnavailable,
    NothingToApprove,
    NothingToMerge,
    ProjectHasNoFiles,
    RepoAlreadyLinked,
    RepoEmpty,
    RepoNotFound,
    RepoNotLinked,
    RepoNotSupported,
    RepoTooBig,
    SameBranch,
    SignInExpired,
    SignInUnavailable,
    WebhookSignatureInvalid,
)
from github_sync.models import GithubAccount, ProjectRepo
from github_sync.schemas import (
    BranchItem,
    BranchList,
    ConnectFinish,
    ConnectStart,
    GithubAccountOut,
    ImportRequest,
    ImportResult,
    ProjectRepoOut,
    PullOut,
    RepoCreate,
    RepoItem,
    RepoList,
)
from projects.exceptions import ProjectNotFound

_STATE_SECONDS = 600
_DELIVERY_SECONDS = 86400
_SLUG = re.compile(r"[^A-Za-z0-9._-]+")
_BRANCH = re.compile(r"[A-Za-z0-9._/-]+")
_MESSAGES = {
    "synced": "Saved to GitHub",
    "pushing": "Saving to GitHub…",
    "pulling": "Getting changes from GitHub…",
    "conflict": "GitHub had other changes. We kept both: review the pull request.",
    "blocked": "A key is written in {file}. Remove it to keep saving to GitHub.",
    "approval": "A workflow file changed. Approve it to keep saving.",
    "reconnect": "Reconnect GitHub to keep saving.",
    "gone": "The repository was deleted or moved.",
    "error": "Couldn't reach GitHub. We'll retry on the next change.",
}


@contextmanager
def _calling() -> Iterator[None]:
    """GitHub's failures as the route's: a lost sign-in asks for a new one, anything else is "try again"."""
    try:
        yield
    except client.Reconnect:
        raise GithubReconnect from None
    except (client.GithubError, httpx.HTTPError):
        raise GithubUnavailable from None


async def _sync(chat_id: str) -> None:
    await sync.push_revision(chat_id, "Update from Accretion")
    await sync.check_head(chat_id)


def _account_out(account: GithubAccount | None) -> GithubAccountOut:
    if account is None:
        return GithubAccountOut(configured=github_settings.configured, connected=False)
    return GithubAccountOut(
        configured=github_settings.configured,
        connected=account.secret is not None,
        login=account.login,
        installed=account.installation_id is not None,
    )


def _repo_out(repo: ProjectRepo | None, account: GithubAccount | None) -> ProjectRepoOut:
    if repo is None:
        return ProjectRepoOut(linked=False)
    # Pushes run on the App installation; without it nothing syncs, whatever the row last said.
    status = repo.status if account is not None and account.installation_id is not None else "reconnect"
    files = repo.detail.get("files") or [""]
    return ProjectRepoOut(
        linked=True,
        owner=repo.owner,
        name=repo.name,
        url=f"https://github.com/{repo.owner}/{repo.name}",
        branch=repo.branch,
        default_branch=repo.default_branch,
        status=status,
        message=_MESSAGES.get(status, _MESSAGES["error"]).format(file=files[0]),
        detail=repo.detail if status == repo.status else {},
    )


def _installed(account: GithubAccount | None) -> int:
    if account is None:
        raise GithubNotConnected
    if account.installation_id is None:
        raise GithubReconnect
    return account.installation_id


async def _linked(
    db: AsyncSession, user: TokenUser, project_id: str
) -> tuple[Chat, ProjectRepo | None, GithubAccount | None]:
    """The project, its repository and the owner's account, ownership checked, in one query."""
    row = (
        await db.execute(
            select(Chat, ProjectRepo, GithubAccount)
            .outerjoin(ProjectRepo, ProjectRepo.chat_id == Chat.id)
            .outerjoin(GithubAccount, GithubAccount.user_id == Chat.user_id)
            .where(Chat.id == project_id, Chat.user_id == user.id)
        )
    ).first()
    if row is None:
        raise ProjectNotFound
    return row[0], row[1], row[2]


async def _repo(db: AsyncSession, user: TokenUser, project_id: str) -> tuple[ProjectRepo, GithubAccount, int]:
    """A linked project's repository, its owner's account and the App installation that reaches it."""
    _, repo, account = await _linked(db, user, project_id)
    if repo is None:
        raise RepoNotLinked
    installation_id = _installed(account)
    assert account is not None, "_installed refuses a missing account"
    return repo, account, installation_id


async def _save(db: AsyncSession, chat_id: str, **values: Any) -> ProjectRepo:
    saved = await db.scalar(
        update(ProjectRepo)
        .where(ProjectRepo.chat_id == chat_id)
        .values(**values, updated_at=datetime.now(UTC))
        .returning(ProjectRepo)
        # The session already holds this row; without populate_existing RETURNING hands back that stale copy.
        .execution_options(synchronize_session=False, populate_existing=True)
    )
    if saved is None:
        raise RepoNotLinked
    return saved


def _branch_name(name: str) -> str:
    if not _BRANCH.fullmatch(name) or ".." in name or name.startswith("/") or name.endswith(("/", ".lock")):
        raise BranchNameInvalid
    return name


async def account(db: AsyncSession, user: TokenUser) -> GithubAccountOut:
    return _account_out(await db.get(GithubAccount, user.id))


async def begin_connect(db: AsyncSession, user: TokenUser) -> ConnectStart:
    """Installing the App also signs the user in (the App asks for authorization during installation), so one
    redirect chain returns both. A user who already installed it only signs in."""
    if not github_settings.configured:
        raise GithubNotConfigured
    row = await db.get(GithubAccount, user.id)
    state = secrets.token_urlsafe(32)
    try:
        # Bound to this user: the callback page finishes it signed in, so someone else's link can never put their
        # GitHub account on this user.
        await bus.client.set(f"accretion:github:connect:{state}", str(user.id), ex=_STATE_SECONDS)
    except RedisError:
        raise SignInUnavailable from None
    if row is not None and row.installation_id is not None:
        query = urlencode({"client_id": github_settings.GITHUB_APP_CLIENT_ID, "state": state})
        return ConnectStart(url=f"https://github.com/login/oauth/authorize?{query}")
    query = urlencode({"state": state})
    return ConnectStart(url=f"https://github.com/apps/{github_settings.GITHUB_APP_SLUG}/installations/new?{query}")


async def finish_connect(db: AsyncSession, user: TokenUser, payload: ConnectFinish) -> GithubAccountOut:
    try:
        stored = await bus.client.getdel(f"accretion:github:connect:{payload.state}")
    except RedisError:
        raise SignInUnavailable from None
    if stored != str(user.id):
        raise SignInExpired
    with _calling():
        credentials = await client.oauth(code=payload.code)
        if credentials is None:
            raise SignInExpired
        me = await client.call("GET", "/user", credentials["access_token"])
        listed = await client.call("GET", "/user/installations", credentials["access_token"], params={"per_page": 100})
    # The installation GitHub named must be one this user can reach: the query string is the user's to forge.
    reachable = {item["id"]: item for item in listed["installations"]}
    installation_id = payload.installation_id if payload.installation_id in reachable else None
    if installation_id is None:
        installation_id = next((i for i, item in reachable.items() if item["account"]["id"] == me["id"]), None)
    now = datetime.now(UTC)
    values = {
        "github_user_id": me["id"],
        "login": me["login"],
        "installation_id": installation_id,
        "secret": client.seal(credentials),
        "updated_at": now,
    }
    saved = await db.scalar(
        insert(GithubAccount)
        .values(user_id=user.id, **values)
        .on_conflict_do_update(index_elements=[GithubAccount.user_id], set_=values)
        .returning(GithubAccount)
    )
    if installation_id is not None:
        await db.execute(
            update(ProjectRepo)
            .where(
                ProjectRepo.chat_id.in_(select(Chat.id).where(Chat.user_id == user.id)),
                ProjectRepo.status == "reconnect",
            )
            .values(status="synced", detail={}, updated_at=now)
            .execution_options(synchronize_session=False)
        )
    return _account_out(saved)


async def disconnect(db: AsyncSession, user: TokenUser) -> None:
    """Forget the account and every project's link. The repositories stay on GitHub."""
    await db.execute(
        delete(ProjectRepo)
        .where(ProjectRepo.chat_id.in_(select(Chat.id).where(Chat.user_id == user.id)))
        .execution_options(synchronize_session=False)
    )
    await db.execute(delete(GithubAccount).where(GithubAccount.user_id == user.id))


async def list_repos(db: AsyncSession, user: TokenUser) -> RepoList:
    installation_id = _installed(await db.get(GithubAccount, user.id))
    with _calling():
        token = await client.user_token(user.id)
        # ponytail: first 100 repositories, most recently updated first; page when someone has more.
        body = await client.call(
            "GET",
            f"/user/installations/{installation_id}/repositories",
            token,
            params={"per_page": 100, "sort": "updated"},
        )
    return RepoList(
        repos=[
            RepoItem(
                id=repo["id"],
                full_name=repo["full_name"],
                private=repo["private"],
                updated_at=repo.get("updated_at"),
            )
            for repo in body["repositories"]
        ]
    )


async def import_repo(db: AsyncSession, user: TokenUser, payload: ImportRequest) -> ImportResult:
    installation_id = _installed(await db.get(GithubAccount, user.id))
    with _calling():
        token = await client.installation_token(installation_id)
        try:
            # Read as the user: an organization's installation reaches repositories this user may not read. The
            # installation token then does the download.
            found = await client.call("GET", f"/repositories/{payload.repo_id}", await client.user_token(user.id))
        except client.GithubError as exc:
            if exc.status == 404:
                raise RepoNotFound from None
            raise
        branch = found["default_branch"]
        try:
            ref = await client.call(
                "GET", f"/repos/{found['full_name']}/git/ref/heads/{quote(branch, safe='/')}", token
            )
        except client.GithubError as exc:
            # 409: the repository has no commits.
            if exc.status in (404, 409):
                raise (RepoEmpty if exc.status == 409 else BranchNotFound) from None
            raise
        try:
            chat_id = await sync.import_repo(user.id, token, found, branch, ref["object"]["sha"])
        except LookupError:
            raise RepoNotSupported from None
        except ValueError:
            raise RepoTooBig from None
    return ImportResult(project_id=chat_id)


async def project_repo(db: AsyncSession, user: TokenUser, project_id: str) -> ProjectRepoOut:
    _, repo, account = await _linked(db, user, project_id)
    return _repo_out(repo, account)


async def create_repo(
    db: AsyncSession, user: TokenUser, project_id: str, payload: RepoCreate, background: BackgroundTasks
) -> ProjectRepoOut:
    """A private repository for the project, then its first push in the background."""
    chat, repo, account = await _linked(db, user, project_id)
    if repo is not None:
        raise RepoAlreadyLinked
    if chat.latest_saved_revision_id is None:
        raise ProjectHasNoFiles
    installation_id = _installed(account)
    base = _SLUG.sub("-", payload.name or chat.title or "my-app").strip("-.")[:90] or "my-app"
    with _calling():
        token = await client.user_token(user.id)
        for n in range(1, 11):
            try:
                # auto_init: GitHub's Git Data API refuses blobs in an empty repository, so the first push needs a
                # commit to build on.
                created = await client.call(
                    "POST",
                    "/user/repos",
                    token,
                    json={"name": base if n == 1 else f"{base}-{n}", "private": True, "auto_init": True},
                )
                break
            except client.GithubError as exc:
                # 422: the name is taken; try the next suffix.
                if exc.status != 422 or n == 10:
                    raise
        try:
            await client.call("PUT", f"/user/installations/{installation_id}/repositories/{created['id']}", token)
        except client.GithubError:
            # An installation on all repositories already reaches it, and refuses the call.
            pass
        app_token = await client.installation_token(installation_id)
        branch = created["default_branch"]
        ref_path = f"/repos/{created['full_name']}/git/ref/heads/{quote(branch, safe='/')}"
        ref = await client.call("GET", ref_path, app_token)
    saved = await db.scalar(
        insert(ProjectRepo)
        .values(
            chat_id=chat.id,
            repo_id=created["id"],
            owner=created["owner"]["login"],
            name=created["name"],
            branch=branch,
            default_branch=branch,
            synced_sha=ref["object"]["sha"],
            status="pushing",
        )
        .on_conflict_do_nothing()
        .returning(ProjectRepo)
    )
    if saved is None:
        raise RepoAlreadyLinked
    background.add_task(sync.push_revision, chat.id, "Saved from Accretion")
    return _repo_out(saved, account)


async def unlink(db: AsyncSession, user: TokenUser, project_id: str) -> None:
    """The project stops syncing; the repository stays on GitHub. One statement, ownership in it."""
    await db.execute(
        delete(ProjectRepo)
        .where(
            ProjectRepo.chat_id == project_id,
            ProjectRepo.chat_id.in_(select(Chat.id).where(Chat.user_id == user.id)),
        )
        .execution_options(synchronize_session=False)
    )


async def sync_now(db: AsyncSession, user: TokenUser, project_id: str, background: BackgroundTasks) -> ProjectRepoOut:
    _, repo, account = await _linked(db, user, project_id)
    if repo is None:
        raise RepoNotLinked
    background.add_task(_sync, project_id)
    return _repo_out(repo, account)


async def approve_workflows(
    db: AsyncSession, user: TokenUser, project_id: str, background: BackgroundTasks
) -> ProjectRepoOut:
    """Allow the workflow files the held push listed, exactly as they were, and push again."""
    _, repo, account = await _linked(db, user, project_id)
    if repo is None:
        raise RepoNotLinked
    hashes = repo.detail.get("hashes")
    if repo.status != "approval" or not hashes:
        raise NothingToApprove
    saved = await _save(
        db, project_id, approved_workflows={**repo.approved_workflows, **hashes}, status="pushing", detail={}
    )
    background.add_task(_sync, project_id)
    return _repo_out(saved, account)


async def branches(db: AsyncSession, user: TokenUser, project_id: str) -> BranchList:
    repo, _, installation_id = await _repo(db, user, project_id)
    with _calling():
        token = await client.installation_token(installation_id)
        listed = await client.call("GET", f"/repos/{repo.owner}/{repo.name}/branches", token, params={"per_page": 100})
    return BranchList(branches=[BranchItem(name=b["name"], current=b["name"] == repo.branch) for b in listed])


async def create_branch(db: AsyncSession, user: TokenUser, project_id: str, name: str) -> ProjectRepoOut:
    """A branch at the commit both sides agree on. The project keeps saving to its current branch."""
    repo, account, installation_id = await _repo(db, user, project_id)
    with _calling():
        token = await client.installation_token(installation_id)
        try:
            await client.call(
                "POST",
                f"/repos/{repo.owner}/{repo.name}/git/refs",
                token,
                json={"ref": f"refs/heads/{_branch_name(name)}", "sha": repo.synced_sha},
            )
        except client.GithubError as exc:
            if exc.status == 422:
                raise BranchExists from None
            raise
    return _repo_out(repo, account)


async def switch_branch(
    db: AsyncSession, user: TokenUser, project_id: str, name: str, background: BackgroundTasks
) -> ProjectRepoOut:
    repo, account, installation_id = await _repo(db, user, project_id)
    with _calling():
        token = await client.installation_token(installation_id)
        try:
            await client.call(
                "GET", f"/repos/{repo.owner}/{repo.name}/git/ref/heads/{quote(_branch_name(name), safe='/')}", token
            )
        except client.GithubError as exc:
            if exc.status == 404:
                raise BranchNotFound from None
            raise
    saved = await _save(db, project_id, status="pulling", detail={})
    background.add_task(sync.switch_branch, project_id, name)
    return _repo_out(saved, account)


async def open_pull(db: AsyncSession, user: TokenUser, project_id: str) -> PullOut:
    """A pull request of the project's branch into the default branch; the open one when it exists."""
    repo, _, installation_id = await _repo(db, user, project_id)
    base = repo.default_branch
    if repo.branch == base:
        raise SameBranch
    with _calling():
        token = await client.installation_token(installation_id)
        try:
            pull = await client.call(
                "POST",
                f"/repos/{repo.owner}/{repo.name}/pulls",
                token,
                json={"title": f"Changes from {repo.branch}", "head": repo.branch, "base": base},
            )
        except client.GithubError as exc:
            # 422: one is open already, or there is nothing to merge.
            if exc.status != 422:
                raise
            open_pulls = await client.call(
                "GET",
                f"/repos/{repo.owner}/{repo.name}/pulls",
                token,
                params={"head": f"{repo.owner}:{repo.branch}", "base": base, "state": "open"},
            )
            if not open_pulls:
                raise NothingToMerge from None
            pull = open_pulls[0]
    return PullOut(url=pull["html_url"])


async def accept_webhook(body: bytes, signature: str | None, delivery: str | None) -> bool:
    """Whether to handle this delivery: signed by GitHub, and not seen before."""
    if not github_settings.configured:
        raise GithubNotConfigured
    secret = github_settings.GITHUB_APP_WEBHOOK_SECRET.encode()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise WebhookSignatureInvalid
    if not delivery:
        return True
    try:
        return bool(await bus.client.set(f"accretion:github:delivery:{delivery}", "1", nx=True, ex=_DELIVERY_SECONDS))
    except RedisError:
        # Every handler is idempotent: a redelivery handled twice changes nothing.
        return True
