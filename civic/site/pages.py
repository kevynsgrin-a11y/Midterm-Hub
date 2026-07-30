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


def _crumbs(items: list) -> list:
    """Collapse consecutive identical labels, keeping the shallower URL.

    Every record is statewide, so ``jurisdiction_name == state_name`` and the raw
    chain renders "Home / States / Texas / Texas" — visibly, and in the
    BreadcrumbList JSON-LD that Google prints in the SERP.
    """
    out: list = []
    for label, url in items:
        if out and out[-1][0] == label:
            continue
        out.append((label, url))
    return out


def _cards(cfg: SiteConfig, elections: list[ElectionView], *, context: str = "global") -> str:
    """A card grid that tracks its own content count.

    ``auto-fill`` reserves empty tracks, so one card in a 3-column grid left two
    thirds of the row void on the most-visited page type. ``data-count`` lets CSS
    pick a track template that the content actually fills.
    """
    n = len(elections)
    return (
        f'<div class="card-grid" data-count="{min(n, 3)}" data-reveal="cards">'
        + "".join(C.election_card(cfg, e, context=context) for e in elections)
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
    # Without JS the query string is meaningless on a static host, so the form
    # targets the A–Z list anchor: the button then does exactly what it says,
    # and the noscript line tells the reader where they are about to land.
    jump = (
        f'<form class="jump-form" action="{esc(rel(cfg, "/states/#all-states"))}" '
        'method="get" role="search" aria-label="Jump to a state">'
        '<label for="state-jump" class="sr-only">Choose a state</label>'
        '<select id="state-jump" name="state" class="select" data-jump>'
        '<option value="">Choose a state…</option>'
        f"{jump_options}</select>"
        f'<button class="btn btn--primary" type="submit">{copy.CTA["find_state"]}</button>'
        f'<noscript><p class="jump-form__nojs">{esc(copy.HOME_HERO["nojs"])}</p></noscript>'
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
        chips = "".join(
            C.deadline_chip(dl, e0._today, window_end=e0.early_voting_end_date)
            for dl in e0.deadlines[:2]
        )
        next_card = (
            f'<a class="hero__next" href="{esc(rel(cfg, e0.url))}">'
            '<span class="overline">Next election in the country</span>'
            f'<span class="hero__next-row">{C.date_block(e0)}'
            f'<span class="hero__next-lines"><span class="hero__next-name">'
            f'{esc(e0.jurisdiction_name)} {esc(e0.election_type_label.lower())}</span>'
            f'<span class="hero__next-meta num">{esc(e0.date_short)} · '
            f"{C.countdown_span(e0)}</span>"
            "</span></span>"
            f'<span class="hero__next-chips">{chips}</span></a>'
        )
    # The instrument reads the cycle: bob position = today's place between the
    # earliest tracked date and the general election.
    instrument = icons.hero_plumbline()
    generals = [e for e in site.elections if e.election_type == "general"]
    if generals and site.elections:
        target = max(generals, key=lambda e: sum(1 for x in generals if x.election_date == e.election_date))
        first = min(e.election_date for e in site.elections)
        cycle_days = max((target.election_date - first).days, 1)
        days_left = (target.election_date - site.today).days
        month_ticks = []
        cur = first.replace(day=1)
        while cur <= target.election_date:
            frac = (cur - first).days / cycle_days
            if 0 <= frac <= 1:
                month_ticks.append((frac, cur.strftime("%b").upper()))
            cur = cur.replace(year=cur.year + cur.month // 12, month=cur.month % 12 + 1)
        instrument = icons.hero_plumbline(
            days_remaining=max(days_left, 0),
            cycle_days=cycle_days,
            target_label=f"the {target.date_short} general election",
            month_ticks=month_ticks,
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
        f'or see how we check every date →</a></div>'
        f"{trust_bar}{kpi}</div>"
        f'<div class="hero__instrument">{instrument}{next_card}</div>'
        "</div></section>"
    )
    ribbon = (
        '<section class="ribbon-band" data-reveal="block"><div class="wrap">'
        '<p class="section__index" aria-hidden="true">The 2026 cycle</p>'
        f"{art.cycle_ribbon(cfg, site.elections, site.today)}"
        "</div></section>"
    )

    upcoming_body = (
        _cards(cfg, up[:6])
        if up
        else '<p class="empty">No upcoming elections are on the calendar yet.</p>'
    )
    days_to_next = {
        s.code: s.next_election.days_until for s in site.states if s.next_election
    }
    next_dates = {
        s.code: s.next_election.date_compact for s in site.states if s.next_election
    }
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
        # The map is a second presentation of the tile grid below it, so it is
        # not a second set of 51 tab stops.
        '<div class="browse-layout">'
        + art.us_cartogram(
            cfg, counts, days_to_next=days_to_next, next_dates=next_dates,
            interactive=False,
        )
        + f"{state_grid}</div>",
        id="states", tinted=True, index="02",
    )

    # Only show the tier legend when more than one tier is actually in the data;
    # otherwise it advertises doubt this dataset doesn't warrant. The methodology
    # page always explains all three, which is where that belongs.
    tiers = {e.confidence for e in site.elections}
    aside = (
        C.confidence_legend()
        if len(tiers) > 1
        else f'<p class="trust-band__claim">{esc(copy.FOOTER_LEGEND_SOLO)}</p>'
    )
    trust = _section(
        "How we verify",
        (
            '<div class="trust-band">'
            f'<div class="prose">{"".join(f"<p>{p}</p>" for p in copy.WHY_DATES_GET_MISSED[2:])}'
            f'<p><a href="{rel(cfg, "/methodology/")}">{copy.CTA["read_methodology"]} →</a></p></div>'
            f"{aside}"
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

    main = hero + ribbon + on_calendar + browse + trust + exports
    # Budgeted under 160: Google truncates around there, and the trust clause is
    # the differentiator — it has to survive.
    desc = (
        f"Every 2026 election date and the deadlines that close weeks earlier. "
        f"{site.total_elections} elections across {site.total_states} states, each "
        f"linked to the election office it came from."
    )
    return render_page(
        cfg, site, path="/",
        title=f"{BRAND} — 2026 Midterm Election Dates & Deadlines",
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
    days_to_next = {
        s.code: s.next_election.days_until for s in site.states if s.next_election
    }
    next_dates = {
        s.code: s.next_election.date_compact for s in site.states if s.next_election
    }
    cartogram = art.us_cartogram(
        cfg, counts, days_to_next=days_to_next, next_dates=next_dates,
        interactive=False,
    )
    main = (
        '<div class="wrap page-head"><p class="dateline num">UPDATED '
        f'{esc(site.version)}</p><h1>Elections by state</h1>'
        '<p class="lede">Browse verified 2026 election calendars by '
        f'state — {site.total_states} covered.</p></div>'
        f'<div class="wrap" data-reveal="block">{cartogram}</div>'
        f'<div class="wrap" data-reveal="block"><h2 class="section-h2" id="all-states">'
        f"All states</h2>{grid}</div>"
    )
    items = [(s.name, s.url) for s in site.states]
    return render_page(
        cfg, site, path="/states/",
        title="2026 Elections by State — Plumbline",
        description=(
            "Browse verified 2026 election calendars by state — primary and "
            "general dates, voter-registration deadlines, and early-voting windows."
        ),
        main_html=main, breadcrumb_items=[HOME, STATES],
        jsonld=[
            seo.collection_ld(cfg, "Elections by state", "/states/", items, site.last_modified),
            seo.breadcrumb_ld(cfg, [HOME, STATES], "/states/"),
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
            f'{esc(ne.date_full)} · {C.countdown_span(ne)}</span></a></div>'
        )

    # A single statewide jurisdiction adds no grouping information, so its heading
    # would just repeat the page's own H1. Render the cards directly in that case.
    single = len(s.jurisdictions) == 1 and s.jurisdictions[0].name == s.name
    sections = []
    if single:
        sections.append(
            '<section class="juris-block" data-reveal="block">'
            f'<h2 class="section-h2">Every {esc(s.name)} election left in 2026</h2>'
            f"{_cards(cfg, s.jurisdictions[0].elections, context='state')}</section>"
        )
    else:
        for j in s.jurisdictions:
            sections.append(
                f'<section class="juris-block" data-reveal="block"><h2 class="juris-block__title">'
                f'<a href="{esc(rel(cfg, j.url))}">{esc(j.name)}</a>'
                f'<span class="juris-block__type overline">{esc(j.jurisdiction_type_label)}</span></h2>'
                f"{_cards(cfg, j.elections)}</section>"
            )

    n_up = len(s.upcoming)
    if n_up == 1:
        lede = (
            f"One election left on {s.name}'s 2026 calendar. Here's the date and "
            "every deadline before it."
        )
    elif n_up:
        lede = (
            f"{n_up} elections left on {s.name}'s 2026 calendar, with every "
            "deadline before each one."
        )
    else:
        lede = (
            f"No {s.name} elections are on the 2026 calendar yet. We add each one "
            "as the state publishes it."
        )
    main = (
        f'<div class="wrap page-head"><p class="dateline num">UPDATED {esc(site.version)}</p>'
        f"<h1>{esc(s.name)} election dates</h1>"
        f'<p class="lede">{esc(lede)}</p>{lead}</div>'
        f'<div class="wrap">{"".join(sections)}</div>'
    )
    breadcrumb = [HOME, STATES, (s.name, s.url)]
    if s.next_election:
        desc = (
            f"{s.name} 2026 elections: next is the "
            f"{s.next_election.election_type_label.lower()} on "
            f"{s.next_election.date_short}. Every registration and early-voting "
            f"deadline, officially sourced."
        )
    else:
        desc = (
            f"Verified 2026 election records for {s.name}: dates, "
            f"registration deadlines, and early voting."
        )
    items = [(e.title, e.url) for e in s.elections]
    return render_page(
        cfg, site, path=s.url,
        title=f"{s.name} 2026 Elections & Deadlines — Plumbline",
        description=desc, main_html=main, breadcrumb_items=breadcrumb,
        og_image=(site.og.get("states", {}) or {}).get(s.code),
        og_image_alt=f"{s.name} 2026 election calendar — Plumbline",
        jsonld=[
            seo.collection_ld(cfg, f"{s.name} elections", s.url, items),
            seo.breadcrumb_ld(cfg, breadcrumb, s.url),
        ],
    )


# ------------------------------------------------------------------- jurisdiction

def _related(cfg: SiteConfig, site: SiteData, e: ElectionView) -> str:
    """Lateral links out of a leaf page.

    Election pages linked only upward, so 51 of 74 records share one date and no
    page connected them. These blocks are the only way to move sideways.
    """
    same_day = [
        x for x in site.elections if x.date_iso == e.date_iso and x.id != e.id
    ][:6]
    same_state = [
        x for x in site.elections if x.state == e.state and x.id != e.id
    ][:4]
    blocks = []
    if same_day:
        links = "".join(
            f'<li><a href="{esc(rel(cfg, x.url))}">{esc(x.state_name)} '
            f"{esc(x.election_type_label.lower())}</a></li>"
            for x in same_day
        )
        total = sum(1 for x in site.elections if x.date_iso == e.date_iso)
        blocks.append(
            f'<div class="related__col"><h3 class="related__h">Also voting '
            f'{esc(e.date_short)}</h3><ul class="related__list">{links}</ul>'
            f'<p class="related__more">{total} elections share this date.</p></div>'
        )
    if same_state:
        links = "".join(
            f'<li><a href="{esc(rel(cfg, x.url))}">{esc(x.election_type_label)} '
            f"— {esc(x.date_short)}</a></li>"
            for x in same_state
        )
        blocks.append(
            f'<div class="related__col"><h3 class="related__h">More in '
            f'{esc(e.state_name)}</h3><ul class="related__list">{links}</ul></div>'
        )
    if not blocks:
        return ""
    return (
        '<section class="detail-section related" data-reveal="block">'
        "<h2>Related elections</h2>"
        f'<div class="related__cols">{"".join(blocks)}</div></section>'
    )


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
            f'<span class="lead-card__title">{esc(ne.election_type_label)} election</span>'
            f'<span class="lead-card__meta num">{esc(ne.date_full)} · {C.countdown_span(ne)}</span></a>'
            f'<div class="lead-card__rail">{C.deadline_rail(cfg, ne)}</div></div>'
        )
    n = len(j.elections)
    lede = (
        f"One election left on {j.name}'s 2026 calendar."
        if n == 1
        else f"{n} elections left on {j.name}'s 2026 calendar."
    )
    # With one record the lead card above IS the record — repeating it in a grid
    # below stated the same fact twice on more than half the jurisdictions.
    records = (
        ""
        if n <= 1
        else (
            f'<div class="wrap" data-reveal="block">'
            f'<h2 class="section-h2">Every election record</h2>'
            f"{_cards(cfg, j.elections, context='state')}</div>"
        )
    )
    # With one record this page used to be a lead card over 700px of nothing.
    # Fold the substance up: what's on the ballot, where the date came from, and
    # somewhere to go next.
    extras = ""
    if ne:
        offices = ""
        if ne.offices:
            lis = "".join(f"<li>{esc(o)}</li>" for o in ne.offices)
            offices = (
                '<section class="detail-section" data-reveal="block"><h2>On the ballot</h2>'
                f'<p class="detail-trust__blurb">{esc(copy.BALLOT_INTRO)}</p>'
                f'<ul class="offices-list">{lis}</ul></section>'
            )
        reg_notice = ""
        if ne.registration_closed:
            reg_notice = (
                f'<p class="reg-closed">{icons.ICON_ALERT}<span>'
                f'{esc(copy.REG_CLOSED_NOTE.format(date=ne.registration_deadline_formatted))}'
                "</span></p>"
            )
        sourcing = (
            '<section class="detail-section detail-trust" data-reveal="block">'
            "<h2>Where these dates came from</h2>"
            f'<p class="detail-trust__blurb">{esc(ne.confidence_blurb)}</p>'
            f"{C.provenance(cfg, ne)}</section>"
        )
        extras = (
            f'<div class="wrap detail-body">{reg_notice}'
            f'<p class="confirm-note">{esc(copy.CONFIRM_NOTE)}</p>'
            f"{offices}{sourcing}{_related(cfg, site, ne)}</div>"
        )
    main = (
        f'<div class="wrap page-head"><p class="dateline num">UPDATED {esc(site.version)}</p>'
        f"<h1>{esc(j.name)} election dates</h1>"
        f'<p class="lede">{esc(lede)}</p>'
        f'<div class="page-head__actions">{subscribe}</div>{lead}</div>'
        f"{records}{extras}"
    )
    breadcrumb = _crumbs(
        [HOME, STATES, (j.state_name, f"/states/{j.state}/"), (j.name, j.url)]
    )
    place = j.state_name if j.name == j.state_name else f"{j.name}, {j.state_name}"
    if ne:
        desc = (
            f"{place} elections: next is the {ne.election_type_label.lower()} on "
            f"{ne.date_short}. Registration and early-voting deadlines, each linked "
            f"to its official source."
        )
    else:
        desc = (
            f"Every verified {place} election: dates, registration deadlines, "
            f"and early voting, each linked to its official source."
        )
    items = [(e.title, e.url) for e in j.elections]
    ld = seo.collection_ld(cfg, f"{j.name} elections", j.url, items)
    ld["@graph"][0]["hasPart"] = {
        "@type": "DataDownload",
        "name": f"Add {j.name} elections to your calendar",
        "encodingFormat": "text/calendar",
        "contentUrl": seo.absu(cfg, j.ics_url),
    }
    juris_title = j.name if j.name == j.state_name else f"{j.name}, {j.state}"
    return render_page(
        cfg, site, path=j.url,
        title=f"{juris_title} Elections & Deadlines — Plumbline",
        description=desc, main_html=main, breadcrumb_items=breadcrumb,
        og_image=(site.og.get("states", {}) or {}).get(j.state),
        og_image_alt=f"{j.name} 2026 election calendar — Plumbline",
        jsonld=[ld, seo.breadcrumb_ld(cfg, breadcrumb, j.url)],
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
        f'<a class="btn btn--primary" href="{esc(ics_href)}" download>'
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
        f'<span class="detail-hero__countdown">· {C.countdown_span(e)}</span></p>'
        f'<div class="detail-hero__meta">{C.tag(e.election_type, e.election_type_label)}'
        f'{C.confidence_badge(e.confidence)}</div>'
        f'<div class="detail-hero__actions">{add_cal}'
        f'{C.source_link(cfg, e.source_url)}</div>'
        "</div></div>"
    )
    # A closed registration window used to be signalled by a strikethrough and
    # nothing else — no sentence, no next step. Say it, and point somewhere useful.
    reg_notice = ""
    if e.registration_closed:
        reg_notice = (
            f'<p class="reg-closed">{icons.ICON_ALERT}<span>'
            f'{esc(copy.REG_CLOSED_NOTE.format(date=e.registration_deadline_formatted))}'
            "</span></p>"
        )
    rail = (
        '<section class="detail-section" data-reveal="block"><h2>Key dates &amp; deadlines</h2>'
        f"{C.deadline_rail(cfg, e)}{reg_notice}"
        f'<p class="confirm-note">{esc(copy.CONFIRM_NOTE)}</p></section>'
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

    breadcrumb = _crumbs([
        HOME, STATES, (e.state_name, e.state_url),
        (e.jurisdiction_name, e.jurisdiction_url),
        (f"{e.election_type_label} — {e.date_short}", e.url),
    ])
    reg = next((d for d in e.deadlines if d.key == "registration_deadline"), None)
    # Absolute date only — no relative countdown, which would go stale in the index.
    # Budgeted to ~160 chars so the trust signal survives Google's truncation.
    desc = (
        f"{e.place_phrase} {e.election_type_label.lower()} election: {e.date_full}."
    )
    if reg:
        desc += f" Register by {reg.formatted}."
    offices = e.offices_summary
    if offices and len(desc) + len(offices) + 20 < 140:
        desc += f" On the ballot: {offices}."
    elif e.offices:
        desc += f" {len(e.offices)} offices on the ballot."
    desc += " Official source." if e.confidence == "official" else " Provisional date."
    return render_page(
        cfg, site, path=e.url,
        title=f"{e.jurisdiction_name} {e.election_type_label} Election — {e.date_short}",
        description=desc, main_html=main, breadcrumb_items=breadcrumb, og_type="article",
        article_published=e.source_retrieved_at, article_modified=e.verified_at,
        og_image=(site.og.get("elections", {}) or {}).get(e.id),
        og_image_alt=f"{e.jurisdiction_name} {e.election_type_label} election — {e.date_short}",
        jsonld=[
            seo.event_ld(cfg, e, (site.og.get("elections", {}) or {}).get(e.id)),
            seo.breadcrumb_ld(cfg, breadcrumb, e.url),
        ],
    )


# --------------------------------------------------------------- static content

def _prose_page(
    cfg: SiteConfig, site: SiteData, *, path: str, title: str, h1: str, desc: str,
    body: str, breadcrumb, jsonld=None, dateline: str = "", lede: str = "",
) -> str:
    dl = f'<p class="dateline num">{esc(dateline)}</p>' if dateline else ""
    ld = f'<p class="lede">{esc(lede)}</p>' if lede else ""
    # One container, one measure. Previously .wrap (72rem) and .prose.wrap (42rem)
    # each centred independently, so the H1 and the body text sat on different
    # left edges — a 240px mismatch at 1440.
    main = (
        '<div class="wrap prose-page">'
        f'<div class="page-head">{dl}<h1>{esc(h1)}</h1>{ld}</div>'
        f'<article class="prose" data-reveal="block">{body}</article>'
        "</div>"
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
        desc="Plumbline is an independent, nonpartisan reference for U.S. election dates — the 2026 midterm cycle and beyond, sourced, confidence-rated, and human-verified.",
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
        f'<li><a href="{esc(rel(cfg, "/downloads/json/" + s.code + "/index.json"))}">'
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
            f'<a class="btn btn--secondary" href="{esc(csv_href)}" download>'
            f'{icons.ICON_DOWNLOAD} Download CSV</a>'
            f'<a class="btn btn--ghost" href="{esc(changelog_href)}">See what changed</a>',
        )
        + C.export_card(
            cfg, "JSON",
            "The same records as structured JSON, one file per state plus per-"
            "jurisdiction files.",
            (
                f'<a class="btn btn--secondary" href="{esc(rel(cfg, "/downloads/json/" + site.states[0].code + "/index.json"))}">View JSON</a>'
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
            f"The full 2026 U.S. election dataset as versioned CSV, per-state JSON, "
            f"and .ics calendar feeds. Version {site.version}, CC BY 4.0."
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
