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
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Civic-blue left rail + brass hairline.
    d.rectangle([0, 0, 14, H], fill=PRIMARY)
    d.rectangle([14, 0, 17, H], fill=BRASS)
    # Plumb-bob mark + wordmark, top-left.
    ax = 74
    d.line([ax, 60, ax, 104], fill=INK, width=4)
    d.polygon([(ax, 100), (ax + 13, 122), (ax, 152), (ax - 13, 122)], fill=BRASS)
    from PIL import ImageFont

    wm = ImageFont.truetype(fonts["serif"], 40)
    d.text((ax + 34, 84), "Plumbline", font=wm, fill=INK)
    # Bottom rule + domain.
    d.line([64, H - 92, W - 64, H - 92], fill=BORDER, width=2)
    dom = ImageFont.truetype(fonts["mono"], 26)
    d.text((64, H - 74), "midtermwatch.com", font=dom, fill=MUTED)
    return img, d


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
    d.text((64, 210), "U.S. OFF-CYCLE & LOCAL ELECTIONS", font=eyebrow, fill=BRASS_INK)
    title = ImageFont.truetype(fonts["serif"], 76)
    for i, line in enumerate(["Know when your next", "election really is."]):
        d.text((64, 250 + i * 86), line, font=title, fill=INK)
    sub = ImageFont.truetype(fonts["sans"], 30)
    d.text((64, 430), "Verified dates and deadlines — every one sourced,", font=sub, fill=MUTED)
    d.text((64, 470), "confidence-rated, and human-verified.", font=sub, fill=MUTED)
    if demo:
        _demo_chip(d, fonts)
    return _save(img, out_dir, "/og/default.png")


def _election_card(e: ElectionView, fonts, out_dir, demo) -> str:
    from PIL import ImageFont

    img, d = _base(fonts)
    eyebrow = ImageFont.truetype(fonts["sans_b"], 26)
    d.text((64, 196), f"{e.state_name.upper()} · {e.jurisdiction_type_label.upper()}",
           font=eyebrow, fill=BRASS_INK)
    date_f = ImageFont.truetype(fonts["serif"], 60)
    d.text((64, 232), e.date_short, font=date_f, fill=PRIMARY)
    name_f = ImageFont.truetype(fonts["serif"], 64)
    lines = _wrap(d, e.jurisdiction_name, name_f, W - 128)[:2]
    for i, line in enumerate(lines):
        d.text((64, 312 + i * 72), line, font=name_f, fill=INK)
    ty = 312 + len(lines) * 72 + 6
    type_f = ImageFont.truetype(fonts["sans"], 32)
    d.text((64, ty), f"{e.election_type_label} election", font=type_f, fill=MUTED)
    # Confidence chip.
    label = {"official": "OFFICIAL SOURCE", "secondary": "SECONDARY SOURCE",
             "inferred": "INFERRED"}.get(e.confidence, e.confidence.upper())
    fg = OFFICIAL if e.confidence == "official" else BRASS_INK
    _chip(d, 64, H - 150, label, fonts, fg, SURFACE, BORDER)
    if demo:
        _demo_chip(d, fonts)
    return _save(img, out_dir, f"/og/{e.state}/{e.jurisdiction_slug}/{e.id}.png")


def generate(site: SiteData, out_dir: Path, demo: bool = False) -> dict:
    """Generate all OG cards. Returns {'default': path|None, 'elections': {id: path}}.
    Empty/None entries mean 'omit og:image' for that page."""
    fonts = _fonts()
    if fonts is None:
        return {"default": None, "elections": {}}
    result: dict = {"elections": {}}
    try:
        result["default"] = _default_card(fonts, out_dir, demo)
    except Exception:
        result["default"] = None
    for e in site.elections:
        try:
            result["elections"][e.id] = _election_card(e, fonts, out_dir, demo)
        except Exception:
            pass
    return result
