"""One renderer per page type. Each computes its meta + JSON-LD and returns a full
HTML document via render_page."""
from __future__ import annotations

from typing import Optional

from . import art
from . import components as C
from . import copy, icons, seo
from .base import SiteConfig, esc, rel
from .data import ElectionView, JurisdictionView, SiteData, StateView
from .render import render_page

BRAND = copy.BRAND
HOME = ("Home", "/")
STATES = ("States", "/states/")


def _cards(cfg: SiteConfig, elections: list[ElectionView]) -> str:
    return (
        '<div class="card-grid" data-reveal="cards">'
        + "".join(C.election_card(cfg, e) for e in elections)
        + "</div>"
    )


def _section(
    title: str, body: str, *, id: Optional[str] = None, lead: str = "",
    tinted: bool = False, index: Optional[str] = None,
) -> str:
    idattr = f' id="{id}"' if id else ""
    cls = "section section--tinted" if tinted else "section"
    lead_html = f'<p class="section__lead">{lead}</p>' if lead else ""
    index_html = (
        f'<p class="section__index" aria-hidden="true">{esc(index)}</p>' if index else ""
    )
    return (
        f'<section class="{cls}"{idattr} data-reveal="block">'
        f'<div class="wrap">{index_html}<h2 class="section__title">{title}</h2>'
        f"{lead_html}{body}</div></section>"
    )


# --------------------------------------------------------------------------- home

def render_home(cfg: SiteConfig, site: SiteData) -> str:
    hero_h1 = copy.HOME_HERO["h1"]
    up = site.upcoming
    next_date = up[0].date_short if up else "—"

    jump_options = "".join(
        f'<option value="{esc(s.code)}" data-url="{esc(rel(cfg, s.url))}">{esc(s.name)}</option>'
        for s in site.states
    )
    jump = (
        f'<form class="jump-form" action="{rel(cfg, "/states/")}" method="get" '
        'role="search" aria-label="Jump to a state">'
        '<label for="state-jump" class="sr-only">Choose a state</label>'
        '<select id="state-jump" name="state" class="select" data-jump>'
        '<option value="">Choose a state…</option>'
        f"{jump_options}</select>"
        f'<button class="btn btn--primary" type="submit">{copy.CTA["find_state"]}</button>'
        "</form>"
    )
    kpi = (
        '<dl class="kpi-strip">'
        f'<div class="kpi"><dt>Elections tracked</dt><dd class="num">{site.total_elections}</dd></div>'
        f'<div class="kpi"><dt>States &amp; DC</dt><dd class="num">{site.total_states}</dd></div>'
        f'<div class="kpi"><dt>Next election</dt><dd class="num">{esc(next_date)}</dd></div>'
        "</dl>"
    )
    # Editorial highlight on the load-bearing phrase (span is trusted markup).
    marked_title = esc(hero_h1).replace(
        "next election", '<span class="hero__mark">next election</span>'
    )
    trust_bar = (
        '<ul class="trust-bar" aria-label="Why you can trust these dates">'
        + "".join(
            f'<li class="trust-pill">{icons.TRUST_ICONS[k]}<span>{esc(label)}</span></li>'
            for k, label in copy.TRUST_BAR
        )
        + "</ul>"
    )
    next_card = ""
    if up:
        e0 = up[0]
        chips = "".join(C.deadline_chip(dl, e0._today) for dl in e0.deadlines[:2])
        next_card = (
            f'<a class="hero__next" href="{esc(rel(cfg, e0.url))}">'
            '<span class="overline">Next election</span>'
            f'<span class="hero__next-row">{C.date_block(e0)}'
            f'<span class="hero__next-lines"><span class="hero__next-name">'
            f'{esc(e0.jurisdiction_name)}</span>'
            f'<span class="hero__next-meta num">{esc(e0.date_short)} · {esc(e0.countdown)}</span>'
            "</span></span>"
            f'<span class="hero__next-chips">{chips}</span></a>'
        )
    hero = (
        '<section class="hero">'
        f"{art.guilloche_svg()}"
        '<div class="wrap"><div class="hero__copy">'
        f'<p class="hero__eyebrow overline">{esc(copy.HOME_HERO["eyebrow"])}</p>'
        f'<h1 class="hero__title">{marked_title}</h1>'
        f'<p class="hero__subhead">{esc(copy.HOME_HERO["subhead"])}</p>'
        f'<div class="hero__actions">{jump}'
        f'<a class="hero__secondary" href="{rel(cfg, "/methodology/")}">'
        f'or see how we verify →</a></div>'
        f"{trust_bar}{kpi}</div>"
        f'<div class="hero__instrument">{icons.hero_plumbline()}{next_card}</div>'
        "</div></section>"
    )

    upcoming_body = (
        _cards(cfg, up[:6])
        if up
        else '<p class="empty">No upcoming elections are on the calendar yet.</p>'
    )
    on_calendar = _section(
        "On the calendar now",
        upcoming_body + (
            f'<p class="section__more"><a href="{rel(cfg, "/states/")}">'
            f'{copy.CTA["browse_states"]} →</a></p>'
        ),
        index="01",
    )

    state_grid = (
        '<div class="state-grid">'
        + "".join(C.state_tile(cfg, s) for s in site.states)
        + "</div>"
    )
    counts = {s.code: len(s.upcoming) for s in site.states}
    browse = _section(
        "Browse by state",
        f'<div class="browse-layout">{art.us_cartogram(cfg, counts, compact=True)}'
        f"{state_grid}</div>",
        id="states", tinted=True, index="02",
    )

    trust = _section(
        "How we verify",
        (
            '<div class="trust-band">'
            f'<div class="prose">{"".join(f"<p>{p}</p>" for p in copy.WHAT_IS_OFF_CYCLE[2:])}'
            f'<p><a href="{rel(cfg, "/methodology/")}">{copy.CTA["read_methodology"]} →</a></p></div>'
            f"{C.confidence_legend()}"
            "</div>"
        ),
        index="03",
    )

    exports = _section(
        "Use the data",
        (
            '<div class="card-grid">'
            + C.export_card(
                cfg, "CSV",
                "Versioned flat file with a human-readable changelog — diff any two "
                "releases to see exactly what moved.",
                f'<a class="btn btn--secondary" href="{rel(cfg, "/data/")}">'
                f'{copy.CTA["get_data_access"]}</a>',
            )
            + C.export_card(
                cfg, "ICS",
                "Per-jurisdiction calendar feeds — subscribe and your town's "
                "election dates land on your phone.",
                f'<a class="btn btn--secondary" href="{rel(cfg, "/data/#calendar-feeds")}">'
                "Calendar feeds</a>",
            )
            + C.export_card(
                cfg, "JSON",
                "The same verified records as structured JSON, per state — for civic "
                "tools, newsrooms, and researchers.",
                f'<a class="btn btn--secondary" href="{rel(cfg, "/data/")}">Data overview</a>',
            )
            + "</div>"
        ),
        id="data",
        tinted=True,
        index="04",
    )

    main = hero + on_calendar + browse + trust + exports
    desc = (
        f"Verified dates and deadlines for off-cycle, municipal, and local U.S. "
        f"elections. Every record cites an official source and shows a confidence "
        f"level. {site.total_elections} elections across {site.total_states} states."
    )
    return render_page(
        cfg, site, path="/",
        title=f"{BRAND} — U.S. Off-Cycle & Local Election Dates",
        description=desc, main_html=main, edition=True, body_class="page-home",
        jsonld=[seo.home_graph(cfg, site)],
    )


# ------------------------------------------------------------------- states index

def render_states_index(cfg: SiteConfig, site: SiteData) -> str:
    grid = (
        '<div class="state-grid">'
        + "".join(C.state_tile(cfg, s) for s in site.states)
        + "</div>"
    )
    counts = {s.code: len(s.upcoming) for s in site.states}
    main = (
        '<div class="wrap page-head"><p class="dateline num">UPDATED '
        f'{esc(site.version)}</p><h1>Elections by state</h1>'
        '<p class="lede">Browse verified off-cycle and local election calendars by '
        f'state — {site.total_states} covered.</p></div>'
        f'<div class="wrap" data-reveal="block">{art.us_cartogram(cfg, counts)}</div>'
        f'<div class="wrap" data-reveal="block"><h2 class="section-h2">All states</h2>{grid}</div>'
    )
    items = [(s.name, s.url) for s in site.states]
    return render_page(
        cfg, site, path="/states/",
        title="Elections by State — Plumbline",
        description=(
            "Browse verified off-cycle and local election calendars by state — "
            "dates, voter-registration deadlines, and early-voting windows."
        ),
        main_html=main, breadcrumb_items=[HOME, STATES],
        jsonld=[
            seo.collection_ld(cfg, "Elections by state", "/states/", items, site.last_modified),
            seo.breadcrumb_ld(cfg, [HOME, STATES]),
        ],
    )


# ---------------------------------------------------------------------- state hub

def render_state_hub(cfg: SiteConfig, site: SiteData, s: StateView) -> str:
    lead = ""
    if s.next_election:
        ne = s.next_election
        lead = (
            '<div class="lead-card"><p class="overline">Next up in '
            f'{esc(s.name)}</p><a class="lead-card__link" href="{esc(rel(cfg, ne.url))}">'
            f'{C.date_block(ne)}<span class="lead-card__title">{esc(ne.jurisdiction_name)} — '
            f'{esc(ne.election_type_label)}</span><span class="lead-card__meta num">'
            f'{esc(ne.date_full)} · {esc(ne.countdown)}</span></a></div>'
        )

    sections = []
    for j in s.jurisdictions:
        sections.append(
            f'<section class="juris-block" data-reveal="block"><h2 class="juris-block__title">'
            f'<a href="{esc(rel(cfg, j.url))}">{esc(j.name)}</a>'
            f'<span class="juris-block__type overline">{esc(j.jurisdiction_type_label)}</span></h2>'
            f"{_cards(cfg, j.elections)}</section>"
        )

    main = (
        f'<div class="wrap page-head"><p class="dateline num">UPDATED {esc(site.version)}</p>'
        f"<h1>{esc(s.name)} elections</h1>"
        f'<p class="lede">{s.election_count} verified election'
        f'{"s" if s.election_count != 1 else ""} across {s.jurisdiction_count} '
        f'jurisdiction{"s" if s.jurisdiction_count != 1 else ""}.</p>{lead}</div>'
        f'<div class="wrap">{"".join(sections)}</div>'
    )
    breadcrumb = [HOME, STATES, (s.name, s.url)]
    if s.next_election:
        desc = (
            f"Upcoming {s.name} local & off-cycle elections. Next: "
            f"{s.next_election.title} on {s.next_election.date_short}, plus "
            f"{max(s.election_count - 1, 0)} more. Verified dates, deadlines, sources."
        )
    else:
        desc = (
            f"Verified off-cycle and local election records for {s.name}: dates, "
            f"registration deadlines, and early voting."
        )
    items = [(e.title, e.url) for e in s.elections]
    return render_page(
        cfg, site, path=s.url,
        title=f"{s.name} Off-Cycle & Local Elections — Plumbline",
        description=desc, main_html=main, breadcrumb_items=breadcrumb,
        jsonld=[
            seo.collection_ld(cfg, f"{s.name} elections", s.url, items),
            seo.breadcrumb_ld(cfg, breadcrumb),
        ],
    )


# ------------------------------------------------------------------- jurisdiction

def render_jurisdiction(cfg: SiteConfig, site: SiteData, j: JurisdictionView) -> str:
    subscribe = (
        f'<a class="btn btn--secondary" href="{esc(rel(cfg, j.ics_url))}" download>'
        f'{icons.ICON_CALENDAR} {copy.CTA["subscribe_ics"]}</a>'
    )
    ne = j.next_election
    lead = ""
    if ne:
        lead = (
            '<div class="lead-card"><p class="overline">Next election</p>'
            f'<a class="lead-card__link" href="{esc(rel(cfg, ne.url))}">{C.date_block(ne)}'
            f'<span class="lead-card__title">{esc(ne.election_type_label)} Election</span>'
            f'<span class="lead-card__meta num">{esc(ne.date_full)} · {esc(ne.countdown)}</span></a>'
            f'<div class="lead-card__rail">{C.deadline_rail(cfg, ne)}</div></div>'
        )
    main = (
        f'<div class="wrap page-head"><p class="dateline num">UPDATED {esc(site.version)}</p>'
        f"<h1>{esc(j.name)} elections</h1>"
        f'<p class="lede">{esc(j.jurisdiction_type_label)} · {esc(j.state_name)}. '
        f'{len(j.elections)} verified record'
        f'{"s" if len(j.elections) != 1 else ""}.</p>'
        f'<div class="page-head__actions">{subscribe}</div>{lead}</div>'
        f'<div class="wrap" data-reveal="block"><h2 class="section-h2">Election records</h2>'
        f"{_cards(cfg, j.elections)}</div>"
    )
    breadcrumb = [HOME, STATES, (j.state_name, f"/states/{j.state}/"), (j.name, j.url)]
    desc = (
        f"Every verified election for {j.name}, {j.state_name}: dates, registration "
        f"deadlines, early voting."
    )
    if ne:
        desc += f" Next: {ne.title} on {ne.date_short}. Subscribe via .ics."
    items = [(e.title, e.url) for e in j.elections]
    ld = seo.collection_ld(cfg, f"{j.name} elections", j.url, items)
    ld["@graph"][0]["hasPart"] = {
        "@type": "DataDownload",
        "name": f"Add {j.name} elections to your calendar",
        "encodingFormat": "text/calendar",
        "contentUrl": seo.absu(cfg, j.ics_url),
    }
    return render_page(
        cfg, site, path=j.url,
        title=f"{j.name}, {j.state} Elections & Deadlines — Plumbline",
        description=desc, main_html=main, breadcrumb_items=breadcrumb,
        jsonld=[ld, seo.breadcrumb_ld(cfg, breadcrumb)],
    )


# ---------------------------------------------------------------- election detail

def render_election(cfg: SiteConfig, site: SiteData, e: ElectionView) -> str:
    offices = ""
    if e.offices:
        lis = "".join(f"<li>{esc(o)}</li>" for o in e.offices)
        offices = (
            '<section class="detail-section" data-reveal="block"><h2>On the ballot</h2>'
            f'<ul class="offices-list">{lis}</ul></section>'
        )
    ics_href = rel(cfg, f"/downloads/ics/{e.state}/{e.jurisdiction_slug}.ics")
    add_cal = (
        f'<a class="btn btn--primary" href="{ics_href}" download>'
        f'{icons.ICON_CALENDAR} {copy.CTA["add_to_calendar"]}</a>'
    )
    verified_line = (
        f'<p class="dateline num">VERIFIED {esc(e.verified_at[:10])}</p>'
        if e.verified_at else ""
    )
    hero = (
        '<div class="wrap detail-hero">'
        f"{C.date_block(e, large=True)}"
        '<div class="detail-hero__body">'
        f"{verified_line}"
        f'<p class="overline">{esc(e.jurisdiction_type_label)} · {esc(e.state_name)}</p>'
        f'<h1 class="detail-hero__title">{esc(e.jurisdiction_name)} '
        f'{esc(e.election_type_label)} Election</h1>'
        f'<p class="detail-hero__date num">{esc(e.date_full)} '
        f'<span class="detail-hero__countdown">· {esc(e.countdown)}</span></p>'
        f'<div class="detail-hero__meta">{C.tag(e.election_type, e.election_type_label)}'
        f'{C.confidence_badge(e.confidence)}</div>'
        f'<div class="detail-hero__actions">{add_cal}'
        f'{C.source_link(cfg, e.source_url)}</div>'
        "</div></div>"
    )
    rail = (
        '<section class="detail-section" data-reveal="block"><h2>Key dates &amp; deadlines</h2>'
        f'{C.deadline_rail(cfg, e)}</section>'
    )
    trust = (
        '<section class="detail-section detail-trust" data-reveal="block"><h2>Sourcing &amp; confidence</h2>'
        f'<p class="detail-trust__blurb">{esc(e.confidence_blurb)}</p>'
        f"{C.provenance(cfg, e)}"
        f'<p class="detail-trust__foot"><a href="{rel(cfg, "/methodology/#confidence")}">'
        'What do confidence levels mean? →</a></p></section>'
    )
    main = (
        f"{hero}"
        f'<div class="wrap detail-body">{rail}{offices}{trust}</div>'
    )

    breadcrumb = [
        HOME, STATES, (e.state_name, e.state_url),
        (e.jurisdiction_name, e.jurisdiction_url),
        (f"{e.election_type_label} — {e.date_short}", e.url),
    ]
    reg = next((d for d in e.deadlines if d.key == "registration_deadline"), None)
    # Absolute date only — no relative countdown, which would go stale in the index.
    desc = (
        f"The {e.jurisdiction_name}, {e.state_name} {e.election_type_label.lower()} "
        f"election is {e.date_full}."
    )
    if reg:
        desc += f" Voter registration deadline {reg.formatted}."
    if e.offices_summary:
        desc += f" {e.offices_summary}."
    desc += f" Source-verified ({e.confidence_label})."
    if e.confidence == "inferred":
        desc += " (provisional)"
    return render_page(
        cfg, site, path=e.url,
        title=f"{e.jurisdiction_name} {e.election_type_label} Election — {e.date_short}",
        description=desc, main_html=main, breadcrumb_items=breadcrumb, og_type="article",
        article_published=e.source_retrieved_at, article_modified=e.verified_at,
        og_image=(site.og.get("elections", {}) or {}).get(e.id),
        og_image_alt=f"{e.jurisdiction_name} {e.election_type_label} election — {e.date_short}",
        jsonld=[
            seo.event_ld(cfg, e),
            seo.breadcrumb_ld(cfg, breadcrumb),
        ],
    )


# --------------------------------------------------------------- static content

def _prose_page(
    cfg: SiteConfig, site: SiteData, *, path: str, title: str, h1: str, desc: str,
    body: str, breadcrumb, jsonld=None, dateline: str = "", lede: str = "",
) -> str:
    dl = f'<p class="dateline num">{esc(dateline)}</p>' if dateline else ""
    ld = f'<p class="lede">{esc(lede)}</p>' if lede else ""
    main = (
        f'<div class="wrap page-head">{dl}<h1>{esc(h1)}</h1>{ld}</div>'
        f'<article class="wrap prose" data-reveal="block">{body}</article>'
    )
    return render_page(
        cfg, site, path=path, title=title, description=desc, main_html=main,
        breadcrumb_items=breadcrumb, og_type="article", jsonld=jsonld,
    )


def render_about(cfg: SiteConfig, site: SiteData) -> str:
    body = "".join(f"<p>{p}</p>" for p in copy.ABOUT)
    body += (
        '<h2 id="accessibility">Accessibility</h2>'
        "<p>Plumbline is built to WCAG 2.1 AA in both light and dark themes: "
        "semantic landmarks, a skip link, visible focus, sufficient color contrast, "
        "and no information conveyed by color alone. Confidence is shown four ways — "
        "a signal-strength meter, a text label, color, and border texture. If "
        "something is hard to use, tell us and we'll fix it.</p>"
    )
    breadcrumb = [HOME, ("About", "/about/")]
    return _prose_page(
        cfg, site, path="/about/", title="About Plumbline — Public-Interest Election Data",
        h1="About Plumbline",
        desc="Plumbline is an independent, nonpartisan reference for U.S. off-cycle and local election dates — sourced, confidence-rated, and human-verified.",
        body=body, breadcrumb=breadcrumb,
        dateline=f"UPDATED {site.version}",
        lede="Curation-first, nonpartisan, and candid about its limits — the whole product is being right, and being able to show why.",
        jsonld=[seo.breadcrumb_ld(cfg, breadcrumb)],
    )


def render_methodology(cfg: SiteConfig, site: SiteData) -> str:
    from .data import CONFIDENCE_BLURB, CONFIDENCE_LABELS

    steps = "".join(
        f"<li><strong>{name}.</strong> {text}</li>" for name, text in copy.METHODOLOGY_STEPS
    )
    defs = "".join(
        f"<dt>{CONFIDENCE_LABELS[c]}</dt><dd>{CONFIDENCE_BLURB[c]}</dd>"
        for c in ("official", "secondary", "inferred")
    )
    body = (
        f"<ol class='method-steps'>{steps}</ol>"
        '<h2 id="confidence">Confidence levels</h2>'
        "<p>Every date is labeled with how firm it is. These labels appear on every "
        "record and in the data exports.</p>"
        f"{C.confidence_legend()}"
        f"<dl class='conf-defs'>{defs}</dl>"
        f"<h2>The last word</h2><p>{copy.METHODOLOGY_OUTRO}</p>"
    )
    breadcrumb = [HOME, ("Methodology", "/methodology/")]
    return _prose_page(
        cfg, site, path="/methodology/",
        title="Methodology — How We Verify Election Dates | Plumbline",
        h1="Our methodology",
        desc="How Plumbline sources, tiers, verifies, protects, and versions every election date — and what official, secondary, and inferred mean.",
        body=body, breadcrumb=breadcrumb,
        dateline=f"VERSION {site.version}", lede=copy.METHODOLOGY_INTRO,
        jsonld=[seo.defined_terms_ld(cfg), seo.breadcrumb_ld(cfg, breadcrumb)],
    )


def render_data(cfg: SiteConfig, site: SiteData) -> str:
    intro = "".join(f"<p>{esc(p)}</p>" for p in copy.DATA_PRODUCT)
    audiences = "".join(
        f"<li><strong>{esc(who)}.</strong> {esc(what)}</li>"
        for who, what in copy.DATA_PRODUCT_AUDIENCES
    )
    json_links = "".join(
        f'<li><a href="{rel(cfg, "/downloads/json/" + s.code + "/index.json")}">'
        f"{esc(s.name)}</a></li>"
        for s in site.states
    )
    json_index = (
        f'<div class="wrap json-index-block"><h2 class="section-h2">Per-state JSON</h2>'
        f"<ul class=\"json-index\">{json_links}</ul>"
        f'<p class="license-note">The dataset is licensed under '
        f'<a href="https://creativecommons.org/licenses/by/4.0/" rel="license">'
        f"CC&nbsp;BY&nbsp;4.0</a> — free to use with attribution.</p></div>"
        if site.states
        else '<div class="wrap"><p class="license-note">Per-state JSON is available '
        'once records are published. The dataset is licensed under '
        '<a href="https://creativecommons.org/licenses/by/4.0/" rel="license">'
        "CC&nbsp;BY&nbsp;4.0</a>.</p></div>"
    )
    csv_href = rel(cfg, f"/downloads/csv/{site.version}/off_cycle_elections_{site.version}.csv")
    changelog_href = rel(cfg, f"/downloads/csv/{site.version}/CHANGELOG.md")
    cards = (
        '<div class="card-grid">'
        + C.export_card(
            cfg, "CSV + changelog",
            f"The full verified dataset, version {site.version}, with a human-readable "
            "changelog of every change.",
            f'<a class="btn btn--secondary" href="{csv_href}" download>'
            f'{icons.ICON_DOWNLOAD} Download CSV</a>'
            f'<a class="btn btn--ghost" href="{changelog_href}">See what changed</a>',
        )
        + C.export_card(
            cfg, "JSON",
            "The same records as structured JSON, one file per state plus per-"
            "jurisdiction files.",
            (
                f'<a class="btn btn--secondary" href="{rel(cfg, "/downloads/json/" + site.states[0].code + "/index.json")}">View JSON</a>'
                if site.states else '<span class="export-card__soon">Available with published data</span>'
            ),
        )
        + C.export_card(
            cfg, "ICS calendar feeds",
            "Per-jurisdiction calendar feeds — add a town's election dates straight to "
            "your phone or planning tool.",
            f'<a class="btn btn--ghost" href="{rel(cfg, "/states/")}">Find a jurisdiction</a>',
            anchor="calendar-feeds",
        )
        + "</div>"
    )
    body = (
        f'<div class="wrap page-head"><p class="dateline num">VERSION {esc(site.version)}</p>'
        "<h1>Election data for teams</h1>"
        '<p class="lede">Plumbline Data is the same verified record set, packaged as '
        "versioned flat files you can drop straight into a model, a CRM, or a field "
        "plan.</p></div>"
        f'<div class="wrap" data-reveal="block"><h2 class="section-h2">Downloads</h2>{cards}</div>'
        f"{json_index}"
        f'<section class="section section--tinted"><div class="wrap prose">{intro}'
        f"<h2>Built for teams that plan around dates</h2><ul>{audiences}</ul>"
        f"<p>{copy.DATA_PRODUCT_CLOSER} "
        f'<a href="{rel(cfg, "/methodology/")}">Read the methodology →</a></p>'
        "</div></section>"
    )
    breadcrumb = [HOME, ("Data", "/data/")]
    return render_page(
        cfg, site, path="/data/",
        title="Election Data Exports (CSV, JSON, ICS) — Plumbline",
        description=(
            f"Download the full versioned dataset of U.S. off-cycle and local "
            f"elections: CSV with changelog, per-state JSON, and per-jurisdiction "
            f"calendars (.ics). Current version {site.version}."
        ),
        main_html=body, breadcrumb_items=breadcrumb,
        jsonld=[seo.dataset_ld(cfg, site), seo.breadcrumb_ld(cfg, breadcrumb)],
    )


def render_404(cfg: SiteConfig, site: SiteData) -> str:
    main = (
        '<div class="wrap page-head error-page">'
        "<h1>We couldn't find that page</h1>"
        '<p class="lede">The page may have moved, or the election may have rolled off '
        "the calendar. Try browsing by state.</p>"
        f'<p class="error-page__actions"><a class="btn btn--primary" '
        f'href="{rel(cfg, "/states/")}">Browse states</a> '
        f'<a class="btn btn--secondary" href="{rel(cfg, "/")}">Go home</a></p></div>'
    )
    return render_page(
        cfg, site, path="/404.html", title="Page not found — Plumbline",
        description="The page could not be found.", main_html=main,
        robots="noindex,follow", omit_canonical=True,
    )
