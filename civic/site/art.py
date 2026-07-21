"""Code-generated, hermetic vector art. No libraries, no external assets — every
mark is math emitted as inline SVG so it stays crisp at any resolution and adds
zero network requests."""
from __future__ import annotations

import math

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
    steps = 150
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
            pts.append(f"{x:.1f},{y:.1f}")
        polylines.append(
            f'<polyline points="{" ".join(pts)}" fill="none" '
            f'stroke="currentColor" stroke-width="0.6"/>'
        )
    return (
        f'<svg class="{cls}" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" aria-hidden="true" focusable="false" '
        f'preserveAspectRatio="xMidYMid slice">{"".join(polylines)}</svg>'
    )


def us_cartogram(cfg: SiteConfig, counts: dict[str, int], *, compact: bool = False) -> str:
    """A single-hue US tile-grid cartogram keyed to upcoming-election counts. States
    with tracked upcoming elections link to their hub; the rest render as honest
    quiet cells. Accessible: real links + per-cell labels + a table fallback."""
    max_count = max(counts.values(), default=0)
    cells = []
    rows = []  # for the visually-hidden table fallback
    for code, (r, c) in sorted(US_TILEGRID.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        n = counts.get(code, 0)
        if n == 0:
            bucket = 0
        else:
            frac = n / max_count if max_count else 0
            bucket = 1 + min(3, int(frac * 3.999))
        style = f"grid-row:{r + 1};grid-column:{c + 1}"
        name = STATE_NAMES.get(code, code)
        if n:
            label = f"{name}: {n} upcoming election{'s' if n != 1 else ''}"
            cells.append(
                f'<a class="cart-cell cart-b{bucket}" style="{style}" '
                f'href="{esc(rel(cfg, f"/states/{code}/"))}" aria-label="{esc(label)}">'
                f"{code}</a>"
            )
            rows.append(f"<tr><th scope='row'>{esc(name)}</th><td>{n}</td></tr>")
        else:
            label = f"{name}: no tracked elections yet"
            cells.append(
                f'<span class="cart-cell cart-b0 cart-quiet" style="{style}" '
                f'aria-label="{esc(label)}"><span aria-hidden="true">{code}</span></span>'
            )
    legend = (
        '<div class="cart-legend" aria-hidden="true"><span>Fewer</span>'
        '<i class="cart-b0"></i><i class="cart-b1"></i><i class="cart-b2"></i>'
        '<i class="cart-b3"></i><i class="cart-b4"></i><span>More upcoming</span></div>'
    )
    # Wrapped in an sr-only DIV (not a bare sr-only table) so table auto-layout can't
    # expand past the viewport and cause horizontal scroll; still read by AT.
    table = (
        '<div class="sr-only"><table>'
        '<caption>Upcoming tracked elections by state</caption>'
        '<thead><tr><th scope="col">State</th><th scope="col">Upcoming</th></tr></thead>'
        f'<tbody>{"".join(rows) or "<tr><td>No upcoming elections tracked yet.</td></tr>"}</tbody></table></div>'
    )
    cls = "cartogram cartogram--compact" if compact else "cartogram"
    return (
        '<figure class="cartogram-fig">'
        f'<div class="{cls}" role="group" '
        'aria-label="U.S. states by number of upcoming tracked elections; select a state to view it.">'
        f'{"".join(cells)}</div>{legend}{table}</figure>'
    )
