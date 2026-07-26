"""Build-time Open Graph share cards — 1200x630 PNGs rendered with Pillow.

These are the ONE surface with baked-in text (social crawlers can't read the live
DOM), so they are fixed-light-theme and high-contrast. Generation is best-effort:
if Pillow or the fonts are unavailable, we return an empty map and the pages simply
omit og:image (the SEO layer already treats that as a valid fallback)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .data import ElectionView, SiteData

W, H = 1200, 630
BG = (245, 243, 236)
INK = (26, 26, 23)
MUTED = (90, 87, 79)
PRIMARY = (27, 64, 121)
BRASS = (176, 125, 43)
BRASS_INK = (122, 85, 24)
SURFACE = (255, 255, 255)
BORDER = (203, 197, 182)
OFFICIAL = (36, 91, 65)

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
    "/Library/Fonts",
]


def _font_path(name: str) -> Optional[str]:
    for d in _FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def _fonts():
    """Return a loader dict or None if OG generation isn't possible."""
    import importlib.util

    if importlib.util.find_spec("PIL") is None:
        return None
    serif = _font_path("DejaVuSerif-Bold.ttf")
    sans = _font_path("DejaVuSans.ttf")
    sans_b = _font_path("DejaVuSans-Bold.ttf")
    mono = _font_path("DejaVuSansMono.ttf")
    if not (serif and sans and mono):
        return None
    return {"serif": serif, "sans": sans, "sans_b": sans_b or sans, "mono": mono}


def available() -> bool:
    return _fonts() is not None


def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _base(fonts):
    """Masthead band only. The domain moves up beside the wordmark so the whole
    lower strip is free for real content — the previous layout spent the bottom
    92px on a rule and a URL while the right half of the canvas sat empty."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Civic-blue left rail + brass hairline.
    d.rectangle([0, 0, 14, H], fill=PRIMARY)
    d.rectangle([14, 0, 17, H], fill=BRASS)
    # Plumb-bob mark + wordmark, top-left.
    ax = 64
    d.line([ax, 48, ax, 84], fill=INK, width=4)
    d.polygon([(ax, 80), (ax + 11, 98), (ax, 122), (ax - 11, 98)], fill=BRASS)
    wm = ImageFont.truetype(fonts["serif"], 34)
    d.text((ax + 34, 66), "Plumbline", font=wm, fill=INK)
    dom = ImageFont.truetype(fonts["mono"], 22)
    dw = d.textlength("midtermwatch.com", font=dom)
    d.text((W - 64 - dw, 74), "midtermwatch.com", font=dom, fill=MUTED)
    d.line([64, 132, W - 64, 132], fill=BORDER, width=2)
    return img, d


def _ellipsize(d, text, font, max_w):
    if d.textlength(text, font=font) <= max_w:
        return text
    while text and d.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def _wrap_limited(d, text, font, max_w, max_lines):
    """Wrap, and mark the truncation instead of dropping it silently."""
    lines = _wrap(d, text, font, max_w)
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    kept[-1] = _ellipsize(d, kept[-1] + " " + lines[max_lines].split()[0], font, max_w)
    return kept


def _date_plaque(d, e, fonts):
    """The fix for the empty right half: a date plaque mirroring the site's own
    date-block component, anchored by a 150px day numeral that stays legible at
    iMessage thumbnail size."""
    from PIL import ImageFont

    x0, y0, x1, y1 = 740, 150, 1136, 470
    cx = (x0 + x1) // 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=SURFACE, outline=BORDER, width=2)
    # Header band with square bottom corners.
    d.rounded_rectangle([x0, y0, x1, y0 + 64], radius=8, fill=PRIMARY)
    d.rectangle([x0, y0 + 46, x1, y0 + 64], fill=PRIMARY)
    kind = {"general": "ELECTION DAY", "primary": "PRIMARY DAY",
            "runoff": "RUNOFF DAY"}.get(e.election_type, "ELECTION DAY")
    f_kind = ImageFont.truetype(fonts["sans_b"], 24)
    d.text((cx - d.textlength(kind, font=f_kind) / 2, y0 + 20), kind, font=f_kind,
           fill=(255, 255, 255))
    mon = e.election_date.strftime("%b").upper()
    f_mon = ImageFont.truetype(fonts["sans_b"], 42)
    d.text((cx - d.textlength(mon, font=f_mon) / 2, 244), mon, font=f_mon, fill=BRASS_INK)
    day = str(e.election_date.day)
    f_day = ImageFont.truetype(fonts["serif"], 150)
    d.text((cx - d.textlength(day, font=f_day) / 2, 274), day, font=f_day, fill=INK)
    dow = e.election_date.strftime("%A").upper()
    f_dow = ImageFont.truetype(fonts["sans_b"], 26)
    d.text((cx - d.textlength(dow, font=f_dow) / 2, 418), dow, font=f_dow, fill=MUTED)


def _chip(d, x, y, text, fonts, fg, bg, border):
    from PIL import ImageFont

    f = ImageFont.truetype(fonts["sans_b"], 24)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 28, y + 40], radius=4, fill=bg, outline=border, width=2)
    d.text((x + 14, y + 7), text, font=f, fill=fg)
    return x + tw + 28


def _demo_chip(d, fonts):
    _chip(d, W - 250, H - 78, "SAMPLE DATA", fonts, (122, 85, 24), (243, 232, 206), BRASS)


def _save(img, out_dir: Path, rel_path: str) -> str:
    dest = out_dir / rel_path.lstrip("/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)
    return rel_path


def _default_card(fonts, out_dir, demo) -> str:
    from PIL import ImageFont

    img, d = _base(fonts)
    eyebrow = ImageFont.truetype(fonts["sans_b"], 26)
    d.text((64, 186), "2026 MIDTERMS · 50 STATES + DC", font=eyebrow, fill=BRASS_INK)
    title = ImageFont.truetype(fonts["serif"], 72)
    for i, line in enumerate(["Your next election,", "and every deadline", "before it."]):
        d.text((64, 226 + i * 82), line, font=title, fill=INK)
    sub = ImageFont.truetype(fonts["sans"], 28)
    d.text((64, 490), "Every date links to the election office it came from.",
           font=sub, fill=MUTED)
    if demo:
        _demo_chip(d, fonts)
    return _save(img, out_dir, "/og/default.png")


def _election_card(e: ElectionView, fonts, out_dir, demo) -> str:
    """Two columns: editorial left, date plaque right, deadline chips beneath.

    Every one of these carried the same layout with swapped text and a blank
    right half — 90% of the pixels were identical across all 74 cards, and the
    registration deadline, the early-voting window, and the offices on the ballot
    appeared nowhere.
    """
    from PIL import ImageFont

    img, d = _base(fonts)
    eyebrow = ImageFont.truetype(fonts["sans_b"], 26)
    d.text((64, 168), f"{e.state_name.upper()} · {e.jurisdiction_type_label.upper()}",
           font=eyebrow, fill=BRASS_INK)
    name_f = ImageFont.truetype(fonts["serif"], 68)
    lines = _wrap_limited(d, e.jurisdiction_name, name_f, 636, 2)
    for i, line in enumerate(lines):
        d.text((64, 206 + i * 76), line, font=name_f, fill=INK)
    ty = 206 + len(lines) * 76 + 14
    type_f = ImageFont.truetype(fonts["sans"], 30)
    d.text((64, ty), f"{e.election_type_label} Election · 2026", font=type_f, fill=MUTED)

    _date_plaque(d, e, fonts)

    # Deadline strip — the product value, previously absent entirely.
    x = 64
    reg = next((dl for dl in e.deadlines if dl.key == "registration_deadline"), None)
    ev = next((dl for dl in e.deadlines if dl.key == "early_voting_start"), None)
    chips = []
    if reg:
        chips.append((f"REGISTER BY {reg.formatted.upper()}", BRASS_INK, SURFACE, BRASS))
    if ev:
        chips.append((f"EARLY VOTING FROM {ev.formatted.upper()}", MUTED, SURFACE, BORDER))
    f_chip = ImageFont.truetype(fonts["sans_b"], 22)
    for text, fg, bg, border in chips:
        w = d.textlength(text, font=f_chip) + 32
        if x + w > 1136:
            break
        d.rounded_rectangle([x, 500, x + w, 544], radius=4, fill=bg, outline=border, width=2)
        d.text((x + 16, 510), text, font=f_chip, fill=fg)
        x += w + 12

    # Footer: what's on the ballot, and when a person last checked it.
    d.line([64, 570, W - 64, 570], fill=BORDER, width=2)
    f_foot = ImageFont.truetype(fonts["sans"], 20)
    if e.offices_summary:
        d.text((64, 582), _ellipsize(d, f"ON THE BALLOT: {e.offices_summary.upper()}",
                                     f_foot, 560), font=f_foot, fill=MUTED)
    # The trust signal goes here rather than in the chip row, where it was the
    # third chip and got dropped whenever both deadline chips fit.
    label = {"official": "OFFICIAL SOURCE", "secondary": "SECONDARY SOURCE",
             "inferred": "PROVISIONAL"}.get(e.confidence, e.confidence.upper())
    f_mono = ImageFont.truetype(fonts["mono"], 20)
    vt = f"{label} · VERIFIED {e.verified_at[:10]}" if e.verified_at else label
    d.text((W - 64 - d.textlength(vt, font=f_mono), 582), vt, font=f_mono,
           fill=OFFICIAL if e.confidence == "official" else BRASS_INK)
    if demo:
        _demo_chip(d, fonts)
    return _save(img, out_dir, f"/og/{e.state}/{e.jurisdiction_slug}/{e.id}.png")


def _state_card(s, fonts, out_dir, demo) -> str:
    """A card per state hub. Without these, all 51 state pages — the natural unit
    to share ("here's the Texas calendar") — unfurled with the same generic image."""
    from PIL import ImageFont

    img, d = _base(fonts)
    eyebrow = ImageFont.truetype(fonts["sans_b"], 26)
    d.text((64, 168), "2026 ELECTION CALENDAR", font=eyebrow, fill=BRASS_INK)
    name_f = ImageFont.truetype(fonts["serif"], 68)
    lines = _wrap_limited(d, s.name, name_f, 636, 2)
    for i, line in enumerate(lines):
        d.text((64, 206 + i * 76), line, font=name_f, fill=INK)
    ty = 206 + len(lines) * 76 + 14
    n = len(s.upcoming)
    sub = "One election left" if n == 1 else f"{n} elections left"
    type_f = ImageFont.truetype(fonts["sans"], 30)
    d.text((64, ty), f"{sub} · every deadline before each", font=type_f, fill=MUTED)

    ne = s.next_election
    if ne:
        _date_plaque(d, ne, fonts)
        f_chip = ImageFont.truetype(fonts["sans_b"], 22)
        reg = next((dl for dl in ne.deadlines if dl.key == "registration_deadline"), None)
        x = 64
        if reg:
            t = f"REGISTER BY {reg.formatted.upper()}"
            w = d.textlength(t, font=f_chip) + 32
            d.rounded_rectangle([x, 500, x + w, 544], radius=4, fill=SURFACE,
                                outline=BRASS, width=2)
            d.text((x + 16, 510), t, font=f_chip, fill=BRASS_INK)
            x += w + 12
        t = "OFFICIAL SOURCES"
        w = d.textlength(t, font=f_chip) + 32
        if x + w <= 1136:
            d.rounded_rectangle([x, 500, x + w, 544], radius=4, fill=SURFACE,
                                outline=BORDER, width=2)
            d.text((x + 16, 510), t, font=f_chip, fill=OFFICIAL)

    d.line([64, 570, W - 64, 570], fill=BORDER, width=2)
    f_foot = ImageFont.truetype(fonts["sans"], 20)
    d.text((64, 582), "EVERY DATE LINKS TO THE ELECTION OFFICE IT CAME FROM",
           font=f_foot, fill=MUTED)
    if demo:
        _demo_chip(d, fonts)
    return _save(img, out_dir, f"/og/state/{s.code}.png")


def generate(site: SiteData, out_dir: Path, demo: bool = False) -> dict:
    """Generate all OG cards. Returns {'default': path|None, 'elections': {id: path},
    'states': {code: path}}. Empty/None entries mean 'omit og:image' for that page."""
    fonts = _fonts()
    if fonts is None:
        return {"default": None, "elections": {}, "states": {}}
    result: dict = {"elections": {}, "states": {}}
    try:
        result["default"] = _default_card(fonts, out_dir, demo)
    except Exception:
        result["default"] = None
    for e in site.elections:
        try:
            result["elections"][e.id] = _election_card(e, fonts, out_dir, demo)
        except Exception:
            pass
    for s in site.states:
        try:
            result["states"][s.code] = _state_card(s, fonts, out_dir, demo)
        except Exception:
            pass
    return result
