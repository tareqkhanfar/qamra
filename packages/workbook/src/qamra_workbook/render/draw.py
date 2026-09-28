"""SVG drawing primitives shared by page types. Coordinates are millimetres unless noted.

Tracing follows Addendum 6 §6: bold dots (not faint), a green start dot on every stroke, arrows for the
direction. Shapes carry `data-shape` so tests can count exactly what a page shows.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from markupsafe import Markup, escape

from qamra_workbook.geometry import Point, Stroke
from qamra_workbook.pictures.model import OUTLINE
from qamra_workbook.puzzles.coloring import Shape

DOT = "#4A5078"  # tracing dots: dark enough to read at arm's length, lighter than a pencil line
START = "#2FA36B"  # start dots are green ("go")
ARROW = "#E27D63"

Attr = float | str


def n(x: float) -> str:
    """Compact number for SVG attributes."""
    text = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def el(tag: str, content: str = "", /, **attrs: Attr) -> str:
    """An SVG element. Numbers are written compactly and `stroke_width` becomes `stroke-width`; use
    `class_` for `class`. `content` is inserted as is (escape text yourself)."""
    parts = " ".join(
        f'{k.rstrip("_").replace("_", "-")}="{n(v) if isinstance(v, int | float) else escape(v)}"'
        for k, v in attrs.items()
    )
    return f"<{tag} {parts}>{content}</{tag}>" if content else f"<{tag} {parts}/>"


def d_path(*commands: tuple[str, float | tuple[float, ...]]) -> str:
    """Path data from (command, numbers) pairs: d_path(("M", (0, 0)), ("L", (5, 5)))."""
    out = []
    for cmd, nums in commands:
        values = nums if isinstance(nums, tuple) else (nums,)
        out.append(cmd + " ".join(n(v) for v in values))
    return " ".join(out)


def polyline(points: Iterable[Point]) -> str:
    return d_path(*((("M" if i == 0 else "L"), p) for i, p in enumerate(points)))


def svg(width: float, height: float, body: str, css_class: str = "") -> Markup:
    """An SVG whose user units are millimetres."""
    cls = f' class="{css_class}"' if css_class else ""
    return Markup(  # nosec B704 (built from numbers and library drawings)
        f'<svg{cls} viewBox="0 0 {n(width)} {n(height)}" width="{n(width)}mm" height="{n(height)}mm"'
        f' aria-hidden="true">{body}</svg>'
    )


def path(d: str, *, stroke: str, width: float, fill: str = "none", **attrs: Attr) -> str:
    """A stroked path with round caps and joins (the house style for lines)."""
    return el(
        "path",
        d=d,
        fill=fill,
        stroke=stroke,
        stroke_width=width,
        stroke_linecap="round",
        stroke_linejoin="round",
        **attrs,
    )


def star_points(cx: float, cy: float, outer: float, inner: float, points: int = 5) -> str:
    corners = []
    for i in range(2 * points):
        r = outer if i % 2 == 0 else inner
        a = math.radians(-90 + 180 * i / points)
        corners.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return polyline(corners) + " Z"


def heart_path(cx: float, cy: float, w: float, h: float) -> str:
    """A heart filling a w × h box centred on (cx, cy)."""
    x0, y0 = cx - w / 2, cy - h / 2
    curves = (
        (0.3, 0.86, 0, 0.66, 0, 0.33),
        (0, 0.1, 0.17, 0, 0.3, 0),
        (0.4, 0, 0.47, 0.06, 0.5, 0.16),
        (0.53, 0.06, 0.6, 0, 0.7, 0),
        (0.83, 0, 1, 0.1, 1, 0.33),
        (1, 0.66, 0.7, 0.86, 0.5, 1),
    )
    scaled = [tuple(x0 + v * w if k % 2 == 0 else y0 + v * h for k, v in enumerate(c)) for c in curves]
    return d_path(("M", (cx, y0 + h)), *(("C", c) for c in scaled)) + " Z"


def shape(s: Shape, *, fill: str = "#FFFFFF", stroke: str = OUTLINE, width: float = 0.9) -> str:
    """A geometric shape, tagged with its kind (`data-shape`)."""
    paint: dict[str, Attr] = {
        "fill": fill,
        "stroke": stroke,
        "stroke_width": width,
        "stroke_linejoin": "round",
        "data_shape": s.kind,
    }
    if s.rotate:
        paint["transform"] = f"rotate({n(s.rotate)} {n(s.cx)} {n(s.cy)})"
    x, y, w, h = s.cx - s.w / 2, s.cy - s.h / 2, s.w, s.h
    match s.kind:
        case "circle":
            return el("ellipse", cx=s.cx, cy=s.cy, rx=w / 2, ry=h / 2, **paint)
        case "square" | "rectangle":
            return el("rect", x=x, y=y, width=w, height=h, rx=min(w, h) * 0.08, **paint)
        case "triangle":
            d = polyline([(s.cx, y), (x + w, y + h), (x, y + h)]) + " Z"
        case "diamond":
            d = polyline([(s.cx, y), (x + w, s.cy), (s.cx, y + h), (x, s.cy)]) + " Z"
        case "star":
            d = star_points(s.cx, s.cy + h * 0.04, w / 2, w / 4.6)
        case "heart":
            d = heart_path(s.cx, s.cy, w, h)
    return el("path", d=d, **paint)


def dots(points: Iterable[Point], r: float, color: str = DOT) -> str:
    return "".join(el("circle", cx=x, cy=y, r=r, fill=color) for x, y in points)


def dotted(stroke: Stroke, *, spacing: float, r: float, color: str = DOT) -> str:
    """Bold tracing dots along a stroke; the first one is left for the start dot."""
    return dots(stroke.dots(spacing)[1:], r, color)


def _turned(point: Point, angle: float) -> str:
    return f"translate({n(point[0])} {n(point[1])}) rotate({n(angle)})"


def arrow(point: Point, angle: float, size: float, color: str = ARROW) -> str:
    """A small solid arrowhead pointing along `angle` (degrees)."""
    s = size
    head = polyline([(s * 0.6, 0), (-s * 0.45, -s * 0.55), (-s * 0.2, 0), (-s * 0.45, s * 0.55)]) + " Z"
    return el(
        "path",
        d=head,
        fill=color,
        stroke=color,
        stroke_width=s * 0.12,
        stroke_linejoin="round",
        transform=_turned(point, angle),
    )


def chevron(point: Point, angle: float, size: float, color: str = "#FFFFFF", width: float = 1.6) -> str:
    """An open arrow (›), drawn on top of a thick letter body."""
    d = polyline([(-size * 0.35, -size * 0.55), (size * 0.3, 0), (-size * 0.35, size * 0.55)])
    return path(d, stroke=color, width=width, transform=_turned(point, angle))


def start_dot(
    point: Point, r: float, label: str = "", color: str = START, font_size: float | None = None
) -> str:
    """The green dot where a stroke starts, with its stroke number when there are several."""
    x, y = point
    out = el("circle", cx=x, cy=y, r=r, fill=color, stroke="#FFFFFF", stroke_width=r * 0.22)
    if label:
        size = font_size if font_size is not None else r * 1.35
        text = str(escape(label))
        out += el(
            "text", text, x=x, y=y + size * 0.36, text_anchor="middle", font_size=size, class_="dot-label"
        )
    return out
