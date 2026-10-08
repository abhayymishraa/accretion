"""Executed inside Linux E2B by the host: a proxy in front of the app's web server that adds a
navigation bridge to each HTML page, so the builder's address bar can follow and step the preview.

The bridge lives in the proxy,
never in the project's files, so it survives every edit the model makes and works for every kit.
Usage: python3 preview_proxy.py <listen port> <app port> <JSON list of builder origins>
"""

import asyncio
import json
import re
import sys

LISTEN, TARGET = int(sys.argv[1]), int(sys.argv[2])
ORIGINS = json.loads(sys.argv[3])
HEAD_LIMIT = 64 * 1024
# The app's own pages are small; anything larger passes through untouched.
HTML_LIMIT = 8 * 1024 * 1024
HEAD_TAG = re.compile(rb"<head(\s[^>]*)?>", re.I)

# Reports each page change to the builder and follows its back/forward requests. Messages go only
# to the builder's own origins.
BRIDGE = (
    "<script>(() => {"
    "if (window.parent === window) return;"
    "const origins = " + json.dumps(ORIGINS) + ";"
    "const report = () => origins.forEach((origin) => window.parent.postMessage("
    '{type: "accretion:location", path: location.pathname + location.search + location.hash}, origin));'
    'for (const name of ["pushState", "replaceState"]) {'
    "const original = history[name];"
    "history[name] = function () { const result = original.apply(this, arguments); report(); return result; };"
    "}"
    'addEventListener("popstate", report);'
    'addEventListener("hashchange", report);'
    'addEventListener("message", (event) => {'
    "const data = event.data;"
    "if (event.source !== window.parent || !origins.includes(event.origin)) return;"
    'if (!data || data.type !== "accretion:navigate" || typeof data.path !== "string") return;'
    'if (!data.path.startsWith("/") || data.path.startsWith("//")) return;'
    "location.replace(data.path);"
    "});"
    "report();"
    "})();</script>"
).encode()


def headers(head):
    lines = head.split(b"\r\n")
    return lines[0], [line for line in lines[1:] if line]


def value(lines, name):
    for line in lines:
        key, _, rest = line.partition(b":")
        if key.strip().lower() == name:
            return rest.strip()
    return b""


def without(lines, *names):
    return [line for line in lines if line.partition(b":")[0].strip().lower() not in names]


async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()


async def read_chunked(reader):
    body = bytearray()
    while True:
        size = int((await reader.readuntil(b"\r\n")).split(b";")[0].strip(), 16)
        if size == 0:
            while await reader.readuntil(b"\r\n") != b"\r\n":  # trailers end at an empty line
                pass
            return bytes(body)
        if len(body) + size > HTML_LIMIT:
            raise ValueError("page too large")
        body += await reader.readexactly(size)
        await reader.readexactly(2)


async def handle(client_reader, client_writer):
    try:
        head = await client_reader.readuntil(b"\r\n\r\n")
        upstream_reader, upstream_writer = await asyncio.open_connection("127.0.0.1", TARGET)
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError, OSError):
        client_writer.close()
        return
    request, lines = headers(head)
    method = request.split(b" ", 1)[0]
    # Websockets (Vite and Next live reload), chunked uploads and HEAD pass through byte for byte.
    if value(lines, b"upgrade") or value(lines, b"transfer-encoding") or method == b"HEAD":
        upstream_writer.write(head)
        await asyncio.gather(pipe(client_reader, upstream_writer), pipe(upstream_reader, client_writer))
        return
    # One request per connection, uncompressed, so an HTML body can be read and patched.
    lines = without(lines, b"connection", b"keep-alive", b"accept-encoding") + [
        b"Connection: close",
        b"Accept-Encoding: identity",
    ]
    upstream_writer.write(b"\r\n".join([request, *lines]) + b"\r\n\r\n")
    length = int(value(lines, b"content-length") or 0)
    try:
        if length:
            upstream_writer.write(await client_reader.readexactly(length))
        await upstream_writer.drain()
        response, response_lines = headers(await upstream_reader.readuntil(b"\r\n\r\n"))
        html = value(response_lines, b"content-type").lower().startswith(b"text/html")
        status = response.split(b" ", 2)[1] if response.count(b" ") else b""
        if not html or status in {b"204", b"304"} or value(response_lines, b"content-encoding"):
            client_writer.write(
                b"\r\n".join([response, *without(response_lines, b"connection")]) + b"\r\nConnection: close\r\n\r\n"
            )
            await pipe(upstream_reader, client_writer)
            return
        if value(response_lines, b"transfer-encoding").lower() == b"chunked":
            body = await read_chunked(upstream_reader)
        elif value(response_lines, b"content-length"):
            body = await upstream_reader.readexactly(int(value(response_lines, b"content-length")))
        else:
            body = await upstream_reader.read(-1)  # HTTP/1.0 style: the page ends when the app closes
        match = HEAD_TAG.search(body)
        body = body[: match.end()] + BRIDGE + body[match.end() :] if match else BRIDGE + body
        response_lines = without(response_lines, b"connection", b"content-length", b"transfer-encoding")
        client_writer.write(
            b"\r\n".join([response, *response_lines, b"Content-Length: %d" % len(body), b"Connection: close"])
            + b"\r\n\r\n"
            + body
        )
        await client_writer.drain()
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError, OSError, ValueError):
        pass
    finally:
        client_writer.close()
        upstream_writer.close()


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", LISTEN, limit=HEAD_LIMIT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
