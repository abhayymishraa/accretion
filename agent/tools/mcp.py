"""MCP servers the user connected: the one module that uses the MCP SDK, so an SDK upgrade touches only this file.

Remote Streamable HTTP servers only. Every request, including the OAuth discovery URLs a server hands back,
goes through a client that refuses non-public addresses, so a user-supplied URL cannot reach the platform's
own network. Credentials are decrypted here and sent only to the server they belong to: never to the model,
the transcript or the sandbox.
"""

import base64
import hashlib
import ipaddress
import json
import logging
import re
import secrets
import socket
import struct
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlencode, urlsplit

import anyio
import httpx2
from mcp import Client
from mcp.client.auth import OAuthClientProvider, OAuthFlowError, OAuthRegistrationError
from mcp.client.auth.utils import (
    build_oauth_authorization_server_metadata_discovery_urls,
    build_protected_resource_metadata_discovery_urls,
    create_client_registration_request,
    extract_resource_metadata_from_www_auth,
    extract_scope_from_www_auth,
    get_client_metadata_scopes,
    handle_auth_metadata_response,
    handle_protected_resource_response,
    handle_registration_response,
    validate_authorization_response_iss,
)
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthMetadata,
    OAuthToken,
    ProtectedResourceMetadata,
)
from sqlalchemy import update

from agent.sandbox.secrets import fernet
from agent.tools.config import tools_settings
from config import settings
from db.base import AutocommitSessionLocal
from db.models import McpServer

logger = logging.getLogger("webbuilder.mcp")

Auth = Literal["none", "header", "oauth"]
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
# Platform servers every build gets, from code and never stored, so a user has no row to turn off. Each entry
# is a Server built with the platform's own credentials from settings. Empty until the platform ships one;
# adding one needs no migration.
DEFAULT_SERVERS: dict[str, "Server"] = {}
# Names a user's server may not take, so a default added later can never be shadowed by one.
RESERVED_NAMES = frozenset({"default", "platform", "accretion", *DEFAULT_SERVERS})
CALL_SECONDS = 60
CONNECT_SECONDS = 15
MAX_TOOLS = 200
# A server that keeps returning a cursor must not hold a build or a request forever.
MAX_PAGES = 50
# The MCP output limit, a token estimated as four characters. Over the limit, the result is cut to the limit's
# length in characters and ends with a truncation notice.
MAX_RESULT_TOKENS = 25_000
_CHARS_PER_TOKEN = 4
_TRUNCATED = (
    f"\n[OUTPUT TRUNCATED - exceeded {MAX_RESULT_TOKENS} token limit]\nThe tool output was truncated. If this MCP "
    "server provides pagination or filtering tools, use them to retrieve specific portions of the data. If "
    "pagination is not available, inform the user that you are working with truncated output and results may be "
    "incomplete."
)
# The platform's key for a server that works without one, by its exact address so it reaches that service only.
# A key the user saves replaces it; with neither, the server is called anonymously.
_PLATFORM_HEADERS = {
    url: {name: value}
    for url, name, value in [
        ("https://mcp.context7.com/mcp", "Context7-API-Key", tools_settings.CONTEXT7_API_KEY),
        (
            "https://huggingface.co/mcp",
            "Authorization",
            tools_settings.HF_TOKEN and f"Bearer {tools_settings.HF_TOKEN}",
        ),
    ]
    if value
}
REDIRECT_URI = f"{settings.FRONTEND_URL}/connectors/callback"
# A server's logo is stored on its row as a data URI, so a page never loads an image from the server's host.
ICON_BYTES = 32_768
_ICON_DOWNLOAD_BYTES = 512 * 1024
# The image types a logo may be, told by its first bytes, never by what the server or the upload claims.
_ICON_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
    (b"RIFF", "image/webp"),
    # A favicon: some servers name theirs (Hugging Face does), and every browser shows one through <img>.
    (b"\x00\x00\x01\x00", "image/x-icon"),
]
_PURPOSE = b"accretion mcp credentials v1"


class McpError(Exception):
    """A server that cannot be reached, refuses us, or answers in a way we cannot use; the message is for people."""


class AddressRefused(McpError):
    """The URL is not an https address on the public internet: the user's to fix, not the server's."""


class NeedsReconnect(McpError):
    """The server wants a new sign-in: a build cannot open a browser, so the user reconnects in Connections."""


@dataclass
class Server:
    id: str
    name: str
    title: str
    url: str
    auth: Auth
    description: str = ""
    header_name: str | None = None
    secret: str | None = None
    # The tools the user approved, as stored: name, description, input_schema, read_only, fingerprint.
    tools: list[dict[str, Any]] = field(default_factory=list)


def seal(value: dict[str, Any]) -> str:
    return fernet(_PURPOSE).encrypt(json.dumps(value).encode()).decode()


def unseal(secret: str | None) -> dict[str, Any]:
    return json.loads(fernet(_PURPOSE).decrypt(secret.encode())) if secret else {}


async def require_public(url: str) -> None:
    """Raise McpError unless the URL is https on a host that resolves only to public addresses."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise AddressRefused("Use an https:// address for the server.")
    # ponytail: checked on each request, not pinned to the connection, so a DNS answer that changes between
    # this check and the connect can slip through. Upgrade path: connect to the checked address, pass the
    # host name for TLS.
    try:
        found = await anyio.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        raise AddressRefused(f"Cannot find the server {parts.hostname!r}.") from None
    for *_, address in found:
        if not ipaddress.ip_address(str(address[0]).split("%")[0]).is_global:
            raise AddressRefused(f"{parts.hostname!r} is not a public address.")


class _PublicOnly(httpx2.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        try:
            await require_public(str(request.url))
        except McpError as exc:
            raise httpx2.ConnectError(str(exc), request=request) from None
        return await super().handle_async_request(request)


def _http(auth: httpx2.Auth | None = None, headers: dict[str, str] | None = None) -> httpx2.AsyncClient:
    # Redirects are not followed: a server or its metadata cannot send us somewhere else unchecked.
    return httpx2.AsyncClient(
        transport=_PublicOnly(), auth=auth, headers=headers, follow_redirects=False, timeout=CONNECT_SECONDS
    )


def client_metadata() -> OAuthClientMetadata:
    return OAuthClientMetadata(
        client_name="Accretion",
        redirect_uris=[REDIRECT_URI],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
        application_type="web",
    )


class _StoredTokens:
    """The SDK's TokenStorage over our encrypted row: refreshed tokens are saved back as soon as they arrive."""

    def __init__(self, server: Server) -> None:
        self.server = server
        self.data = unseal(server.secret)

    async def get_tokens(self) -> OAuthToken | None:
        return OAuthToken.model_validate(self.data["tokens"]) if "tokens" in self.data else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.data["tokens"] = tokens.model_dump(mode="json", exclude_none=True)
        self.data["expires_at"] = time.time() + tokens.expires_in if tokens.expires_in else None
        await self._save()

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return OAuthClientInformationFull.model_validate(self.data["client"]) if "client" in self.data else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.data["client"] = client_info.model_dump(mode="json", exclude_none=True)
        await self._save()

    async def _save(self) -> None:
        secret = seal(self.data)
        async with AutocommitSessionLocal() as db:
            await db.execute(update(McpServer).where(McpServer.id == self.server.id).values(secret=secret))
        # A build keeps one Server for the run: the next call must send the rotated refresh token, not the old one.
        self.server.secret = secret


class _Provider(OAuthClientProvider):
    """The SDK provider, given back what a restart forgets. Stock, it loads the stored token without its expiry
    or the token endpoint, so an expired token is sent, refused, and the user is asked to sign in again although
    a refresh token would do."""

    def __init__(self, server: Server) -> None:
        self.stored = _StoredTokens(server)
        super().__init__(server.url, client_metadata(), self.stored, redirect_handler=self._needs_reconnect)
        self.title = server.title

    async def _initialize(self) -> None:
        await super()._initialize()
        self.context.token_expiry_time = self.stored.data.get("expires_at")
        if metadata := self.stored.data.get("metadata"):
            self.context.oauth_metadata = OAuthMetadata.model_validate(metadata)

    async def _needs_reconnect(self, _url: str) -> None:
        raise NeedsReconnect(f"Sign in to {self.title} again in Connections.")


@asynccontextmanager
async def connect(server: Server) -> AsyncIterator[Client]:
    """One session with the server, signed in as the user. Closed when the block ends."""
    auth = _Provider(server) if server.auth == "oauth" else None
    headers = _PLATFORM_HEADERS.get(server.url, {}) if server.auth == "none" else {}
    if server.auth == "header":
        key = unseal(server.secret).get("value")
        if not key or not server.header_name:
            raise McpError(f"Add your {server.title} key in Connections first.")
        headers = {server.header_name: key}
    try:
        async with (
            _http(auth=auth, headers=headers) as http,
            Client(streamable_http_client(server.url, http_client=http), read_timeout_seconds=CALL_SECONDS) as client,
        ):
            yield client
    except McpError:
        raise
    except Exception as exc:
        # The SDK raises transport, protocol and auth errors of many kinds; the run needs one it can explain.
        inner = next((e for e in getattr(exc, "exceptions", ()) if isinstance(e, McpError)), None)
        if inner:
            raise inner from None
        logger.warning("MCP server failed server=%s error_type=%s", server.name, type(exc).__name__)
        raise McpError(f"{server.title} did not answer as an MCP server ({type(exc).__name__}).") from None


def fingerprint(tool: Any) -> str:
    """What the user approved: if a server changes a tool's name, text, inputs or hints, the approval lapses."""
    seen = {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.input_schema,
        "annotations": tool.annotations.model_dump(mode="json", exclude_none=True) if tool.annotations else None,
    }
    return hashlib.sha256(json.dumps(seen, sort_keys=True).encode()).hexdigest()[:32]


async def list_tools(server: Server) -> tuple[list[dict[str, Any]], str | None]:
    """Every tool the server offers, as stored for approval, up to MAX_TOOLS, and the address of the logo the
    server names for itself (`serverInfo.icons`), if any."""
    found: list[dict[str, Any]] = []
    async with connect(server) as client:
        info = client.server_info
        # ponytail: the first icon the server lists; pick by size or theme if servers start listing several.
        icon = info.icons[0].src if info and info.icons else None
        cursor = None
        for _ in range(MAX_PAGES):
            if len(found) >= MAX_TOOLS:
                break
            page = await client.list_tools(cursor=cursor)
            found += [
                {
                    "name": tool.name,
                    "description": (tool.description or "")[:2000],
                    # The server's own words for finding the tool, which the search scores.
                    "search_hint": hint
                    if isinstance(hint := (tool.meta or {}).get("anthropic/searchHint"), str)
                    else "",
                    "input_schema": tool.input_schema,
                    # Unmarked tools count as able to change things: the spec's default, and the safe one.
                    "read_only": bool(tool.annotations and tool.annotations.read_only_hint),
                    "fingerprint": fingerprint(tool),
                }
                for tool in page.tools
            ]
            cursor = page.next_cursor
            if not cursor:
                break
    return found[:MAX_TOOLS], icon


def _one_icon(body: bytes) -> bytes:
    """An ICO holds every size at once (Hugging Face's favicon is nine, 200 KB): keep the largest up to 64 px,
    the most a logo is shown at, as an ICO of one image, or as the PNG it holds. Anything unreadable is kept
    as it was, for the checks after to refuse."""
    try:
        (count,) = struct.unpack_from("<H", body, 4)
        entries = [struct.unpack_from("<BBBBHHII", body, 6 + 16 * i) for i in range(count)]
    except struct.error:
        return body
    fits = [entry for entry in entries if 0 < entry[0] <= 64] or entries
    if not fits:
        # An ICO with no images: nothing to show, so no logo.
        return b""
    width, height, colors, _, planes, bits, size, offset = max(fits, key=lambda entry: entry[0] or 256)
    image = body[offset : offset + size]
    if image.startswith(_ICON_MAGIC[0][0]):
        return image
    return (
        struct.pack("<HHH", 0, 1, 1)
        + struct.pack("<BBBBHHII", width, height, colors, 0, planes, bits, size, 22)
        + image
    )


def icon_uri(body: bytes) -> str | None:
    """The image as a data URI, or None when it is too large or not an image type a logo may be."""
    if body.startswith(b"\x00\x00\x01\x00"):
        body = _one_icon(body)
    if len(body) > ICON_BYTES:
        return None
    mime = next((kind for magic, kind in _ICON_MAGIC if body.startswith(magic)), None)
    if mime == "image/webp" and body[8:12] != b"WEBP":
        mime = None
    # An SVG shown through <img> runs no script, so it is safe as a logo.
    if mime is None and body.lstrip()[:5].lower() in (b"<svg ", b"<?xml"):
        mime = "image/svg+xml"
    return f"data:{mime};base64,{base64.b64encode(body).decode()}" if mime else None


def data_uri_icon(src: str) -> str | None:
    """A logo given as a base64 data URI, checked by its bytes; None when it is not one a logo may be."""
    head, _, encoded = src.partition(";base64,")
    if not head.startswith("data:") or not encoded:
        return None
    try:
        return icon_uri(base64.b64decode(encoded, validate=True))
    except ValueError:
        return None


async def fetch_icon(src: str) -> str | None:
    """The logo a server names, fetched once through the public-only client. None when it cannot be used."""
    if src.startswith("data:"):
        return data_uri_icon(src)
    body = b""
    try:
        async with _http() as http, http.stream("GET", src) as answer:
            if answer.status_code != 200:
                return None
            async for chunk in answer.aiter_bytes():
                body += chunk
                # An ICO may hold many sizes before one is cut out; anything larger is not a logo.
                if len(body) > _ICON_DOWNLOAD_BYTES:
                    return None
    except (httpx2.HTTPError, McpError):
        return None
    return icon_uri(body)


async def call_tool(server: Server, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run one approved tool after checking it is still the tool the user approved."""
    approved = {tool["name"]: tool["fingerprint"] for tool in server.tools}
    async with connect(server) as client:
        current: dict[str, str] = {}
        cursor = None
        for _ in range(MAX_PAGES):
            page = await client.list_tools(cursor=cursor)
            current |= {tool.name: fingerprint(tool) for tool in page.tools}
            cursor = page.next_cursor
            if not cursor or name in current:
                break
        if current.get(name) != approved.get(name):
            return {
                "ok": False,
                "error": f"{server.title} changed this tool since the user approved it. Ask the user to review it "
                "in Connections before using it.",
            }
        result = await client.call_tool(name, arguments, read_timeout_seconds=CALL_SECONDS)
    parts = [
        getattr(block, "text", None) or f"[{getattr(block, 'type', 'content')} omitted]" for block in result.content
    ]
    if result.structured_content is not None:
        parts.append(json.dumps(result.structured_content, ensure_ascii=False))
    text = "\n".join(parts)
    if round(len(text) / _CHARS_PER_TOKEN) > MAX_RESULT_TOKENS:
        text = text[: MAX_RESULT_TOKENS * _CHARS_PER_TOKEN] + _TRUNCATED
    return {"ok": not result.is_error, "content": text}


async def detect_auth(url: str) -> Auth:
    """How a server signs in, from its answer to an unauthenticated request. A server that refuses it and
    publishes OAuth details (RFC 9728) signs in with its own page; one that refuses it without them takes a key.
    The user can change the choice on the server's page."""
    await require_public(url)
    try:
        async with _http() as http:
            answer, resource_metadata = await _probe(http, url)
    except httpx2.HTTPError:
        raise McpError("The server did not answer. Check the address.") from None
    if answer.status_code not in (401, 403):
        return "none"
    return "oauth" if resource_metadata else "header"


async def _probe(http: httpx2.AsyncClient, url: str) -> tuple[httpx2.Response, ProtectedResourceMetadata | None]:
    """An unauthenticated ping, and the OAuth details (RFC 9728) the server publishes, if any. An open server may
    publish them too (Exa does)."""
    answer = await http.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Accept": "application/json, text/event-stream"},
    )
    for found in build_protected_resource_metadata_discovery_urls(extract_resource_metadata_from_www_auth(answer), url):
        if resource_metadata := await handle_protected_resource_response(await http.get(found)):
            return answer, resource_metadata
    return answer, None


async def begin_sign_in(server: Server) -> tuple[str, dict[str, Any]]:
    """The authorization URL to send the user to, and the flow state to keep until they come back.

    Discovery, registration and PKCE here; the code exchange in finish_sign_in, in another request and maybe
    another worker, so the state is returned for Redis rather than held in this process.
    """
    try:
        return await _begin_sign_in(server)
    except (OAuthFlowError, OAuthRegistrationError, httpx2.HTTPError):
        raise McpError(f"{server.title} did not accept a sign-in from Accretion.") from None


async def _begin_sign_in(server: Server) -> tuple[str, dict[str, Any]]:
    async with _http() as http:
        answer, resource_metadata = await _probe(http, server.url)
        auth_server = str(resource_metadata.authorization_servers[0]) if resource_metadata else None
        metadata = None
        for url in build_oauth_authorization_server_metadata_discovery_urls(auth_server, server.url):
            ok, metadata = await handle_auth_metadata_response(await http.get(url))
            if ok and metadata:
                break
        if not metadata:
            raise McpError(f"{server.title} does not offer a sign-in. Use its key, or no sign-in.")
        if not metadata.registration_endpoint:
            raise McpError(f"{server.title} needs an app registered by hand, which Accretion cannot do yet.")
        stored = unseal(server.secret)
        if "client" in stored and stored.get("issuer") == str(metadata.issuer):
            client = OAuthClientInformationFull.model_validate(stored["client"])
        else:
            registration = create_client_registration_request(metadata, client_metadata(), auth_server or server.url)
            client = await handle_registration_response(await http.send(registration))
    verifier = secrets.token_urlsafe(64)
    challenge = hashlib.sha256(verifier.encode()).digest()
    state = secrets.token_urlsafe(32)
    resource = str(resource_metadata.resource) if resource_metadata else server.url
    scope = get_client_metadata_scopes(extract_scope_from_www_auth(answer), resource_metadata, metadata)
    query = {
        "response_type": "code",
        "client_id": client.client_id,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": base64.urlsafe_b64encode(challenge).decode().rstrip("="),
        "code_challenge_method": "S256",
        "resource": resource,
        **({"scope": scope} if scope else {}),
    }
    flow = {
        "state": state,
        "verifier": verifier,
        "resource": resource,
        "issuer": str(metadata.issuer),
        "metadata": metadata.model_dump(mode="json", exclude_none=True),
        "client": client.model_dump(mode="json", exclude_none=True),
    }
    return f"{metadata.authorization_endpoint}?{urlencode(query)}", flow


async def finish_sign_in(flow: dict[str, Any], code: str, iss: str | None) -> dict[str, Any]:
    """Exchange the code for tokens; returns the credentials to seal on the server's row."""
    metadata = OAuthMetadata.model_validate(flow["metadata"])
    # RFC 9207: a callback naming another issuer is a mix-up attack.
    try:
        validate_authorization_response_iss(iss, metadata)
    except OAuthFlowError:
        raise McpError("This sign-in came back from a different server. Connect again.") from None
    client = OAuthClientInformationFull.model_validate(flow["client"])
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client.client_id,
        "code_verifier": flow["verifier"],
        "resource": flow["resource"],
    }
    if client.client_secret:
        form["client_secret"] = client.client_secret
    try:
        async with _http() as http:
            answer = await http.post(str(metadata.token_endpoint), data=form)
    except httpx2.HTTPError:
        raise McpError("The sign-in did not finish. Try connecting again.") from None
    if answer.status_code != 200:
        raise McpError("The sign-in did not finish. Try connecting again.")
    tokens = OAuthToken.model_validate_json(answer.content)
    return {
        "tokens": tokens.model_dump(mode="json", exclude_none=True),
        "expires_at": time.time() + tokens.expires_in if tokens.expires_in else None,
        "client": flow["client"],
        "issuer": flow["issuer"],
        "metadata": flow["metadata"],
    }
