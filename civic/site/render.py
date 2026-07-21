"""The HTML document shell: <head> (meta + SEO + JSON-LD + pre-paint theme script),
the sticky masthead, and the colophon footer. Pages supply their <main> content."""
from __future__ import annotations

import json
from typing import Any, Optional

from . import copy, icons
from .base import SiteConfig, absu, asset, attrs, esc, rel
from .components import confidence_legend
from .data import SiteData

DEFAULT_ROBOTS = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:0"

# Pre-paint: apply saved theme before first paint (no FOUC) and flag JS presence.
THEME_SCRIPT = (
    "(function(){try{var t=localStorage.getItem('plumbline-theme');"
    "if(t==='dark'||t==='light'){document.documentElement.setAttribute('data-theme',t);}}"
    "catch(e){}document.documentElement.classList.add('js');})();"
)


def _nav(cfg: SiteConfig, path: str) -> str:
    items = []
    for label, url, aria in copy.NAV:
        active = path == url or (url != "/" and path.startswith(url))
        cur = ' aria-current="page"' if active else ""
        aria_attr = f' aria-label="{esc(aria)}"' if aria else ""
        items.append(
            f'<a href="{esc(rel(cfg, url))}"{aria_attr}{cur}>{esc(label)}</a>'
        )
    return '<nav class="masthead__nav" aria-label="Primary">' + "".join(items) + "</nav>"


def _theme_toggle() -> str:
    return (
        '<button type="button" class="btn--icon theme-toggle" '
        'aria-label="Switch color theme" aria-pressed="false">'
        f"{icons.ICON_SUN}{icons.ICON_MOON}"
        '<span class="sr-only">Switch color theme</span></button>'
    )


def _masthead(cfg: SiteConfig, site: SiteData, path: str, edition: bool) -> str:
    wordmark = (
        f'<a class="masthead__wordmark" href="{esc(rel(cfg, "/"))}" '
        f'aria-label="{esc(copy.BRAND)} home">{icons.LOGO_MARK}'
        f'<span class="masthead__word">{esc(copy.BRAND)}</span></a>'
    )
    top = (
        '<div class="masthead__inner">'
        f"{wordmark}"
        f'<div class="masthead__right">{_nav(cfg, path)}{_theme_toggle()}</div>'
        "</div>"
    )
    edition_row = ""
    if edition:
        edition_row = (
            '<div class="masthead__edition">'
            f'<span class="overline">{esc(copy.BRAND)}</span>'
            f'<span class="dateline num">Edition {esc(site.version)} · '
            f"Updated {esc(site.last_modified[:10])}</span></div>"
        )
    cls = "site-header" + (" site-header--edition" if edition else "")
    return f'<header class="{cls}">{top}{edition_row}</header>'


def _footer(cfg: SiteConfig, site: SiteData) -> str:
    cols = []
    for title, links in copy.FOOTER_COLUMNS:
        li = "".join(
            f'<li><a href="{esc(rel(cfg, url))}">{esc(label)}</a></li>'
            for label, url in links
        )
        cols.append(
            f'<div class="footer__col"><h2 class="footer__head overline">{esc(title)}</h2>'
            f"<ul>{li}</ul></div>"
        )
    colophon = (
        '<div class="footer__meta">'
        f'<p class="footer__tagline">{esc(copy.TAGLINE)}</p>'
        f'<p class="footer__provenance num">{icons.LOGO_MARK} Data version '
        f"{esc(site.version)} · Last verified {esc(site.last_modified[:10])}</p>"
        f'<p class="footer__disclaimer">{esc(copy.FOOTER_BLURB)}</p>'
        "</div>"
    )
    return (
        '<footer class="site-footer">'
        '<div class="site-footer__inner">'
        f'<div class="footer__cols">{"".join(cols)}</div>'
        f'<div class="footer__legend"><p class="overline">Every date is confidence-rated</p>'
        f"{confidence_legend()}</div>"
        f"{colophon}</div></footer>"
    )


def _jsonld_scripts(blocks: Optional[list[dict[str, Any]]]) -> str:
    if not blocks:
        return ""
    out = []
    for block in blocks:
        payload = json.dumps(block, ensure_ascii=False, separators=(",", ":"))
        # Prevent premature </script> termination inside JSON-LD.
        payload = payload.replace("</", "<\\/")
        out.append(f'<script type="application/ld+json">{payload}</script>')
    return "".join(out)


def render_page(
    cfg: SiteConfig,
    site: SiteData,
    *,
    path: str,
    title: str,
    description: str,
    main_html: str,
    breadcrumb_items: Optional[list] = None,
    robots: str = DEFAULT_ROBOTS,
    og_type: str = "website",
    jsonld: Optional[list[dict[str, Any]]] = None,
    body_class: str = "",
    edition: bool = False,
    omit_canonical: bool = False,
    article_published: Optional[str] = None,
    article_modified: Optional[str] = None,
    og_image: Optional[str] = None,
    og_image_alt: Optional[str] = None,
) -> str:
    """Assemble a complete, self-contained HTML document."""
    from .components import breadcrumb as _breadcrumb

    canonical = None if omit_canonical else absu(cfg, path)

    # Resolve the OG share image: explicit for this page, else the site default card.
    og_rel = og_image
    og_alt = og_image_alt
    if og_rel is None:
        og_rel = (getattr(site, "og", {}) or {}).get("default")
        if og_rel and not og_alt:
            og_alt = f"{copy.BRAND} — {copy.TAGLINE}"
    og_url = absu(cfg, og_rel) if og_rel else None
    css_href = asset(cfg, "styles.css")
    js_href = asset(cfg, "site.js")
    favicon = asset(cfg, "favicon.svg")

    head = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
        f'<meta name="robots" content="{esc(robots)}">',
    ]
    if canonical:
        head.append(f'<link rel="canonical" href="{esc(canonical)}">')
    head += [
        '<meta name="theme-color" content="#F5F3EC" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#131316" media="(prefers-color-scheme: dark)">',
        f'<link rel="icon" type="image/svg+xml" href="{esc(favicon)}">',
        # Open Graph
        f'<meta property="og:site_name" content="{esc(copy.BRAND)}">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:type" content="{esc(og_type)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
    ]
    if canonical:
        head.append(f'<meta property="og:url" content="{esc(canonical)}">')
    if article_published:
        head.append(f'<meta property="article:published_time" content="{esc(article_published)}">')
    if article_modified:
        head.append(f'<meta property="article:modified_time" content="{esc(article_modified)}">')
    if og_url:
        head += [
            f'<meta property="og:image" content="{esc(og_url)}">',
            '<meta property="og:image:type" content="image/png">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{esc(og_alt or title)}">',
        ]
    head += [
        f'<meta name="twitter:card" content="{"summary_large_image" if og_url else "summary"}">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
        f'<link rel="stylesheet" href="{esc(css_href)}">',
        f"<script>{THEME_SCRIPT}</script>",
        _jsonld_scripts(jsonld),
        "</head>",
    ]

    crumb_html = ""
    if breadcrumb_items:
        crumb_html = _breadcrumb(cfg, breadcrumb_items)

    demo_banner = ""
    if getattr(site, "demo", False):
        demo_banner = (
            '<div class="demo-banner" role="note">'
            "<strong>Demonstration site.</strong> Every election shown is illustrative "
            f'sample data — not a real election. <a href="{esc(rel(cfg, "/about/"))}">'
            "About the data</a>.</div>"
        )

    body = [
        f'<body{attrs(class_=body_class or None)}>',
        f'<a class="skip-link" href="#main">{esc(copy.CTA["skip_to_content"])}</a>',
        demo_banner,
        _masthead(cfg, site, path, edition),
        '<main id="main" tabindex="-1">',
        crumb_html,
        main_html,
        "</main>",
        _footer(cfg, site),
        f'<script src="{esc(js_href)}" defer></script>',
        "</body>",
        "</html>",
    ]
    return "\n".join(head) + "\n" + "\n".join(body) + "\n"
