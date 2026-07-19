"""Escaping, site config, and URL helpers shared across the renderers.

Kept dependency-free (no imports from render/components) so both can import it.
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Any


def esc(value: Any) -> str:
    """HTML-escape for both text and quoted attributes (escapes & < > \" ')."""
    return _html.escape("" if value is None else str(value), quote=True)


@dataclass(frozen=True)
class SiteConfig:
    """Deploy-target configuration.

    ``origin`` is the scheme+host with no trailing slash (e.g. ``https://x.github.io``).
    ``base_path`` is a leading-slash, no-trailing-slash prefix for project subpath
    hosting (e.g. ``/Midterm-Hub``), or ``""`` for domain-root hosting.
    """

    origin: str = "https://plumbline.example"
    base_path: str = ""

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
    """Href for a file under /assets/."""
    return rel(cfg, "/assets/" + path.lstrip("/"))


def safe_href(url: str) -> str:
    """Allowlist http/https (and site-relative) URLs for use in href; neutralize any
    other scheme (javascript:, data:, vbscript:, …) to defuse a poisoned source_url."""
    if url is None:
        return "#"
    u = url.strip()
    low = u.lower()
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
