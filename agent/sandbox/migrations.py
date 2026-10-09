"""The migration gate (spec 6): dry-run on a copy, ask before losing data, dump, migrate, restore.

The host applies migrations; agents only write them (a command guard in tools.py), and no kit
migrates at startup. The gate runs when a file under the kit's `migrations` paths changed since
the set recorded in .accretion/migrated.json, which project start writes after the first migration.
"""

import json
import re
import shlex
from collections.abc import Collection
from typing import Any

from e2b import CommandExitException, SandboxException

from .workspace import ROOT

APPLIED = ".accretion/migrated.json"
_ENV = "set -a; . ./.env; set +a; "

# Spec 6 step 3: dropping or emptying a table or column, or changing a column's type, loses data.
_DESTRUCTIVE = re.compile(
    # SQL (Postgres makes COLUMN optional in ALTER ... TYPE).
    r"\bDROP\s+(?:TABLE|COLUMN|SCHEMA|TYPE|VIEW|DATABASE)\b|\bTRUNCATE\b|\bDELETE\s+FROM\b"
    r"|\bALTER\s+(?:COLUMN\s+)?\S+\s+(?:SET\s+DATA\s+)?TYPE\b"
    # Alembic, any receiver (op., batch_op.): drops and type changes.
    r"|\.drop_(?:table|column)\s*\(|\btype_\s*="
    # MongoDB driver.
    r"|\.drop\s*\(|\bdropCollection\b|\bdropDatabase\b|\bdelete(?:One|Many)\s*\(|\bremove\s*\("
    r"|\bfindOneAndDelete\b|\$unset\b",
    re.IGNORECASE,
)


class DestructiveMigration(Exception):
    """A new migration would delete saved data; the user must approve these files first."""

    def __init__(self, files: list[str]):
        super().__init__("A database change would delete saved data")
        self.files = files


async def _sh(sandbox, command: str, timeout_seconds: int = 180) -> tuple[bool, str]:
    """A failed or timed-out command is a result, not an exception: the gate must always get to
    its restore and cleanup steps."""
    try:
        result = await sandbox.commands.run(command, cwd=ROOT, timeout=timeout_seconds)
    except CommandExitException as exc:
        return False, (exc.stdout + exc.stderr)[-4000:]
    except SandboxException as exc:
        return False, str(exc)[-4000:]
    return True, (result.stdout + result.stderr)[-4000:]


async def _hashes(sandbox, paths: list[str]) -> dict[str, str]:
    if not paths:
        return {}
    targets = " ".join(shlex.quote(path) for path in paths)
    ok, output = await _sh(
        sandbox, f"find {targets} -type f -not -path '*/__pycache__/*' 2>/dev/null | sort | xargs -r sha256sum", 30
    )
    hashes = {}
    for line in output.splitlines() if ok else []:
        digest, _, path = line.partition("  ")
        if path:
            hashes[path] = digest
    return hashes


async def record_applied(sandbox, stack: dict[str, Any]) -> None:
    """The migrations now in the database; the gate only looks at files changed after this."""
    await sandbox.files.write(f"{ROOT}/{APPLIED}", json.dumps(await _hashes(sandbox, stack["migrations"])))


def _upgrade_part(text: str) -> str:
    # An Alembic file always carries its own downgrade drops; only the upgrade runs forward.
    return text.split("def downgrade", 1)[0]


def _copy_commands(stack: dict[str, Any], target: str) -> tuple[str, str]:
    """(dump the live database to `target`, restore it from `target`), outside db/ so a checkpoint's
    own dump never overwrites it."""
    if stack["database"] == "postgres":
        return (
            f'pg_dump --clean --if-exists --no-owner "$DATABASE_URL" > {target}',
            f'psql "$DATABASE_URL" -q -f {target} >/dev/null',
        )
    return (
        f'mongodump --uri "$MONGO_URL" --archive={target} --quiet',
        f'mongorestore --uri "$MONGO_URL" --archive={target} --drop --quiet',
    )


async def snapshot(sandbox, stack: dict[str, Any], target: str) -> bool:
    return (await _sh(sandbox, _ENV + _copy_commands(stack, target)[0]))[0]


async def restore_snapshot(sandbox, stack: dict[str, Any], target: str) -> bool:
    return (await _sh(sandbox, _ENV + _copy_commands(stack, target)[1]))[0]


async def _dry_run(sandbox, stack: dict[str, Any]) -> tuple[bool, str]:
    """Spec 6 step 2: migrate a copy of the live database, with the URL pointed at the copy."""
    if stack["database"] == "postgres":
        admin = "-h 127.0.0.1 -U user"
        copy = f"dropdb {admin} --if-exists app_dryrun && createdb {admin} -O app app_dryrun"
        load = 'pg_dump --no-owner "$DATABASE_URL" | psql -q "${DATABASE_URL%/app}/app_dryrun" >/dev/null'
        url = 'DATABASE_URL="${DATABASE_URL%/app}/app_dryrun"'
        drop = f"dropdb {admin} --if-exists app_dryrun"
    else:
        copy = "mongosh --quiet app_dryrun --eval 'db.dropDatabase()' >/dev/null"
        load = (
            'mongodump --uri "$MONGO_URL" --archive --quiet | mongorestore --uri mongodb://127.0.0.1:27017'
            " --archive --nsFrom 'app.*' --nsTo 'app_dryrun.*' --quiet"
        )
        url = 'MONGO_URL="${MONGO_URL%/app}/app_dryrun"'
        drop = copy
    try:
        return await _sh(sandbox, f"{_ENV}{copy} && {load} && {url} bash -c {shlex.quote(stack['migrate'])}")
    finally:
        await _sh(sandbox, _ENV + drop, 60)


async def gate(sandbox, stack: dict[str, Any], *, allow_data_loss: Collection[str] = ()) -> dict[str, Any]:
    """`allow_data_loss` lists the migration files the user approved after being asked."""
    current = await _hashes(sandbox, stack["migrations"])
    try:
        applied = json.loads(await sandbox.files.read(f"{ROOT}/{APPLIED}"))
    except (SandboxException, ValueError):
        # No record yet (or an unreadable one): every migration file counts as changed.
        applied = {}
    changed = [path for path, digest in current.items() if applied.get(path) != digest]
    if not changed:
        return {"ok": True, "migrations": "unchanged"}
    destructive = [
        path
        for path in changed
        if path not in allow_data_loss
        and _DESTRUCTIVE.search(_upgrade_part(await sandbox.files.read(f"{ROOT}/{path}")))
    ]
    if destructive:
        raise DestructiveMigration(destructive)
    ok, output = await _dry_run(sandbox, stack)
    if not ok:
        return {"ok": False, "migrations": "dry_run_failed", "files": changed, "output": output}
    # Spec 6 steps 1 and 4: dump first (outside db/, so no checkpoint replaces it), and restore it
    # if the real migration fails. No dump, no migration.
    backup = "/tmp/accretion-premigrate.dump"
    if not await snapshot(sandbox, stack, backup):
        return {"ok": False, "migrations": "backup_failed", "files": changed}
    ok, output = await _sh(sandbox, _ENV + stack["migrate"])
    if not ok:
        await restore_snapshot(sandbox, stack, backup)
        return {"ok": False, "migrations": "failed_and_restored", "files": changed, "output": output}
    await sandbox.files.write(f"{ROOT}/{APPLIED}", json.dumps(current))
    return {"ok": True, "migrations": "applied", "files": changed}
