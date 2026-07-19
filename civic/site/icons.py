"""Inline SVG icons and marks. All decorative icons are aria-hidden/focusable=false;
meaningful marks carry role/title. System-hermetic — no external assets."""
from __future__ import annotations

# The Plumb Bob wordmark mark (anchor bar + plumb line + filled bob).
LOGO_MARK = (
    "<svg class='pl-mark' width='20' height='20' viewBox='0 0 20 20' "
    "aria-hidden='true' focusable='false'>"
    "<line x1='4.5' y1='2' x2='15.5' y2='2' stroke='currentColor' "
    "stroke-width='1.5' stroke-linecap='round'/>"
    "<line x1='10' y1='2.75' x2='10' y2='11' stroke='currentColor' stroke-width='1.5'/>"
    "<path d='M10 10.5 L13 14 L10 18 L7 14 Z' fill='var(--primary)' "
    "stroke='var(--primary)' stroke-width='0.5' stroke-linejoin='round'/>"
    "</svg>"
)


def _svg(body: str, size: int = 16, extra: str = "") -> str:
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' "
        f"stroke='currentColor' stroke-width='1.75' stroke-linecap='round' "
        f"stroke-linejoin='round' aria-hidden='true' focusable='false'{extra}>{body}</svg>"
    )


# Deadline glyphs keyed by Deadline.key.
DEADLINE_ICONS = {
    "candidate_filing_deadline": _svg(
        "<path d='M4 21V4a1 1 0 0 1 1-1h9l2 3h4v9H8'/><path d='M4 21h5'/>", 14
    ),  # flag
    "registration_deadline": _svg(
        "<path d='M12 20h9'/><path d='M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z'/>", 14
    ),  # pencil
    "mail_ballot_request_deadline": _svg(
        "<rect x='3' y='5' width='18' height='14' rx='1'/><path d='m3 7 9 6 9-6'/>", 14
    ),  # envelope
    "early_voting_start": _svg(
        "<rect x='3' y='4' width='18' height='17' rx='2'/><path d='M16 2v4M8 2v4M3 10h18'/>"
        "<path d='m9 15 2 2 4-4'/>", 14
    ),  # calendar-check
    "early_voting_end": _svg(
        "<rect x='3' y='4' width='18' height='17' rx='2'/><path d='M16 2v4M8 2v4M3 10h18'/>"
        "<path d='m10 14 4 4M14 14l-4 4'/>", 14
    ),  # calendar-x
}

# Sun / moon for the theme toggle.
ICON_SUN = _svg(
    "<circle cx='12' cy='12' r='4'/>"
    "<path d='M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2"
    "M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4'/>",
    18, extra=" class='icon icon-sun'",
)
ICON_MOON = _svg(
    "<path d='M12 3a6.4 6.4 0 0 0 9 9 9 9 0 1 1-9-9Z'/>",
    18, extra=" class='icon icon-moon'",
)

# Small up-right arrow for external source links.
ICON_EXTERNAL = _svg("<path d='M7 17 17 7M8 7h9v9'/>", 12, extra=" class='icon-ext'")

ICON_CALENDAR = _svg(
    "<rect x='3' y='4' width='18' height='17' rx='2'/><path d='M16 2v4M8 2v4M3 10h18'/>",
    16,
)
ICON_DOWNLOAD = _svg("<path d='M12 3v12m0 0 4-4m-4 4-4-4M5 21h14'/>", 16)


def confidence_meter(level: str) -> str:
    """Three rising bars; `level` fills 3/2/1 for official/secondary/inferred."""
    filled = {"official": 3, "secondary": 2, "inferred": 1}.get(level, 1)
    heights = [(6, 6), (9, 3), (12, 0)]  # (height, y-top) for x = 0,5,10
    bars = []
    for i, (h, y) in enumerate(heights):
        op = "1" if i < filled else "0.28"
        bars.append(
            f"<rect x='{i * 5}' y='{y}' width='3' height='{h}' rx='0.5' "
            f"fill='currentColor' fill-opacity='{op}'/>"
        )
    return (
        "<svg class='confidence-meter' width='14' height='12' viewBox='0 0 13 12' "
        "aria-hidden='true' focusable='false'>" + "".join(bars) + "</svg>"
    )


FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20'>"
    "<style>path{fill:#1B4079}line{stroke:#1A1A17}"
    "@media (prefers-color-scheme:dark){path{fill:#8CB2E0}line{stroke:#F2EFE8}}</style>"
    "<line x1='10' y1='2.75' x2='10' y2='11' stroke-width='1.5'/>"
    "<path d='M10 10.5 L13 14 L10 18 L7 14 Z'/>"
    "</svg>"
)
