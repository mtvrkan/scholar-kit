#!/usr/bin/env python3
"""Render the Open Graph cards into ``web/public/og.png`` and ``og-en.png``.

Why a script and not a hand-drawn image: the card restates what the site says,
and that has to stay in step with the design. Regenerating is one command;
redrawing by hand is how a share card ends up advertising last year's palette —
which is exactly what happened to the version before last. It drew a warm-paper
document with an ink-teal accent, and the site had been black glass for three
redesigns.

Why two cards where there used to be one. The previous version reasoned that a
static site with one URL gets exactly one card, so the card had better carry
both languages — and it did, and the result was a thumbnail with a Turkish
headline, an English headline, a four-count strip, a nine-row pipeline panel and
two footer lines competing inside 1200x630 that most people see at a third of
that size. A share card is read in about a second. This one says one thing per
language: who it is and what it does.

The site still declares the Turkish card, because the site's first language is
Turkish and `og:locale` can only name one. The English card is not decoration
for it: `README.md` is an English document read by English readers and it
opens with this image, so the second card has a real home rather than being an
unused alternate.

Why a committed PNG and not an SVG: link unfurlers on Slack, X, LinkedIn and
iMessage do not rasterise SVG, and several drop the card entirely when the image
fails to decode. So the raster is the artefact and this file is its source.

Everything is drawn at 3x and resampled down. Pillow puts no antialiasing on
`arc` or on a diagonal edge, and the wordmark is four quarter-annuli thirty
pixels across — at 1x it came out as four chipped smudges, which is what a logo
looks like when it is drawn by a library that does not do curves at small sizes.
Supersampling is the whole fix and it costs a second.

Fonts come from the host system, which is acceptable precisely because the
output is committed: this runs on an author's machine, not in CI. The site's own
faces ship as WOFF2 and Pillow cannot read those, so the roles below name the
closest system stand-ins and the script SAYS when it had to fall back rather
than silently drawing the default bitmap font at display size.

    python web/make_og.py            # writes web/public/og.png and og-en.png
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - developer-facing tool
    sys.exit("Pillow is required: python -m pip install Pillow")

W, H = 1200, 630
SS = 3                                   # supersampling factor
PUBLIC = Path(__file__).resolve().parent / "public"

# ── the palette, transcribed from the stylesheet's dark theme ─────────────
# Role names match the CSS custom properties so a change there is a one-line
# change here rather than an exercise in matching hexes by eye.
PAPER = (0, 0, 0)              # --paper
RULE_2 = (34, 36, 43)          # --rule-2
INK = (255, 255, 255)          # --ink
INK_2 = (216, 216, 216)        # --ink-2
INK_3 = (154, 154, 154)        # --ink-3
GLOW = (34, 40, 72)            # the cold pool the page's ground carries

# Candidate faces per role, most-wanted first.
FACES = {
    # The site sets its display line in Inter; Segoe UI Semibold is the nearest
    # thing a Windows machine has, and Helvetica the nearest on a Mac.
    "display": ["segoeuisb.ttf", "segoeuib.ttf", "SFNSDisplay.ttf", "Helvetica.ttc",
                "arialbd.ttf", "DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    # The emphasised half of the headline is Instrument Serif italic on the
    # site. Georgia italic is a high-contrast serif italic that exists nearly
    # everywhere; it is not the same face and it is the same gesture.
    "accent": ["georgiai.ttf", "Georgia Italic.ttf", "Times New Roman Italic.ttf",
               "timesi.ttf", "DejaVuSerif-Italic.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"],
    "body": ["segoeui.ttf", "Helvetica.ttc", "Arial.ttf", "arial.ttf",
             "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/System/Library/Fonts"),
             Path("/Library/Fonts"), Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]

_missing: set[str] = set()

# ── the two cards, as data ────────────────────────────────────────────────
# Everything that differs between them is here, and the drawing below reads
# this and nothing else — which is what stops the second card from quietly
# becoming a different design from the first.
CARDS = {
    "og.png": {
        "h1": "Akademik çalışmanın",
        "h2": "tamamı",
        "accent": "Claude Code içinde",
        "lede": "Makale ve tezden proje önerisine, etik başvurusundan hakem raporuna.",
        "tail": "MIT lisansı",
    },
    "og-en.png": {
        "h1": "Every part of",
        "h2": "academic work",
        "accent": "inside Claude Code",
        "lede": "From papers and theses to grant proposals, ethics applications and referee reports.",
        "tail": "MIT licence",
    },
}


def font(role: str, size: int) -> ImageFont.FreeTypeFont:
    for name in FACES[role]:
        for candidate in ([Path(name)] if Path(name).is_absolute()
                          else [d / name for d in FONT_DIRS]):
            if candidate.exists():
                try:
                    return ImageFont.truetype(str(candidate), size)
                except OSError:
                    continue
    _missing.add(role)
    return ImageFont.load_default(size)


def fit(d: ImageDraw.ImageDraw, s: str, role: str, size: int, limit: int):
    """The largest size at or under `size` at which `s` fits in `limit` px.

    An earlier card ran its headline under the specimen panel and off the right
    edge — the one defect nobody sees until the link has already been shared,
    because the author is looking at the source and the reader is looking at a
    thumbnail. Fitting is cheap; checking by eye every time the copy changes is
    not.
    """
    for px in range(size, 12 * SS, -SS):
        f = font(role, px)
        if d.textlength(s, font=f) <= limit:
            if px < size:
                print(f"  note: '{s[:30]}…' set at {px // SS}px, not {size // SS}px, "
                      f"to fit {limit // SS}px")
            return f
    return font(role, 12 * SS)


def text(d: ImageDraw.ImageDraw, xy, s, f, fill, spacing: float = 0.0):
    """Draw a string, optionally letter-spaced. Returns the advance width."""
    if not spacing:
        d.text(xy, s, font=f, fill=fill)
        return d.textlength(s, font=f)
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + spacing
    return x - xy[0]


def width(d: ImageDraw.ImageDraw, s, f, spacing: float = 0.0) -> float:
    return d.textlength(s, font=f) + (len(s) * spacing if spacing else 0.0)


def mark(img: Image.Image, x: float, y: float, s: float, colour) -> None:
    """The wordmark's glyph, read off the path in `Base.astro` rather than
    guessed at.

    That path is four subpaths and each one is a QUARTER ANNULUS centred on a
    corner of the 256-unit box: an outer quarter-circle of radius 128 and an
    inner one of radius 64, closed. Two earlier versions got the geometry wrong
    in opposite directions — a square with quarter-discs punched out of it drew
    the negative of the mark, and a stroked arc of width 64 at radius 96 drew
    the right ring by the wrong means.

    Wrong means, because `arc` and `ellipse` are the two primitives Pillow does
    not antialias, and a stroked arc is drawn by stepping the radius: the ring
    comes out with a ragged outer edge and a thickness that visibly varies
    around the sweep. Supersampling the card by three hid none of it, because a
    31px mark is still only 93px at 3x — which is why the card shipped with four
    chipped commas where the site has four petals. What is drawn here instead is
    a MASK, four times larger again, in which each quarter is a filled
    `pieslice` of radius 128 with a `pieslice` of radius 64 punched back out of
    it — the annulus as an area rather than as a stroke, which Pillow fills
    cleanly — and the mask is resampled down before it is pasted. The edge
    quality comes from that resample, which is the only antialiasing available
    here and is enough.

    The four quarters occupy the four quadrants of the box exactly and never
    overlap, so punching one's inner disc cannot erase a neighbour.
    """
    OS = 4                                    # oversample, on top of the card's
    n = max(8, round(s * OS))
    m = Image.new("L", (n, n), 0)
    md = ImageDraw.Draw(m)
    u = n / 256.0
    for (cx, cy), (a0, a1) in (
            ((0, 0), (0, 90)),                # top-left corner, opening down-right
            ((256, 0), (90, 180)),            # top-right, opening down-left
            ((256, 256), (180, 270)),         # bottom-right, opening up-left
            ((0, 256), (270, 360))):          # bottom-left, opening up-right
        for radius, fill in ((128, 255), (64, 0)):
            r = radius * u
            md.pieslice([cx * u - r, cy * u - r, cx * u + r, cy * u + r],
                        a0, a1, fill=fill)
    side = max(1, round(s))
    m = m.resize((side, side), Image.LANCZOS)
    img.paste(Image.new("RGB", m.size, colour), (round(x), round(y)), m)


def ground(img: Image.Image) -> None:
    """The site's own ground: black, one cold pool of light, ruled paper."""
    d = ImageDraw.Draw(img)

    # The light source, painted as a coarse radial by hand — Pillow has no
    # gradient primitive and a per-pixel loop at 3600x1890 is slower than this
    # is worth. Concentric ellipses, blended toward the pool's colour.
    cx, cy = int(W * SS * 0.5), int(H * SS * 0.34)
    steps = 54
    for i in range(steps, 0, -1):
        rad = int(i * 20 * SS)
        k = (1 - i / float(steps)) ** 2
        col = tuple(round(PAPER[j] + (GLOW[j] - PAPER[j]) * k * 0.55) for j in range(3))
        d.ellipse([cx - rad * 1.7, cy - rad, cx + rad * 1.7, cy + rad], fill=col)

    # Ruled paper. Same 2.25rem rhythm as the page, at 16px to the rem, faded
    # out at the left and right margins the way the site's own mask does. Drawn
    # as full-width lines on a scratch layer and composited through a horizontal
    # ramp — one blend for the whole card instead of one per pixel.
    rule = Image.new("RGB", (W * SS, H * SS), (255, 255, 255))
    mask = Image.new("L", (W * SS, H * SS), 0)
    md = ImageDraw.Draw(mask)
    edge = W * SS * 0.14
    for x in range(0, W * SS, 4 * SS):
        a = min(x / edge, (W * SS - x) / edge, 1.0)
        md.rectangle([x, 0, x + 4 * SS, H * SS], fill=int(22 * a))
    lines = Image.new("L", (W * SS, H * SS), 0)
    ld = ImageDraw.Draw(lines)
    for y in range(0, H * SS, 36 * SS):
        ld.rectangle([0, y, W * SS, y + SS - 1], fill=255)
    mask = Image.composite(mask, Image.new("L", mask.size, 0), lines)
    img.paste(Image.composite(rule, img, mask), (0, 0))


def draw_card(name: str, spec: dict) -> Path:
    img = Image.new("RGB", (W * SS, H * SS), PAPER)
    ground(img)
    d = ImageDraw.Draw(img)

    def px(v: float) -> float:
        return v * SS

    centre = px(W / 2)
    inner = px(W - 2 * 96)          # the text column: 96px margins

    # ── identity, centred ──────────────────────────────────────────────────
    f_brand = font("display", int(px(40)))
    ms, gap = px(44), px(19)
    label_w = (width(d, "Scholar", f_brand) + px(5)
               + width(d, "·", f_brand) + px(8)
               + width(d, "Kit", f_brand))
    x = centre - (ms + gap + label_w) / 2
    brand_y = px(131)
    # The mark is centred on the wordmark's INK, measured here rather than
    # derived from the face's nominal ascent and cap height. Those are an
    # estimate that differs per fallback face, and estimating put the glyph
    # visibly high: the letters occupy cap-top to baseline, while the mark's
    # own ink fills its whole square, so the two centres are not the same
    # distance from `brand_y` and cannot be placed with one number.
    ink_top, ink_bottom = d.textbbox((0, brand_y), "ScholarKit", font=f_brand)[1::2]
    mark(img, x, (ink_top + ink_bottom) / 2 - ms / 2, ms, INK)
    x += ms + gap
    x += text(d, (x, brand_y), "Scholar", f_brand, INK) + px(5)
    x += text(d, (x, brand_y), "·", f_brand, INK_3) + px(8)
    text(d, (x, brand_y), "Kit", f_brand, INK)

    # ── headline ───────────────────────────────────────────────────────────
    # Two display lines and one accent line, each centred and each sized to fit
    # rather than trusted to.
    y = px(233)
    for line in (spec["h1"], spec["h2"]):
        f = fit(d, line, "display", int(px(60)), inner)
        d.text((centre - d.textlength(line, font=f) / 2, y), line, font=f, fill=INK)
        y += px(70)

    f_acc = fit(d, spec["accent"], "accent", int(px(62)), inner)
    d.text((centre - d.textlength(spec["accent"], font=f_acc) / 2, y - px(6)),
           spec["accent"], font=f_acc, fill=INK_3)

    # ── one sentence ───────────────────────────────────────────────────────
    # The card used to end in the same four figures the page opens with: 43
    # commands, 68 tools, 2415 tests, 0 fabricated entries. Three of the four
    # are inventory, and inventory is what a reader checks AFTER deciding to
    # look — it does not belong in the second that a thumbnail gets. They also
    # made the card two documents, an identity above and a spec sheet below,
    # which is why the headline had been squeezed into the top half to make
    # room. One card, one claim; the counts are on the page and in both READMEs,
    # each derived from the repository by a test rather than typed.
    f_lede = fit(d, spec["lede"], "body", int(px(21)), inner)
    d.text((centre - d.textlength(spec["lede"], font=f_lede) / 2, px(449)),
           spec["lede"], font=f_lede, fill=INK_2)

    # ── footer ─────────────────────────────────────────────────────────────
    d.line([px(96), px(H - 58), px(W - 96), px(H - 58)], fill=RULE_2, width=SS)
    f_f = font("body", int(px(13)))
    text(d, (px(96), px(H - 40)), "SCHOLAR.MTVRKAN.COM", f_f, INK_3, spacing=px(2))
    tail = spec["tail"].upper()
    text(d, (px(W - 96) - width(d, tail, f_f, px(2)), px(H - 40)), tail, f_f, INK_3,
         spacing=px(2))

    out = PUBLIC / name
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W, H), Image.LANCZOS).save(out, "PNG", optimize=True)
    return out


def main() -> int:
    for name, spec in CARDS.items():
        print(f"{name}:")
        out = draw_card(name, spec)
        print(f"  wrote {out} ({out.stat().st_size // 1024} KB, {W}x{H})")

    if _missing:
        print(f"warning: no system face found for {sorted(_missing)} — "
              f"the cards fell back to a default font and will not match the site")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
