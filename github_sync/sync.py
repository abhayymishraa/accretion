"""Two-way sync between a project's saved revisions and its GitHub repository.

Push: the latest revision becomes one commit on the branch, fast-forward only. Pull: GitHub's head becomes the
project's newest revision. When both moved, both are kept: the project takes GitHub's version and Accretion's work
goes to a pull request. Nothing here force-pushes, and nothing here raises into a build.
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import tarfile
import uuid
import zipfile
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy import delete, func, insert, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError

from agent import events
from agent.sandbox import archive, migrations, project
from agent.sandbox import secrets as sandbox_secrets
from agent.sandbox.kits import KITS
from agent.storage import persistence
from agent.storage.storage import StorageError
from db.base import AsyncSessionLocal, AutocommitSessionLocal
from db.models import Chat, ProjectRevision, Run
from github_sync import client
from github_sync.models import GithubAccount, ProjectRepo

logger = logging.getLogger("webbuilder.github")

# They describe the live database, which GitHub never sees: never pushed, and kept from the project on a pull.
_DUMP = "db/dump."
_WORKFLOWS = ".github/workflows/"
_ENV_EXAMPLE = ".env.example"
_MAX_CHANGES = 200
# Advisory lock class for "one sync at a time per project"; the second key is the project id's hash.
_LOCK_CLASS = 4801
_FAILURES = (
    client.GithubError,
    httpx.HTTPError,
    StorageError,
    ValueError,
    KeyError,
    zipfile.BadZipFile,
    tarfile.TarError,
)

Link = tuple[ProjectRepo, Chat, GithubAccount | None]


def _held(path: str) -> bool:
    """A path a project can hold (agent/sandbox/archive.py): no node_modules, no .env, nothing unsafe."""
    try:
        archive.safe_path(path)
    except ValueError:
        return False
    return True


def _ours(path: str) -> bool:
    """A path the project holds and GitHub receives. Everything else in GitHub's tree is left as it is."""
    return _held(path) and not path.startswith(_DUMP) and not any(p.startswith(".env") for p in path.split("/"))


def _carried(path: str) -> bool:
    return path.startswith(_DUMP) or path == migrations.APPLIED


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _blob_sha(data: bytes) -> str:
    """Git's id for a file, so a file GitHub already holds is never uploaded again."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _workflow_hashes(files: dict[str, bytes]) -> dict[str, str]:
    return {path: _sha256(data) for path, data in files.items() if path.startswith(_WORKFLOWS)}


def _unzip(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {name: z.read(name) for name in z.namelist()}


def _zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    return buffer.getvalue()


def _untar(data: bytes) -> dict[str, bytes]:
    """A repository tarball's files under the project's archive rules (agent/sandbox/archive.py): regular files
    only, safe paths only, within its file and size limits. Paths a project cannot hold (node_modules, .env) are
    skipped, as a checkpoint skips them."""
    files: dict[str, bytes] = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar:
            # GitHub puts every file under one "<owner>-<repo>-<sha>/" folder.
            path = member.name.partition("/")[2]
            if not member.isfile() or not _held(path):
                continue
            total += member.size
            if total > archive.MAX_BYTES or len(files) >= archive.MAX_FILES:
                raise ValueError("Repository exceeds the project limits")
            source = tar.extractfile(member)
            assert source is not None, "a regular file has content"
            files[path] = source.read()
    return files


def _env_example(names: set[str]) -> bytes:
    lines = ["# The keys this app reads. Values are never saved to GitHub: set them where the app runs."]
    return "\n".join([*lines, *(f"{name}=" for name in sorted(names))]).encode() + b"\n"


def detect_kit(files: dict[str, bytes]) -> str | None:
    """Which kit runs this repository, or None when none can."""
    stack = files.get(".accretion/stack.json")
    if stack:
        try:
            kit = json.loads(stack).get("id")
        except (ValueError, AttributeError):
            kit = None
        if kit in KITS:
            return str(kit)
    deps: set[str] = set()
    for path, data in files.items():
        if path.rsplit("/", 1)[-1] != "package.json":
            continue
        try:
            body = json.loads(data)
        except ValueError:
            continue
        for key in ("dependencies", "devDependencies"):
            if isinstance(body, dict) and isinstance(body.get(key), dict):
                deps |= set(body[key])
    python = b"\n".join(data for path, data in files.items() if path.endswith(("requirements.txt", "pyproject.toml")))
    if "next" in deps and "drizzle-orm" in deps:
        return "next-postgres"
    if "vite" in deps and "express" in deps:
        return "vite-express-mongo" if "mongoose" in deps else "vite-express-postgres"
    if "vite" in deps and (b"fastapi" in python.lower() or any(path.startswith("backend/alembic/") for path in files)):
        return "vite-fastapi-postgres"
    return None


async def _load(chat_id: str) -> Link | None:
    async with AutocommitSessionLocal() as db:
        row = (
            await db.execute(
                select(ProjectRepo, Chat, GithubAccount)
                .join(Chat, Chat.id == ProjectRepo.chat_id)
                .outerjoin(GithubAccount, GithubAccount.user_id == Chat.user_id)
                .where(ProjectRepo.chat_id == chat_id)
            )
        ).first()
    return None if row is None else (row[0], row[1], row[2])


async def _repos(where: Any, **values: Any) -> None:
    async with AutocommitSessionLocal() as db:
        await db.execute(
            update(ProjectRepo)
            .where(where)
            .values(**values, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )


async def _set(chat_id: str, **values: Any) -> None:
    await _repos(ProjectRepo.chat_id == chat_id, **values)


async def _build_open(chat_id: str) -> bool:
    async with AutocommitSessionLocal() as db:
        found = await db.scalar(
            select(Run.id).where(Run.chat_id == chat_id, Run.status.in_(("queued", "running"))).limit(1)
        )
    return found is not None


@asynccontextmanager
async def _serialized(chat_id: str) -> AsyncIterator[None]:
    """One sync at a time per project, across processes: a push and a webhook's pull never interleave.
    ponytail: holds one pooled connection for the length of a sync (seconds); a Redis lock if syncs crowd the
    pool."""
    async with AsyncSessionLocal.begin() as db:
        await db.execute(select(func.pg_advisory_xact_lock(_LOCK_CLASS, func.hashtext(chat_id))))
        yield


async def _guard(chat_id: str, work: Callable[[], Awaitable[bool]]) -> bool:
    """Run work under the project's lock. A failure becomes the row's status, never an exception."""
    try:
        async with _serialized(chat_id):
            return await work()
    except client.Reconnect:
        status = "reconnect"
    except client.GithubError as exc:
        logger.warning("GitHub sync failed chat_id=%s status=%s", chat_id, exc.status)
        status = "reconnect" if exc.status == 401 else "error"
    except _FAILURES as exc:
        logger.warning("GitHub sync failed chat_id=%s error_type=%s", chat_id, type(exc).__name__)
        status = "error"
    except SQLAlchemyError:
        logger.exception("GitHub sync failed on the database chat_id=%s", chat_id)
        return False
    try:
        await _set(chat_id, status=status, detail={})
    except SQLAlchemyError:
        logger.exception("GitHub sync status not saved chat_id=%s", chat_id)
    return False


def _path(repo: ProjectRepo, rest: str) -> str:
    return f"/repos/{quote(repo.owner)}/{quote(repo.name)}{rest}"


async def _head(token: str, repo: ProjectRepo, branch: str) -> str:
    ref = await client.call("GET", _path(repo, f"/git/ref/heads/{quote(branch, safe='/')}"), token)
    return str(ref["object"]["sha"])


async def _token(account: GithubAccount | None) -> tuple[str, GithubAccount]:
    if account is None or account.installation_id is None:
        raise client.Reconnect
    return await client.installation_token(account.installation_id), account


async def _commit(
    token: str, repo: ProjectRepo, account: GithubAccount, files: dict[str, bytes], message: str
) -> str | None:
    """A commit holding files on top of synced_sha, or None when GitHub's tree already holds exactly them. The
    tree is written whole, so a file deleted in the project is deleted on GitHub."""
    parent = await client.call("GET", _path(repo, f"/git/commits/{repo.synced_sha}"), token)
    tree_path = _path(repo, f"/git/trees/{parent['tree']['sha']}")
    listing = await client.call("GET", tree_path, token, params={"recursive": "1"})
    if listing.get("truncated"):
        # A partial listing would make the commit delete what it did not list.
        raise ValueError("Repository tree too large to list")
    before = {e["path"]: (e["mode"], e["type"], e["sha"]) for e in listing["tree"] if e["type"] != "tree"}
    known = {sha for _, _, sha in before.values()}
    entries = {path: entry for path, entry in before.items() if not _ours(path)}
    for path, data in files.items():
        sha = _blob_sha(data)
        if sha not in known:
            # ponytail: one at a time, as GitHub asks for requests that create content; the first push of a large
            # project takes a while, later ones upload only what changed.
            blob = {"content": base64.b64encode(data).decode(), "encoding": "base64"}
            await client.call("POST", _path(repo, "/git/blobs"), token, json=blob)
            known.add(sha)
        mode = before[path][0] if path in before and before[path][1] == "blob" else "100644"
        entries[path] = (mode, "blob", sha)
    if entries == before:
        return None
    tree = await client.call(
        "POST",
        _path(repo, "/git/trees"),
        token,
        json={"tree": [{"path": p, "mode": m, "type": t, "sha": s} for p, (m, t, s) in sorted(entries.items())]},
    )
    commit = await client.call(
        "POST",
        _path(repo, "/git/commits"),
        token,
        json={
            "message": message,
            "tree": tree["sha"],
            "parents": [repo.synced_sha],
            "author": {
                "name": account.login,
                "email": f"{account.github_user_id}+{account.login}@users.noreply.github.com",
            },
        },
    )
    return str(commit["sha"])


async def _local(repo: ProjectRepo, chat: Chat, example: bool) -> tuple[ProjectRevision, dict[str, bytes]] | None:
    """The latest revision's files as GitHub gets them, or None when they must not go: a file holds a key, or a
    workflow file changed since the user approved it. The row's status then says which."""
    revision = await persistence.latest_revision(chat.id)
    if revision is None:
        return None
    files = await asyncio.to_thread(_unzip, await persistence.revision_bytes(revision))
    files = {path: data for path, data in files.items() if _ours(path)}
    platform = await project.app_env(chat.id, chat.kit)
    values = await sandbox_secrets.user_secrets(chat.id)
    forms = events.secret_forms((project.private(platform) | values).values())
    keyed = []
    for path, data in files.items():
        text = data.decode(errors="ignore")
        if events.hide_secrets(text, forms) != text:
            keyed.append(path)
    if keyed:
        await _set(chat.id, status="blocked", detail={"files": sorted(keyed)[:20]})
        return None
    waiting = {p: h for p, h in _workflow_hashes(files).items() if repo.approved_workflows.get(p) != h}
    if waiting:
        await _set(chat.id, status="approval", detail={"files": sorted(waiting), "hashes": waiting})
        return None
    if example:
        kit = KITS.get(chat.kit)
        names = {*(sandbox_secrets.kit_names(kit) if kit else []), *values, *platform}
        files[_ENV_EXAMPLE] = _env_example(names)
    # Without an example (a conflict branch) GitHub's own .env.example is kept: it is not a project path.
    return revision, files


async def _open_conflict(token: str, repo: ProjectRepo, sha: str) -> str:
    """Accretion's commit on a new branch, and a pull request of it into the tracked branch."""
    # Named by the commit: a 422 means a retry of this same commit already made the branch.
    branch = f"accretion/conflict-{sha[:12]}"
    try:
        await client.call("POST", _path(repo, "/git/refs"), token, json={"ref": f"refs/heads/{branch}", "sha": sha})
    except client.GithubError as exc:
        if exc.status != 422:
            raise
    pull = await client.call(
        "POST",
        _path(repo, "/pulls"),
        token,
        json={
            "title": "Changes made in Accretion",
            "head": branch,
            "base": repo.branch,
            "body": "GitHub had changes Accretion didn't have yet. The project now has GitHub's version; "
            "this pull request holds the changes made in Accretion. Merge it to bring them back.",
        },
    )
    return str(pull["html_url"])


async def snapshot(token: str, owner: str, name: str, sha: str) -> dict[str, bytes]:
    """The repository's files at sha, as a project holds them. The download is capped at twice the project's
    size limit: what a project cannot hold (node_modules) still comes in the tarball."""
    path = f"/repos/{quote(owner)}/{quote(name)}/tarball/{sha}"
    tarball = await client.download(path, token, 2 * archive.MAX_BYTES)
    return await asyncio.to_thread(_untar, tarball)


async def _pull(
    repo: ProjectRepo, chat: Chat, token: str, head: str, branch: str, status: str, detail: dict[str, Any]
) -> bool:
    """GitHub's head as the project's newest revision. The database dump and its migration record come from the
    current revision: they describe the live database."""
    await _set(chat.id, status="pulling")
    current = await persistence.latest_revision(chat.id)
    carried: dict[str, bytes] = {}
    if current is not None:
        held = await asyncio.to_thread(_unzip, await persistence.revision_bytes(current))
        carried = {path: data for path, data in held.items() if _carried(path)}
    files = {p: d for p, d in (await snapshot(token, repo.owner, repo.name, head)).items() if not _carried(p)} | carried
    template = current.template_id if current is not None else await project.template_ref()
    revision_id, _ = await persistence.save_revision(chat.id, None, await asyncio.to_thread(_zip, files), template)
    old = current.manifest if current is not None else {}
    changed = {p for p, d in files.items() if not _carried(p) and old.get(p, {}).get("sha256") != _sha256(d)}
    changed |= {p for p in old if p not in files}
    await _set(
        chat.id,
        branch=branch,
        synced_sha=head,
        synced_revision_id=revision_id,
        pending_sha=None,
        outside_changes=sorted(set(repo.outside_changes) | changed)[:_MAX_CHANGES],
        approved_workflows={**repo.approved_workflows, **_workflow_hashes(files)},
        status=status,
        detail=detail,
    )
    return current is None or revision_id != current.id


async def _take(repo: ProjectRepo, chat: Chat, account: GithubAccount, token: str, head: str, branch: str) -> bool:
    """Pull branch's head. Work not on GitHub yet goes to a conflict pull request first, so nothing is lost."""
    status, detail = "synced", {}
    if chat.latest_saved_revision_id != repo.synced_revision_id:
        local = await _local(repo, chat, False)
        if local is None:
            # Held by a key or a workflow file: pulling now would bury that work under GitHub's.
            await _set(chat.id, pending_sha=head)
            return False
        sha = await _commit(token, repo, account, local[1], "Changes made in Accretion")
        if sha is not None:
            status, detail = "conflict", {"pull_url": await _open_conflict(token, repo, sha)}
    return await _pull(repo, chat, token, head, branch, status, detail)


async def _pulled_since(chat_id: str, base_revision_id: str) -> bool:
    """Whether GitHub's version was saved after the revision a build started from. Pulls save without a run."""
    base = select(ProjectRevision.created_at).where(ProjectRevision.id == base_revision_id).scalar_subquery()
    async with AutocommitSessionLocal() as db:
        found = await db.scalar(
            select(ProjectRevision.id)
            .where(
                ProjectRevision.chat_id == chat_id,
                ProjectRevision.run_id.is_(None),
                ProjectRevision.created_at > base,
            )
            .limit(1)
        )
    return found is not None


async def push_revision(chat_id: str, message: str, base_revision_id: str | None = None) -> None:
    """Push the project's latest revision, with a .env.example naming every value the app reads. base_revision_id:
    the revision a build started from. When GitHub's version was pulled during that build, the build's files are
    older than GitHub's, and a plain push would undo GitHub's changes: they go to a conflict pull request instead."""

    async def work() -> bool:
        link = await _load(chat_id)
        if link is None:
            return False
        repo, chat, account = link
        if repo.status in ("reconnect", "gone") or chat.latest_saved_revision_id in (None, repo.synced_revision_id):
            return False
        # A build's checkpoints are pushed by after_run once it ends, never mid-build. After a run, an open build
        # is a newer one, whose own after_run pushes.
        if await _build_open(chat_id):
            return False
        token, account = await _token(account)
        local = await _local(repo, chat, True)
        if local is None:
            return False
        revision, files = local
        await _set(chat_id, status="pushing")
        title = (message.strip().splitlines() or ["Update from Accretion"])[0][:72]
        sha = await _commit(token, repo, account, files, title)
        if sha is not None and base_revision_id and await _pulled_since(chat_id, base_revision_id):
            url = await _open_conflict(token, repo, sha)
            head = await _head(token, repo, repo.branch)
            return await _pull(repo, chat, token, head, repo.branch, "conflict", {"pull_url": url})
        if sha is not None:
            try:
                await client.call(
                    "PATCH",
                    _path(repo, f"/git/refs/heads/{quote(repo.branch, safe='/')}"),
                    token,
                    json={"sha": sha, "force": False},
                )
            except client.GithubError as exc:
                # 422: not a fast-forward, GitHub moved. Keep both.
                if exc.status != 422:
                    raise
                url = await _open_conflict(token, repo, sha)
                head = await _head(token, repo, repo.branch)
                return await _pull(repo, chat, token, head, repo.branch, "conflict", {"pull_url": url})
        await _set(
            chat_id, synced_sha=sha or repo.synced_sha, synced_revision_id=revision.id, status="synced", detail={}
        )
        return False

    await _guard(chat_id, work)


async def follow(chat_id: str, *, after_build: bool) -> bool:
    """after_build: pull what GitHub got while a build ran. Call it after the build's finish statement, so any build
    still open is a newer one, which defers the pull to that build's own end."""

    async def work() -> bool:
        link = await _load(chat_id)
        if link is None:
            return False
        repo, chat, account = link
        if repo.status in ("reconnect", "gone") or (after_build and repo.pending_sha is None):
            return False
        token, account = await _token(account)
        head = await _head(token, repo, repo.branch)
        if head == repo.synced_sha:
            values: dict[str, Any] = {"pending_sha": None} if repo.pending_sha else {}
            # Both sides agree: a status left by a failed or interrupted sync no longer holds.
            settled = chat.latest_saved_revision_id == repo.synced_revision_id
            if repo.status in ("error", "pushing", "pulling") and settled:
                values |= {"status": "synced", "detail": {}}
            if values:
                await _set(chat_id, **values)
            return False
        # After a run, an open build is a newer one: its own after_run pulls.
        if await _build_open(chat_id):
            await _set(chat_id, pending_sha=head)
            return False
        return await _take(repo, chat, account, token, head, repo.branch)

    return await _guard(chat_id, work)


async def check_head(chat_id: str) -> bool:
    """Pull when GitHub's head moved without us hearing (a lost webhook). Run in the background on project open."""
    return await follow(chat_id, after_build=False)


async def take_outside_changes(chat_id: str) -> list[str]:
    """Files changed on GitHub since the builder last ran, cleared as they are read."""
    old = (
        select(ProjectRepo.chat_id, ProjectRepo.outside_changes.label("changes"))
        .where(ProjectRepo.chat_id == chat_id)
        .with_for_update()
        .subquery()
    )
    try:
        async with AutocommitSessionLocal() as db:
            changes = await db.scalar(
                update(ProjectRepo)
                .where(ProjectRepo.chat_id == old.c.chat_id, func.jsonb_array_length(old.c.changes) > 0)
                .values(outside_changes=[])
                .returning(old.c.changes)
                .execution_options(synchronize_session=False)
            )
    except SQLAlchemyError:
        logger.exception("Reading outside changes failed chat_id=%s", chat_id)
        return []
    # A file given back by a run that did not succeed may also have changed again since.
    return list(dict.fromkeys(changes or []))


async def return_outside_changes(chat_id: str, files: list[str]) -> None:
    """Give back changes a run took but did not build on, beside any that arrived since."""
    try:
        async with AutocommitSessionLocal() as db:
            await db.execute(
                update(ProjectRepo)
                .where(ProjectRepo.chat_id == chat_id)
                .values(outside_changes=ProjectRepo.outside_changes.op("||")(literal(files, JSONB)))
            )
    except SQLAlchemyError:
        logger.exception("Returning outside changes failed chat_id=%s", chat_id)


async def switch_branch(chat_id: str, branch: str) -> None:
    """Track another branch: unpushed work goes to a pull request into the old one, then the new head is pulled."""

    async def work() -> bool:
        link = await _load(chat_id)
        if link is None:
            return False
        repo, chat, account = link
        token, account = await _token(account)
        head = await _head(token, repo, branch)
        if head == repo.synced_sha and chat.latest_saved_revision_id == repo.synced_revision_id:
            await _set(chat_id, branch=branch, pending_sha=None, status="synced", detail={})
            return False
        return await _take(repo, chat, account, token, head, branch)

    await _guard(chat_id, work)


async def import_repo(user_id: int, token: str, found: dict[str, Any], branch: str, head: str) -> str:
    """A new project holding the repository's head as its first revision, linked to it. Raises ValueError when
    the repository is too big and LookupError when no kit runs it; the project is not kept then."""
    files = await snapshot(token, found["owner"]["login"], found["name"], head)
    kit = detect_kit(files)
    if kit is None:
        raise LookupError("No kit runs this repository")
    data = await asyncio.to_thread(_zip, files)
    chat_id = str(uuid.uuid4())
    async with AutocommitSessionLocal() as db:
        await db.execute(insert(Chat).values(id=chat_id, user_id=user_id, title=found["name"][:255], kit=kit))
        try:
            # Its own transaction, after the project row is committed: the upload checks the project exists.
            revision_id, _ = await persistence.save_revision(chat_id, None, data, await project.template_ref())
            await db.execute(
                insert(ProjectRepo).values(
                    chat_id=chat_id,
                    repo_id=found["id"],
                    owner=found["owner"]["login"],
                    name=found["name"],
                    branch=branch,
                    default_branch=found["default_branch"],
                    synced_sha=head,
                    synced_revision_id=revision_id,
                    status="synced",
                    approved_workflows=_workflow_hashes(files),
                )
            )
        except Exception:
            await db.execute(delete(Chat).where(Chat.id == chat_id))
            raise
    return chat_id


async def _accounts_lost(installation_id: int) -> None:
    """The App was uninstalled or suspended: every repository of those users shows "Reconnect"."""
    users = (
        update(GithubAccount)
        .where(GithubAccount.installation_id == installation_id)
        .values(installation_id=None, updated_at=datetime.now(UTC))
        .returning(GithubAccount.user_id)
        .cte("users")
    )
    async with AutocommitSessionLocal() as db:
        await db.execute(
            update(ProjectRepo)
            .where(ProjectRepo.chat_id.in_(select(Chat.id).where(Chat.user_id.in_(select(users.c.user_id)))))
            .values(status="reconnect", updated_at=datetime.now(UTC))
            .add_cte(users)
            .execution_options(synchronize_session=False)
        )


async def handle_event(event: str, payload: dict[str, Any]) -> None:
    """A verified webhook delivery. Every handler is idempotent: a redelivery changes nothing."""
    action = payload.get("action")
    try:
        if event == "push":
            after, ref = payload.get("after") or "", payload.get("ref") or ""
            if not ref.startswith("refs/heads/") or not after.strip("0"):
                return
            async with AutocommitSessionLocal() as db:
                chat_ids = (
                    await db.scalars(
                        select(ProjectRepo.chat_id).where(
                            ProjectRepo.repo_id == payload["repository"]["id"],
                            ProjectRepo.branch == ref.removeprefix("refs/heads/"),
                            # Our own push comes back as a webhook; its head is already synced.
                            ProjectRepo.synced_sha != after,
                        )
                    )
                ).all()
            for chat_id in chat_ids:
                await check_head(chat_id)
        elif event == "installation" and action in ("deleted", "suspend"):
            await _accounts_lost(payload["installation"]["id"])
        elif event == "installation_repositories" and action == "removed":
            removed = [repo["id"] for repo in payload.get("repositories_removed", [])]
            await _repos(ProjectRepo.repo_id.in_(removed), status="reconnect")
        elif event == "github_app_authorization" and action == "revoked":
            async with AutocommitSessionLocal() as db:
                await db.execute(
                    update(GithubAccount)
                    .where(GithubAccount.github_user_id == payload["sender"]["id"])
                    .values(secret=None, updated_at=datetime.now(UTC))
                )
        elif event == "repository" and action in ("renamed", "transferred"):
            found = payload["repository"]
            await _repos(ProjectRepo.repo_id == found["id"], owner=found["owner"]["login"], name=found["name"])
        elif event == "repository" and action == "edited" and "default_branch" in payload.get("changes", {}):
            found = payload["repository"]
            await _repos(ProjectRepo.repo_id == found["id"], default_branch=found["default_branch"])
        elif event == "repository" and action == "deleted":
            await _repos(ProjectRepo.repo_id == payload["repository"]["id"], status="gone")
    except (KeyError, TypeError, SQLAlchemyError):
        logger.exception("GitHub webhook failed event=%s action=%s", event, action)
