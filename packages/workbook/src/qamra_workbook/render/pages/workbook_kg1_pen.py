"""«دوسية التأسيس» KG1 pen skills (Addendum 5 §3, ages 4–5): stroke rows in extra-large sizes (4 rows a page
at xl, 5 at l/m), each stroke before the letter that needs it: straight lines, arcs and waves, zigzags, big
circles, lanes, bridges, loops, the teeth of س, small closed loops, copying on a dot grid and joined strokes
without lifting the pen; the winding and sharp-turn roads; and the short rows the reviews reuse."""

from __future__ import annotations

import math
import random

from qamra_workbook.geometry import Stroke
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_common import INK, W, card, pic, picture_id, svg, text
from qamra_workbook.render.pages.workbook_pen import PAIRS, shape_stroke, traced
from qamra_workbook.render.pages.workbook_review import Box, Drawn, Task
from qamra_workbook.render.registry import Built, PageContext, page_type

ROWS = {"xl": 4, "l": 5, "m": 5}
BUMPS = {"wave": 4, "bridge": 4, "teeth": 5, "connected": 6, "lane": 2}
GRID_MODELS = {  # drawings on a 5 × 5 dot grid, as lists of polylines in grid units
    "house": ([(0, 4), (0, 1), (2, 0), (4, 1), (4, 4), (0, 4)], [(1.5, 4), (1.5, 2.5), (2.5, 2.5), (2.5, 4)]),
    "boat": ([(0, 2), (4, 2), (3, 4), (1, 4), (0, 2)], [(2, 2), (2, 0), (3.5, 1), (2, 1.5)]),
}
WINDING = "M148 40 C148 78 46 62 46 98 C46 134 148 118 148 152 C148 182 100 186 58 184"
SHARP = "M150 34 L150 72 L96 72 L96 108 L150 108 L150 144 L60 144 L60 182"
STRAIGHT = "M150 46 L46 162"  # one straight road, corner to corner


def loops_stroke(x0: float, x1: float, y: float, amp: float) -> Stroke:
    """Big round loops from x0 to x1 (a prolate cycloid): about 18 mm wide and 21 mm tall, five or so a row,
    so a four-year-old can follow each turn; the pen starts on the low side of the first loop."""
    sign = 1 if x1 > x0 else -1
    height = min(amp * 1.6, 13.0)
    k = max(3, min(6, round(abs(x1 - x0) / (2 * math.pi * height * 0.28))))
    a = abs(x1 - x0) / (2 * math.pi * k)
    steps = 40 * k
    t = [2 * math.pi * k * i / steps for i in range(steps + 1)]
    return Stroke(
        draw.polyline(
            [(x0 + sign * (a * u + height * math.sin(u)), y + height * 0.8 * math.cos(u)) for u in t]
        )
    )


def row_strokes(line: str, x0: float, x1: float, y: float, amp: float) -> list[Stroke]:
    """The strokes of one row of `line` from x0 (the start) to x1, centred on y; `amp` is half the height."""
    n = draw.n
    if line == "loop":
        return [loops_stroke(x0, x1, y, amp)]
    if line == "arc":
        w = (x1 - x0) / 3
        return [
            Stroke(
                f"M{n(x0 + i * w)} {n(y + amp)} Q{n(x0 + (i + 0.5) * w)} {n(y - 2.6 * amp)} "
                f"{n(x0 + (i + 0.88) * w)} {n(y + amp)}"
            )
            for i in range(3)
        ]
    if line == "zigzag":
        pts = [(x0 + (x1 - x0) * i / 6, y + (amp if i % 2 else -amp)) for i in range(7)]
        return [Stroke(draw.polyline(pts))]
    if line == "small-loop":
        w, sign = (x1 - x0) / 4, 1 if x1 > x0 else -1
        d = f"M{n(x0)} {n(y + amp)}"
        for i in range(4):
            x, far = x0 + i * w + sign * w * 0.15, x0 + i * w + sign * (w * 0.15 + amp * 2.2)
            d += (
                f" L{n(x)} {n(y + amp)} C{n(x)} {n(y - amp)} {n(far)} {n(y - amp)} "
                f"{n(far)} {n(y + amp * 0.2)} "
                f"C{n(far)} {n(y + amp)} {n(x)} {n(y + amp)} {n(x)} {n(y + amp)}"
            )
        return [Stroke(d)]
    if line in BUMPS:
        k = BUMPS[line]
        w = (x1 - x0) / k
        base = y + amp if line == "bridge" else y - amp if line == "teeth" else y
        d = f"M{n(x0)} {n(base)}"
        for i in range(k):
            up, down = y - 1.7 * amp, y + 1.7 * amp
            peak = up if line == "bridge" else down if line == "teeth" else up if i % 2 == 0 else down
            d += f" Q{n(x0 + (i + 0.5) * w)} {n(peak)} {n(x0 + (i + 1) * w)} {n(base)}"
        return [Stroke(d)]
    return [Stroke(draw.polyline([(x0, y), (x1, y)]))]


def lane(centre: Stroke, half: float) -> str:
    """A lane to draw inside: two edges around the centre line, which is left as faint dots."""
    out = [draw.path(centre.d, stroke="#E5CD9E", width=2 * half + 2)]
    out.append(draw.path(centre.d, stroke="#FFFFFF", width=2 * half))
    out.append(draw.dotted(centre, spacing=7, r=0.8, color="#D6CBB2"))
    out.append(draw.start_dot(centre.start, 2.8))
    return "".join(out)


def band_rows(line: str, rows: int, rtl: bool) -> list[str]:
    """Rows of one stroke kind between a start picture and an end picture (the start on the reading side)."""
    pitch = 204 / rows
    ps = min(30.0, pitch - 12)
    amp = pitch * 0.2
    body = []
    for i, (a, b) in enumerate(PAIRS[:rows]):
        y = i * pitch
        cy = y + pitch / 2 - 2
        body.append(card(0, y + 1, W, pitch - 4, r=7))
        start_x, end_x = (W - ps - 4, 4) if rtl else (4, W - ps - 4)
        body.append(pic(a, start_x, cy - ps / 2, ps))
        body.append(pic(b, end_x, cy - ps / 2, ps))
        x0, x1 = (W - ps - 10, ps + 10) if rtl else (ps + 10, W - ps - 10)
        if line == "lane":
            body.append(lane(row_strokes("lane", x0, x1, cy, amp * 0.8)[0], amp * 0.9))
            continue
        body += [traced(s, spacing=4.8, r=1.25, start=2.8) for s in row_strokes(line, x0, x1, cy, amp)]
    return body


def grid_copy(y: float, model: str) -> list[str]:
    """A drawing on a dot grid (right) and the same empty grid to copy it on (left)."""
    step, top = 15.0, y + 14
    right, left = W - 10 - 4 * step, 10.0
    body = [card(0, y + 1, W, 100, r=7)]
    for gx in (right, left):
        for r in range(5):
            for c in range(5):
                body.append(draw.el("circle", cx=gx + c * step, cy=top + r * step, r=1.0, fill="#B8B2A6"))
    for poly in GRID_MODELS[model]:
        pts = [(right + gx * step, top + gy * step) for gx, gy in poly]
        body.append(draw.path(draw.polyline(pts), stroke=INK, width=1.6))
    first = GRID_MODELS[model][0][0]
    body.append(draw.start_dot((left + first[0] * step, top + first[1] * step), 2.4))
    body.append(text("أَرْسُمُ مِثْلَهُ هُنا", left + 2 * step, y + 92, 4.6, color="#676B83"))
    return body


@page_type("kg1-pen-lines")
def kg1_pen_lines(ctx: PageContext) -> Built:
    p = ctx.page.params
    line, size = str(p.get("line", "horizontal")), str(p.get("size", "xl"))
    rtl = str(p.get("direction", "rtl")) != "ltr"
    body: list[str] = []
    if line == "vertical":
        cols = 4 if size == "xl" else 5
        for i, (a, b) in enumerate(PAIRS[:cols]):
            cx = W - (i + 0.5) * W / cols
            body += [pic(a, cx - 14, 0, 28), pic(b, cx - 14, 176, 28)]
            body.append(traced(Stroke(draw.polyline([(cx, 34), (cx, 172)])), spacing=4.8, r=1.25, start=2.8))
    elif line == "diagonal":
        for row in range(3):
            y = row * 68
            body.append(card(0, y + 1, W, 64, r=7))
            for k in range(4):
                x = W - 22 - k * 46
                top, bottom = (
                    ((x, y + 10), (x - 24, y + 58)) if row % 2 == 0 else ((x - 24, y + 10), (x, y + 58))
                )
                body.append(traced(Stroke(draw.polyline([top, bottom])), spacing=4.8, r=1.25, start=2.8))
    elif line == "circle":
        for k in range(6):
            row, col = divmod(k, 2)
            cx, cy = W - (col + 0.5) * W / 2, (row + 0.5) * 68
            body.append(card(cx - 44, cy - 32, 88, 64, r=7))
            body.append(traced(shape_stroke("circle", cx, cy, 54), spacing=4.8, r=1.25, start=2.8))
    elif line == "grid-copy":
        body += grid_copy(0, "house") + grid_copy(104, "boat")
    else:
        body += band_rows(line, ROWS.get(size, 5), rtl)
    return Built({"svg": svg(body)}, None, [])


@page_type("kg1-trace-path")
def kg1_trace_path(ctx: PageContext) -> Built:
    """A wide winding road, or a road with sharp turns, from the start picture to the end picture."""
    kind = str(ctx.page.params.get("path", "winding"))
    words = [str(w) for w in ctx.page.params.get("words", ["turtle", "lettuce"])]
    start, end = picture_id(words[0]), picture_id(words[-1])
    road = Stroke({"sharp-turns": SHARP, "straight": STRAIGHT}.get(kind, WINDING))
    wide = 15.0 if kind == "sharp-turns" else 19.0
    body = [card(0, 0, W, 204, r=8, fill="#F4F9FD", stroke="none")]
    body.append(draw.path(road.d, stroke="#E5CD9E", width=wide + 2.6))
    body.append(draw.path(road.d, stroke="#F6E7C8", width=wide))
    body.append(traced(road, spacing=5, r=1.3, start=3))
    body.append(pic(start, 128, 0, 42))
    body.append(pic(end, 16, 160, 42) if kind == "sharp-turns" else pic(end, 12, 158, 42))
    return Built({"svg": svg(body)}, None, [])


def kg1_pen_row(skill: str) -> Task:
    """A short row of a KG1 stroke between two pictures, for the reviews and the pen check."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        mid = box.y + box.h / 2
        line = {"connected-rtl": "connected", "connected-ltr": "connected", "wave": "wave"}.get(skill, skill)
        if line == "circle":
            size = min(box.h - 4, 24.0)
            for k in range(3):
                cx = box.x + box.w - (k + 0.5) * box.w / 3
                out.body.append(traced(shape_stroke("circle", cx, mid, size), spacing=3.8, r=0.95, start=2))
            return out
        a, b = r.choice(PAIRS)
        size = min(box.h - 2, 18.0)
        ltr = skill == "connected-ltr"
        out.body.append(pic(a, box.x if ltr else box.x + box.w - size, mid - size / 2, size))
        out.body.append(pic(b, box.x + box.w - size if ltr else box.x, mid - size / 2, size))
        x0, x1 = box.x + box.w - size - 4, box.x + size + 4
        if ltr:
            x0, x1 = x1, x0
        amp = min(box.h * 0.22, 6.0)
        if line == "lane":
            out.body.append(lane(row_strokes("lane", x0, x1, mid, amp * 0.8)[0], amp * 0.9))
            return out
        out.body += [traced(s, spacing=3.8, r=0.95, start=2) for s in row_strokes(line, x0, x1, mid, amp)]
        return out

    return task
