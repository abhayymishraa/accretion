"""What the build host does with a linked Supabase project: move the app's data in, migrate it, report its
security findings and answer the builder's read-only queries. The database URL reaches the sandbox only as the
environment of the one command that needs it, never a file the builder can read."""

import json
import logging
import re
from typing import Any

from e2b import CommandExitException, SandboxException
from sqlalchemy import literal, select, update
from sqlalchemy.dialects.postgresql import JSONB

from agent.sandbox.migrations import DUMP_COMPAT
from agent.sandbox.workspace import ROOT
from db.base import AutocommitSessionLocal
from db.models import Chat
from exceptions import DetailedHTTPException
from supabase_connect import client
from supabase_connect.models import ProjectDatabase
from supabase_connect.service import save_status

logger = logging.getLogger("webbuilder.supabase")

_MAX_ROWS = 200
_MAX_CHARS = 20_000
_MAX_FINDINGS = 20


async def _target(chat_id: str, status: str) -> tuple[int, str, dict[str, Any]] | None:
    """(owner, ref, sealed values) of the chat's link in `status`."""
    async with AutocommitSessionLocal() as db:
        found = (
            await db.execute(
                select(Chat.user_id, ProjectDatabase.project_ref, ProjectDatabase.secret)
                .join(Chat, Chat.id == ProjectDatabase.chat_id)
                .where(ProjectDatabase.chat_id == chat_id, ProjectDatabase.status == status)
            )
        ).first()
    if found is None:
        return None
    user_id, ref, secret = found.tuple()
    return user_id, ref, client.unseal(secret)


async def prepare(sandbox, chat_id: str, kit_id: str) -> bool:
    """Copies the built-in database into Supabase while the link is "moving". True when it moved data, so the
    caller restarts the app on its new database. A failure leaves the built-in database as it was."""
    target = await _target(chat_id, "moving")
    if target is None:
        return False
    command = (
        "set -a; . ./.env; set +a; set -o pipefail; "
        f'pg_dump --no-owner --no-privileges "$DATABASE_URL" | {DUMP_COMPAT}'
        ' | psql -q -v ON_ERROR_STOP=1 --single-transaction "$SUPABASE_DB_URL" >/dev/null'
    )
    try:
        await sandbox.commands.run(command, cwd=ROOT, envs={"SUPABASE_DB_URL": target[2]["database_url"]}, timeout=600)
    except (CommandExitException, SandboxException) as exc:
        # The output is not logged: psql can echo row data.
        logger.warning("Supabase data move failed chat=%s kit=%s error_type=%s", chat_id, kit_id, type(exc).__name__)
        # No message of its own: the panel shows the "error" status's default.
        await save_status(chat_id, "error", message=None)
        return False
    await save_status(chat_id, "ready", message=None)
    return True


async def migration_target(chat_id: str) -> str | None:
    """The database URL for the migration gate once the app runs on Supabase."""
    target = await _target(chat_id, "ready")
    return target[2]["database_url"] if target else None


async def security_findings(chat_id: str) -> list[dict[str, str]]:
    """Supabase's security advisor after a migration, e.g. a table anyone with the public key can read. Stored for
    the project panel too. Empty when it cannot be read: the advisor is a hint, never a reason to fail a build."""
    target = await _target(chat_id, "ready")
    if target is None:
        return []
    user_id, ref, _ = target
    try:
        body = await client.call(user_id, "GET", f"/v1/projects/{ref}/advisors/security", params={"lint_type": "sql"})
    except DetailedHTTPException:
        return []
    findings = [
        {key: str(lint.get(key) or "") for key in ("title", "detail", "remediation", "level")}
        for lint in body.get("lints", [])
        if lint.get("level") in ("ERROR", "WARN")
    ][:_MAX_FINDINGS]
    async with AutocommitSessionLocal() as db:
        await db.execute(
            update(ProjectDatabase)
            .where(ProjectDatabase.chat_id == chat_id)
            .values(detail=ProjectDatabase.detail.op("||")(literal({"findings": findings}, JSONB)))
        )
    return findings


# The query runs with the Management API's rights, which read Supabase's own schemas: stored secrets, users' emails and
# password hashes. ponytail: a name check stops accidents, not a builder set on it (a function can still reach them);
# run as a narrower role if that matters.
_PRIVATE_SCHEMAS = re.compile(r"\b(?:auth|vault|pgsodium|storage|supabase_functions|net)\s*\.", re.IGNORECASE)


async def read_query(chat_id: str, sql: str) -> dict[str, Any]:
    """The builder's read-only SQL against the app's Supabase database, bounded to 200 rows and 20,000
    characters."""
    target = await _target(chat_id, "ready")
    if target is None:
        return {"ok": False, "error": "This app doesn't use a Supabase database."}
    if _PRIVATE_SCHEMAS.search(sql):
        return {"ok": False, "error": "Supabase's own schemas (auth, vault, storage) hold secrets and personal data."}
    user_id, ref, _ = target
    try:
        rows = await client.call(
            user_id, "POST", f"/v1/projects/{ref}/database/query", json={"query": sql, "read_only": True}
        )
    except DetailedHTTPException as exc:
        return {"ok": False, "error": exc.detail}
    rows = rows if isinstance(rows, list) else []
    total = len(rows)
    rows = rows[:_MAX_ROWS]
    while rows and len(json.dumps(rows, default=str)) > _MAX_CHARS:
        rows = rows[: len(rows) // 2]
    return {"ok": True, "rows": rows, "row_count": total, "truncated": len(rows) < total}
