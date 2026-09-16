"""Host-side E2B template releases. Never invoked by the generation agent."""

import argparse
import json
import re
import sys
from pathlib import Path
from uuid import UUID

from e2b import Template, wait_for_url

CONTEXT = Path(__file__).resolve().parent
NAME_PATTERN = r"[a-z0-9][a-z0-9_-]*(?:/[a-z0-9][a-z0-9_-]*)?"


def release_reference(value: str) -> str:
    if not re.fullmatch(rf"{NAME_PATTERN}:v[A-Za-z0-9._-]+", value):
        raise argparse.ArgumentTypeError(
            "Use a release name such as webbuilder-react-design:v2026-09-14-1"
        )
    return value


def build_reference(value: str) -> str:
    name, separator, build_id = value.rpartition(":")
    try:
        if not separator or not re.fullmatch(NAME_PATTERN, name):
            raise ValueError
        if str(UUID(build_id)) != build_id:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Use template-name:<exact-build-UUID>, not a moving tag"
        ) from exc
    return value


def build(release: str) -> dict[str, str]:
    template = (
        Template(file_context_path=CONTEXT)
        .from_dockerfile(str(CONTEXT / "Dockerfile"))
        .set_start_cmd(
            "cd /home/user/react-app && exec node node_modules/vite/bin/vite.js "
            "--host 0.0.0.0 --port 5173 --strictPort",
            wait_for_url("http://127.0.0.1:5173/"),
        )
    )
    info = Template.build(
        template,
        release,
        cpu_count=1,
        memory_mb=1024,
        on_build_logs=lambda entry: print(entry.message, file=sys.stderr),
    )
    reference = f"{release.rsplit(':', 1)[0]}:{info.build_id}"
    return {
        "release": release,
        "template_id": info.template_id,
        "build_id": info.build_id,
        "build_ref": reference,
        "backend_env": f"E2B_TEMPLATE_ID={reference}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser(
        "build", help="Build a versioned template using E2B quota"
    )
    build_parser.add_argument("release", type=release_reference)
    promote_parser = commands.add_parser(
        "promote", help="Move an environment tag to an exact build"
    )
    promote_parser.add_argument("build_ref", type=build_reference)
    promote_parser.add_argument(
        "--to", choices=("staging", "production"), required=True
    )
    args = parser.parse_args()

    if args.command == "build":
        result = build(args.release)
    else:
        info = Template.assign_tags(args.build_ref, args.to)
        result = {
            "build_ref": args.build_ref,
            "build_id": info.build_id,
            "tag": args.to,
            "backend_env": f"E2B_TEMPLATE_ID={args.build_ref}",
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
