"""«أُلَوِّنُ حُروفي»: the 28 letter pages (content/coloring/letters.yaml).

Each page is the big letter as line art (`glyphs.letter`), its name, and 2–3 pictures from the code-drawn
picture library in their line-art version, redrawn here with the coloring books' bold black outline.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from qamra_workbook.coloring.glyphs import letter
from qamra_workbook.coloring.ink import INK, MAIN, Pen, fmt, svg
from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import LINE_STROKE, OUTLINE, STROKE

REPO = Path(__file__).resolve().parents[5]
CONTENT = REPO / "content" / "coloring" / "letters.yaml"
PICTURE_LINE_MM = 2.2  # the pictures' outline on paper (a 56 mm picture keeps its details open)


@dataclass(frozen=True)
class Shown:
    picture: str
    word_ar: str


@dataclass(frozen=True)
class LetterPage:
    char: str
    name_ar: str
    name_en: str
    pictures: tuple[Shown, ...]

    @property
    def id(self) -> str:
        return f"letter-{ord(self.char):04x}"


@dataclass(frozen=True)
class LettersBook:
    title_ar: str
    title_en: str
    letters: tuple[LetterPage, ...]


def _shown(entry: str) -> Shown:
    pid, _, word = entry.partition("|")
    return Shown(pid, word or picture(pid).word_ar)


@functools.cache
def load(path: Path = CONTENT) -> LettersBook:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    pages = tuple(
        LetterPage(x["char"], x["name_ar"], x["name_en"], tuple(_shown(str(s)) for s in x["pictures"]))
        for x in raw["letters"]
    )
    return LettersBook(raw["title_ar"], raw["title_en"], pages)


_WIDTH = re.compile(r'stroke-width="([0-9.]+)"')


def picture_svg(
    picture_id: str, size_mm: float, *, mode: str = "line", line_mm: float = PICTURE_LINE_MM
) -> str:
    """A library picture `size_mm` wide as coloring line art: white areas, pure black outlines of
    `PICTURE_LINE_MM` on paper (the library's own widths are for a 40 mm picture). In `color` mode the
    picture keeps its colours (covers, previews) with the same black outline."""
    pic = picture(picture_id)
    style = "line" if mode == "line" else "color"
    inner = pic.inner(style)  # type: ignore[arg-type]
    units = line_mm / (size_mm / 100)
    base = LINE_STROKE if style == "line" else STROKE
    inner = _WIDTH.sub(lambda m: f'stroke-width="{fmt(float(m.group(1)) / base * units)}"', inner)
    inner = inner.replace(OUTLINE, INK)
    return (
        f'<svg class="cb-pic" viewBox="-4 -4 108 108" width="{fmt(size_mm * 1.08)}mm" '
        f'height="{fmt(size_mm * 1.08)}mm" aria-hidden="true">{inner}</svg>'
    )


def letter_panel(char: str, w: float = 186.0, h: float = 140.0, *, mode: str = "line") -> str:
    """The letter as tall as `h` allows (at most 150 mm wide), centred, with four small stars to colour in
    the side margins."""
    from qamra_workbook.coloring.ink import GOLD, rounded_star

    probe = letter(char, 100.0)
    height = min(h - 12, 150.0 * probe.h / probe.w)
    g = letter(char, height)
    pen = Pen(mode="line" if mode == "line" else "color")
    width = MAIN + 0.4
    x, y = (w - g.w) / 2, (h - g.h) / 2
    under = (
        f'<path d="{g.d}" fill="{INK}" stroke="{INK}" stroke-width="{fmt(2 * width)}" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
    )
    paint = pen.paint("#FFFFFF")
    body = f'<g transform="translate({fmt(x)} {fmt(y)})">{under}<path d="{g.d}" fill="{paint}"/></g>'
    side = max(x - 24, x / 2)  # near a narrow letter, in the margin beside a wide one
    stars = [
        (side, h * 0.16, 6.5),
        (w - side, h * 0.28, 5.5),
        (side + 1, h * 0.78, 5.0),
        (w - side - 1, h * 0.86, 6.5),
    ]
    if x >= 9:
        body += pen.shape(*(rounded_star(sx, sy, r) for sx, sy, r in stars), fill=GOLD)
    return svg(w, h, body, css_class="cb-letter", pad=width + 1)


def letter_svg(char: str, height_mm: float, *, mode: str = "line", fill: str = "#FFFFFF") -> str:
    """The big letter: white inside (or `fill` in colour), a bold black outline around the letter's outer
    edge only. The font draws some letters from overlapping contours (the loop of «ط», the tail of «و»): a
    stroke on the path would draw their seams too, so the outline is a twice-as-wide stroke under the
    filled letter, whose fill hides the inner half and every seam."""
    g = letter(char, height_mm)
    pen = Pen(mode="line" if mode == "line" else "color")
    width = MAIN + 0.4
    under = (
        f'<path d="{g.d}" fill="{INK}" stroke="{INK}" stroke-width="{fmt(2 * width)}" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
    )
    body = under + f'<path d="{g.d}" fill="{pen.paint(fill)}"/>'
    return svg(g.w, g.h, body, css_class="cb-letter", pad=width + 1)
