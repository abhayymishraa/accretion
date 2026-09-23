"""Shared browser checks and bounded observations; screenshots stay in memory."""
from typing import Any
import base64
from contextlib import suppress
import json
from pathlib import Path
import shlex
from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from .config import sandbox_settings

MAX_SCREENSHOT_BYTES = 200_000


class PreviewStep(BaseModel):
    action: Literal['click', 'fill', 'check', 'press', 'expect_visible', 'expect_hidden',
                    'expect_text', 'expect_checked']
    selector: str = Field(min_length=1, max_length=300)
    value: str = Field(default='', max_length=200)

    @model_validator(mode='after')
    def validate_value(self):
        if self.action == 'expect_text' and not self.value.strip():
            raise ValueError('Text assertions need a nonempty expected value')
        if self.action == 'press' and self.value not in {'Enter', 'Escape', 'Tab', 'Space', 'ArrowDown', 'ArrowUp'}:
            raise ValueError('Use Enter, Escape, Tab, Space, ArrowDown or ArrowUp')
        return self


async def check_browser(workspace, *, preflight=False, viewport=None, path='/', screenshot_path=None, checks=None) -> dict[str, Any]:
    script = Path(__file__).with_name('browser-check.cjs').read_text()
    args = []
    if preflight:
        args = ['--preflight']
    elif viewport is not None:
        args = ['--inspect', viewport, path]
        if screenshot_path is not None:
            args.append(screenshot_path)
    if checks:
        args += ['--checks', json.dumps(checks)]
    command = 'PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers ' + shlex.join(['node', '-e', script, '--', *args])
    result: dict[str, Any] = await workspace.command(command, timeout=90 if checks else 45)
    return result


async def ensure_preview_current(workspace) -> None:
    from .preview import control_preview
    if workspace.preview_revision != workspace.revision:
        # Advance only after restart succeeds; failed restarts must remain retryable.
        await control_preview(workspace.sandbox, 'restart')
        workspace.preview_revision = workspace.revision


async def inspect_preview(workspace, *, viewport, path, screenshot=False, steps=None) -> dict[str, Any]:
    if (not path.startswith('/') or path.startswith('//') or '\\' in path
            or any(ord(char) < 32 for char in path) or len(path) > 512):
        raise ValueError('Use a local preview path such as / or /settings')
    if viewport not in {'desktop', 'mobile'}:
        raise ValueError('Use the desktop or mobile viewport')
    if steps:
        if len(steps) > 8 or not steps[-1].action.startswith('expect_'):
            raise ValueError('Use at most eight steps, ending with an assertion of the result')
        # Keep one replayable acceptance sequence per viewport, including failed attempts.
        workspace.preview_checks[viewport] = {'path': path, 'steps': [step.model_dump() for step in steps]}
    if screenshot:
        if not sandbox_settings.PREVIEW_SCREENSHOTS_ENABLED:
            raise ValueError('Screenshot observations are disabled for this model deployment')
        if workspace.screenshot_attempts >= 2:
            raise ValueError('Screenshot limit reached; use text inspection for the rest of this run')
        workspace.screenshot_attempts += 1
    await ensure_preview_current(workspace)
    screenshot_path = f'/tmp/webbuilder-preview-{uuid4().hex}.jpg' if screenshot else None
    try:
        checks = {viewport: workspace.preview_checks[viewport]} if steps else None
        result = await check_browser(workspace, viewport=viewport, path=path,
                                     screenshot_path=screenshot_path, checks=checks)
        observation = parse_observation(result, workspace.revision)
        if screenshot and observation.get('checked'):
            observation['screenshot'] = {'captured': False}
            try:
                image = await read_screenshot(workspace.sandbox, screenshot_path)
            except Exception:
                observation['screenshot']['error'] = 'Screenshot unavailable; use the text observation'
            else:
                observation['screenshot'].update(captured=True, bytes=len(image), detail='low')
                # Runner removes this private field before JSON/public events or persistence.
                observation['_image'] = {'type': 'image_url', 'image_url': {
                    'url': 'data:image/jpeg;base64,' + base64.b64encode(image).decode('ascii'),
                    'detail': 'low'}}
        return observation
    finally:
        if screenshot_path:
            with suppress(Exception):
                await workspace.sandbox.files.remove(screenshot_path, request_timeout=5)


async def read_screenshot(sandbox, path) -> bytes:
    data = bytearray()
    reader = await sandbox.files.read(path, format='stream', request_timeout=10, stream_idle_timeout=5)
    async with reader:
        async for chunk in reader:
            if len(data) + len(chunk) > MAX_SCREENSHOT_BYTES:
                raise ValueError('Screenshot exceeds the size limit')
            data.extend(chunk)
    if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
        raise ValueError('Screenshot is not a JPEG')
    return bytes(data)


def parse_observation(result, revision) -> dict[str, Any]:
    try:
        observation = json.loads(result['stdout'])
    except (ValueError, KeyError):
        return {'ok': False, 'checked': False, 'revision': revision,
                'error': 'Browser inspection did not return an observation',
                'stderr': result.get('stderr', '')[:2000]}
    if not isinstance(observation, dict) or not isinstance(observation.get('pages'), list):
        return {'ok': False, 'checked': False, 'revision': revision,
                'error': 'Browser inspection returned an invalid observation'}
    return {**observation, 'ok': bool(result['ok'] and observation.get('ok')),
            'revision': revision, 'final_verification': False}
