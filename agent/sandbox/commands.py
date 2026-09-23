"""Bounded command observations. Reconnect to owned processes, never replay them."""
from typing import Any
import asyncio
from uuid import uuid4

import httpx
from e2b import CommandExitException, SandboxException

MAX_OUTPUT = 12_000
MAX_STREAM_OUTPUT = 256_000
# Pi's bash tool: keep the tail, save full text to a file named in the output.
# ponytail: files die with the sandbox; a stale path means rerun the command.
_FULL_OUTPUT_DIR = '/tmp/tool-output'


async def _bounded_output(sandbox, text: str, stream: str, max_output: int) -> str:
    if len(text) <= max_output:
        return text
    path = f'{_FULL_OUTPUT_DIR}/{uuid4().hex}-{stream}.log'
    try:
        await sandbox.files.write(path, text, request_timeout=10)
    except (SandboxException, httpx.HTTPError):
        where = 'full output could not be saved'
    else:
        where = f'full output: {path}'
    return text[-max_output:] + f'\n[showing the last {max_output} of {len(text)} characters; {where}]'


class CommandStateError(SandboxException):
    """The run must retire its sandbox before any further edits or checkpoints."""


async def run_command(sandbox, command: str, *, cwd: str, timeout: int, max_output: int = MAX_OUTPUT) -> dict[str, Any]:
    handle = None
    received = 0
    reconnected = False

    def limit_output(chunk):
        nonlocal received
        received += len(chunk)
        if received > MAX_STREAM_OUTPUT:
            raise CommandStateError('Command output limit reached; sandbox cleanup is required')

    # The SDK owns output buffers. Callbacks enforce only our run's output budget.
    callbacks = {'on_stdout': limit_output, 'on_stderr': limit_output}
    try:
        # SDK connection timeouts do not stop remote processes. The outer deadline
        # includes the one permitted reconnect; failure escapes to sandbox retirement.
        async with asyncio.timeout(timeout):
            handle = await sandbox.commands.run(command, background=True, cwd=cwd,
                timeout=timeout, request_timeout=min(timeout, 10), **callbacks)
            try:
                result = await handle.wait()
            except (CommandExitException, CommandStateError):
                raise
            except Exception:
                pid = handle.pid
                await handle.disconnect()
                # A process that exited without an observed exit event is unknown,
                # not successful. Only reconnect to this invocation's running PID.
                running = await sandbox.commands.list(request_timeout=5)
                if not any(process.pid == pid and process.cmd == '/bin/bash'
                           and process.args == ['-l', '-c', command] and process.cwd == cwd
                           for process in running):
                    raise CommandStateError('Command exit could not be confirmed; sandbox cleanup is required')
                handle = await sandbox.commands.connect(pid, timeout=timeout,
                    request_timeout=5, **callbacks)
                reconnected = True
                result = await handle.wait()
    except CommandExitException as exc:
        result = exc
    except CommandStateError:
        raise
    except TimeoutError:
        raise CommandStateError('Command timed out; its process may still be running. Sandbox cleanup is required') from None
    except Exception:
        # Even a lost start response can leave a process running without its PID.
        raise CommandStateError('Command connection lost; its outcome is unknown. Sandbox cleanup is required') from None
    finally:
        if handle is not None:
            # Cancellation also closes the SDK stream. Service owns terminating the
            # entire sandbox, including children of an interrupted shell process.
            await handle.disconnect()
    assert handle is not None  # reaching here means the command started
    return {'ok': result.exit_code == 0, 'status': 'exited', 'pid': handle.pid,
            'exit_code': result.exit_code, 'reconnected': reconnected,
            'output_may_be_incomplete': reconnected,
            'stdout': await _bounded_output(sandbox, result.stdout, 'stdout', max_output),
            'stderr': await _bounded_output(sandbox, result.stderr, 'stderr', max_output),
            **({'error_type': 'CommandExitException'} if result.exit_code != 0 else {})}
