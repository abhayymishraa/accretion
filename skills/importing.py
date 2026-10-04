"""Bringing skills in from outside: a file the user uploads, or the SKILL.md files in a GitHub repository.

Everything goes through the same rules as a skill written in the form: parse_skill reads the file and
SkillCreate checks it. The library keeps instructions only, so a .zip's supporting files are not kept."""

import asyncio
import io
import re
import zipfile
from collections.abc import AsyncIterator
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from agent.tools.skills import MAX_SKILL_BYTES, parse_skill
from skills.exceptions import GitHubUnavailable, SkillImportInvalid, SkillImportTooLarge
from skills.schemas import FoundSkill, GitHubSkills, ImportFailure, SkillCreate

# An upload is one skill file, or a .zip holding one; the frontmatter may add a little to the body's limit.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_SKILL_FILE_BYTES = MAX_SKILL_BYTES + 4096
MAX_ZIP_ENTRIES = 100
MAX_GITHUB_SKILLS = 100

_GITHUB_URL = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?"
    r"(?:/tree/(?P<ref>[^/]+)(?:/(?P<folder>.+?))?)?/?"
)
_SHORT_NAME = re.compile(r"(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)")


async def read_upload(stream: AsyncIterator[bytes]) -> bytes:
    """The request body, refused as soon as it passes the upload limit rather than after reading it all."""
    data = bytearray()
    async for chunk in stream:
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise SkillImportTooLarge
    return bytes(data)


def skill_from_text(text: str) -> SkillCreate:
    try:
        name, description, instructions = parse_skill(text)
        return SkillCreate(name=name, description=description, instructions=instructions)
    # ValidationError is a ValueError: caught first, so its message says which field failed.
    except ValidationError as exc:
        error = exc.errors()[0]
        raise SkillImportInvalid(f"{error['loc'][0]}: {error['msg']}") from None
    except ValueError as exc:
        raise SkillImportInvalid(str(exc)) from None


def _text(data: bytes) -> str:
    if len(data) > MAX_SKILL_FILE_BYTES:
        raise SkillImportTooLarge
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise SkillImportInvalid("The skill file must be UTF-8 text") from None


def skill_from_upload(filename: str, data: bytes) -> SkillCreate:
    """A .md or .mdx skill file, or a .zip with exactly one SKILL.md in it."""
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix in {".md", ".mdx"}:
        return skill_from_text(_text(data))
    if suffix != ".zip":
        raise SkillImportInvalid("Import a .md, .mdx or .zip file")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise SkillImportInvalid("This .zip file cannot be opened") from None
    entries = archive.infolist()
    if len(entries) > MAX_ZIP_ENTRIES:
        raise SkillImportInvalid(f"A .zip may hold at most {MAX_ZIP_ENTRIES} files")
    skill_files = [
        entry for entry in entries if not entry.is_dir() and PurePosixPath(entry.filename).name == "SKILL.md"
    ]
    if len(skill_files) != 1:
        raise SkillImportInvalid("The .zip must hold exactly one SKILL.md")
    # Checked before reading, and bounded while reading: the size a .zip declares can be a lie.
    if skill_files[0].file_size > MAX_SKILL_FILE_BYTES:
        raise SkillImportTooLarge
    with archive.open(skill_files[0]) as source:
        return skill_from_text(_text(source.read(MAX_SKILL_FILE_BYTES + 1)))


def _repository(url: str) -> tuple[str, str, str | None, str]:
    """owner, repo, ref (None: the default branch) and folder from a GitHub URL or owner/repo."""
    match = _GITHUB_URL.fullmatch(url) or _SHORT_NAME.fullmatch(url)
    if match is None:
        raise SkillImportInvalid("Enter a GitHub repository, like github.com/owner/repo")
    found = match.groupdict()
    return found["owner"], found["repo"], found.get("ref"), (found.get("folder") or "").strip("/")


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    try:
        response = await client.get(url)
    except httpx.HTTPError:
        raise GitHubUnavailable from None
    if response.status_code == 404:
        raise SkillImportInvalid("That repository was not found, or it is private")
    if response.status_code in {403, 429}:
        raise GitHubUnavailable("GitHub is limiting requests right now. Try again later.")
    if response.status_code != 200:
        raise GitHubUnavailable
    return response


async def _skill_files(client: httpx.AsyncClient, url: str) -> tuple[str, str, str, list[str]]:
    """The repository, the ref read, and the SKILL.md paths in it (in the folder, when one was given)."""
    owner, repo, ref, folder = _repository(url)
    api = f"https://api.github.com/repos/{owner}/{repo}"
    if ref is None:
        ref = str((await _get(client, api)).json()["default_branch"])
    tree = (await _get(client, f"{api}/git/trees/{ref}?recursive=1")).json()["tree"]
    paths = [
        entry["path"]
        for entry in tree
        if entry["type"] == "blob"
        and PurePosixPath(entry["path"]).name == "SKILL.md"
        and entry.get("size", 0) <= MAX_SKILL_FILE_BYTES
        and (not folder or entry["path"].startswith(folder + "/"))
    ]
    return f"{owner}/{repo}", ref, f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/", paths[:MAX_GITHUB_SKILLS]


async def _read_skills(
    client: httpx.AsyncClient, raw: str, paths: list[str]
) -> tuple[list[tuple[str, SkillCreate]], list[ImportFailure]]:
    """Fetches and checks each SKILL.md, a few at a time; one bad file does not stop the others."""
    gate = asyncio.Semaphore(8)

    async def read(path: str) -> tuple[str, SkillCreate] | ImportFailure:
        async with gate:
            try:
                # Quoted, so a "#" or "?" in a folder name stays part of the path.
                response = await _get(client, raw + quote(path))
                return path, skill_from_text(_text(response.content))
            except (SkillImportInvalid, SkillImportTooLarge, GitHubUnavailable) as exc:
                return ImportFailure(path=path, reason=str(exc.detail))

    results = await asyncio.gather(*(read(path) for path in paths))
    return (
        [result for result in results if not isinstance(result, ImportFailure)],
        [result for result in results if isinstance(result, ImportFailure)],
    )


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=10, follow_redirects=True, headers={"Accept": "application/vnd.github+json", "User-Agent": "Accretion"}
    )


async def discover(url: str) -> GitHubSkills:
    """The skills a repository holds, with the files that cannot be imported and why."""
    async with _client() as client:
        repository, ref, raw, paths = await _skill_files(client, url)
        found, skipped = await _read_skills(client, raw, paths)
    skills = [FoundSkill(path=path, name=skill.name, description=skill.description) for path, skill in found]
    return GitHubSkills(repository=repository, ref=ref, skills=skills, skipped=skipped)


async def fetch_selected(url: str, wanted: list[str]) -> tuple[list[tuple[str, SkillCreate]], list[ImportFailure]]:
    """The chosen skills, read again from GitHub: the import never trusts what the browser sends back."""
    async with _client() as client:
        _, _, raw, paths = await _skill_files(client, url)
        missing = [
            ImportFailure(path=path, reason="Not found in the repository") for path in wanted if path not in paths
        ]
        found, failed = await _read_skills(client, raw, [path for path in paths if path in wanted])
    return found, [*missing, *failed]
