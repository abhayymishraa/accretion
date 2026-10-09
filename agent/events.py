"""Bounded public diagnostics. Prompts, source files and provider credentials stay out."""

import base64
import gzip
import hashlib
import json
import os
import re

from detect_secrets.core.plugins.initialize import from_plugin_classname
from detect_secrets.plugins.base import BasePlugin, RegexBasedDetector
from sqlalchemy import select

from db.base import AsyncSessionLocal, AutocommitSessionLocal
from db.models import Run, RunEvent

from .sandbox.workspace import HIDDEN
from .storage.persistence import put_object, read_object
from .storage.storage import StorageError

# Bounds the events held in memory and written per run. Sized against
# RUN_MAX_TURNS: a turn emits roughly three events, so a cap below the turn
# budget would end healthy runs before the turn budget ever applied.
MAX_RUN_EVENTS = 2000
# The archive ceiling and the event cap are one pair, kept together so raising
# one cannot silently break the other. An archive over this is never stored, and
# maintenance prunes run_events only after a verified archive, so exceeding it
# leaves those rows in the database permanently.
ARCHIVE_MAX_BYTES = 4 * 1024 * 1024
# One page of events for streaming and list responses, which is a display
# bound rather than a completeness one.
EVENT_PAGE = 201
_CREDENTIAL = re.compile(r"(?i)(bearer\s+|(?:api[_-]?key|password|secret|token)\s*[=:]\s*)[^\s,;\"\']+")
_KEY_SHAPE = re.compile(r"\b(?:sk-[\w-]{12,}|gh[pousr]_[\w]+|AIza[\w-]+)\b")
_URL_LOGIN = re.compile(r"(\w+://)[^\s/@]+:[^\s/@]+@")


def redact(value, *, max_length=4000, max_items=250):
    if isinstance(value, dict):
        return {
            k: redact(v, max_length=max_length, max_items=max_items)
            for k, v in value.items()
            if k.lower() not in {"authorization", "cookie", "password", "secret", "api_key", "token"}
        }
    if isinstance(value, list):
        return [redact(v, max_length=max_length, max_items=max_items) for v in value[:max_items]]
    if not isinstance(value, str):
        return value
    for key, secret in os.environ.items():
        if len(secret) >= 8 and any(s in key for s in ("KEY", "SECRET", "TOKEN", "PASSWORD", "DATABASE_URL")):
            value = value.replace(secret, "[redacted]")
    value = _CREDENTIAL.sub(r"\1[redacted]", value)
    value = _KEY_SHAPE.sub("[redacted]", value)
    value = _URL_LOGIN.sub(r"\1[redacted]@", value)
    return value if max_length is None else value[:max_length]


# Shorter values are not hidden: they would cut ordinary words out of the output, and a real key is longer.
_MIN_SECRET = 8
# The second net, for keys nobody saved (one hardcoded in a file, one printed by a tool): detect-secrets' patterns
# for providers' key formats. Left out: the entropy and keyword detectors, which flag every hash in a lockfile;
# Artifactory's, which matches words such as APDisplayName; public IPs, which are not secrets; and private keys,
# whose patterns find only the BEGIN line, so _PEM hides the whole block instead.
_DETECTORS = frozenset(
    {
        "AWSKeyDetector",
        "AzureStorageKeyDetector",
        "BasicAuthDetector",
        "DiscordBotTokenDetector",
        "GitHubTokenDetector",
        "GitLabTokenDetector",
        "JwtTokenDetector",
        "MailchimpDetector",
        "NpmDetector",
        "OpenAIDetector",
        "PypiTokenDetector",
        "SendGridDetector",
        "SlackDetector",
        "SquareOAuthDetector",
        "StripeDetector",
        "TelegramBotTokenDetector",
        "TwilioKeyDetector",
    }
)


def _key_patterns() -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for name in sorted(_DETECTORS):
        # Typed here: the library returns an unbound TypeVar, which mypy cannot infer from.
        plugin: BasePlugin = from_plugin_classname(name)
        if isinstance(plugin, RegexBasedDetector):
            patterns.extend(plugin.denylist)
    return patterns


_KEY_PATTERNS = _key_patterns()
_PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S)


def _hide_match(match: re.Match[str]) -> str:
    """The key itself: a pattern's group when it captures the key (a URL's password), else the whole match
    (GitHub's group is only the ghp prefix)."""
    key = match.group(1) if match.re.groups else None
    return match.group(0).replace(key, HIDDEN) if key and len(key) >= _MIN_SECRET else HIDDEN


def secret_forms(values) -> list[str]:
    """Each value as it can appear in output: itself and its Base64. Base64 is matched at all three byte
    alignments, without the characters a neighbouring byte changes, so a key inside a longer encoded blob
    (a Basic auth header, a JWT, a dump) is found too. Longest first, so no form is cut by a shorter one."""
    forms = set()
    for value in values:
        if len(value) < _MIN_SECRET:
            continue
        forms.add(value)
        data = value.encode()
        for shift in range(3):
            for encode in (base64.b64encode, base64.urlsafe_b64encode):
                encoded = encode(b"\0" * shift + data).decode().rstrip("=")
                # Drop the leading group a padding byte touches, and the trailing character the next byte touches.
                forms.add(encoded[4 if shift else 0 : -1])
    return sorted((form for form in forms if len(form) >= _MIN_SECRET), key=len, reverse=True)


def hide_secrets(value, forms):
    """value with every form of the user's keys, and every key in a provider's known format, replaced, through
    dicts and lists, before the model, the transcript or the chat sees it. Anything else (screenshot bytes)
    passes unchanged."""
    if isinstance(value, dict):
        return {k: hide_secrets(v, forms) for k, v in value.items()}
    if isinstance(value, list):
        return [hide_secrets(v, forms) for v in value]
    if isinstance(value, str):
        for form in forms:
            value = value.replace(form, HIDDEN)
        value = _PEM.sub(HIDDEN, value)
        for pattern in _KEY_PATTERNS:
            value = pattern.sub(_hide_match, value)
    return value


async def run_events(db, run_id, after_sequence=0, limit=EVENT_PAGE):
    rows = (
        await db.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.sequence > after_sequence)
            .order_by(RunEvent.sequence)
            .limit(limit)
        )
    ).all()
    return [{**row.payload, "sequence": row.sequence} for row in rows]


async def archive_run(run_id):
    async with AutocommitSessionLocal() as db:
        run = await db.get(Run, run_id)
        if not run or run.status in ("running", "awaiting_input") or run.log_sha256:
            return
        # The archive must cover the whole run: paging here would store a prefix
        # and then let maintenance prune the rows the prefix left out.
        events = await run_events(db, run_id, limit=MAX_RUN_EVENTS + 1)
    if not events:
        return
    lines = []
    for event in events:
        entry = redact(event)
        encoded = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode()
        if len(encoded) > 4096:
            # Retain every event's identity/order, visibly truncate oversized legacy diagnostics.
            entry = {
                k: (v[:128] if isinstance(v, str) else v)
                for k, v in entry.items()
                if k
                in {
                    "e",
                    "run_id",
                    "event_id",
                    "sequence",
                    "created_at",
                    "name",
                    "call_id",
                    "status",
                    "ok",
                    "message",
                    "output",
                    "revision_id",
                    "duration_ms",
                }
            }
            entry["details_truncated"] = True
            encoded = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode()
        lines.append(encoded + b"\n")
    body = b"".join(lines)
    if len(body) > ARCHIVE_MAX_BYTES:
        raise StorageError("Run diagnostic archive exceeds its ceiling")
    archive = gzip.compress(body, mtime=0)
    key = f"logs/{run_id}.jsonl.gz"
    await put_object(key, archive, "application/gzip", chat_id=run.chat_id)
    # Confirm bytes before allowing expanded DB diagnostics to be pruned later.
    stored_sha256 = hashlib.sha256(await read_object(key, len(archive))).hexdigest()
    archive_sha256 = hashlib.sha256(archive).hexdigest()
    if stored_sha256 != archive_sha256:
        raise StorageError("Run log archive verification failed")
    async with AsyncSessionLocal.begin() as db:
        run = await db.get(Run, run_id)
        if not run:
            return  # Project deletion already queued the deterministic log key for cleanup.
        run.log_key, run.log_sha256 = key, archive_sha256
