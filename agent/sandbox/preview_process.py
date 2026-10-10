"""Executed inside Linux E2B by the host, never exposed as an agent tool."""

import contextlib
import fcntl
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path("/home/user/react-app")
STACK = ROOT / ".accretion/stack.json"
# Process groups this script started for a kit's services; stop only ever signals these.
GROUPS = Path("/tmp/accretion-services.json")


def kit_env():
    """The project's .env, then the user's keys in .env.json (both written by the host), on top of the sandbox
    environment. Only the app's services get the user's keys; the builder's commands source .env alone."""
    env = dict(os.environ)
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() and not name.lstrip().startswith("#"):
                env[name.strip()] = value.strip()
    user = ROOT / ".env.json"
    if user.is_file():
        env.update(json.loads(user.read_text()))
    return env


def stop_services():
    if not GROUPS.is_file():
        return
    for pgid in json.loads(GROUPS.read_text()):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pgid, signal.SIGKILL)
    GROUPS.unlink()


def start_services(proxy):
    """Start the kit's services in stack.json order and wait for each ready path (spec 8).

    Last comes the navigation proxy (preview_proxy.py), the port the preview URL points at.
    """
    stack = json.loads(STACK.read_text())
    env = kit_env()
    groups = []
    port, script, origins = proxy
    web = next(s for s in stack["services"] if s["port"] == stack["preview_port"])
    services = stack["services"] + [
        {
            "name": "preview proxy",
            "cwd": ".",
            "port": int(port),
            "ready": web["ready"],
            "start": shlex.join(["python3", script, port, str(web["port"]), origins]),
        }
    ]
    try:
        for service in services:
            port = service["port"]
            # Refuse an unknown listener instead of killing it or accepting its HTTP 200.
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(("0.0.0.0", port))
            process = subprocess.Popen(
                ["/bin/bash", "-c", service["start"]],
                cwd=ROOT / service["cwd"],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            groups.append(process.pid)
            GROUPS.write_text(json.dumps(groups))
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError(service["name"] + " exited before it was ready")
                try:
                    with urlopen(f"http://127.0.0.1:{port}{service['ready']}", timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError(service["name"] + " was not ready within 60 seconds")
                time.sleep(0.3)
    except BaseException:
        stop_services()
        raise


def main(action, proxy):
    if action not in {"stop", "start", "restart"}:
        raise ValueError("Unknown preview operation")
    # Outside the restored/archived project tree, and released even on failure.
    # The backend serializes project operations. This lock also protects remote
    # command overlap after a transport timeout. No public restart endpoint exists.
    with open("/tmp/webbuilder-preview.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action in {"stop", "restart"}:
            stop_services()
        if action in {"start", "restart"}:
            start_services(proxy)
    print("Preview " + action + " completed")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:5])
