#!/usr/bin/env python3
"""Refresh vendored skills from the upstream repositories recorded in provenance.

Each source pins a repository, a commit and a sha256 per vendored file. This
re-vendors the skill directories at upstream HEAD, deletes files upstream has
removed, and regenerates the hashes so agent/skills.py keeps verifying real
content. License files are skipped: upstream keeps them at repository root,
they change rarely, and overwriting legal text automatically is not this
workflow's job.
"""
import base64
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'agent' / 'skills'
SOURCES = ('taste-source.json', 'find-skills-source.json', 'design-sources.json')


def gh(path, jq):
    result = subprocess.run(['gh', 'api', path, '--jq', jq], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{path}: {result.stderr.strip()[:200]}')
    return result.stdout


def is_license(key):
    return pathlib.PurePosixPath(key).name.upper().startswith('LICENSE')


def sync(entry, dry_run):
    repo, prefix = entry['repository'], entry['upstream_prefix']
    before = entry['commit']
    head = gh(f'repos/{repo}/commits?per_page=1', '.[0].sha').strip()
    # Read the tree at that exact commit, so a push mid-run cannot mix two revisions.
    tree = json.loads(gh(f'repos/{repo}/git/trees/{head}?recursive=1',
                         '[.tree[] | select(.type=="blob") | {path,sha}]'))

    # Directories this source owns, taken from the keys already vendored.
    owned = {key.split('/')[0] for key in entry['files'] if '/' in key}
    keep = {key: value for key, value in entry['files'].items() if is_license(key)}
    keep_blobs = {key: value for key, value in entry.get('upstream_git_blobs', {}).items()
                  if is_license(key)}
    local = {item['path'][len(prefix):]: item['sha'] for item in tree
             if item['path'].startswith(prefix)}
    wanted = {key: sha for key, sha in local.items()
              if key.split('/')[0] in owned and not is_license(key)}

    previous = {key for key in entry['files'] if not is_license(key)}
    added, removed, changed = sorted(set(wanted) - previous), sorted(previous - set(wanted)), []

    files, blobs = dict(keep), dict(keep_blobs)
    for key, blob in sorted(wanted.items()):
        content = base64.b64decode(gh(f'repos/{repo}/git/blobs/{blob}', '.content'))
        digest = hashlib.sha256(content).hexdigest()
        if entry['files'].get(key) not in (None, digest):
            changed.append(key)
        files[key], blobs[key] = digest, blob
        if not dry_run:
            target = ROOT / key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    if not dry_run:
        for key in removed:
            (ROOT / key).unlink(missing_ok=True)
        entry['commit'] = head
        entry['files'] = dict(sorted(files.items()))
        if 'upstream_git_blobs' in entry:
            entry['upstream_git_blobs'] = dict(sorted(blobs.items()))
    return {'repo': repo, 'from': before[:8], 'to': head[:8],
            'added': added, 'removed': removed, 'changed': changed}


def main():
    dry_run = '--dry-run' in sys.argv
    reports = []
    for name in SOURCES:
        path = ROOT / name
        data = json.loads(path.read_text())
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            reports.append(sync(entry, dry_run))
        if not dry_run:
            path.write_text(json.dumps(data, indent=2) + '\n')

    touched = 0
    for report in reports:
        delta = len(report['added']) + len(report['removed']) + len(report['changed'])
        touched += delta
        status = 'up to date' if report['from'] == report['to'] and not delta else \
                 f"{report['from']} -> {report['to']}"
        print(f"{report['repo']:38} {status}")
        for label in ('added', 'removed', 'changed'):
            for key in report[label]:
                print(f"    {label:8} {key}")
    print(f"\n{'would change' if dry_run else 'changed'}: {touched} file(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
