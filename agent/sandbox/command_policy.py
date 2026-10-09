"""Commands the host refuses to run for the model, whatever the model asks."""

import re

# Starting a second dev server breaks the host-owned preview (spec 8: services are started
# by the host from stack.json). Builds (`vite build`, `next build`) stay allowed.
# Long-running processes the kits already run (sandbox/kits/*/stack.json services) or that never exit.
DEV_SERVER = re.compile(
    r"npm\s+run\s+(?:dev|start)\b|\buvicorn\b|\bnext\s+(?:dev|start)\b|\bvite(?:\.js)?(?!\s+build)(?:\s|$)"
    r"|\b(?:tsx|node)\b[^|;&]*\bsrc/index\.ts\b|\bmongod\b|\bpg_ctl\b|\bsystemctl\s+(?:start|restart)\b|\btail\s+-f\b"
)
# A search names a server without starting one: `ps aux | grep uvicorn` is diagnosis. Quoted
# patterns are kept whole, so a `|` inside `grep -E "a|uvicorn"` does not end the segment.
_SEARCH = re.compile(r"\b(?:grep|egrep|pgrep)\b(?:\s+(?:\"[^\"]*\"|'[^']*'|[^\s|;&]+))*")
# Spec 6 migration gate: the host applies migrations, after checking they keep saved data.
MIGRATE = re.compile(
    r"\balembic\s+(?:upgrade|downgrade|stamp)\b|\bnpm\s+run\s+migrate\b|\bdrizzle-kit\s+(?:migrate|push)\b"
    r"|\b(?:tsx|node)\s+(?:\S*/)?(?:db/migrate|src/db)\.ts\b|\bmongosh\b|\bpsql\b|\b(?:create|drop)_all\b"
)
# An install run where no package.json exists creates a stray project there (a second copy of React,
# for one). Only the no-directory form is checked: `cd <dir> &&` and `--prefix` name a directory.
_NPM_INSTALL = re.compile(r"\bnpm\s+(?:i|install|add)\b")
_NAMES_DIR = re.compile(r"\bcd\s+\S|--prefix\b")
_RELATIVE_INSTALL = re.compile(r"npm\s+(?:i|install)\s+(?:\.{1,2})(?:\s|$)")


def refusal(command: str) -> str | None:
    """Why the host refuses this command, or None. The stray-install check needs the sandbox: installs_at_root."""
    if _RELATIVE_INSTALL.search(command):
        return "Relative imports are not npm packages"
    if DEV_SERVER.search(_SEARCH.sub("", command)):
        return "The project's services are already running; do not start another server"
    if MIGRATE.search(command):
        return (
            "Do not migrate or edit the database directly: write the migration file."
            " The host applies new migrations before each agent-browser command and when you finish."
        )
    return None


def installs_at_root(command: str) -> bool:
    """An npm install that names no directory, so it runs in the project root."""
    return bool(_NPM_INSTALL.search(command)) and not _NAMES_DIR.search(command)
