"""Build the E2B template (spec 8): one template, `accretion`, holding every kit and both databases.

Usage (from the repo root, E2B_API_KEY in .env):
    make template-build            # tags the build with its date and `production`
    make template-build TAG=staging
The backend asks for `accretion:<tag>` (E2B_TEMPLATE) and records the exact build each project
started on, so moving a tag never changes an existing project.

Both database servers are installed; neither runs at boot. `accretion-db start <engine>` starts
the one a kit declares, so an idle database costs no RAM (E2B bills CPU and RAM, not disk).
Every kit is copied to /opt/accretion/kits/<id>, installed and gated (typecheck, build, migrate,
services answer) during the build, so a project always starts from a verified working app
("green on day one"). The servers run as the sandbox user with their own data directories.
"""

import json
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path

from e2b import Template, default_build_logger

HERE = Path(__file__).resolve().parent
KITS_DIR = HERE / "kits"
NAME = "accretion"
TEMPLATE_KITS = "/opt/accretion/kits"
ROOT = "/home/user/react-app"
# Latest stable (2026-09): Postgres 18 from PGDG, MongoDB 8.3. MongoDB publishes server packages
# for bookworm only, so the base stays on bookworm; its 8.3 repo is signed with the 8.0 key.
# PG_MAJOR is repeated in accretion-db.sh.
PG_MAJOR = 18
MONGO_SERIES = "8.3"
# Spec 8: 2-4 GB; the default 512 MiB-1 GB cannot run a frontend, a backend and a database.
CPU_COUNT = 2
MEMORY_MB = 4096
AGENT_BROWSER = "0.38.1"
# Page output is untrusted, so the CLI marks it with nonce boundaries (contentBoundaries) and caps it
# under the command tool's 12k output (maxOutput), leaving room for the rest of a chained command.
AGENT_BROWSER_CONFIG = {
    "executablePath": "/usr/local/bin/chrome-headless-shell",
    "screenshotDir": "/tmp/agent-browser",
    "contentBoundaries": True,
    "maxOutput": 8000,
}
GATE_ENV = {
    "postgres": {"DATABASE_URL": "postgresql://app:gate@127.0.0.1:5432/app"},
    "mongo": {"MONGO_URL": "mongodb://127.0.0.1:27017/app"},
}


def kits() -> dict[str, str]:
    """Kit id -> its database, from each sandbox/kits/<id>/stack.json."""
    return {
        path.parent.name: json.loads(path.read_text())["database"] for path in sorted(KITS_DIR.glob("*/stack.json"))
    }


def build_template() -> Template:
    template = (
        Template(
            file_context_path=HERE,
            file_ignore_patterns=["**/node_modules/**", "**/.venv/**", "**/dist/**", "**/.next/**", "**/db/*.db*"],
        )
        .from_image("node:24.21.0-bookworm-slim")
        .set_user("root")
        # base: python3 runs the archive script and FastAPI kits.
        .run_cmd(
            "apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg tree procps"
            " python3 python3-venv && rm -rf /var/lib/apt/lists/*"
        )
        # browser: Playwright's pinned package downloads Chromium's headless shell with its system
        # libraries; agent-browser drives that same binary, so the image carries one browser.
        .set_envs({"PLAYWRIGHT_BROWSERS_PATH": "/opt/pw-browsers"})
        .copy(["checks/package.json", "checks/package-lock.json"], "/opt/webbuilder-checks/")
        .run_cmd(
            "cd /opt/webbuilder-checks && npm ci --no-audit --no-fund"
            " && npx playwright install --with-deps --only-shell chromium"
            " && chmod -R a+rX /opt/webbuilder-checks /opt/pw-browsers"
        )
        # The model verifies the app with agent-browser through its ordinary command tool. Its npm
        # package ships the native CLI, so the skipped postinstall is not needed (checked 0.38.1).
        # Template envs do not reach runtime commands, so the browser path lives in agent-browser's
        # own user config, which every invocation reads (keys are camelCase; others are ignored).
        .run_cmd(
            f"npm install -g agent-browser@{AGENT_BROWSER} --no-audit --no-fund && agent-browser --version"
            " && mkdir -p /home/user/.agent-browser && printf '%s' "
            + shlex.quote(json.dumps(AGENT_BROWSER_CONFIG))
            + ' > /home/user/.agent-browser/config.json && ln -s'
            ' "$(ls /opt/pw-browsers/chromium_headless_shell-*/chrome-*/chrome-headless-shell)"'
            f" {AGENT_BROWSER_CONFIG['executablePath']} && chown -R user:user /home/user/.agent-browser"
        )
        # Postgres from PGDG.
        .run_cmd(
            "curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc"
            " | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg"
            ' && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg]'
            ' https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main"'
            " > /etc/apt/sources.list.d/pgdg.list"
            f" && apt-get update && apt-get install -y --no-install-recommends postgresql-{PG_MAJOR}"
            f" postgresql-client-{PG_MAJOR} && rm -rf /var/lib/apt/lists/*"
        )
        # MongoDB with its shell and dump tools.
        .run_cmd(
            "curl -fsSL https://pgp.mongodb.com/server-8.0.asc"
            " | gpg --dearmor -o /usr/share/keyrings/mongodb-server-8.0.gpg"
            ' && echo "deb [signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg]'
            f' https://repo.mongodb.org/apt/debian bookworm/mongodb-org/{MONGO_SERIES} main"'
            " > /etc/apt/sources.list.d/mongodb-org.list"
            " && apt-get update && apt-get install -y --no-install-recommends mongodb-org"
            " && rm -rf /var/lib/apt/lists/*"
        )
        .copy("accretion-db.sh", "/usr/local/bin/accretion-db")
        .run_cmd("chmod 755 /usr/local/bin/accretion-db")
        .run_cmd(f"mkdir -p {TEMPLATE_KITS} {ROOT} && chown -R user:user {TEMPLATE_KITS} {ROOT}")
        .copy("kit-gate.mjs", "/opt/accretion/kit-gate.mjs")
    )
    for kit in kits():
        template = template.copy(f"kits/{kit}", f"{TEMPLATE_KITS}/{kit}")
    # COPY's user= does not own the destination folder itself; npm then cannot create node_modules.
    template = template.run_cmd(f"chown -R user:user {TEMPLATE_KITS}").set_user("user")
    template = template.run_cmd(
        # Local trust auth: the server listens on 127.0.0.1 inside the sandbox only. One "app"
        # role and database; DATABASE_URL still carries a generated password.
        # UTF8 explicitly: the image has no locale, so initdb would pick SQL_ASCII and psycopg
        # would return bytes. The package's socket dir /var/run/postgresql belongs to postgres,
        # so the sandbox user's server keeps its socket in /tmp. TCP stays on loopback only.
        f"/usr/lib/postgresql/{PG_MAJOR}/bin/initdb -D /home/user/.pg --auth=trust --username=user"
        " --encoding=UTF8 --locale=C.UTF-8 >/dev/null"
        " && printf \"%s\\n\" \"unix_socket_directories = '/tmp'\" \"listen_addresses = '127.0.0.1'\""
        " >> /home/user/.pg/postgresql.conf && mkdir -p /home/user/.mongo"
        " && accretion-db start postgres && createuser -h 127.0.0.1 -U user app"
        " && createdb -h 127.0.0.1 -U user -O app app && accretion-db stop postgres"
    )
    for kit, database in kits().items():
        # Green on day one: install, then typecheck, build, migrate and boot every service.
        # Each build step is its own process: start the kit's database, gate, then stop it. The
        # reset leaves every project started from the template an empty database.
        gate = json.dumps({**GATE_ENV[database], "APP_SECRET": "gate"})
        template = template.run_cmd(
            f"accretion-db start {database} && KIT_GATE_ENV='{gate}' node /opt/accretion/kit-gate.mjs"
            f" {TEMPLATE_KITS}/{kit} && accretion-db reset {database};"
            f" status=$?; accretion-db stop {database}; exit $status"
        )
    return template.set_workdir(ROOT)


def main() -> None:
    if len(sys.argv) > 2:
        sys.exit("usage: templates.py [tag]  (default: production)")
    tag = sys.argv[1] if len(sys.argv) == 2 else "production"
    version = datetime.now(UTC).strftime("v%Y%m%d-%H%M")
    info = Template.build(
        build_template(),
        NAME,
        # The date tag names this build forever; the second tag is the one the backend follows.
        tags=[version, tag],
        cpu_count=CPU_COUNT,
        memory_mb=MEMORY_MB,
        on_build_logs=default_build_logger(),
    )
    print(f"Built {NAME}:{version} (build {info.build_id}); {NAME}:{tag} now points at it.")


if __name__ == "__main__":
    main()
