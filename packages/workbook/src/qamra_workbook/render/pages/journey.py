"""Journey pages (Addendum 6 §2, §4.13): the journey map with the child's character, and the certificate."""

from __future__ import annotations

import math
from itertools import pairwise

from markupsafe import Markup, escape

from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import art, draw
from qamra_workbook.render.pages.motor import character_image
from qamra_workbook.render.registry import Built, PageContext, page_type

# the journey map (Addendum 6 §2): think → observe → listen → hand → pen → trace → write → read → create.
# `label` is the plain key the plans use (`stops: [أفكر, …]`, `here: [أتتبع]`; marks are ignored when they
# are matched), `text` the vowelized name printed on the map for the child.
STOPS: tuple[dict[str, str], ...] = (
    {"label": "أفكر", "text": "أُفَكِّرُ", "icon": "brain", "color": "#8C79C9"},
    {"label": "ألاحظ", "text": "أُلاحِظُ", "icon": "eye", "color": "#3B9E90"},
    {"label": "أسمع", "text": "أَسْمَعُ", "icon": "ear", "color": "#4A95D3"},
    {"label": "أحرك يدي", "text": "أُحَرِّكُ يَدي", "icon": "hand", "color": "#E27D63"},
    {"label": "أمسك القلم", "text": "أُمْسِكُ القَلَمَ", "icon": "pencil", "color": "#EB9036"},
    {"label": "أتتبع", "text": "أَتَتَبَّعُ", "icon": "trace", "color": "#D96B93"},
    {"label": "أكتب", "text": "أَكْتُبُ", "icon": "write", "color": "#A26AB6"},
    {"label": "أقرأ", "text": "أَقْرَأُ", "icon": "book", "color": "#5A79CF"},
    {"label": "أحل وأبدع", "text": "أَحُلُّ وَأُبْدِعُ", "icon": "rainbow", "color": "#5A9E6C"},
)
ROAD, ROAD_EDGE = "#F6E7C8", "#E5CD9E"


def stop_key(label: object) -> str:
    """A stop's lookup key: its name without marks («أحرّك يدي» and «أُحَرِّكُ يَدي» are the same stop)."""
    return strip_tashkeel(str(label)).strip()


def stops_of(ctx: PageContext) -> list[dict[str, str]]:
    """The map's stops: labels as in the plan (`[أفكر, …]`) take the default icon, color and vowelized
    `text`; a stop can also be a mapping with its own `icon`, `color` and `text`."""
    defaults = {s["label"]: s for s in STOPS}
    out = []
    for raw in ctx.page.params.get("stops") or STOPS:
        stop = {"label": raw} if isinstance(raw, str) else {k: str(v) for k, v in raw.items()}
        key = stop_key(stop["label"])
        base = defaults.get(key, {"icon": "star", "color": "#E2A32A", "text": stop["label"]})
        out.append(
            {
                "label": key,
                "text": stop.get("text", base["text"]),
                "icon": stop.get("icon", base["icon"]),
                "color": stop.get("color", base["color"]),
            }
        )
    return out


MAP_W, MAP_H = 186.0, 190.0
ROWS_Y = (158.0, 101.0, 44.0)  # bottom to top: the journey climbs the page


def _positions(count: int) -> list[tuple[float, float]]:
    """Stops on three rows, snaking right to left, then left to right, then right to left again."""
    per_row = math.ceil(count / len(ROWS_Y))
    out = []
    for i in range(count):
        row, k = divmod(i, per_row)
        left, right = 44.0, (132.0 if row == 0 else 142.0)  # the first row leaves room for the child
        t = k / max(per_row - 1, 1)
        x = right - t * (right - left) if row % 2 == 0 else left + t * (right - left)
        out.append((x, ROWS_Y[row]))
    return out


def _road(points: list[tuple[float, float]]) -> str:
    """A smooth road through the stops: gentle waves along each row, round U-turns between rows."""
    commands: list[tuple[str, float | tuple[float, ...]]] = [("M", points[0])]
    for (x1, y1), (x2, y2) in pairwise(points):
        if abs(y1 - y2) < 1:  # along a row
            mid = (x1 + x2) / 2
            commands += [("Q", ((x1 + mid) / 2, y1 - 5, mid, y1)), ("Q", ((mid + x2) / 2, y1 + 5, x2, y2))]
        else:  # a U-turn on the side the row ended
            bulge = -36 if x1 < MAP_W / 2 else 36
            commands.append(("C", (x1 + bulge, y1, x2 + bulge, y2, x2, y2)))
    return draw.d_path(*commands)


def _stop(x: float, y: float, stop: dict[str, str], label: str) -> str:
    """A stop on the map: its icon, a star to colour, its name and its number (`label`, in the book's
    numerals)."""
    glyph = art.glyph(stop["icon"], "#FFFFFF", 2.3)
    color = stop["color"]
    return "".join(
        (
            draw.el("circle", cx=x, cy=y + 1.2, r=11.5, fill="#1C2140", opacity=0.12),
            draw.el("circle", cx=x, cy=y, r=11.5, fill="#FFFFFF"),
            draw.el("circle", cx=x, cy=y, r=9.8, fill=color),
            draw.el("svg", glyph, x=x - 6, y=y - 6, width=12, height=12, viewBox="0 0 24 24"),
            draw.el(
                "path",
                d=draw.star_points(x + 11.5, y - 10.5, 5.2, 2.4),
                fill="#FFFFFF",
                stroke="#E2A32A",
                stroke_width=0.9,
                stroke_linejoin="round",
            ),
            draw.el(
                "rect",
                x=x - 15,
                y=y + 13,
                width=30,
                height=8.4,
                rx=4.2,
                fill="#FFFFFF",
                stroke=color,
                stroke_width=0.6,
            ),
            draw.el(
                "text", str(escape(stop["text"])), x=x, y=y + 19.2, text_anchor="middle", class_="stop-text"
            ),
            draw.el("circle", cx=x - 9, cy=y - 9, r=3.2, fill=color, stroke="#FFFFFF", stroke_width=0.8),
            draw.el(
                "text",
                label,
                x=x - 9,
                y=y - 7.9,
                text_anchor="middle",
                class_="stop-num",
            ),
        )
    )


@page_type("journey-map")
def journey_map(ctx: PageContext) -> Built:
    stops = stops_of(ctx)
    problems = [] if 3 <= len(stops) <= 12 else [f"the map shows 3–12 stops, not {len(stops)}"]
    w, h = MAP_W, MAP_H
    positions = _positions(len(stops))
    road = _road([(176.0, ROWS_Y[0]), *positions, (14.0, ROWS_Y[-1])])
    hills = draw.d_path(
        ("M", (0, h - 40)),
        ("C", (40, h - 52, 80, h - 30, 120, h - 42)),
        ("S", (170, h - 50, w, h - 44)),
        ("L", (w, h - 8)),
        ("Q", (w, h, w - 8, h)),
        ("L", (8, h)),
        ("Q", (0, h, 0, h - 8)),
    )
    meadow = draw.d_path(
        ("M", (0, 72)),
        ("C", (30, 64, 60, 76, 96, 68)),
        ("S", (150, 58, w, 66)),
        ("L", (w, 108)),
        ("C", (150, 116, 110, 100, 70, 110)),
        ("S", (20, 118, 0, 112)),
    )
    body = [
        draw.el("rect", x=0, y=0, width=w, height=h, rx=8, fill="#F4F9FD"),
        draw.el("path", d=hills + " Z", fill="#E6F2DE"),
        draw.el("path", d=meadow + " Z", fill="#EEF6E8", opacity=0.8),
        draw.path(road, stroke=ROAD_EDGE, width=15),
        draw.path(road, stroke=ROAD, width=12.4),
        draw.path(road, stroke="#FFFFFF", width=0.9, stroke_dasharray="2.6 3.4", opacity=0.9),
    ]
    body += [
        _stop(x, y, s, ctx.num(k))
        for k, ((x, y), s) in enumerate(zip(positions, stops, strict=True), start=1)
    ]
    fx, fy = 14.0, ROWS_Y[-1]  # the finish flag
    body.append(
        draw.path(draw.d_path(("M", (fx, fy + 2)), ("L", (fx, fy - 24))), stroke="#7E5236", width=1.6)
    )
    flag = draw.d_path(("M", (fx, fy - 24)), ("L", (fx + 15, fy - 20)), ("L", (fx, fy - 15)))
    body.append(draw.el("path", d=flag + " Z", fill="#E5604E", stroke="#A7432D", stroke_width=0.6))
    body.append(character_image(ctx, 158, ROWS_Y[0] + 14, 60))
    return Built({"svg": draw.svg(w, h, "".join(body), "journey-map")}, None, problems)


def _ray(i: int, edge: int, rays: int = 16) -> str:
    """One corner of sunburst ray `i` on the certificate (a 100-unit box)."""
    a = math.radians(i * 360 / rays + (-4.5 if edge == 0 else 4.5))
    return f"{draw.n(50 + 48 * math.cos(a))} {draw.n(50 + 48 * math.sin(a))}"


def _star(x: float, y: float, r: float) -> str:
    return draw.star_points(x, y, r, r * 0.46)


def _rosette(cx: float, cy: float, outer: float, inner: float, points: int = 24) -> str:
    pts = []
    for k in range(points):
        r = outer if k % 2 == 0 else inner
        a = math.radians(k * 360 / points)
        pts.append(("M" if k == 0 else "L", (cx + r * math.cos(a), cy + r * math.sin(a))))
    return draw.d_path(*pts) + " Z"


MEDAL = Markup(  # nosec B704 (static art)
    '<svg viewBox="0 0 30 38" aria-hidden="true">'
    '<path d="M9 18 L4 36 L9 33 L12 37 L15 21 Z" fill="#E27D63"/>'
    '<path d="M21 18 L26 36 L21 33 L18 37 L15 21 Z" fill="#5A79CF"/>'
    + draw.el("path", d=_rosette(15, 14, 13, 11.2), fill="#E2A32A")
    + draw.el("circle", cx=15, cy=14, r=9.4, fill="#FCEFD2", stroke="#C98A1B", stroke_width=0.6)
    + draw.el(
        "path",
        d=draw.star_points(15, 14.6, 6, 2.7),
        fill="#F2B33D",
        stroke="#C98A1B",
        stroke_width=0.5,
        stroke_linejoin="round",
    )
    + "</svg>"
)


@page_type("certificate", frame="full")
def certificate(ctx: PageContext) -> Built:
    stops = stops_of(ctx)
    badges = [
        Markup('<span class="cert-stop" style="background: {}">{}</span>').format(
            s["color"], art.icon(s["icon"])
        )
        for s in stops
    ]
    data = {
        "line": ctx.text(str(ctx.page.params.get("line", "لَقَدْ {أَنْهَيْتَ/أَنْهَيْتِ} «رِحْلَتي الأولى لِلتَّعَلُّمِ»"))),
        "name": ctx.book.child.name,
        "date": "",  # left blank: the grown-up writes the day the child finishes, not the print date
        "character": ctx.assets.character.resolve().as_uri() if ctx.assets.character else "",
        "badges": badges,
        "star": _star,
        "ray": _ray,
        "medal": MEDAL,
    }
    return Built(data)
