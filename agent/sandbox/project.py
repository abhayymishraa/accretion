"""A kit project's life in its sandbox (spec 8): first start, restore, and database dumps.

Everything here runs from the project root with the project's .env sourced.
"""

import json
import shlex

from e2b import AsyncTemplate

from .config import sandbox_settings
from .kits import KITS, TEMPLATE_KITS_DIR, Kit
from .migrations import record_applied
from .preview import control_preview
from .secrets import ensure_secrets, env_file, user_env_file, user_secrets
from .workspace import ROOT

# The user's keys, read only by the app's services (preview_process.kit_env). Its .env. name keeps it out of
# saved revisions, the file tools and the file tree, like .env.
USER_ENV = ".env.json"


async def template_ref() -> str:
    """The exact build E2B_TEMPLATE's tag points at now. Projects store this, not the tag, so a
    later tag move never changes the image an existing project restores onto."""
    name, tag = sandbox_settings.E2B_TEMPLATE.split(":", 1)
    for item in await AsyncTemplate.get_tags(name):
        if item.tag == tag:
            return f"{name}:{item.build_id}"
    raise KitTemplateMissing(f"Template tag {sandbox_settings.E2B_TEMPLATE!r} does not exist; run make template-build")


class KitTemplateMissing(Exception):
    pass


async def _start_database(sandbox, kit: Kit) -> None:
    """Spec 8: only the kit's database runs; the template starts none at boot."""
    await sandbox.commands.run(f"accretion-db start {kit.database}", timeout=60)


async def _run(sandbox, command: str, *, timeout_seconds: int = 180) -> None:
    """One stack.json step from the project root with .env loaded. Empty means nothing to do."""
    if command:
        await sandbox.commands.run(f"set -a; . ./.env; set +a; {command}", cwd=ROOT, timeout=timeout_seconds)


async def _write_config(sandbox, chat_id: str, kit: Kit) -> None:
    """.env and .env.json from the project's secrets (mode 600) and the kit's stack.json for the process
    controller."""
    values, user = await ensure_secrets(chat_id, kit)
    await sandbox.files.write(f"{ROOT}/.env", env_file(values))
    await sandbox.files.write(f"{ROOT}/{USER_ENV}", user_env_file(user))
    await sandbox.commands.run(
        f"chmod 600 {ROOT}/.env {ROOT}/{USER_ENV} && mkdir -p {ROOT}/.accretion {ROOT}/db", timeout=10
    )
    await sandbox.files.write(f"{ROOT}/.accretion/stack.json", json.dumps(kit.model_dump(), indent=2))


async def sync_secrets(sandbox, chat_id: str) -> None:
    """A reused sandbox gets the user's current keys; the app restarts only when they changed, so a key saved
    since the sandbox started reaches the app without a rebuild."""
    content = user_env_file(await user_secrets(chat_id))
    path = f"{ROOT}/{USER_ENV}"
    # No file reads as no keys, as kit_env reads it.
    current = await sandbox.files.read(path) if await sandbox.files.exists(path) else user_env_file({})
    if current == content:
        return
    await sandbox.files.write(path, content)
    await sandbox.commands.run(f"chmod 600 {path}", timeout=10)
    await control_preview(sandbox, "restart")


async def start_new(sandbox, chat_id: str, kit_id: str) -> None:
    """A new project's files: the kit, dependencies included, moved into place from the template. start_services
    then migrates and starts it."""
    kit = KITS[kit_id]
    source = shlex.quote(f"{TEMPLATE_KITS_DIR}/{kit.id}")
    # A rename on one disk, not a copy of every dependency file (10.8 s down to 0.5 s). The kit's .venv scripts
    # keep their template path in the shebang, so that path stays as a link to the project.
    await sandbox.commands.run(f"rmdir {ROOT} && mv {source} {ROOT} && ln -s {ROOT} {source}", timeout=120)
    await _write_config(sandbox, chat_id, kit)


async def start_services(sandbox, kit_id: str) -> None:
    """After start_new: the kit's database, migrated and seeded, then its services."""
    kit = KITS[kit_id]
    await _start_database(sandbox, kit)
    await _run(sandbox, kit.migrate)
    await record_applied(sandbox, kit.model_dump())
    await _run(sandbox, kit.seed)
    await control_preview(sandbox, "start")


async def restore(sandbox, chat_id: str, kit_id: str) -> None:
    """After a revision archive is unpacked: dependencies, then the database from its dump
    (or the kit's migrations when the revision has none), then the services."""
    kit = KITS[kit_id]
    await _write_config(sandbox, chat_id, kit)
    await _run(sandbox, kit.install, timeout_seconds=300)
    await _start_database(sandbox, kit)
    # Kits write their dump as db/dump.* (stack.json `dump`); db/ may also hold source files.
    listing = await sandbox.commands.run(f"ls {ROOT}/db/dump.* 2>/dev/null || true", timeout=10)
    if kit.restore and listing.stdout.strip():
        # The dump matches the revision's .accretion/migrated.json; a newer migration file in the
        # revision stays unapplied until the gate runs it.
        await _run(sandbox, kit.restore)
    else:
        await _run(sandbox, kit.migrate)
        await record_applied(sandbox, kit.model_dump())
    await control_preview(sandbox, "start")


async def dump(sandbox, kit_id: str) -> None:
    """Spec 3: the database travels with the revision, dumped into db/ before each checkpoint."""
    await _run(sandbox, KITS[kit_id].dump, timeout_seconds=120)
