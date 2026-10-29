"""The builder's web_fetch: one public https page as plain text, read through the public-only transport."""

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx2

from .mcp import PublicOnly

# What is read of a response, and what of its text reaches the model (about 10k tokens).
MAX_BYTES = 2_000_000
MAX_CHARS = 40_000
_CUT = "\n[page cut at {limit:,} characters]"
_TEXT_TYPES = frozenset({"application/json", "application/xml", "application/javascript"})
_SKIPPED = frozenset({"script", "style", "noscript", "svg", "template", "iframe", "canvas"})
_BLOCKS = frozenset(
    {"p", "div", "section", "article", "header", "footer", "main", "nav", "aside", "li", "tr", "br", "hr", "pre"}
    | {"blockquote", "figure", "figcaption", "table", "form", "ul", "ol", "dl", "dt", "dd"}
)
_SPACES = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES = re.compile(r"\n\s*\n\s*\n+")


class _Text(HTMLParser):
    """Visible text with headings as #, links as [text](address) and images as ![alt](address)."""

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.parts: list[str] = []
        self.skipping = 0
        self.links: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        if tag in _SKIPPED:
            self.skipping += 1
        elif self.skipping:
            return
        elif re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in _BLOCKS:
            self.parts.append("\n")
        elif tag == "a":
            href = found.get("href")
            self.links.append(urljoin(self.base, href) if href and not href.startswith("#") else None)
            self.parts.append("[" if self.links[-1] else "")
        elif tag == "img" and found.get("src"):
            self.parts.append(f"![{found.get('alt') or ''}]({urljoin(self.base, found['src'] or '')})")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED:
            self.skipping = max(0, self.skipping - 1)
        elif tag == "a" and self.links and not self.skipping:
            href = self.links.pop()
            self.parts.append(f"]({href})" if href else "")
        elif re.fullmatch(r"h[1-6]", tag) or tag in _BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skipping:
            self.parts.append(data)

    def text(self) -> str:
        lines = (_SPACES.sub(" ", line).strip() for line in "".join(self.parts).split("\n"))
        return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def page_text(html: str, base: str) -> str:
    parser = _Text(base)
    parser.feed(html)
    parser.close()
    return parser.text()


async def fetch(url: str) -> dict[str, Any]:
    """The page at `url` as text. Every address it reaches, redirects included, is checked as public first."""
    parts = urlsplit(url.strip())
    if parts.scheme == "http":
        parts = parts._replace(scheme="https")
    async with httpx2.AsyncClient(
        transport=PublicOnly(),
        follow_redirects=True,
        max_redirects=5,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AccretionBuilder/1.0)", "Accept": "text/html,*/*;q=0.8"},
    ) as client:
        try:
            async with client.stream("GET", urlunsplit(parts)) as response:
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) >= MAX_BYTES:
                        break
        except httpx2.HTTPError as exc:
            return {"ok": False, "error": f"The page could not be fetched: {exc}"}
    kind = response.headers.get("content-type", "").partition(";")[0].strip().lower()
    if not (kind.startswith("text/") or kind in _TEXT_TYPES or kind.endswith("+xml") or kind.endswith("+json")):
        error = f"The address returns {kind or 'no type'}, not a page"
        return {"ok": False, "status": response.status_code, "error": error}
    text = bytes(body).decode(response.encoding or "utf-8", errors="replace")
    if kind in {"text/html", "application/xhtml+xml"}:
        text = page_text(text, str(response.url))
    return {
        "ok": response.is_success,
        "url": str(response.url),
        "status": response.status_code,
        "content": text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + _CUT.format(limit=MAX_CHARS),
    }
