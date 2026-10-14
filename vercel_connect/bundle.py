"""The files Vercel receives for an app: its latest saved revision, with the kit's vercel.json when it has none.

Vercel builds the app from these files. Migrations run in that build, against the database the user added on
Vercel, so neither Accretion's API nor the sandbox ever connects to the production database.
"""

import json
from typing import Any

from agent.sandbox import archive

# Saved revisions hold no .env or node_modules (agent/sandbox/archive.py); these are local-only besides.
_LOCAL_ONLY = ("db/dump.", ".accretion/stack.json", ".accretion/migrated.json")
# The direct address migrations need: Neon's unpooled one, another Postgres integration's, else the app's own.
_MIGRATION_URL = 'DATABASE_URL="${DATABASE_URL_UNPOOLED:-${POSTGRES_URL_NON_POOLING:-$DATABASE_URL}}"'
# Vercel runs an exported Express app as a function and does not support app.listen; projects made before the
# kits exported their app still end with the kit's line.
_EXPRESS_ENTRY = "backend/src/index.ts"
_KIT_LISTEN = 'app.listen(4000, "0.0.0.0", () => console.log("api listening on 4000"));'
_EXPORTED_LISTEN = (
    "// Vercel runs the exported app as a function and does not support app.listen.\n"
    'if (!process.env.VERCEL) app.listen(4000, "0.0.0.0", () => console.log("api listening on 4000"));\n\n'
    "export default app;"
)
# Frontend at the root, API under /api: the same split the preview's proxy makes.
_REWRITES = [
    {"source": "/api/(.*)", "destination": {"service": "backend"}},
    {"source": "/(.*)", "destination": {"service": "frontend"}},
]


class NotPublishable(ValueError):
    """The app's code needs a change before Vercel can run it; the message says which, in the user's words."""


def framework(kit_id: str) -> str:
    return "nextjs" if kit_id == "next-postgres" else "services"


def _services(backend: dict[str, str]) -> dict[str, Any]:
    return {
        "services": {"frontend": {"root": "frontend/"}, "backend": {"root": "backend/", **backend}},
        "rewrites": _REWRITES,
    }


def vercel_config(kit_id: str) -> dict[str, Any]:
    """Each kit's layout on Vercel. Only tested layouts are listed; an unknown kit cannot be published."""
    configs: dict[str, dict[str, Any]] = {
        "next-postgres": {"buildCommand": f"{_MIGRATION_URL} npm run migrate && npm run build"},
        "vite-fastapi-postgres": _services(
            {"entrypoint": "app.main:app", "buildCommand": f"{_MIGRATION_URL} python -m alembic upgrade head"}
        ),
        "vite-express-postgres": _services(
            {"entrypoint": "src/index.ts", "buildCommand": f"{_MIGRATION_URL} npm run migrate"}
        ),
        # MONGO_URL is set on the project from Atlas's MONGODB_URI before the build.
        "vite-express-mongo": _services({"entrypoint": "src/index.ts", "buildCommand": "npm run migrate"}),
    }
    return {"$schema": "https://openapi.vercel.sh/vercel.json", **configs[kit_id]}


def _published(path: str) -> bool:
    try:
        archive.safe_path(path)
    except ValueError:
        return False
    return not path.startswith(_LOCAL_ONLY) and not any(part.startswith(".env") for part in path.split("/"))


def files(kit_id: str, saved: dict[str, bytes]) -> dict[str, bytes]:
    """What Vercel builds: the saved files a project holds, the Express entry made exportable, and a vercel.json."""
    result = {path: data for path, data in saved.items() if _published(path)}
    if kit_id.startswith("vite-express-"):
        entry = result.get(_EXPRESS_ENTRY, b"").decode()
        if "export default app" not in entry:
            if entry.count(_KIT_LISTEN) != 1:
                raise NotPublishable(
                    "The app's server can't run on Vercel yet. Ask the builder: "
                    "“Export the Express app as the default export, and call app.listen only outside Vercel.”"
                )
            result[_EXPRESS_ENTRY] = entry.replace(_KIT_LISTEN, _EXPORTED_LISTEN).encode()
    # The kits ship this file and the builder may edit it; projects made before they did get the kit's.
    if "vercel.json" in result:
        try:
            config = json.loads(result["vercel.json"])
        except ValueError:
            config = None
        if not isinstance(config, dict):
            raise NotPublishable(
                "The app's vercel.json is not valid. Ask the builder: “Fix vercel.json so it is a valid JSON object.”"
            )
    else:
        result["vercel.json"] = (json.dumps(vercel_config(kit_id), indent=2) + "\n").encode()
    return result
