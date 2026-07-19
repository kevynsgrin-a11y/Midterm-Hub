"""Code-generated, hermetic vector art. No libraries, no external assets — every
mark is math emitted as inline SVG so it stays crisp at any resolution and adds
zero network requests."""
from __future__ import annotations

import math


def guilloche_svg(width: int = 760, height: int = 520, lines: int = 11) -> str:
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
        f'<svg class="hero__guilloche" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" aria-hidden="true" focusable="false" '
        f'preserveAspectRatio="xMidYMid slice">{"".join(polylines)}</svg>'
    )
