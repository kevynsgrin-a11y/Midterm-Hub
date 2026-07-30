"""Reusable UI fragments. Each returns an HTML string and matches the design spec's
class names exactly so it lines up with assets/styles.css."""
from __future__ import annotations

import datetime
from typing import Optional

from . import icons
from .base import SiteConfig, attrs, esc, rel, safe_href
from .data import (
    CONFIDENCE_BLURB,
    CONFIDENCE_LABELS,
    Deadline,
    ElectionView,
    StateView,
    fmt_compact,
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


def deadline_chip(dl: Deadline, today: datetime.date, *, window_end: Optional[datetime.date] = None) -> str:
    """One deadline as a status chip.

    Status is carried by an explicit *word*, never by strikethrough or colour
    alone (WCAG 1.4.1). ``early_voting_start`` opens a window rather than closing
    a door: once it is past, early voting is HAPPENING, so it must never render as
    "passed". ``window_end`` lets an open early-voting chip name its closing date.

    ``data-deadline`` carries the machine date so site.js can recompute the status
    against the reader's own clock — this HTML is a static build that may be days old.
    """
    days = (dl.date - today).days
    cls = "deadline-chip"
    state = ""

    if dl.opens:
        if days > 0:
            state = "Opens"
        elif window_end is None or today <= window_end:
            cls += " deadline-chip--open"
            state = "Open now"
        else:
            cls += " deadline-chip--closed"
            state = "Closed"
    else:
        if days == 0:
            cls += " deadline-chip--today"
            state = "Today"
        elif 0 < days <= 7:
            cls += " deadline-chip--urgent"
        elif days < 0:
            cls += " deadline-chip--closed"
            state = "Closed"

    glyph = icons.DEADLINE_ICONS.get(dl.key, "")
    time_html = (
        f' <span class="deadline-chip__time">{esc(dl.time)}</span>' if dl.time else ""
    )
    date_html = (
        f'<time class="deadline-chip__date num" datetime="{esc(dl.date.isoformat())}">'
        f"{esc(dl.formatted)}</time>"
    )
    state_html = (
        f'<span class="deadline-chip__state">{esc(state)}</span>' if state else ""
    )
    # "in N days" for the urgent band, so urgency is stated and not just tinted.
    if not state and 0 < days <= 7:
        state_html = (
            f'<span class="deadline-chip__state">in {days} day{"s" if days != 1 else ""}</span>'
        )
    return (
        f'<span class="{cls}" data-deadline="{esc(dl.date.isoformat())}"'
        f'{attrs(data_opens=True if dl.opens else None)}'
        f'{attrs(data_window_end=window_end.isoformat() if window_end else None)}>{glyph}'
        f'<span class="deadline-chip__label">{esc(dl.label)}</span>'
        f"{date_html}{time_html}{state_html}</span>"
    )


def confidence_badge(level: str) -> str:
    """Confidence as meter + word + colour + border.

    The blurb is real content in an sr-only span, not a ``title`` tooltip: on a
    card the stretched title link covers the badge, so a tooltip never fires on
    hover, and ``title`` on a non-focusable span is never keyboard-reachable.
    """
    label = CONFIDENCE_LABELS.get(level, level)
    blurb = CONFIDENCE_BLURB.get(level, "")
    return (
        f'<span class="confidence-badge confidence-badge--{esc(level)}">'
        f"{icons.confidence_meter(level)}"
        f'<span class="sr-only">Data confidence: </span>'
        f'<span class="confidence-badge__label">{esc(label)}</span>'
        f'<span class="sr-only">. {esc(blurb)}</span>'
        f"</span>"
    )


def confidence_legend() -> str:
    badges = "".join(confidence_badge(l) for l in ("official", "secondary", "inferred"))
    return f'<div class="confidence-legend" role="group" aria-label="Data confidence levels">{badges}</div>'


def source_link(cfg: SiteConfig, url: str) -> str:
    return (
        f'<a class="source-link num" href="{esc(safe_href(url))}" rel="nofollow noopener" '
        f'target="_blank">SOURCE{icons.ICON_EXTERNAL}'
        f'<span class="sr-only"> (opens in a new tab)</span></a>'
    )


def countdown_span(e: ElectionView, cls: str = "countdown") -> str:
    """Relative timing, tagged with its machine date.

    This is a static build rebuilt weekly, so a baked "in 2 days" becomes a lie
    within days. site.js recomputes every ``[data-countdown]`` against the
    reader's clock; the server-rendered text is the no-JS fallback.
    """
    return (
        f'<span class="{cls}" data-countdown="{esc(e.date_iso)}">{esc(e.countdown)}</span>'
    )


def election_card(cfg: SiteConfig, e: ElectionView, *, context: str = "global") -> str:
    """One election as a card.

    ``context="state"`` drops the jurisdiction from the title — inside a state
    page the place is already established, so repeating "Texas" under an H1 of
    "Texas election dates" wastes the only line that could distinguish a primary
    from a general.
    """
    past_cls = " election-card--past" if not e.is_upcoming else ""
    offices = (
        f'<p class="election-card__offices">{esc(e.offices_summary)}</p>'
        if e.offices_summary
        else ""
    )
    window_end = e.early_voting_end_date
    chips = "".join(deadline_chip(dl, e._today, window_end=window_end) for dl in e.deadlines[:3])
    chips_html = f'<div class="election-card__chips">{chips}</div>' if chips else ""
    weekday_date = f"{e.election_date.strftime('%a')} · {e.date_short}"
    if context == "state":
        title = f"{e.election_type_label} election"
    else:
        title = f"{e.jurisdiction_name} {e.election_type_label.lower()} election"
    past_flag = (
        '<span class="election-card__flag">Past</span>' if not e.is_upcoming else ""
    )
    return (
        f'<article class="election-card{past_cls}"{attrs(data_type=e.election_type)}>'
        f'<div class="election-card__kicker">{tag(e.election_type, e.election_type_label)}'
        f'<span class="election-card__jtype">{esc(e.jurisdiction_type_label)}</span>'
        f"{past_flag}</div>"
        f'<div class="election-card__head">{date_block(e)}'
        f'<div class="election-card__headings">'
        f'<h3 class="election-card__title"><a href="{esc(rel(cfg, e.url))}">'
        f"{esc(title)}</a></h3>"
        f'<p class="election-card__date num">{esc(weekday_date)} '
        f'<span class="election-card__countdown">· {countdown_span(e)}</span></p>'
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

    # NEXT marks the soonest upcoming *deadline* (never election day); election day
    # always carries the ELECTION tag when it is still upcoming.
    deadline_count = len(nodes) - 1
    next_idx = next((i for i in range(deadline_count) if nodes[i][1] >= today), None)

    items = []
    for i, (label, d, key, time) in enumerate(nodes):
        days = (d - today).days
        classes = ["rail__node"]
        if key == "election":
            classes.append("rail__node--election")
        if days < 0:
            classes.append("rail__node--past")
        if i == next_idx:
            classes.append("rail__node--next")
        tag_text = ""
        tag_cls = "rail__tag"
        if key == "election" and days >= 0:
            tag_text, tag_cls = "ELECTION", "rail__tag rail__tag--election"
        elif i == next_idx:
            tag_text = "NEXT"
        # Emitted unconditionally (empty when unused) and as a sibling of the label
        # rather than a child, so every node reserves the same tag row and the dates
        # share one baseline regardless of how many lines a label wraps to.
        tagline = f'<span class="{tag_cls}">{esc(tag_text)}</span>'
        time_html = f" <span class='rail__time'>{esc(time)}</span>" if time else ""
        items.append(
            f'<li class="{" ".join(classes)}">'
            f'<span class="rail__marker" aria-hidden="true"></span>'
            f'<span class="rail__label">{esc(label)}</span>'
            f"{tagline}"
            f'<time class="rail__date num" datetime="{esc(d.isoformat())}">'
            f"{esc(_fmt(d))}{time_html}</time>"
            f"</li>"
        )
    return (
        '<ol class="deadline-rail" aria-label="Election deadline timeline">'
        + "".join(items)
        + "</ol>"
    )


def _prov_row(label: str, value_html: str) -> str:
    return (
        f'<div class="provenance__row"><span class="provenance__key">{esc(label)}</span>'
        f'<span class="provenance__val">{value_html}</span></div>'
    )


def provenance(cfg: SiteConfig, e: ElectionView) -> str:
    rows = [
        _prov_row(
            "SOURCE",
            f'<a href="{esc(safe_href(e.source_url))}" rel="nofollow noopener" '
            f'target="_blank" title="{esc(e.source_url)}">{esc(e.source_url)}</a>',
        )
    ]
    if e.source_retrieved_at:
        rows.append(_prov_row("RETRIEVED", esc(e.source_retrieved_at)))
    if e.verified_by:
        vt = f" · {esc(e.verified_at[:10])}" if e.verified_at else ""
        # "editorial" is a database actor enum, not a person's name — don't ship it.
        who = "Plumbline editors" if e.verified_by == "editorial" else e.verified_by
        rows.append(_prov_row("CHECKED BY", f"{esc(who)}{vt}"))
    if e.timezone:
        rows.append(_prov_row("TIMEZONE", esc(e.timezone)))
    notes = (
        f'<p class="provenance__notes">{esc(e.notes)}</p>' if e.notes else ""
    )
    # The content hash is a join key for data users, not something a voter needs.
    record_id = (
        '<details class="provenance__record"><summary>Record ID (for data users)</summary>'
        f'<p class="provenance__id num">{esc(e.id)}</p></details>'
    )
    return (
        '<aside class="provenance" aria-label="Where this date came from">'
        '<p class="provenance__title">Where this date came from</p>'
        f'{"".join(rows)}{notes}{record_id}</aside>'
    )


def state_tile(cfg: SiteConfig, s: StateView) -> str:
    """A state tile that carries its next date, not just a count.

    A wall of 51 tiles reading "1 upcoming" is 51 copies of one bit. The date is
    the fact a visitor came for, and the urgency bar makes "in 2 days" scannable
    against "in 100 days" without relying on colour alone.
    """
    ne = s.next_election
    if ne:
        days = max(ne.days_until, 0)
        # 180-day horizon: full bar = imminent, empty = far off.
        pct = round(max(0.0, 1 - min(days, 180) / 180) * 100)
        meta = (
            f'<span class="state-tile__date num" data-countdown="{esc(ne.date_iso)}"'
            f' data-countdown-format="compact">{esc(fmt_compact(ne.election_date))}</span>'
            f'<span class="state-tile__urgency" style="--u:{pct}%" aria-hidden="true"></span>'
        )
        quiet = ""
    else:
        meta = '<span class="state-tile__date state-tile__date--quiet">No dates yet</span>'
        quiet = " is-quiet"
    return (
        f'<a class="state-tile{quiet}" href="{esc(rel(cfg, s.url))}">'
        f'<span class="state-tile__abbr">{esc(s.code)}</span>'
        f'<span class="state-tile__name">{esc(s.name)}</span>'
        f"{meta}</a>"
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
