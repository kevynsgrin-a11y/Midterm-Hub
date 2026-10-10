"""Escaping, site config, and URL helpers shared across the renderers.

Kept dependency-free (no imports from render/components) so both can import it.
"""
from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from urllib.parse import urlsplit


def esc(value: Any) -> str:
    """HTML-escape for both text and quoted attributes (escapes & < > \" ')."""
    return _html.escape("" if value is None else str(value), quote=True)


@dataclass(frozen=True)
class SiteConfig:
    """Deploy-target configuration.

    ``origin`` is the scheme+host with no trailing slash (e.g. ``https://x.github.io``).
    ``base_path`` is a leading-slash, no-trailing-slash prefix for project subpath
    hosting (e.g. ``/Midterm-Hub``), or ``""`` for domain-root hosting.
    ``asset_map`` maps a logical asset name to its content-hashed filename.
    ``critical_css`` is the above-the-fold subset inlined into every <head>.
    """

    origin: str = "https://plumbline.example"
    base_path: str = ""
    asset_map: Mapping[str, str] = field(default_factory=dict)
    critical_css: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "origin", self.origin.rstrip("/"))
        bp = self.base_path.strip()
        if bp and not bp.startswith("/"):
            bp = "/" + bp
        object.__setattr__(self, "base_path", bp.rstrip("/"))


def rel(cfg: SiteConfig, path: str) -> str:
    """Root-relative href for internal links; passes external/anchor links through."""
    if path.startswith(("http://", "https://", "mailto:", "#")):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{cfg.base_path}{path}"


def absu(cfg: SiteConfig, path: str) -> str:
    """Absolute URL for canonicals, Open Graph, sitemap <loc>, and JSON-LD @id."""
    if path.startswith(("http://", "https://")):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{cfg.origin}{cfg.base_path}{path}"


def asset(cfg: SiteConfig, path: str) -> str:
    """Href for a file under /assets/, content-hashed when the build supplied one.

    Hashing is a correctness requirement, not an optimisation: HTML and CSS expire
    on independent clocks, so after a rebuild a returning visitor can be served new
    HTML against stale CSS. Any change that couples the two — a renamed class, a
    new selector — renders broken until both caches turn over.
    """
    name = path.lstrip("/")
    return rel(cfg, "/assets/" + cfg.asset_map.get(name, name))


def safe_href(url: str) -> str:
    """Allowlist http/https (and site-relative) URLs for use in href; neutralize any
    other scheme (javascript:, data:, vbscript:, …) to defuse a poisoned source_url."""
    if url is None:
        return "#"
    u = url.strip()
    low = u.lower()
    # Protocol-relative "//evil.example/x" would pass the leading-slash test below
    # and silently resolve off-site, so reject it before the allowlist.
    if low.startswith("//"):
        return "#"
    if low.startswith(("http://", "https://", "mailto:", "/", "#", "./", "../")):
        return u
    return "#"


def attrs(**kw: Any) -> str:
    """Render HTML attributes; True renders bare, None/False are skipped. Trailing
    underscores are stripped so Python keywords work (``class_`` -> ``class``)."""
    out = []
    for k, v in kw.items():
        k = k.rstrip("_").replace("_", "-")
        if v is True:
            out.append(f" {k}")
        elif v is None or v is False:
            continue
        else:
            out.append(f' {k}="{esc(v)}"')
    return "".join(out)


# A bare URL inside free text. It must not start mid-word, and it ends at whitespace or at a
# character that cannot be part of a URL in prose (angle brackets, straight or curly quotes).
# Keep this and the helpers below in step with lib/note-links.mjs; both read
# tests/fixtures/note_link_cases.json.
_URL_RE = re.compile(r"(?<![A-Za-z0-9])https?://[^\s<>\"'`\u2018\u2019\u201c\u201d]+", re.IGNORECASE)
_SENTENCE_PUNCTUATION = ".,;:!?"
_OPENING_BRACKET = {")": "(", "]": "[", "}": "{"}


def _trim_url(url: str) -> str:
    """Drop what ends the sentence rather than the URL: trailing . , ; : ! ? and any closing
    bracket that has no opening bracket inside the URL (so ``(see https://x.gov/a)`` loses
    the ``)`` but ``https://x.gov/Foo_(bar)`` keeps it)."""
    while url:
        last = url[-1]
        if last in _SENTENCE_PUNCTUATION or (
            last in _OPENING_BRACKET and url.count(last) > url.count(_OPENING_BRACKET[last])
        ):
            url = url[:-1]
        else:
            break
    return url


def _is_linkable(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:  # e.g. "https://[bad": urlsplit rejects an unterminated IPv6 host
        return False
    return parts.scheme.lower() in ("http", "https") and bool(parts.hostname)


def split_note_links(text: Optional[str]) -> list[tuple[str, Optional[str]]]:
    """Split free text into ``(text, href)`` parts; ``href`` is None for plain text.

    Only ``http``/``https`` URLs with a host become links, so ``javascript:``, ``data:`` and
    ``mailto:`` stay plain text. The parts always rejoin to the original string."""
    if not text:
        return []
    parts: list[tuple[str, Optional[str]]] = []
    cursor = 0
    for match in _URL_RE.finditer(text):
        url = _trim_url(match.group())
        if not _is_linkable(url):
            continue
        if match.start() > cursor:
            parts.append((text[cursor : match.start()], None))
        parts.append((url, url))
        cursor = match.start() + len(url)
    if cursor < len(text):
        parts.append((text[cursor:], None))
    return parts


def linkify(text: Optional[str]) -> str:
    """HTML for plain text in which bare http(s) URLs are external links.

    Each part is escaped on its own after the split, so nothing in the text can reach the
    page as markup; ``safe_href`` is the same allowlist the source link goes through."""
    out = []
    for piece, href in split_note_links(text):
        if href is not None and safe_href(href) != "#":
            out.append(f'<a href="{esc(href)}" rel="nofollow noopener" target="_blank">{esc(piece)}</a>')
        else:
            out.append(esc(piece))
    return "".join(out)
