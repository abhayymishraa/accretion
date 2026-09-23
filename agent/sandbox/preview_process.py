"""Executed inside Linux E2B by the host, never exposed as an agent tool."""
import fcntl
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path('/home/user/react-app')
VITE = ROOT / 'node_modules/vite/bin/vite.js'


def project_servers():
    """Recognize both the original npm wrapper's child and our direct Vite CLI."""
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args = (proc / 'cmdline').read_bytes().split(b'\0')
            if len(args) < 2 or Path(os.fsdecode(args[0])).name != 'node':
                continue
            if b'--port' not in args:
                continue
            port_index = args.index(b'--port') + 1
            if args[port_index:port_index + 1] != [b'5173']:
                continue
            if any(arg in {b'build', b'preview', b'optimize'} for arg in args[2:]):
                continue
            if (proc / 'cwd').resolve() != ROOT:
                continue
            entry = ROOT / os.fsdecode(args[1])
            if entry.resolve() == VITE.resolve():
                yield int(proc.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue


def stop():
    for pid in project_servers():
        try:
            # A pidfd prevents signaling a different process if Linux reuses the PID.
            fd = os.pidfd_open(pid)
        except ProcessLookupError:
            continue
        try:
            if pid not in project_servers():
                continue
            signal.pidfd_send_signal(fd, signal.SIGTERM)
            if not select.select([fd], [], [], 5)[0]:
                signal.pidfd_send_signal(fd, signal.SIGKILL)
                if not select.select([fd], [], [], 3)[0]:
                    raise RuntimeError('Previous Vite process did not exit')
        except ProcessLookupError:
            pass
        finally:
            os.close(fd)


def start():
    if list(project_servers()):
        raise RuntimeError('Vite is already running; refusing a duplicate server')
    if not VITE.is_file():
        raise RuntimeError('Project Vite installation is missing')
    # Refuse an unknown listener instead of killing it or accepting its HTTP 200.
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('0.0.0.0', 5173))
    # Disconnect all command-session pipes so the server survives this invocation.
    process = subprocess.Popen(
        ['node', str(VITE), '--host', '0.0.0.0', '--port', '5173', '--strictPort'],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Vite exited before readiness; check project configuration and port 5173')
            try:
                with urlopen('http://127.0.0.1:5173/', timeout=1) as response:
                    ready = response.status == 200
                if ready and process.poll() is None:
                    return
            except OSError:
                pass
            time.sleep(0.2)
        raise RuntimeError('Vite did not become ready within 20 seconds')
    except BaseException:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
        raise


def main(action):
    if action not in {'stop', 'start', 'restart'}:
        raise ValueError('Unknown preview operation')
    # Outside the restored/archived project tree, and released even on failure.
    # The backend serializes project operations. This lock also protects remote
    # command overlap after a transport timeout. No public restart endpoint exists.
    with open('/tmp/webbuilder-preview.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action in {'stop', 'restart'}:
            stop()
        if action in {'start', 'restart'}:
            start()
    print('Preview ' + action + ' completed')


if __name__ == '__main__':
    main(sys.argv[1])
