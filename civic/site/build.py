"""Build orchestration: walk the site data and write every file.

Emits the full page tree (directory-style clean URLs), copies hermetic assets,
generates real downloadable JSON/CSV/ICS into /downloads/, and writes sitemap.xml,
robots.txt, and 404.html. Reuses the tested exporters so the /data/ links are live.
"""
from __future__ import annotations

import datetime
import hashlib
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import icons, pages, seo
from .base import SiteConfig
from .data import load_site_data
from ..exports.csv_export import export_csv
from ..exports.ics_export import export_ics
from ..exports.json_export import export_json

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


@dataclass
class BuildResult:
    out_dir: str
    pages_written: int
    downloads_written: bool
    version: str


def _url_to_file(out: Path, url_path: str) -> Path:
    """Map a URL path to an output file. Directory URLs get index.html."""
    clean = url_path.strip("/")
    if url_path.endswith(".html") or url_path.endswith(".xml") or url_path.endswith(".txt"):
        return out / clean
    if clean == "":
        return out / "index.html"
    return out / clean / "index.html"


def _write(out: Path, url_path: str, content: str) -> None:
    dest = _url_to_file(out, url_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


# Selector prefixes whose rules must paint before the stylesheet arrives: the
# shell a visitor sees first. Kept as a prefix list rather than a hand-copied
# block so the critical set is extracted from the real sheet and can never drift.
CRITICAL_PREFIXES = (
    ":root", "*", "html", "body", "a", "h1", "h2", "h3", "h4", "p",
    ".sr-only", ".wrap", ".prose", ".skip-link", ":focus-visible",
    ".site-header", ".masthead", ".hero", ".page-head", ".lede", ".overline",
    ".dateline", ".btn", ".select", ".field", ".jump-form", ".trust-", ".kpi",
    ".num", ".breadcrumb", ".section__index", ".date-block", ".tag",
)


def _critical_css(source: str) -> str:
    """Extract the above-the-fold subset of the stylesheet.

    A render-blocking <link> costs two full round trips before first paint; on a
    high-latency connection that measured 4.5s of blank viewport. Inlining this
    subset and deferring the rest cuts it roughly in half.
    """
    out, i, n = [], 0, len(source)
    while i < n:
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        brace = source.find("{", i)
        if brace == -1:
            break
        selector = source[i:brace].strip()
        # Walk to the matching close brace so nested at-rules stay intact.
        depth, j = 0, brace
        while j < n:
            if source[j] == "{":
                depth += 1
            elif source[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = source[i:j + 1]
        i = j + 1
        if selector.startswith("@media") and "prefers-color-scheme" in selector:
            out.append(block)  # dark tokens must not wait for the full sheet
        elif selector.startswith("@"):
            continue
        elif any(
            part.strip().startswith(CRITICAL_PREFIXES)
            for part in selector.split(",")
        ):
            out.append(block)
    return "".join(out)


def _copy_assets(out: Path) -> dict[str, str]:
    """Copy assets under content-hashed names; return {logical: hashed}.

    The favicon keeps its stable name — it is referenced by convention from
    outside our own HTML.
    """
    assets_out = out / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    critical = ""
    for name in ("styles.css", "site.js"):
        src = ASSETS_DIR / name
        if src.exists():
            data = src.read_bytes()
            digest = hashlib.sha256(data).hexdigest()[:8]
            stem, _, ext = name.rpartition(".")
            hashed = f"{stem}.{digest}.{ext}"
            (assets_out / hashed).write_bytes(data)
            mapping[name] = hashed
            if name == "styles.css":
                critical = _critical_css(data.decode("utf-8"))
    (assets_out / "favicon.svg").write_text(
        "<?xml version='1.0' encoding='UTF-8'?>" + icons.FAVICON_SVG, encoding="utf-8"
    )
    mapping["__critical__"] = critical
    return mapping


def build_site(
    conn: sqlite3.Connection,
    out_dir: str,
    *,
    origin: str,
    base_path: str = "",
    version: str,
    generated_at: Optional[str] = None,
    today: Optional[datetime.date] = None,
    include_unverified: bool = False,
    with_downloads: bool = True,
    demo: bool = False,
    cname: Optional[str] = None,
) -> BuildResult:
    if generated_at is None:
        generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    site = load_site_data(
        conn, version=version, generated_at=generated_at, today=today,
        include_unverified=include_unverified,
    )
    site.demo = demo

    out = Path(out_dir)
    # (og cards are generated below, after the output tree is created)
    # Rebuild the managed tree from scratch so removed pages/downloads never linger
    # and diverge from sitemap.xml. Guard against nuking a root/home directory.
    resolved = out.resolve()
    if resolved == Path("/") or resolved == Path.home() or str(resolved) == "":
        raise ValueError(f"refusing to build into {resolved!r}")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    # Assets are copied first so their content hashes are known before any page
    # references them.
    asset_map = _copy_assets(out)
    critical_css = asset_map.pop("__critical__", "")
    cfg = SiteConfig(
        origin=origin, base_path=base_path, asset_map=asset_map,
        critical_css=critical_css,
    )

    # Generate Open Graph share cards BEFORE rendering pages, so each page can point
    # og:image only at a card that actually exists (best-effort; empty if unavailable).
    from . import ogcards

    site.og = ogcards.generate(site, out, demo=demo)

    count = 0
    # Static top-level pages.
    _write(out, "/", pages.render_home(cfg, site)); count += 1
    _write(out, "/states/", pages.render_states_index(cfg, site)); count += 1
    _write(out, "/about/", pages.render_about(cfg, site)); count += 1
    _write(out, "/methodology/", pages.render_methodology(cfg, site)); count += 1
    _write(out, "/data/", pages.render_data(cfg, site)); count += 1
    _write(out, "/404.html", pages.render_404(cfg, site)); count += 1

    # Per-state hubs.
    for s in site.states:
        _write(out, s.url, pages.render_state_hub(cfg, site, s)); count += 1
    # Per-jurisdiction pages.
    for j in site.jurisdictions:
        _write(out, j.url, pages.render_jurisdiction(cfg, site, j)); count += 1
    # Per-election detail pages.
    for e in site.elections:
        _write(out, e.url, pages.render_election(cfg, site, e)); count += 1

    # sitemap + robots.
    _write(out, "/sitemap.xml", seo.sitemap_xml(cfg, site))
    _write(out, "/robots.txt", seo.robots_txt(cfg))

    # Custom-domain marker for GitHub Pages (harmless on other hosts).
    if cname:
        (out / "CNAME").write_text(cname.strip() + "\n", encoding="utf-8")

    if with_downloads:
        downloads = out / "downloads"
        export_json(conn, downloads, version, generated_at, include_unverified)
        export_csv(conn, downloads, version, generated_at, include_unverified)
        # Pin ICS DTSTAMP to generated_at (deterministic), not wall-clock now().
        gen_dt = datetime.datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        export_ics(conn, downloads, version, generated_at, gen_dt, cfg_origin_domain(cfg), include_unverified)
        if demo and downloads.exists():
            (downloads / "NOTICE.txt").write_text(
                "DEMONSTRATION DATA — every record in these files is illustrative "
                "sample data, not a real election. Do not rely on it.\n",
                encoding="utf-8",
            )

    return BuildResult(
        out_dir=str(out), pages_written=count, downloads_written=with_downloads, version=version
    )


def cfg_origin_domain(cfg: SiteConfig) -> str:
    """Bare host for ICS UIDs, derived from the site origin."""
    host = cfg.origin.split("://", 1)[-1]
    return host or "civic-calendar.local"
