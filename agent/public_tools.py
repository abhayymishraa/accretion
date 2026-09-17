"""Small, versioned public projections; never publish arbitrary tool arguments/content."""
import json

from .events import redact

MAX_PUBLIC_BYTES = 1600
SAFE_COMMANDS = {'npm run build', 'npm test', 'npm run lint', 'npm run typecheck', 'pwd', 'ls'}


def encode_public(details):
    return json.dumps(details, ensure_ascii=False, separators=(',', ':'))


def _bounded(fields):
    """Redact structured fields first, then shrink values without breaking JSON."""
    result = redact(fields, max_length=None)
    truncated = set()
    while len(encode_public(result).encode()) > MAX_PUBLIC_BYTES:
        candidates = [(len(encode_public(value).encode()), key) for key, value in result.items()
                      if key not in {'version', 'kind', 'error_category', 'truncated_fields'}
                      and isinstance(value, (str, list)) and value]
        if not candidates:
            break
        _, key = max(candidates)
        value = result[key]
        result[key] = value[:len(value) // 2]
        truncated.add(key)
        result['truncated_fields'] = sorted(truncated)
    return result


def public_tool_details(name, *, args=None, result=None):
    """Same projection feeds durable history, websocket updates and copy actions."""
    fields = {'version': 1, 'kind': name[:80]}
    args = args if isinstance(args, dict) else {}
    changes = args.get('files') if isinstance(args.get('files'), list) else []
    if result is None:
        paths = []
        if name == 'read_files':
            paths = args.get('paths', [])
        elif name == 'write_files':
            paths = [item.get('path') for item in changes if isinstance(item, dict)]
        paths = [path for path in paths if isinstance(path, str)] if isinstance(paths, list) else []
        if paths:
            fields.update(paths=paths, file_count=len(paths))
    else:
        fields['ok'] = bool(result.get('ok'))
        # Results contain source/skill bodies: allowlist by tool before any serialization.
        if name == 'read_files' and isinstance(result.get('files'), (dict, list)):
            paths = [path for path in result['files'] if isinstance(path, str)]
            fields.update(files=paths, file_count=len(paths))
        elif name == 'write_files' and isinstance(result.get('changed_files'), list):
            paths = [path for path in result['changed_files'] if isinstance(path, str)]
            fields.update(changed_files=paths, file_count=len(paths))
        elif name == 'search_project_history':
            messages = result.get('messages') if isinstance(result.get('messages'), list) else []
            refs = [item['id'] for item in messages
                    if isinstance(item, dict) and isinstance(item.get('id'), str)]
            fields.update(message_ids=refs, match_count=len(refs))
        elif name == 'read_skill':
            fields.update({key: result[key] for key in ('name', 'resource', 'sha256', 'bytes', 'status')
                           if isinstance(result.get(key), (str, int, bool))})
        elif name in {'execute_command', 'browser_preflight'}:
            fields.update({key: result[key] for key in ('stdout', 'stderr', 'exit_code', 'pid', 'status', 'reconnected', 'output_may_be_incomplete')
                           if isinstance(result.get(key), (str, int))})
        elif name == 'inspect_preview':
            # Page text stays in model context; public history contains only bounded diagnostics.
            fields.update({key: result[key] for key in ('revision', 'checked', 'final_verification')
                           if isinstance(result.get(key), (int, bool))})
            fields['errors'] = [item[:500] for item in result.get('errors', [])
                                if isinstance(item, str)][:10]
            fields['viewports'] = [page['viewport'] for page in result.get('pages', [])
                                   if isinstance(page, dict) and page.get('viewport') in {'desktop', 'mobile'}]
            fields['steps'] = [{'action': step.get('action'), 'ok': step.get('ok') is True}
                              for page in result.get('pages', []) if isinstance(page, dict)
                              for step in page.get('steps', []) if isinstance(step, dict)][:8]
            screenshot = result.get('screenshot')
            if isinstance(screenshot, dict):
                fields['screenshot_captured'] = screenshot.get('captured') is True
        if isinstance(result.get('error'), str):
            fields['error'] = result['error']
        if isinstance(result.get('error_type'), str):
            fields['error_type'] = result['error_type']
    if name == 'execute_command':
        command = args.get('command')
        if isinstance(command, str) and command.strip() in SAFE_COMMANDS:
            fields['command'] = command.strip()
        else:
            fields['input_omitted'] = True
    return _bounded(fields)


def preflight_failure(result):
    """Classify observed failures without claiming an unverified underlying cause."""
    diagnostic = str(result.get('stderr', '')) + ' ' + str(result.get('error', ''))
    lowered = diagnostic.lower()
    if (result.get('error_type') in {'TimeoutException', 'TimeoutError', 'ReadTimeout'}
            or 'context deadline exceeded' in lowered or 'timed out' in lowered
            or 'timeout' in lowered and 'exceeded' in lowered):
        return ('browser_check_timeout',
                'The sandbox browser startup check timed out. No editing model request was made. '
                'Browser startup needs investigation; this does not prove the template is missing dependencies.')
    if ("cannot find module '/opt/webbuilder-checks/node_modules/playwright'" in lowered
            or "executable doesn't exist" in lowered):
        return ('browser_tools_missing',
                'The sandbox is missing the required browser tooling. Check E2B_TEMPLATE_ID and use '
                'the webbuilder-react-verified template with Playwright and Chromium installed. '
                'No editing model request was made.')
    return ('browser_check_failed',
            'The sandbox browser startup check failed. Inspect the recorded diagnostic before changing '
            'the template. No editing model request was made.')
