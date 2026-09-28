"""A picture is a list of parts drawn in a 100 × 100 box; each part's role decides how it is painted.

Both versions come from the same parts: the color picture paints bodies in their colors, the line-art
(coloring) picture paints them white and keeps only the outlines, the ink details and the eye glints.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from markupsafe import Markup

Style = Literal["color", "line"]
# body: colored area with an outline · ink: solid outline-colored details (eyes, noses)
# line: outline-only strokes (mouths, whiskers) · glint: white eye highlights (both versions)
# shine, tint: soft highlights and blush (color version only)
Role = Literal["body", "ink", "line", "glint", "shine", "tint"]

OUTLINE = "#2B2E4A"
STROKE = 2.6  # in the 100-unit box: ~1 mm on a 40 mm picture
LINE_STROKE = 3.0  # coloring pages get slightly bolder outlines
_TASHKEEL = re.compile(r"[ً-ٰٟ]")


@dataclass(frozen=True)
class Part:
    role: Role
    fill: str  # a palette key of the picture, or a literal color
    elements: str  # SVG elements without paint attributes


@dataclass(frozen=True)
class Picture:
    id: str
    word_ar: str  # vowelized, as printed under the picture
    word_en: str
    category: str
    parts: tuple[Part, ...]
    palette: Mapping[str, str] = field(default_factory=dict)

    @property
    def first_letter_ar(self) -> str:
        bare = strip_tashkeel(self.word_ar)
        return (bare[2:] if bare.startswith("ال") else bare)[:1]

    @property
    def first_letter_en(self) -> str:
        return self.word_en[:1].upper()

    def color(self, key: str, colors: Mapping[str, str] | None = None) -> str:
        if colors and key in colors:
            return colors[key]
        return self.palette.get(key, key)

    def inner(self, style: Style = "color", colors: Mapping[str, str] | None = None) -> str:
        """The painted parts as SVG groups, for composing pictures into scenes."""
        width = STROKE if style == "color" else LINE_STROKE
        out = []
        for part in self.parts:
            paint = _paint(part, style, self.color(part.fill, colors), width)
            if paint is not None:
                out.append(f"<g {paint}>{part.elements}</g>")
        return "".join(out)

    def svg(
        self,
        style: Style = "color",
        *,
        colors: Mapping[str, str] | None = None,
        flip: bool = False,
        css_class: str = "pic",
    ) -> Markup:
        body = self.inner(style, colors)
        if flip:
            body = f'<g transform="translate(100 0) scale(-1 1)">{body}</g>'
        return Markup(  # nosec B704 (library drawings, no user text)
            f'<svg class="{css_class}" viewBox="0 0 100 100" aria-hidden="true">{body}</svg>'
        )


def _paint(part: Part, style: Style, fill: str, width: float) -> str | None:
    stroke = f'stroke="{OUTLINE}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"'
    match part.role:
        case "body":
            return f'fill="{fill if style == "color" else "#FFFFFF"}" {stroke}'
        case "ink":
            return f'fill="{OUTLINE}"'
        case "line":
            return f'fill="none" {stroke}'
        case "glint":
            return 'fill="#FFFFFF"'
        case "shine":
            return 'fill="#FFFFFF" opacity="0.55"' if style == "color" else None
        case "tint":
            return f'fill="{fill}" opacity="0.45"' if style == "color" else None


def strip_tashkeel(text: str) -> str:
    return _TASHKEEL.sub("", text)


# ---- authoring helpers (used by `icons.py`) ------------------------------------------------------------


def body(fill: str, *elements: str) -> Part:
    return Part("body", fill, "".join(elements))


def ink(*elements: str) -> Part:
    return Part("ink", "", "".join(elements))


def line(*elements: str) -> Part:
    return Part("line", "", "".join(elements))


def glint(*elements: str) -> Part:
    return Part("glint", "", "".join(elements))


def shine(*elements: str) -> Part:
    return Part("shine", "", "".join(elements))


def tint(fill: str, *elements: str) -> Part:
    return Part("tint", fill, "".join(elements))


def c(cx: float, cy: float, r: float) -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'


def e(cx: float, cy: float, rx: float, ry: float, rotate: float = 0) -> str:
    turn = f' transform="rotate({rotate} {cx} {cy})"' if rotate else ""
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"{turn}/>'


def p(d: str) -> str:
    return f'<path d="{d}"/>'


def rect(x: float, y: float, w: float, h: float, rx: float = 0) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>'


def scallop_d(cx: float, cy: float, rx: float, ry: float, bumps: int, bulge: float = 0.62) -> str:
    """Path data of a cloud-like closed outline: `bumps` arcs around an ellipse (fleece, manes, seals)."""

    def fmt(x: float) -> str:
        return f"{x:.1f}".rstrip("0").rstrip(".")

    turns = [math.radians(360 * i / bumps - 90) for i in range(bumps)]
    pts = [(cx + math.cos(a) * rx, cy + math.sin(a) * ry) for a in turns]
    d = f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"
    for i in range(bumps):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % bumps]
        radius = math.dist((x1, y1), (x2, y2)) * bulge
        d += f" A{fmt(radius)} {fmt(radius)} 0 0 1 {fmt(x2)} {fmt(y2)}"
    return d + " Z"


def eyes(left: tuple[float, float], right: tuple[float, float], r: float = 3.6) -> tuple[Part, Part]:
    """Two round eyes with a glint: the house style for every face."""
    (lx, ly), (rx, ry) = left, right
    glints = c(lx + r * 0.35, ly - r * 0.4, r * 0.38) + c(rx + r * 0.35, ry - r * 0.4, r * 0.38)
    return ink(e(lx, ly, r, r * 1.15), e(rx, ry, r, r * 1.15)), glint(glints)


def cheeks(left: tuple[float, float], right: tuple[float, float], r: float = 4.5) -> Part:
    return tint("#F08A7E", e(left[0], left[1], r, r * 0.7), e(right[0], right[1], r, r * 0.7))
