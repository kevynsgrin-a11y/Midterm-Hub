"""Structured data (schema.org JSON-LD), sitemap.xml, and robots.txt.

Nothing here fabricates facts: Events carry date-only start dates (no invented poll
times), no organizer/offers, and confidence/provenance are surfaced as
additionalProperty. All @ids reuse a single URL case so entities dedupe cleanly.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional
from xml.sax.saxutils import escape as xml_escape

from .base import SiteConfig, absu
from .copy import BRAND
from .data import (
    CONFIDENCE_BLURB,
    CONFIDENCE_LABELS,
    ElectionView,
    SiteData,
)

CONTEXT = "https://schema.org"
DATA_LICENSE = "https://creativecommons.org/licenses/by/4.0/"


def org_id(cfg: SiteConfig) -> str:
    return absu(cfg, "/") + "#org"


def website_id(cfg: SiteConfig) -> str:
    return absu(cfg, "/") + "#website"


def _org(cfg: SiteConfig) -> dict:
    return {
        "@type": "Organization",
        "@id": org_id(cfg),
        "name": BRAND,
        "url": absu(cfg, "/"),
        "description": (
            "Independent, nonpartisan reference for U.S. off-cycle and local "
            "election dates and deadlines."
        ),
    }


def _website(cfg: SiteConfig) -> dict:
    return {
        "@type": "WebSite",
        "@id": website_id(cfg),
        "name": BRAND,
        "url": absu(cfg, "/"),
        "publisher": {"@id": org_id(cfg)},
        "inLanguage": "en-US",
    }


def home_graph(cfg: SiteConfig, site: SiteData) -> dict:
    return {
        "@context": CONTEXT,
        "@graph": [
            _website(cfg),
            _org(cfg),
            {
                "@type": "WebPage",
                "@id": absu(cfg, "/") + "#webpage",
                "url": absu(cfg, "/"),
                "name": f"{BRAND} — U.S. Off-Cycle & Local Election Dates",
                "isPartOf": {"@id": website_id(cfg)},
                "about": {"@id": org_id(cfg)},
                "dateModified": site.last_modified,
            },
        ],
    }


def breadcrumb_ld(cfg: SiteConfig, items: list[tuple[str, Optional[str]]]) -> dict:
    elements = []
    for i, (label, url) in enumerate(items, start=1):
        el: dict[str, Any] = {"@type": "ListItem", "position": i, "name": label}
        if url:
            el["item"] = absu(cfg, url)
        elements.append(el)
    return {"@context": CONTEXT, "@type": "BreadcrumbList", "itemListElement": elements}


def _place(e: ElectionView) -> dict:
    if e.jurisdiction_type == "state":
        return {
            "@type": "AdministrativeArea",
            "name": e.state_name,
            "address": {"@type": "PostalAddress", "addressRegion": e.state, "addressCountry": "US"},
        }
    address: dict[str, Any] = {"@type": "PostalAddress", "addressRegion": e.state, "addressCountry": "US"}
    if e.jurisdiction_type == "municipality":
        address["addressLocality"] = e.jurisdiction_name
    return {"@type": "Place", "name": e.jurisdiction_name, "address": address}


def _registration_start(e: ElectionView) -> Optional[str]:
    """Return an ISO datetime-with-offset for the registration deadline if a time and
    a resolvable IANA timezone are present; otherwise a date-only string; else None."""
    reg = next((d for d in e.deadlines if d.key == "registration_deadline"), None)
    if reg is None:
        return None
    if reg.time and e.timezone:
        try:
            from zoneinfo import ZoneInfo

            hh, mm = (int(x) for x in reg.time.split(":"))
            dt = datetime.datetime(
                reg.date.year, reg.date.month, reg.date.day, hh, mm, tzinfo=ZoneInfo(e.timezone)
            )
            return dt.isoformat()
        except Exception:
            return reg.date.isoformat()
    return reg.date.isoformat()


def event_ld(cfg: SiteConfig, e: ElectionView) -> dict:
    sub_events = []
    for dl in e.deadlines:
        if dl.key == "registration_deadline":
            start = _registration_start(e)
        elif dl.key == "early_voting_end":
            continue  # folded into the early-voting window below
        else:
            start = dl.date.isoformat()
        node: dict[str, Any] = {"@type": "Event", "name": dl.label, "startDate": start}
        if dl.key == "early_voting_start":
            end = next((d for d in e.deadlines if d.key == "early_voting_end"), None)
            node["name"] = "Early voting"
            if end:
                node["endDate"] = end.date.isoformat()
        sub_events.append(node)

    props = [
        {
            "@type": "PropertyValue",
            "name": "Data confidence",
            "value": CONFIDENCE_LABELS.get(e.confidence, e.confidence),
        },
        {"@type": "PropertyValue", "name": "Verification status", "value": e.status},
    ]
    if e.verified_by:
        props.append({"@type": "PropertyValue", "name": "Verified by", "value": e.verified_by})
    if e.source_retrieved_at:
        props.append(
            {"@type": "PropertyValue", "name": "Source retrieved", "value": e.source_retrieved_at}
        )

    # No relative countdown here: JSON-LD is indexed and would go stale between builds.
    desc = (
        f"The {e.jurisdiction_name}, {e.state_name} {e.election_type_label.lower()} "
        f"election is {e.date_full}."
    )
    if e.offices_summary:
        desc += f" On the ballot: {e.offices_summary}."

    node: dict[str, Any] = {
        "@type": "Event",
        "@id": absu(cfg, e.url) + "#event",
        "name": e.title,
        "startDate": e.date_iso,
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": _place(e),
        "description": desc,
        "url": absu(cfg, e.url),
        "isBasedOn": e.source_url,
        "additionalProperty": props,
        "isAccessibleForFree": True,
    }
    if e.offices:
        node["about"] = [{"@type": "Thing", "name": o} for o in e.offices]
    if sub_events:
        node["subEvent"] = sub_events
    return {"@context": CONTEXT, "@graph": [node]}


def collection_ld(
    cfg: SiteConfig, name: str, url: str, items: list[tuple[str, str]], modified: Optional[str] = None
) -> dict:
    elements = [
        {"@type": "ListItem", "position": i, "name": label, "url": absu(cfg, u)}
        for i, (label, u) in enumerate(items, start=1)
    ]
    page: dict[str, Any] = {
        "@type": "CollectionPage",
        "@id": absu(cfg, url) + "#collection",
        "url": absu(cfg, url),
        "name": name,
        "isPartOf": {"@id": website_id(cfg)},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "itemListElement": elements,
        },
    }
    if modified:
        page["dateModified"] = modified
    return {"@context": CONTEXT, "@graph": [page]}


def defined_terms_ld(cfg: SiteConfig) -> dict:
    terms = [
        {
            "@type": "DefinedTerm",
            "@id": absu(cfg, "/methodology/") + f"#confidence-{code}",
            "termCode": code,
            "name": CONFIDENCE_LABELS[code],
            "description": CONFIDENCE_BLURB[code],
        }
        for code in ("official", "secondary", "inferred")
    ]
    return {
        "@context": CONTEXT,
        "@type": "DefinedTermSet",
        "@id": absu(cfg, "/methodology/") + "#confidence",
        "name": "Confidence levels",
        "hasDefinedTerm": terms,
    }


def dataset_ld(cfg: SiteConfig, site: SiteData) -> dict:
    dataset = {
        "@type": "Dataset",
        "@id": absu(cfg, "/data/") + "#dataset",
        "name": "U.S. Off-Cycle & Local Elections dataset",
        "description": (
            "Curation-first, versioned dataset of U.S. off-cycle and local election "
            "dates and deadlines, with provenance and confidence levels."
        ),
        "url": absu(cfg, "/data/"),
        "version": site.version,
        "dateModified": site.last_modified,
        "creator": {"@id": org_id(cfg)},
        "publisher": {"@id": org_id(cfg)},
        "license": DATA_LICENSE,
        "isAccessibleForFree": True,
        "spatialCoverage": {"@type": "Country", "name": "United States"},
        "variableMeasured": [
            "election_date", "election_type", "jurisdiction", "registration_deadline",
            "early_voting_start", "early_voting_end", "candidate_filing_deadline",
            "confidence", "source_url",
        ],
    }
    # Include the Organization node so creator/publisher @id references resolve on /data/.
    return {"@context": CONTEXT, "@graph": [dataset, _org(cfg)]}


# ---------------------------------------------------------------------------
# sitemap.xml / robots.txt
# ---------------------------------------------------------------------------

def _url_entry(loc: str, lastmod: Optional[str], priority: Optional[str]) -> str:
    parts = [f"    <loc>{xml_escape(loc)}</loc>"]
    if lastmod:
        parts.append(f"    <lastmod>{xml_escape(lastmod[:10])}</lastmod>")
    if priority:
        parts.append(f"    <priority>{priority}</priority>")
    return "  <url>\n" + "\n".join(parts) + "\n  </url>"


def sitemap_xml(cfg: SiteConfig, site: SiteData) -> str:
    entries: list[str] = []
    lm = site.last_modified
    entries.append(_url_entry(absu(cfg, "/"), lm, "1.0"))
    entries.append(_url_entry(absu(cfg, "/states/"), lm, "0.8"))
    entries.append(_url_entry(absu(cfg, "/data/"), lm, "0.8"))
    entries.append(_url_entry(absu(cfg, "/about/"), None, "0.5"))
    entries.append(_url_entry(absu(cfg, "/methodology/"), None, "0.5"))

    def maxmod(elections: list[ElectionView]) -> str:
        stamps = [e.verified_at for e in elections if e.verified_at]
        return max(stamps) if stamps else site.generated_at

    for s in site.states:
        entries.append(_url_entry(absu(cfg, s.url), maxmod(s.elections), "0.7"))
    for j in site.jurisdictions:
        entries.append(_url_entry(absu(cfg, j.url), maxmod(j.elections), "0.6"))
    for e in site.elections:
        pri = "0.7" if e.is_upcoming else "0.4"
        entries.append(_url_entry(absu(cfg, e.url), e.verified_at or site.generated_at, pri))

    body = "\n".join(entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


def robots_txt(cfg: SiteConfig) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        "# Machine-readable exports are the B2B product; keep them crawlable.\n"
        f"Sitemap: {absu(cfg, '/sitemap.xml')}\n"
    )
