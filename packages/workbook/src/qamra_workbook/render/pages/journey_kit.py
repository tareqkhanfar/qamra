"""Drawing shared by the journey's stage pages (Addendum 6 §5).

Like the دوسية's pages, a work area is one SVG in mm (`W` × `H`, class wb, scaled under the header). Answers
are drawn as `key-line` / `key-ring` marks that only the answer key shows. Shadows are silhouettes of the same
drawings, and missing parts and pieces are programmatic cuts and crops of the library pictures (§5: never
an AI image), so every answer is exact.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from qamra_workbook.pictures import PICTURES, Picture
from qamra_workbook.pictures.model import STROKE
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_common import H, W, answer_line, card, hook, picture_id, svg, text
from qamra_workbook.render.people import Drawing, Mark, place

__all__ = ["H", "W", "card", "svg", "text"]

DARK = "#4A4F6A"  # silhouettes: dark, never solid black ink over a big area
SOFT = "#FFF6F2"
INK = "#1C2140"
GOLD, GOLD_EDGE = "#F7C84A", "#D69A1E"
_TAG = re.compile(r"<[^<>]+/>")


def pid(word: str) -> str:
    """A picture id from a print-layer word: an id (`apple`) or an Arabic word."""
    return str(picture_id(word))


def nested(inner: str, x: float, y: float, size: float, box: str = "0 0 100 100", clip: bool = False) -> str:
    attrs = {"style": "overflow: hidden"} if clip else {}
    return draw.el("svg", inner, x=x, y=y, width=size, height=size, viewBox=box, **attrs)


def picture(word: str, x: float, y: float, size: float, style: str = "color", **colors: str) -> str:
    """A library picture in a size × size box; `colors` repaint its palette keys (a red bow, a blue car)."""
    p = PICTURES[pid(word)]
    return nested(p.inner("line" if style == "line" else "color", colors or None), x, y, size)


def silhouette(word: str, x: float, y: float, size: float, color: str = DARK) -> str:
    """The picture's shadow: its bodies and lines in one dark colour, without eyes or highlights."""
    p, out = PICTURES[pid(word)], []
    for part in p.parts:
        if part.role in ("body", "ink"):
            out.append(f'<g fill="{color}" stroke="{color}" stroke-width="{STROKE}" stroke-linejoin="round">')
        elif part.role == "line":
            out.append(f'<g fill="none" stroke="{color}" stroke-width="{STROKE}" stroke-linecap="round">')
        else:
            continue
        out.append(part.elements + "</g>")
    return nested("".join(out), x, y, size)


def person(figure: Drawing, x: float, y_feet: float, height: float, *, shadow: bool = False) -> str:
    """A people.py figure standing on y_feet, or its shadow."""
    if shadow:
        figure = Drawing(tuple(Mark(m.d, DARK, m.width) for m in figure.marks), "")
    return place(figure, x, y_feet, height, 0.0 if shadow else 1.1)


@dataclass(frozen=True)
class Cut:
    """A part of a library picture: elements `(part index, element index or None for all)` and the crop box
    (x, y, w, h in the picture's 100-unit box) that frames it."""

    picture: str
    elements: tuple[tuple[int, int | None], ...]
    box: tuple[float, float, float, float]
    word: str  # the part's name, for the answer key

    def _split(self) -> tuple[Picture, Picture]:
        p = PICTURES[self.picture]
        kept, cut = [], []
        for i, part in enumerate(p.parts):
            tags = _TAG.findall(part.elements)
            chosen = {k for j, k in self.elements if j == i}
            gone = [t for k, t in enumerate(tags) if None in chosen or k in chosen]
            left = [t for t in tags if t not in gone]
            if left:
                kept.append(type(part)(part.role, part.fill, "".join(left)))
            if gone:
                cut.append(type(part)(part.role, part.fill, "".join(gone)))
        return (
            Picture(p.id, p.word_ar, p.word_en, p.category, tuple(kept), p.palette),
            Picture(p.id, p.word_ar, p.word_en, p.category, tuple(cut), p.palette),
        )

    def without(self, x: float, y: float, size: float) -> str:
        """The picture with the part missing: a dashed outline where it was."""
        kept, cut = self._split()
        hole = "".join(part.elements for part in cut.parts if part.role == "body")
        dashed = (
            f'<g fill="#FFFFFF" stroke="#8C90A6" stroke-width="1.6" stroke-dasharray="3.2 2.6">{hole}</g>'
        )
        return nested(kept.inner("color") + dashed, x, y, size)

    def piece(self, x: float, y: float, size: float) -> str:
        """The part alone, framed by its crop box."""
        _, cut = self._split()
        bx, by, bw, bh = self.box
        side = max(bw, bh)
        box = f"{draw.n(bx - (side - bw) / 2)} {draw.n(by - (side - bh) / 2)} {draw.n(side)} {draw.n(side)}"
        return nested(cut.inner("color"), x, y, size, box)

    def crop(self, x: float, y: float, size: float) -> str:
        """A square piece of the whole picture around the part (part-to-whole)."""
        bx, by, bw, bh = self.box
        side = max(bw, bh)
        box = f"{draw.n(bx - (side - bw) / 2)} {draw.n(by - (side - bh) / 2)} {draw.n(side)} {draw.n(side)}"
        return nested(PICTURES[self.picture].inner("color"), x, y, size, box, clip=True)


CUTS: dict[str, Cut] = {
    "car:wheel": Cut("car", ((4, 1), (5, 1)), (60, 56, 28, 28), "العجلة"),
    "rabbit:ear": Cut("rabbit", ((0, 1), (1, 1)), (51, 3, 24, 46), "الأذن"),
    "house:door": Cut("house", ((3, None), (4, None)), (37, 62, 26, 30), "الباب"),
    "duck:beak": Cut("duck", ((2, None),), (2, 30, 26, 22), "المنقار"),
    "house:window": Cut("house", ((5, 0),), (21, 57, 21, 21), "النافذة"),
}


def dots_mark(count: int, x: float, y: float, color: str = "#8C79C9") -> str:
    """A row's number as dots in a pill (• •• •••): stage 1 does not read numerals yet."""
    w = 5 + count * 4.2
    out = [card(x - w / 2, y - 4, w, 8, r=4, fill="#FFFFFF", stroke=color, width=0.6)]
    out += [
        draw.el("circle", cx=x - (count - 1) * 2.1 + k * 4.2, cy=y, r=1.35, fill=color) for k in range(count)
    ]
    return "".join(out)


def star(cx: float, cy: float, r: float, fill: str = "#FFFFFF") -> str:
    """A star to colour (self-assessment, rewards)."""
    return draw.el(
        "path",
        d=draw.star_points(cx, cy, r, r * 0.46),
        fill=fill,
        stroke=GOLD_EDGE,
        stroke_width=0.8,
        stroke_linejoin="round",
    )


Draw = Callable[[int, float, float, float], str]  # (index, x, y, size) → SVG


def join_columns(start: Draw, end: Draw, n: int, answer: Sequence[int], *, h: float = H) -> list[str]:
    """Two columns to join with lines: the child starts at the right column (item i) and draws to the left
    one (`answer[i]`); the dots sit between them and the answer key draws the lines."""
    pitch = h / n
    size = min(pitch - 10, 56.0)
    body, hooks = [], []
    for i in range(n):
        cy = i * pitch + pitch / 2
        body.append(card(W - size - 14, cy - size / 2 - 4, size + 10, size + 8, r=6))
        body.append(start(i, W - size - 9, cy - size / 2, size))
        body.append(card(4, cy - size / 2 - 4, size + 10, size + 8, r=6, fill=SOFT, stroke="none"))
        body.append(end(i, 9, cy - size / 2, size))
        hooks.append(cy)
    right_x, left_x = W - size - 20, size + 20
    for cy in hooks:
        body += [hook(right_x, cy, 2.2), hook(left_x, cy, 2.2)]
    body += [answer_line((right_x, hooks[i]), (left_x, hooks[j])) for i, j in enumerate(answer)]
    return body
