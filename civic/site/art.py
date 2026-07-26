"""Code-generated, hermetic vector art. No libraries, no external assets — every
mark is math emitted as inline SVG so it stays crisp at any resolution and adds
zero network requests."""
from __future__ import annotations

import math
from typing import Optional

from .base import SiteConfig, esc, rel
from .data import STATE_NAMES

# Tile-grid map: each state placed in a stylized (row, col) grid that reads as the US.
# Not geographically exact by design — a tile cartogram trades precision for clarity.
US_TILEGRID: dict[str, tuple[int, int]] = {
    "AK": (0, 0), "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4), "IL": (2, 5),
    "WI": (2, 6), "MI": (2, 7), "NY": (2, 8), "RI": (2, 9), "MA": (2, 10),
    "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4), "IN": (3, 5),
    "OH": (3, 6), "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9),
    "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4), "KY": (4, 5),
    "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9),
    "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5), "NC": (5, 6),
    "SC": (5, 7), "DC": (5, 8),
    "TX": (6, 2), "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7),
    "HI": (7, 0), "FL": (7, 8),
}


def guilloche_svg(
    width: int = 760, height: int = 520, lines: int = 11, cls: str = "hero__guilloche"
) -> str:
    """A currency-grade guilloché band: a family of phase-offset interference waves
    engraved in `currentColor`. Purely decorative (aria-hidden); the caller sets the
    color (brass) and opacity. Reads as a certified / security-document texture."""
    steps = 48
    polylines = []
    for i in range(lines):
        phase = i * (2 * math.pi / lines)
        amp = height * 0.16 * (0.55 + 0.45 * math.sin(i * 0.9))
        freq = 2.1 + 0.28 * i
        drift = height * 0.10
        pts = []
        for s in range(steps + 1):
            t = s / steps
            x = width * t
            y = (
                height / 2
                + amp * math.sin(freq * 2 * math.pi * t + phase)
                + drift * math.sin(0.5 * 2 * math.pi * t + phase * 1.7)
            )
            pts.append(f"{x:.0f},{y:.0f}")
        polylines.append(
            f'<polyline points="{" ".join(pts)}" fill="none" '
            f'stroke="currentColor" stroke-width="0.6"/>'
        )
    return (
        f'<svg class="{cls}" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" aria-hidden="true" focusable="false" '
        f'preserveAspectRatio="xMidYMid slice">{"".join(polylines)}</svg>'
    )


_RIBBON_STROKE = {
    "general": (78, 3.0, "var(--primary)"),
    "primary": (52, 2.0, "var(--brass)"),
    "runoff": (52, 2.0, "var(--brass)"),
    "special": (30, 1.5, "var(--text-subtle)"),
    "municipal": (30, 1.5, "var(--text-subtle)"),
    "school_board": (30, 1.5, "var(--text-subtle)"),
    "ballot_measure": (30, 1.5, "var(--text-subtle)"),
}


def cycle_ribbon(cfg: SiteConfig, elections, today, *, months: int = 7) -> str:
    """The whole cycle as one graphic: every tracked election as a stroke on a
    time axis, tallest for a general, shortest for a local race.

    This is the site's only view of its own dataset as a shape — 74 records
    scattered across a year, with one date carrying most of them. Every stroke is
    a real link, so it works with JS off and is reachable by keyboard; the
    draw-on animation is motion-safe only and the sr-only table carries the data
    for anyone who cannot see it.
    """
    import datetime as _dt

    if not elections:
        return ""
    W, H = 1440, 210
    x0, x1 = 80, 1360
    baseline = 150
    start = today
    end = max(e.election_date for e in elections)
    # Always show at least `months` so a thin tail doesn't stretch the axis.
    min_end = _dt.date(today.year + (today.month + months - 1) // 12,
                       (today.month + months - 1) % 12 + 1, 1)
    end = max(end, min_end)
    span = max((end - start).days, 1)

    def px(d) -> float:
        return x0 + (x1 - x0) * ((d - start).days / span)

    # Month gridlines + labels.
    grid, labels = [], []
    cur = _dt.date(start.year, start.month, 1)
    while cur <= end:
        if cur >= start:
            gx = px(cur)
            grid.append(
                f'<line x1="{gx:.1f}" y1="46" x2="{gx:.1f}" y2="{baseline}" '
                f'stroke="var(--border)" stroke-width="1"/>'
            )
            labels.append(
                f'<text x="{gx + 6:.1f}" y="{baseline + 26}" class="ribbon__month">'
                f'{cur.strftime("%b").upper()}</text>'
            )
        cur = _dt.date(cur.year + cur.month // 12, cur.month % 12 + 1, 1)

    # One stroke per election, jittered when several share a date.
    seen: dict = {}
    strokes = []
    for i, e in enumerate(sorted(elections, key=lambda x: x.election_date)):
        h, w, color = _RIBBON_STROKE.get(e.election_type, (30, 1.5, "var(--text-subtle)"))
        bx = px(e.election_date)
        k = round(bx)
        nth = seen.get(k, 0)
        seen[k] = nth + 1
        bx += (nth % 7 - 3) * 2.0
        strokes.append(
            f'<a href="{esc(rel(cfg, e.url))}" class="ribbon__mark" style="--i:{i}" '
            f'aria-label="{esc(e.jurisdiction_name)} {esc(e.election_type_label.lower())} '
            f'election, {esc(e.date_short)}">'
            f'<line x1="{bx:.1f}" y1="{baseline}" x2="{bx:.1f}" y2="{baseline - h}" '
            f'stroke="{color}" stroke-width="{w}" stroke-linecap="round"/></a>'
        )

    # The general election is the anchor everyone already knows — name it.
    generals = [e for e in elections if e.election_type == "general"]
    anchor = ""
    if generals:
        g = max(generals, key=lambda e: sum(1 for x in generals if x.election_date == e.election_date))
        gx = px(g.election_date)
        n_states = len({e.state for e in elections if e.election_date == g.election_date})
        anchor = (
            f'<line x1="{gx:.1f}" y1="{baseline}" x2="{gx:.1f}" y2="{baseline - 112}" '
            f'stroke="var(--primary)" stroke-width="3" stroke-linecap="round"/>'
            f'<rect x="{gx - 96:.1f}" y="{baseline - 146}" width="192" height="30" rx="4" '
            f'fill="var(--accent-wash)" stroke="var(--primary)" stroke-width="1"/>'
            f'<text x="{gx:.1f}" y="{baseline - 126}" class="ribbon__anchor" '
            f'text-anchor="middle">{esc(g.date_short.upper())} · {n_states} STATES</text>'
        )

    today_mark = (
        f'<line x1="{x0}" y1="40" x2="{x0}" y2="{baseline}" stroke="var(--rail-today)" '
        f'stroke-width="2"/>'
        f'<text x="{x0}" y="32" class="ribbon__today" text-anchor="middle">TODAY</text>'
    )
    counts: dict = {}
    for e in elections:
        counts[e.election_date.strftime("%B %Y")] = counts.get(e.election_date.strftime("%B %Y"), 0) + 1
    table_rows = "".join(
        f"<tr><th scope='row'>{esc(m)}</th><td>{c}</td></tr>" for m, c in counts.items()
    )
    return (
        '<figure class="ribbon-fig">'
        f'<svg class="ribbon" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Timeline of {len(elections)} tracked elections from today through '
        f'{esc(end.strftime("%B %Y"))}." preserveAspectRatio="none">'
        f'{"".join(grid)}'
        f'<line x1="{x0}" y1="{baseline}" x2="{x1}" y2="{baseline}" '
        f'stroke="var(--border-strong)" stroke-width="1"/>'
        f'{"".join(strokes)}{anchor}{today_mark}{"".join(labels)}'
        "</svg>"
        '<div class="sr-only"><table><caption>Tracked elections by month</caption>'
        '<thead><tr><th scope="col">Month</th><th scope="col">Elections</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></div>"
        "</figure>"
    )


def _urgency_bucket(days: Optional[int]) -> int:
    """Fixed day breakpoints, so every step of the ramp can actually occur.

    Bucketing on *count* against ``max_count`` was degenerate: with a maximum of
    two elections per state only buckets 2 and 4 were reachable, so a five-swatch
    legend described a two-colour map. Urgency is also the more useful encoding —
    "who votes soonest" beats "who has the most rows".
    """
    if days is None:
        return 0
    if days <= 14:
        return 4
    if days <= 30:
        return 3
    if days <= 60:
        return 2
    if days <= 120:
        return 1
    return 1 if days <= 400 else 0


def us_cartogram(
    cfg: SiteConfig,
    counts: dict[str, int],
    *,
    compact: bool = False,
    days_to_next: Optional[dict[str, int]] = None,
    next_dates: Optional[dict[str, str]] = None,
    interactive: bool = True,
) -> str:
    """A US tile-grid cartogram shaded by how soon each state votes next.

    ``interactive=False`` renders the cells as non-focusable spans: when the same
    51 destinations are already listed as a tile grid below, making the map a
    second full tab stop set doubles the keyboard cost of every page it is on.
    The per-cell labels and the sr-only table still carry the data.
    """
    days_to_next = days_to_next or {}
    next_dates = next_dates or {}
    cells = []
    rows = []  # for the visually-hidden table fallback
    for code, (r, c) in sorted(US_TILEGRID.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        n = counts.get(code, 0)
        days = days_to_next.get(code)
        bucket = _urgency_bucket(days if n else None)
        soon = " is-soon" if days is not None and days <= 14 and n else ""
        style = f"grid-row:{r + 1};grid-column:{c + 1}"
        name = STATE_NAMES.get(code, code)
        date_txt = next_dates.get(code, "")
        inner = f'<span class="cart-cell__code">{code}</span>' + (
            f'<span class="cart-cell__date">{esc(date_txt)}</span>' if date_txt and not compact else ""
        )
        if n:
            when = f"; next {date_txt}" if date_txt else ""
            label = f"{name}: {n} upcoming election{'s' if n != 1 else ''}{when}"
            if interactive:
                cells.append(
                    f'<a class="cart-cell cart-b{bucket}{soon}" style="{style}" '
                    f'href="{esc(rel(cfg, f"/states/{code}/"))}" aria-label="{esc(label)}">'
                    f"{inner}</a>"
                )
            else:
                cells.append(
                    f'<span class="cart-cell cart-b{bucket}{soon}" style="{style}" '
                    f'role="img" aria-label="{esc(label)}">{inner}</span>'
                )
            rows.append(
                f"<tr><th scope='row'>{esc(name)}</th><td>{n}</td>"
                f"<td>{esc(date_txt or '—')}</td></tr>"
            )
        else:
            label = f"{name}: no tracked elections yet"
            # role="img" so the accessible name is actually exposed — ARIA forbids
            # naming a plain generic span, which left these cells silent.
            cells.append(
                f'<span class="cart-cell cart-b0 cart-quiet" style="{style}" '
                f'role="img" aria-label="{esc(label)}">'
                f'<span class="cart-cell__code" aria-hidden="true">{code}</span></span>'
            )
            rows.append(
                f"<tr><th scope='row'>{esc(name)}</th><td>0</td><td>—</td></tr>"
            )
    legend = (
        '<div class="cart-legend" aria-hidden="true"><span>Later</span>'
        '<i class="cart-b0"></i><i class="cart-b1"></i><i class="cart-b2"></i>'
        '<i class="cart-b3"></i><i class="cart-b4"></i><span>Voting soonest</span></div>'
    )
    # Wrapped in an sr-only DIV (not a bare sr-only table) so table auto-layout can't
    # expand past the viewport and cause horizontal scroll; still read by AT.
    table = (
        '<div class="sr-only"><table>'
        '<caption>Upcoming tracked elections by state</caption>'
        '<thead><tr><th scope="col">State</th><th scope="col">Upcoming</th>'
        '<th scope="col">Next date</th></tr></thead>'
        f'<tbody>{"".join(rows) or "<tr><td>No upcoming elections tracked yet.</td></tr>"}</tbody></table></div>'
    )
    cls = "cartogram cartogram--compact" if compact else "cartogram"
    return (
        '<figure class="cartogram-fig">'
        f'<div class="{cls}" role="group" '
        'aria-label="U.S. states by number of upcoming tracked elections; select a state to view it.">'
        f'{"".join(cells)}</div>{legend}{table}</figure>'
    )
