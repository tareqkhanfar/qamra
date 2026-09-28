"""Eye-hand and pre-writing pages: mazes and themed pen drills."""

from __future__ import annotations

from collections.abc import Callable

from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import Style
from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.puzzles import generate_maze
from qamra_workbook.render import draw
from qamra_workbook.render.registry import Built, PageContext, page_type

HEDGE, HEDGE_LIGHT = "#4F8A45", "#8CC47C"
PENCIL = "#3D4262"


def character_image(ctx: PageContext, x: float, y_feet: float, height: float) -> str:
    """The child's cut-out character standing with its feet at y_feet (SVG <image>, 300 DPI source)."""
    if ctx.assets.character is None:
        return ""
    w = height * ctx.assets.character_aspect
    href = ctx.assets.character.resolve().as_uri()
    return draw.el(
        "image",
        href=href,
        x=x,
        y=y_feet - height,
        width=w,
        height=height,
        preserveAspectRatio="xMidYMax meet",
    )


def nested_picture(picture_id: str, x: float, y: float, size: float, style: Style = "color") -> str:
    """A library picture placed inside a larger SVG drawing."""
    inner = picture(picture_id).inner(style)
    return draw.el("svg", inner, x=x, y=y, width=size, height=size, viewBox="0 0 100 100")


@page_type("maze")
def maze(ctx: PageContext) -> Built:
    """In at the top right (the child stands above the entrance), out at the bottom left into the goal."""
    cols, rows = int(ctx.page.params.get("cols", 5)), int(ctx.page.params.get("rows", 5))
    goal = str(ctx.page.params.get("goal", "garden"))
    m = generate_maze(cols, rows, ctx.page.seed, start_side="top", end_side="left")
    w, h, figure = 186.0, 200.0, 56.0
    goal_room, head_room = 42.0, figure + 4
    cell = min((w - goal_room - 6) / cols, (h - head_room - 4) / rows)
    mw, mh = cell * cols, cell * rows
    x0, y0 = w - 5 - mw, h - mh - 4

    def at(c: float, r: float) -> tuple[float, float]:
        return x0 + c * cell, y0 + r * cell

    walls = " ".join(draw.d_path(("M", at(*a)), ("L", at(*b))) for a, b in m.walls())
    entry_x = x0 + (m.start[0] + 0.5) * cell
    exit_y = y0 + (m.end[1] + 0.5) * cell
    body = [
        draw.el("rect", x=x0 - 4, y=y0 - 4, width=mw + 8, height=mh + 8, rx=7, fill="#E4F1DC"),
        draw.el("rect", x=x0, y=y0, width=mw, height=mh, rx=2, fill="#FFFFFF"),
        draw.path(walls, stroke=HEDGE, width=4.4),
        draw.path(walls, stroke=HEDGE_LIGHT, width=1.5),
        nested_picture(goal, x0 - 43, exit_y - 26, 40),
        character_image(ctx, entry_x - figure * ctx.assets.character_aspect / 2, y0 - 1.5, figure),
        draw.start_dot((entry_x, y0 + 7), 3.4),
        draw.arrow((entry_x, y0 + 14.5), 90, 4.4, "#2FA36B"),
    ]
    path = m.solve() or []
    centers = [(x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell) for c, r in path]
    route = [(entry_x, y0 - 3), *centers, (x0 - 3, exit_y)]
    solution = draw.path(
        draw.polyline(route), stroke="#E0483A", width=1.8, stroke_dasharray="3.2 2.6", opacity=0.9
    )
    data = {
        "svg": draw.svg(w, h, "".join(body), "maze"),
        "svg_solved": draw.svg(w, h, "".join(body) + solution, "maze"),
    }
    answer = [f"الطريق الوحيد إلى {_ar(goal)} مرسوم بالخط الأحمر"]
    return Built(data, answer, m.problems())


def _ar(picture_id: str) -> str:
    return "ال" + strip_tashkeel(picture(picture_id).word_ar)


def _cloud(cx: float, cy: float, width: float) -> str:
    """A friendly cloud with a face, centred on (cx, cy)."""
    scale = width / 88
    x, y = cx - 50 * scale, cy - 47 * scale
    face = (
        '<ellipse cx="41" cy="52" rx="3" ry="3.6" fill="#2B2E4A"/><ellipse cx="59" cy="52" rx="3" ry="3.6" '
        'fill="#2B2E4A"/><circle cx="42" cy="50.8" r="1.1" fill="#fff"/><circle cx="60" cy="50.8" r="1.1" '
        'fill="#fff"/><path d="M45 59 Q50 63.5 55 59" fill="none" stroke="#2B2E4A" stroke-width="2.4" '
        'stroke-linecap="round"/><ellipse cx="34" cy="59" rx="4" ry="2.6" fill="#F08A7E" opacity="0.5"/>'
        '<ellipse cx="66" cy="59" rx="4" ry="2.6" fill="#F08A7E" opacity="0.5"/>'
    )
    inner = picture("cloud").inner("color", {"main": "#D7E9F8"})
    return (
        f'<svg x="{draw.n(x)}" y="{draw.n(y)}" width="{draw.n(100 * scale)}" height="{draw.n(100 * scale)}" '
        f'viewBox="0 0 100 100">{inner}{face}</svg>'
    )


DRILL_W, DRILL_H = 186.0, 190.0


def _rain(ctx: PageContext) -> str:
    """Clouds on top; under each, vertical rain lines to trace down to the flowers (top to bottom)."""
    clouds = int(ctx.page.params.get("clouds", 3))
    lines = int(ctx.page.params.get("lines", 3))
    w, h = DRILL_W, DRILL_H
    top, bottom = 50.0, 158.0
    step = w / clouds
    grass = draw.d_path(
        ("M", (0, h - 22)),
        ("C", (40, h - 30, 70, h - 16, 110, h - 24)),
        ("S", (170, h - 30, w, h - 22)),
        ("L", (w, h - 5)),
        ("Q", (w, h, w - 5, h)),
        ("L", (5, h)),
        ("Q", (0, h, 0, h - 5)),
    )
    body = [draw.el("path", d=grass + " Z", fill="#DDEFD6")]
    strokes: list[Stroke] = []
    for i in range(clouds):
        cx = w - step * (i + 0.5)  # right to left
        body.append(_cloud(cx, 26, 60))
        for k in range(lines):
            x = cx + (k - (lines - 1) / 2) * 14
            strokes.append(Stroke(f"M{draw.n(x)} {top} L{draw.n(x)} {bottom}"))
    for i in range(clouds):
        cx = w - step * (i + 0.5)
        body.append(nested_picture("flower", cx - 15, h - 33, 30))
    for j, s in enumerate(strokes):
        example = j == 0 and ctx.page.example
        body.append(draw.dotted(s, spacing=6.0, r=1.3))
        if example:
            body.append(draw.path(s.d, stroke=PENCIL, width=1.7))
        body.append(draw.start_dot(s.start, 2.6))
        body.append(draw.arrow((s.start[0], s.start[1] + 6.4), 90, 3.2))
        body.append(nested_picture("raindrop", s.end[0] - 3.2, s.end[1] + 1.5, 6.4))
    return "".join(body)


# themes (Addendum 6 §4.3): grass, waves and mountains follow the same shape
DRILLS: dict[str, Callable[[PageContext], str]] = {"rain": _rain}


@page_type("themed-pen-drill")
def themed_pen_drill(ctx: PageContext) -> Built:
    theme = str(ctx.page.params.get("theme", "rain"))
    if theme not in DRILLS:
        raise KeyError(f"no pen-drill theme {theme!r} yet (have: {', '.join(DRILLS)})")
    return Built({"svg": draw.svg(DRILL_W, DRILL_H, DRILLS[theme](ctx), "drill")})
