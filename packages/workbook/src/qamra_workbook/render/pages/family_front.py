"""«مغامراتي مع عائلتي» front pages (Addendum 7 §4, §7): the title page with the child and the family, the
contents map of the twelve adventures, and «عائلتي» (a portrait to draw for everyone the parent entered).

Nothing here assumes a mother and a father: the family is whoever the parent listed (1–6 members), drawn by
the role they chose, and the child is always in the middle.
"""

from __future__ import annotations

import math
from typing import Any

from markupsafe import Markup

from qamra_workbook.render import art, draw
from qamra_workbook.render.pages.family import _balloon, _hill, family_group, family_of, uri
from qamra_workbook.render.pages.motor import nested_picture
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import section_style


def split_name(ctx: PageContext, template: str) -> tuple[str, str, str]:
    """A title around the child's name, so the name can be set in its own color: (before, name, after)."""
    before, found, after = template.partition("{child}")
    name = ctx.book.child.name if found else ""
    return ctx.text(before), name, ctx.text(after)


def title_art(ctx: PageContext) -> Markup:
    """The title page's landscape: a morning sky, the sun, clouds, balloons and hills for the family."""
    g = ctx.book.geometry
    w, h = g.page_w, g.page_h
    sky = f"sky-{ctx.page.id}"
    body = [
        f'<defs><linearGradient id="{sky}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{ctx.style.tint}"/><stop offset="0.62" stop-color="#FFFDF7"/>'
        "</linearGradient></defs>",
        draw.el("rect", x=0, y=0, width=w, height=h, fill=f"url(#{sky})"),
        draw.el("circle", cx=w - 16, cy=16, r=22, fill="#FFE7A3", opacity=0.55),
        nested_picture("sun", w - 31, 1, 30),
        nested_picture("cloud", 14, 20, 30),
        nested_picture("cloud", w - 92, h * 0.36, 24),
        nested_picture("cloud", 22, h * 0.42, 20),
    ]
    sparkles = ((40, 64, 2.6), (w - 22, 78, 2.2), (w * 0.5, 16, 2), (18, h * 0.3, 2.4), (w - 30, h * 0.5, 2))
    for x, y, r in sparkles:
        body.append(draw.el("path", d=draw.star_points(x, y, r, r * 0.45), fill="#F2B33D"))
    for x, y, color in ((12, h * 0.33, "#E4769D"), (22, h * 0.3, "#F2B33D"), (w - 30, h * 0.35, "#2E9FD6")):
        body += _balloon(x, y, color, x + 10, y + 34)
    body += [_hill(h - 92, 8, 0, "#CFE8C0", w, h), _hill(h - 72, 7, 1, "#B9DDA6", w, h)]
    body.append(_hill(h - 50, 6, 0, "#A6D293", w, h))
    for x, dy in ((16, 36), (w - 20, 30), (w * 0.3, 20), (w * 0.72, 24)):
        body.append(nested_picture("flower", x, h - dy, 12))
    return draw.svg(w, h, "".join(body), "tp-svg")


@page_type("title-page", frame="full")
def title_page(ctx: PageContext) -> Built:
    problems: list[str] = []
    family = family_of(ctx, problems)
    before, name, after = split_name(ctx, ctx.page.title)
    group, tags = Markup(""), list[dict[str, Any]]()
    if family is not None:
        group, tags = family_group(ctx, family, 186.0, 118.0)
    adventures = [section_style(k, "family") for k in ctx.page.params.get("adventures", [])]
    if not adventures:
        from qamra_workbook.render.sections import FAMILY

        adventures = [s for k, s in FAMILY.items() if k not in ("front", "back")]
    data = {
        "art": title_art(ctx),
        "before": before,
        "name": name,
        "after": after,
        "sub": ctx.text(ctx.page.instruction),
        "adventures": [{"icon": s.icon, "color": s.color} for s in adventures],
        "count": ctx.num(len(adventures)),
        "group": group,
        "tags": tags,
        "family": family.name if family else "",
        "city": family.city if family else "",
    }
    return Built(data, None, problems)


# ---- the contents map -----------------------------------------------------------------------------------

MAP_W, MAP_H = 186.0, 150.0
_ROWS = (17.0, 53.0, 89.0, 125.0)
_COLS = (153.0, 93.0, 33.0)  # right to left


def map_spots(count: int) -> list[tuple[float, float]]:
    """Where each stop sits on the winding road: three a row, right to left, then back, and so on."""
    spots = []
    for i in range(count):
        row, k = divmod(i, 3)
        cols = _COLS if row % 2 == 0 else tuple(reversed(_COLS))
        spots.append((cols[k], _ROWS[row % len(_ROWS)] + 36 * (row // len(_ROWS))))
    return spots


def map_road(rows: int) -> str:
    """The road through the rows (path data): straight along a row, a half-turn at the page's edge."""
    left, right, r = 22.0, 164.0, 18.0
    parts: list[tuple[str, float | tuple[float, ...]]] = [("M", (MAP_W - 1, _ROWS[0]))]
    for row in range(rows):
        y = _ROWS[0] + 36 * row
        going_left = row % 2 == 0
        end = left if going_left else right
        parts.append(("L", (end, y)))
        if row < rows - 1:
            sweep = 0 if going_left else 1
            parts.append(("A", (r, r, 0, 0, sweep, end, y + 2 * r)))
    return draw.d_path(*parts)


def map_finish(rows: int) -> tuple[float, float]:
    """Where the road ends: the trophy after the last row."""
    return (176.0 if rows % 2 == 0 else 10.0), _ROWS[0] + 36 * (rows - 1)


def map_art(stops: list[dict[str, Any]]) -> Markup:
    rows = max(1, math.ceil(len(stops) / 3))
    road = map_road(rows)
    body = [
        draw.path(road, stroke="#EBDDBE", width=13),
        draw.path(road, stroke="#FFF6E2", width=10.4),
        draw.path(road, stroke="#E0C58C", width=0.7, stroke_dasharray="2.4 2.8"),
    ]
    fx, fy = map_finish(rows)
    body += [
        draw.el("circle", cx=fx, cy=fy, r=7.5, fill="#FFF1C9", stroke="#F2B33D", stroke_width=0.8),
        draw.el(
            "svg",
            art.glyph("trophy", "#E2A32A", 2.2),
            x=fx - 5,
            y=fy - 5,
            width=10,
            height=10,
            viewBox="0 0 24 24",
        ),
    ]
    for (x, y), stop in zip(map_spots(len(stops)), stops, strict=True):
        body += [
            draw.el("circle", cx=x, cy=y + 1, r=10.5, fill="#1C2140", opacity=0.1),
            draw.el("circle", cx=x, cy=y, r=10.5, fill="#FFFFFF"),
            draw.el("circle", cx=x, cy=y, r=9, fill=stop["color"]),
        ]
    return draw.svg(MAP_W, _ROWS[0] + 36 * (rows - 1) + 18, "".join(body), "map-svg")


@page_type("toc")
def toc(ctx: PageContext) -> Built:
    """«خريطة المغامرات»: the twelve adventures as stops on one road, each with its page and a star the child
    colors when the adventure is done; the passport, the family, the challenge and the certificate below."""
    raw = list(ctx.page.params.get("stops", []))
    problems = [] if 1 <= len(raw) <= 12 else [f"the map shows 1–12 adventures, not {len(raw)}"]
    stops: list[dict[str, Any]] = []
    for (x, y), stop in zip(map_spots(len(raw)), raw, strict=True):
        style = section_style(str(stop["section"]), ctx.book.product)
        stops.append(
            {
                "x": x,
                "y": y,
                "icon": style.icon,
                "color": style.color,
                "deep": style.deep,
                "title": ctx.text(str(stop.get("title", style.name_ar))),
                "n": ctx.num(int(stop["n"])) if stop.get("n") else "",
                "k": ctx.num(len(stops) + 1),
            }
        )
    extras = [
        {"icon": str(x["icon"]), "title": ctx.text(str(x["title"])), "n": ctx.num(int(x["n"]))}
        for x in ctx.page.params.get("extras", [])
    ]
    rows = max(1, math.ceil(len(stops) / 3))
    data = {
        "map": map_art(stops) if stops else Markup(""),
        "map_h": _ROWS[0] + 36 * (rows - 1) + 18,
        "stops": stops,
        "extras": extras,
        "start": ctx.text("{ابْدَأْ/ابْدَئي} مِنْ هُنا"),
        "character": uri(ctx.assets.character),
    }
    return Built(data, None, problems)


# ---- «عائلتي» ------------------------------------------------------------------------------------------

FRAME_COLORS = ("#F2B33D", "#E4769D", "#2E9FD6", "#2FA36B", "#8C6CCB", "#F08A3E", "#23A094", "#D9486B")


@page_type("my-family")
def my_family(ctx: PageContext) -> Built:
    """A house with a portrait frame for everyone: the child first, then each member the parent entered (their
    name printed light, to write over), and one empty frame for whoever else the child loves."""
    problems: list[str] = []
    family = family_of(ctx, problems)
    members = list(family.members) if family else []
    frames = [{"name": ctx.book.child.name, "role": "أَنا", "child": True}]
    frames += [{"name": m.label, "role": m.role if m.name else "", "child": False} for m in members]
    frames.append({"name": "", "role": str(ctx.page.params.get("more", "وَمَنْ أَيْضًا؟")), "child": False})
    for i, frame in enumerate(frames):
        frame["color"] = FRAME_COLORS[i % len(FRAME_COLORS)]
    columns = 2 if len(frames) <= 4 else 3 if len(frames) <= 6 else 4  # portraits never get too narrow
    data = {
        "frames": frames,
        "columns": columns,
        "rows": math.ceil(len(frames) / columns),
        "house": ctx.text(str(ctx.page.params.get("house", "بَيْتُ عائِلَةِ {family_name}"))),
        "face_hint": ctx.text("{ارْسُمِ/ارْسُمي} الوَجْهَ"),
    }
    return Built(data, None, problems)
