"""Journey hand and pen pages (Addendum 6 §4.3, §4.10 levels 1–2): lines and shapes to trace, the grass, waves
and mountains drills, a dot picture, half shapes to complete, a missing part to draw and the boat curve for a
finger. Every stroke starts at a green dot with an arrow, from right to left where a line has a direction."""

from __future__ import annotations

import itertools
import re
from typing import Any

from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import PICTURES, Picture
from qamra_workbook.render import draw
from qamra_workbook.render.pages import motor
from qamra_workbook.render.pages.journey_kit import H, W, card, nested, picture, pid, svg
from qamra_workbook.render.pages.workbook_pen import shape_stroke, traced
from qamra_workbook.render.registry import Built, PageContext, page_type

PENCIL = "#3D4262"
LINE = "#C9B994"


def shape_of(kind: str, cx: float, cy: float, s: float) -> Stroke:
    """A shape to trace (s: its size), starting at its top; the boat curve starts at its right tip."""
    if kind == "star":
        return Stroke(draw.star_points(cx, cy + s * 0.04, s / 2, s / 4.6))
    if kind == "heart":
        return Stroke(draw.heart_path(cx, cy, s, s * 0.9))
    if kind == "boat-curve":
        return Stroke(
            f"M{cx + s / 2} {cy - s * 0.25} C{cx + s / 2} {cy + s * 0.45} {cx - s / 2} {cy + s * 0.45} "
            f"{cx - s / 2} {cy - s * 0.25}"
        )
    stroke: Stroke = shape_stroke(kind, cx, cy, s)
    return stroke


def row_strokes(target: str, xr: float, xl: float, y: float, h: float) -> list[Stroke]:
    """Level 1: the lines of one row, from right to left (and top to bottom)."""
    span = xr - xl
    if target == "horizontal":
        return [Stroke(f"M{xr} {y} L{xl} {y}")]
    if target == "vertical":
        return [
            Stroke(f"M{xr - k * span / 6} {y - h / 2} L{xr - k * span / 6} {y + h / 2}") for k in range(7)
        ]
    if target == "diagonal":
        return [
            Stroke(f"M{xr - k * span / 4} {y - h / 2} L{xr - k * span / 4 - h * 0.6} {y + h / 2}")
            for k in range(4)
        ]
    if target == "fence":
        posts = [
            Stroke(f"M{xr - k * span / 5} {y - h / 2} L{xr - k * span / 5} {y + h / 2}") for k in range(6)
        ]
        rails = [Stroke(f"M{xr} {y + f * h} L{xl} {y + f * h}") for f in (-0.2, 0.2)]
        return [*posts, *rails]
    hops, d = 4, [f"M{xr} {y if target == 'waves' else y + h / 3}"]
    step = span / hops
    for k in range(hops):
        x0 = xr - k * step
        if target == "arcs":
            d.append(f"Q{x0 - step / 2} {y - h * 0.9} {x0 - step} {y + h / 3}")
        elif target == "zigzag":
            d.append(f"L{x0 - step / 2} {y - h / 2} L{x0 - step} {y + h / 3}")
        else:  # waves
            d.append(f"Q{x0 - step / 4} {y - h / 2} {x0 - step / 2} {y}")
            d.append(f"Q{x0 - 3 * step / 4} {y + h / 2} {x0 - step} {y}")
    return [Stroke(" ".join(d))]


def targets(ctx: PageContext) -> list[str]:
    raw = ctx.page.params.get("target", "horizontal")
    return [str(t) for t in raw] if isinstance(raw, list) else [str(raw)]


@page_type("write-progression")
def write_progression(ctx: PageContext) -> Built:
    """One level of the writing progression: level 1 traces lines, level 2 traces shapes (on a writing line
    with `line: true`, inside train wagons with `train: true`)."""
    params = ctx.page.params
    level, rows = int(params.get("level", 1)), int(params.get("rows", 3))
    kinds = targets(ctx)
    problems = [] if level in (1, 2) else [f"stage 1 writes at levels 1–2, not {level}"]
    body: list[str] = []
    if level == 1:
        pitch = H / rows
        start, end = params.get("from"), params.get("to")
        for i in range(rows):
            y, kind = i * pitch + pitch / 2, kinds[i % len(kinds)]
            body.append(card(0, i * pitch + 2, W, pitch - 6, r=8))
            xr, xl = (W - 40 if start else W - 12), (40 if end else 12)
            if start:
                body.append(picture(str(start), W - 36, y - 15, 30))
            if end:
                body.append(picture(str(end), 6, y - 15, 30))
            for stroke in row_strokes(kind, xr, xl, y, min(pitch - 22, 30.0)):
                body.append(
                    traced(stroke, spacing=4.4, r=1.25, start=2.6, example=i == 0 and ctx.page.example)
                )
        return Built({"svg": svg(body)}, None, problems)
    sizes = {"big": 40.0, "medium": 30.0, "small": 22.0}
    wanted = [sizes[str(s)] for s in params.get("sizes", ["big", "medium"])]
    rows = max(rows, len(kinds)) if len(kinds) > 1 else rows
    pitch = H / rows
    for i in range(rows):
        kind, size = kinds[i % len(kinds)], wanted[i % len(wanted)]
        top = i * pitch
        base = top + pitch - 12
        body.append(card(0, top + 2, W, pitch - 6, r=8))
        if params.get("line") or kind == "boat-curve":
            body.append(draw.path(f"M{W - 8} {base} L8 {base}", stroke=LINE, width=0.9))
        count = max(2, int((W - 20) // (size + 14)))
        for k in range(count):
            cx = W - 14 - size / 2 - k * (W - 28 - size) / max(count - 1, 1)
            cy = base - size / 2 - 3 if kind != "boat-curve" else base - size * 0.3
            if params.get("train"):
                body.append(
                    card(
                        cx - size / 2 - 5,
                        cy - size / 2 - 5,
                        size + 10,
                        size + 8,
                        r=3,
                        fill="#FFFFFF",
                        stroke="#8C90A6",
                        width=0.7,
                    )
                )
                body += [
                    draw.el("circle", cx=cx + dx, cy=base + 1, r=3, fill=PENCIL)
                    for dx in (-size / 3, size / 3)
                ]
            stroke = shape_of(kind, cx, cy, size)
            body.append(
                traced(stroke, spacing=4.0, r=1.15, start=2.4, example=i == 0 and k == 0 and ctx.page.example)
            )
    return Built({"svg": svg(body)}, None, problems)


# ---- themed drills (Addendum 6 §4.3): grass, waves and mountains join the rain in `motor.DRILLS` -----------


def _drill_rows(ctx: PageContext, kind: str, count: int, top: float, bottom: float) -> list[str]:
    out = []
    pitch = (bottom - top) / count
    for i in range(count):
        y = top + pitch * (i + 0.5)
        for stroke in row_strokes(kind, motor.DRILL_W - 10, 10, y, min(pitch - 10, 28.0)):
            out.append(traced(stroke, spacing=4.6, r=1.3, start=2.6, example=i == 0 and ctx.page.example))
    return out


def _grass(ctx: PageContext) -> str:
    w, h = motor.DRILL_W, motor.DRILL_H
    body = [picture("rabbit", w / 2 - 22, 2, 44)]
    for top in (54.0, 118.0):
        body.append(card(4, top + 34, w - 8, 18, r=8, fill="#DDEFD6", stroke="none"))
        for k in range(int(ctx.page.params.get("lines", 12)) // 2):
            x = w - 18 - k * (w - 36) / 5
            s = Stroke(f"M{x} {top + 12} L{x} {top + 40}")
            body.append(traced(s, spacing=4.4, r=1.3, start=2.6, example=k == 0 and ctx.page.example))
    return "".join(body) + str(card(0, h - 1, w, 1, r=0, fill="none", stroke="none"))


def _waves(ctx: PageContext) -> str:
    w, h = motor.DRILL_W, motor.DRILL_H
    body = [card(0, 50, w, h - 50, r=10, fill="#E1EEFA", stroke="none"), picture("boat", w / 2 - 25, 0, 50)]
    return "".join(body + _drill_rows(ctx, "waves", int(ctx.page.params.get("rows", 3)), 58, h - 6))


def _mountains(ctx: PageContext) -> str:
    w, h = motor.DRILL_W, motor.DRILL_H
    body = [picture("sun", w - 44, 0, 40), card(0, h - 16, w, 16, r=8, fill="#DDEFD6", stroke="none")]
    return "".join(body + _drill_rows(ctx, "zigzag", int(ctx.page.params.get("rows", 2)), 44, h - 18))


for _name, _drill in (("grass", _grass), ("waves", _waves), ("mountains", _mountains)):
    motor.DRILLS.setdefault(_name, _drill)


def _main_path(picture_id: str, part: int) -> str:
    found = re.search(r'd="([^"]+)"', PICTURES[picture_id].parts[part].elements)
    if found is None:
        raise ValueError(f"{picture_id} part {part} has no path")
    return found.group(1)


@page_type("dot-picture")
def dot_picture(ctx: PageContext) -> Built:
    """Join the dots (no numbers yet) from the green start: the picture's body appears."""
    thing = pid(str(ctx.page.params.get("picture", "fish")))
    part = int(ctx.page.params.get("part", 2))
    scale, dx, dy = 1.7, 8.0, 12.0
    outline = Stroke(_main_path(thing, part)).scaled(scale, dx, dy)
    points = outline.dots(outline.length / int(ctx.page.params.get("dots", 14)))
    rest = [p for k, p in enumerate(PICTURES[thing].parts) if k != part and p.role in ("body", "ink", "line")]
    faint = "".join(f'<g fill="#FFFFFF" stroke="#B8BCCB" stroke-width="1.2">{p.elements}</g>' for p in rest)
    body = [card(0, 0, W, H, r=10), nested(faint, dx, dy, 100 * scale)]
    body.append(draw.path(outline.d, stroke="#E0483A", width=1.2, class_="key-line"))
    for k, (x, y) in enumerate(points):
        body.append(
            draw.start_dot((x, y), 3.4) if k == 0 else draw.el("circle", cx=x, cy=y, r=2.4, fill=PENCIL)
        )
    (ax, ay), angle = outline.at(0.045)
    body.append(draw.arrow((ax, ay), angle, 4.2))
    gaps = [((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in itertools.pairwise(points)]
    problems = [] if min(gaps) >= 8 else ["two dots are closer than 8 mm"]
    return Built({"svg": svg(body)}, [f"تظهر {PICTURES[thing].word_ar}"], problems)


# the right half of symmetric outlines in a 100-unit box; the left half is its mirror, in dots
HALVES: dict[str, list[str]] = {
    "balloon": ["M50 12 C64 12 78 22 78 40 C78 58 66 72 50 76"],
    "apple": ["M50 29 C56 24 66 22 74 26 C85 32 87 48 83 60 C78 76 64 88 50 83"],
    "sun": [
        "M50 24 C64 24 76 36 76 50 C76 64 64 76 50 76",
        "M50 16 L50 6",
        "M74 26 L81 19",
        "M84 50 L94 50",
        "M74 74 L81 81",
        "M50 84 L50 94",
    ],
    "heart": ["M50 30 C56 18 76 16 82 30 C88 46 70 64 50 80"],
}


def _mirror(stroke: Stroke, x: float, y: float, k: float) -> Stroke:
    return Stroke(draw.polyline([(x + (100 - px) * k, y + py * k) for px, py in stroke.polyline]))


@page_type("complete-the-shape")
def complete_the_shape(ctx: PageContext) -> Built:
    """Half of each picture is drawn; the other half is dots to trace."""
    items = [str(w) for w in ctx.page.params.get("items", ["balloon", "apple", "sun"])]
    problems = [f"no half outline for {w}" for w in items if w not in HALVES]
    pitch, body = H / len(items), []
    for i, w in enumerate(items):
        size = pitch - 10
        x, y = W / 2 - size / 2, i * pitch + 5
        body.append(card(8, i * pitch + 2, W - 16, pitch - 4, r=8))
        k = size / 100
        for d in HALVES.get(w, []):
            half = Stroke(d)
            body.append(draw.path(half.scaled(k, x, y).d, stroke=PENCIL, width=1.6))
            body.append(
                traced(
                    _mirror(half, x, y, k),
                    spacing=3.8,
                    r=1.05,
                    start=2.2,
                    example=i == 0 and ctx.page.example,
                )
            )
        if w == "balloon":
            body.append(
                draw.path(Stroke("M50 76 C45 84 55 88 48 97").scaled(k, x, y).d, stroke=PENCIL, width=1.2)
            )
    return Built({"svg": svg(body)}, None, problems)


@page_type("draw-missing-part")
def draw_missing_part(ctx: PageContext) -> Built:
    """Each picture misses a part (the sun's rays, the cat's whiskers, the flower's stem): draw it."""
    items: list[dict[str, Any]] = [dict(i) for i in ctx.page.params.get("items", [])]
    pitch, body, key = H / max(len(items), 1), [], []
    for i, item in enumerate(items):
        thing = PICTURES[pid(str(item["picture"]))]
        drop = {int(k) for k in item.get("drop", [])}
        kept = tuple(p for k, p in enumerate(thing.parts) if k not in drop)
        gone = tuple(p for k, p in enumerate(thing.parts) if k in drop)
        size = pitch - 10
        x = W / 2 - size / 2
        body.append(card(8, i * pitch + 2, W - 16, pitch - 4, r=8))
        partial = Picture(thing.id, "", "", "", kept, thing.palette).inner("color")
        body.append(nested(partial, x, i * pitch + 5, size))
        missing = Picture(thing.id, "", "", "", gone, thing.palette).inner("line")
        body.append(nested(missing, x, i * pitch + 5, size).replace("<svg", '<svg class="key-ring"', 1))
        key.append(f"{thing.word_ar}: {item.get('missing', '')}")
        if not drop or not kept:
            return Built({"svg": svg(body)}, key, [f"{thing.id}: drop some parts, not all"])
    return Built({"svg": svg(body)}, key)


@page_type("boat-trace")
def boat_trace(ctx: PageContext) -> Built:
    """The boat curve, big and solid, for a finger: start at the green dot on the right, follow the arrows."""
    s = Stroke(f"M{W - 22} 70 C{W - 22} 170 22 170 22 70")
    body = [card(0, 0, W, H, r=10, fill="#F4F9FD", stroke="none")]
    body.append(draw.path("M4 186 Q26 176 48 186 T92 186 T136 186 T182 186", stroke="#8EC1EC", width=4))
    body.append(draw.path(s.d, stroke="#C98A5B", width=22))
    body.append(draw.path(s.d, stroke="#E3B982", width=17))
    for t in (0.18, 0.38, 0.58, 0.78):
        (x, y), angle = s.at(t)
        body.append(draw.chevron((x, y), angle, 6, "#FFFFFF", 2))
    body.append(draw.start_dot(s.start, 5.5))
    body.append(draw.arrow((s.start[0], s.start[1] - 12), 90, 6))
    return Built({"svg": svg(body)})
