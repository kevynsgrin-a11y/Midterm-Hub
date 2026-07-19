"""Reusable UI fragments. Each returns an HTML string and matches the design spec's
class names exactly so it lines up with assets/styles.css."""
from __future__ import annotations

import datetime
from typing import Optional

from . import icons
from .base import SiteConfig, absu, attrs, esc, rel
from .data import (
    CONFIDENCE_BLURB,
    CONFIDENCE_LABELS,
    Deadline,
    ElectionView,
    JurisdictionView,
    StateView,
)


def date_block(e: ElectionView, large: bool = False) -> str:
    d = e.election_date
    cls = "date-block date-block--lg" if large else "date-block"
    return (
        f'<time class="{cls}" datetime="{esc(e.date_iso)}">'
        f'<span class="date-block__mon">{esc(d.strftime("%b").upper())}</span>'
        f'<span class="date-block__day">{d.day}</span>'
        f'<span class="date-block__dow">{esc(d.strftime("%a"))}</span>'
        f"</time>"
    )


def tag(election_type: str, label: str) -> str:
    return f'<span class="tag"{attrs(data_type=election_type)}>{esc(label)}</span>'


def deadline_chip(dl: Deadline, today: datetime.date) -> str:
    days = (dl.date - today).days
    cls = "deadline-chip"
    passed = days < 0
    if days == 0:
        cls += " deadline-chip--today"
    elif 0 < days <= 7:
        cls += " deadline-chip--urgent"
    elif passed:
        cls += " deadline-chip--past"
    glyph = icons.DEADLINE_ICONS.get(dl.key, "")
    time_html = (
        f' <span class="deadline-chip__time">{esc(dl.time)}</span>' if dl.time else ""
    )
    date_html = f'<span class="deadline-chip__date num">{esc(dl.formatted)}</span>'
    sr = '<span class="sr-only"> (passed)</span>' if passed else ""
    return (
        f'<span class="{cls}">{glyph}'
        f'<span class="deadline-chip__label">{esc(dl.label)}</span>'
        f"{date_html}{time_html}{sr}</span>"
    )


def confidence_badge(level: str) -> str:
    label = CONFIDENCE_LABELS.get(level, level)
    blurb = CONFIDENCE_BLURB.get(level, "")
    return (
        f'<span class="confidence-badge confidence-badge--{esc(level)}" '
        f'title="{esc(blurb)}">'
        f"{icons.confidence_meter(level)}"
        f'<span class="sr-only">Data confidence: </span>'
        f'<span class="confidence-badge__label">{esc(label)}</span>'
        f"</span>"
    )


def confidence_legend() -> str:
    badges = "".join(confidence_badge(l) for l in ("official", "secondary", "inferred"))
    return f'<div class="confidence-legend" role="group" aria-label="Data confidence levels">{badges}</div>'


def source_link(cfg: SiteConfig, url: str) -> str:
    return (
        f'<a class="source-link num" href="{esc(url)}" rel="nofollow noopener" '
        f'target="_blank">SOURCE{icons.ICON_EXTERNAL}'
        f'<span class="sr-only"> (opens in a new tab)</span></a>'
    )


def election_card(cfg: SiteConfig, e: ElectionView) -> str:
    past_cls = " election-card--past" if not e.is_upcoming else ""
    offices = (
        f'<p class="election-card__offices">{esc(e.offices_summary)}</p>'
        if e.offices_summary
        else ""
    )
    chips = "".join(deadline_chip(dl, e._today) for dl in e.deadlines[:3])
    chips_html = f'<div class="election-card__chips">{chips}</div>' if chips else ""
    weekday_date = f"{e.election_date.strftime('%a')} · {e.date_short}"
    return (
        f'<article class="election-card{past_cls}"{attrs(data_type=e.election_type)}>'
        f'<div class="election-card__kicker">{tag(e.election_type, e.election_type_label)}'
        f'<span class="election-card__jtype">{esc(e.jurisdiction_type_label)}</span></div>'
        f'<div class="election-card__head">{date_block(e)}'
        f'<div class="election-card__headings">'
        f'<h3 class="election-card__title"><a href="{esc(rel(cfg, e.url))}">'
        f"{esc(e.jurisdiction_name)}</a></h3>"
        f'<p class="election-card__date num">{esc(weekday_date)} '
        f'<span class="election-card__countdown">· {esc(e.countdown)}</span></p>'
        f"</div></div>"
        f"{offices}{chips_html}"
        f'<div class="election-card__foot">{confidence_badge(e.confidence)}'
        f"{source_link(cfg, e.source_url)}</div>"
        f"</article>"
    )


def deadline_rail(cfg: SiteConfig, e: ElectionView) -> str:
    """Semantic <ol> of milestones ending in election day. Styled as a horizontal
    rail on desktop, a vertical spine on mobile; degrades to a readable list."""
    today = e._today
    nodes: list[tuple[str, datetime.date, str, Optional[str]]] = [
        (dl.label, dl.date, dl.key, dl.time) for dl in e.deadlines
    ]
    nodes.append(("Election day", e.election_date, "election", None))

    # Identify the first upcoming milestone to mark as NEXT.
    next_idx = next((i for i, n in enumerate(nodes) if n[1] >= today), None)

    items = []
    for i, (label, d, key, time) in enumerate(nodes):
        days = (d - today).days
        classes = ["rail__node"]
        if key == "election":
            classes.append("rail__node--election")
        if days < 0:
            classes.append("rail__node--past")
        if i == next_idx and key != "election":
            classes.append("rail__node--next")
        tagline = ""
        if i == next_idx:
            tagline = '<span class="rail__tag">NEXT</span>'
        elif key == "election" and days >= 0:
            tagline = '<span class="rail__tag rail__tag--election">ELECTION</span>'
        time_html = f" <span class='rail__time'>{esc(time)}</span>" if time else ""
        items.append(
            f'<li class="{" ".join(classes)}">'
            f'<span class="rail__marker" aria-hidden="true"></span>'
            f'<span class="rail__label">{esc(label)}{tagline}</span>'
            f'<time class="rail__date num" datetime="{esc(d.isoformat())}">'
            f"{esc(_fmt(d))}{time_html}</time>"
            f"</li>"
        )
    return (
        '<ol class="deadline-rail" aria-label="Election deadline timeline">'
        + "".join(items)
        + "</ol>"
    )


def timeline(e: ElectionView) -> str:
    """Compact deadline list for secondary placement."""
    today = e._today
    rows = []
    for dl in e.deadlines:
        days = (dl.date - today).days
        state = " timeline__node--past" if days < 0 else ""
        rows.append(
            f'<li class="timeline__node{state}">'
            f'<span class="timeline__label">{esc(dl.label)}</span>'
            f'<time class="timeline__date num" datetime="{esc(dl.date.isoformat())}">'
            f"{esc(dl.formatted)}</time></li>"
        )
    rows.append(
        f'<li class="timeline__node timeline__node--election">'
        f'<span class="timeline__label">Election day</span>'
        f'<time class="timeline__date num" datetime="{esc(e.date_iso)}">'
        f"{esc(e.date_short)}</time></li>"
    )
    return f'<ol class="timeline">{"".join(rows)}</ol>'


def _prov_row(label: str, value_html: str) -> str:
    return (
        f'<div class="provenance__row"><span class="provenance__key">{esc(label)}</span>'
        f'<span class="provenance__val">{value_html}</span></div>'
    )


def provenance(cfg: SiteConfig, e: ElectionView) -> str:
    rows = [
        _prov_row(
            "SOURCE",
            f'<a href="{esc(e.source_url)}" rel="nofollow noopener" target="_blank" '
            f'title="{esc(e.source_url)}">{esc(e.source_url)}</a>',
        )
    ]
    if e.source_retrieved_at:
        rows.append(_prov_row("RETRIEVED", esc(e.source_retrieved_at)))
    if e.verified_by:
        vt = f" · {esc(e.verified_at)}" if e.verified_at else ""
        rows.append(_prov_row("VERIFIED BY", f"{esc(e.verified_by)}{vt}"))
    rows.append(_prov_row("RECORD", esc(e.id)))
    rows.append(_prov_row("STATUS", esc(e.status)))
    if e.timezone:
        rows.append(_prov_row("TIMEZONE", esc(e.timezone)))
    notes = (
        f'<p class="provenance__notes">{esc(e.notes)}</p>' if e.notes else ""
    )
    return (
        '<aside class="provenance" aria-label="Record provenance">'
        '<p class="provenance__title">Provenance</p>'
        f'{"".join(rows)}{notes}</aside>'
    )


def state_tile(cfg: SiteConfig, s: StateView) -> str:
    n = len(s.upcoming)
    if n:
        pill = f'<span class="count-pill num">{n} upcoming</span>'
        quiet = ""
    else:
        pill = '<span class="count-pill count-pill--quiet num">—</span>'
        quiet = " is-quiet"
    return (
        f'<a class="state-tile{quiet}" href="{esc(rel(cfg, s.url))}">'
        f'<span class="state-tile__abbr">{esc(s.code)}</span>'
        f'<span class="state-tile__name">{esc(s.name)}</span>'
        f"{pill}</a>"
    )


def breadcrumb(cfg: SiteConfig, items: list[tuple[str, Optional[str]]]) -> str:
    """items: list of (label, url|None); the last item is the current page."""
    lis = []
    for i, (label, url) in enumerate(items):
        last = i == len(items) - 1
        if last or url is None:
            lis.append(
                f'<li><span aria-current="page" title="{esc(label)}">{esc(label)}</span></li>'
            )
        else:
            lis.append(f'<li><a href="{esc(rel(cfg, url))}">{esc(label)}</a></li>')
    return (
        '<nav class="breadcrumb" aria-label="Breadcrumb"><ol>'
        + "".join(lis)
        + "</ol></nav>"
    )


def export_card(
    cfg: SiteConfig, fmt: str, description: str, actions: str, anchor: Optional[str] = None
) -> str:
    anchor_attr = attrs(id=anchor) if anchor else ""
    return (
        f'<article class="export-card"{anchor_attr}>'
        f'<h3 class="export-card__fmt num">{esc(fmt)}</h3>'
        f'<p class="export-card__desc">{esc(description)}</p>'
        f'<div class="export-card__actions">{actions}</div>'
        f"</article>"
    )


def _fmt(d: datetime.date) -> str:
    return f"{d.strftime('%b')} {d.day}, {d.year}"
