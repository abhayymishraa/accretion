"""The checks a publish runs over the files it sends: keys written into them, Supabase's security advisor, and npm
packages with high or critical advisories. Each one is a warning for the Publish tab, never a reason to stop: a
check that cannot run finds nothing."""

import asyncio
import json
import logging

import httpx

from agent import events
from supabase_connect import sandbox as supabase_sandbox

logger = logging.getLogger("webbuilder.vercel")

# npm audit's own source: given versions, it answers only the advisories that apply to them.
_ADVISORIES = "https://registry.npmjs.org/-/npm/v1/security/advisories/bulk"
_SEVERE = {"critical": "ERROR", "high": "WARN"}
_LOCKFILE = "package-lock.json"
_MAX_FINDINGS = 20


def _keys(files: dict[str, bytes]) -> list[dict[str, str]]:
    """Files holding a key in a provider's format: the same patterns that hide keys from the builder."""
    found = []
    for path, data in files.items():
        if path.rpartition("/")[2] == _LOCKFILE:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if events.hide_secrets(text, []) != text:
            found.append(
                {
                    "level": "ERROR",
                    "title": "A secret key is written in the app's code",
                    "detail": f"{path} holds what looks like a secret key. Anyone can read it in the published app.",
                    "remediation": "Save the key in the project's secrets, and read it from the environment.",
                }
            )
    return found


def _installed(files: dict[str, bytes]) -> dict[str, list[str]]:
    """Every package version the app ships, from each package-lock.json; development tools are left out."""
    versions: dict[str, set[str]] = {}
    for path, data in files.items():
        if path.rpartition("/")[2] != _LOCKFILE:
            continue
        try:
            packages = json.loads(data).get("packages") or {}
        except (ValueError, AttributeError):
            continue
        for where, entry in packages.items():
            # "" is the app itself.
            if where and isinstance(entry, dict) and not entry.get("dev") and isinstance(entry.get("version"), str):
                name = entry.get("name") or where.rpartition("node_modules/")[2]
                versions.setdefault(name, set()).add(entry["version"])
    return {name: sorted(found) for name, found in versions.items()}


async def _packages(files: dict[str, bytes]) -> list[dict[str, str]]:
    installed = _installed(files)
    if not installed:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(_ADVISORIES, json=installed)
            response.raise_for_status()
            advisories = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("npm advisory check failed error_type=%s", type(exc).__name__)
        return []
    found = []
    for name, items in sorted(advisories.items()):
        severe = [item for item in items if isinstance(item, dict) and item.get("severity") in _SEVERE]
        if not severe:
            continue
        worst = "critical" if any(item["severity"] == "critical" for item in severe) else "high"
        found.append(
            {
                "level": _SEVERE[worst],
                "title": f"The {name} package has a known security problem",
                "detail": f"{severe[0].get('title', 'A published advisory')}"
                + (f", and {len(severe) - 1} more" if len(severe) > 1 else "")
                + f" ({worst}).",
                "remediation": f"Update {name} to a version without these advisories.",
            }
        )
    return found


async def findings(chat_id: str, files: dict[str, bytes]) -> list[dict[str, str]]:
    keys, packages, database = await asyncio.gather(
        asyncio.to_thread(_keys, files), _packages(files), supabase_sandbox.security_findings(chat_id)
    )
    return [*keys, *database, *packages][:_MAX_FINDINGS]
