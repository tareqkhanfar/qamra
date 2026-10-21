"""A letter as a drawing: the isolated form of an Arabic letter from the display font, as an SVG path in mm.

The coloring books print the big letter as line art (white inside, a 2.6 mm black outline), so the child
colours the letter itself. A path, not text: the outline is a stroke, which Chromium would print as a Type 3
font on text (render/covers.py), and the letter must take part in the drawing's line-art checks.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from qamra_pdf.render import FONTS_DIR

FONT = FONTS_DIR / "QamraDisplay-ExtraBold.ttf"
# a letter shown in another of its forms: the display font's isolated «ه» is a plain ring that reads as the
# digit «٥»; children's alphabets show it as «هـ» (its initial form)
SHAPES = {"ه": "heh.ar.init"}


@dataclass(frozen=True)
class Glyph:
    d: str  # path data in mm, the glyph's ink box at (0, 0)
    w: float
    h: float


@functools.cache
def _font() -> TTFont:
    return TTFont(str(FONT))


def letter(char: str, height_mm: float) -> Glyph:
    """The isolated letter `char`, its ink `height_mm` tall (dots included), y downward, top-left at 0, 0."""
    font = _font()
    cmap = font.getBestCmap()
    name = SHAPES.get(char) or cmap.get(ord(char))
    if name is None:
        raise KeyError(f"{FONT.name} has no glyph for {char!r}")
    glyphs = font.getGlyphSet()
    bounds = BoundsPen(glyphs)
    glyphs[name].draw(bounds)
    if bounds.bounds is None:
        raise ValueError(f"{char!r} has no outline")
    x0, y0, x1, y1 = bounds.bounds
    k = height_mm / (y1 - y0)
    svg_pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    # font units (y up) → mm (y down), the ink box's top-left at the origin
    glyphs[name].draw(TransformPen(svg_pen, (k, 0, 0, -k, -x0 * k, y1 * k)))
    return Glyph(svg_pen.getCommands(), (x1 - x0) * k, height_mm)
