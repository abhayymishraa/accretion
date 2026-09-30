"""Host-owned preview lifecycle; independent of generated project files."""
from pathlib import Path
import shlex

from ..tools.tools import WorkspaceTools


class PreviewError(Exception):
    pass


async def control_preview(sandbox, action):
    if action not in {'stop', 'start', 'restart'}:
        raise ValueError('Unknown preview operation')
    script = Path(__file__).with_name('preview_process.py').read_text()
    result = await WorkspaceTools(sandbox).command(
        'python3 -c ' + shlex.quote(script) + ' ' + action, timeout_seconds=150)
    if not result['ok']:
        raise PreviewError('Preview server could not ' + action + '. Saved project files are preserved.')


async def ensure_preview_current(workspace) -> None:
    """Restart the preview when files changed since it last started, so a check sees current code."""
    if workspace.preview_revision != workspace.revision:
        # Advance only after restart succeeds; failed restarts must remain retryable.
        await control_preview(workspace.sandbox, 'restart')
        workspace.preview_revision = workspace.revision
