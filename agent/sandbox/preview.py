"""Host-owned preview lifecycle; independent of generated project files."""

import json
import shlex

from agent import PACKAGE_ROOT
from config import settings

from .workspace import Workspace

# The preview URL's port: preview_proxy.py, in front of the kit's own web port (stack.json
# preview_port), so the builder can follow and step the app's navigation. Clear of every kit port.
PROXY_PORT = 8790
# Outside /tmp: files.write runs as root and hands the file to `user`, and /tmp's sticky bit
# (fs.protected_regular) then refuses root a second write, so every restart after the first failed.
_PROXY_PATH = "/home/user/.accretion-preview-proxy.py"


class PreviewError(Exception):
    pass


async def control_preview(sandbox, action):
    if action not in {"stop", "start", "restart"}:
        raise ValueError("Unknown preview operation")
    script = (PACKAGE_ROOT / "sandbox" / "preview_process.py").read_text()
    # Outside the project tree: the proxy is host code, never part of the files the model edits.
    await sandbox.files.write(_PROXY_PATH, (PACKAGE_ROOT / "sandbox" / "preview_proxy.py").read_text())
    args = [action, str(PROXY_PORT), _PROXY_PATH, json.dumps(settings.cors_origins)]
    result = await Workspace(sandbox).command(
        "python3 -c " + shlex.quote(script) + " " + " ".join(map(shlex.quote, args)), timeout_seconds=150
    )
    if not result["ok"]:
        raise PreviewError("Preview server could not " + action + ". Saved project files are preserved.")


async def ensure_preview_current(workspace) -> None:
    """Restart the preview when files changed since it last started, so a check sees current code."""
    if workspace.preview_revision != workspace.revision:
        # Advance only after restart succeeds; failed restarts must remain retryable.
        await control_preview(workspace.sandbox, "restart")
        workspace.preview_revision = workspace.revision
