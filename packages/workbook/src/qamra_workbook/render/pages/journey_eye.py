"""Journey eye-leads-hand pages (Addendum 6 §4.2, §4.9 in stage 1): pairs to join, shadows, the shorter road,
tangled strings, a spiral road and right-to-left rows. Roads and strings are generated, and the checks prove
the answer (the short road is clearly shorter, the strings really cross)."""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_kit import (
    H,
    W,
    card,
    join_columns,
    nested,
    person,
    picture,
    pid,
    silhouette,
    svg,
)
from qamra_workbook.render.pages.motor import character_image
from qamra_workbook.render.pages.workbook_common import ANSWER, ring_at
from qamra_workbook.render.people import person as figure
from qamra_workbook.render.registry import Built, PageContext, page_type

ROAD, ROAD_EDGE = "#F6E7C8", "#E5CD9E"
OUTLINE = "#2B2E4A"


BOAT_DOTS = {"1": "بنقطة واحدة", "2": "بنقطتين", "3": "بثلاث نقاط"}  # the answer key is for adults


def boat_name(spec: str) -> str:
    """The answer key's name for a boat: «1-below» → «قارب بنقطة واحدة تحته»."""
    count, where = spec.split("-")
    return f"قارب {BOAT_DOTS[count]} {'تحته' if where == 'below' else 'فوقه'}"


def boat(spec: str) -> str:
    """A boat like a letter body, with dots below or above (stage 1 meets ب ت ث without letters)."""
    count, where = spec.split("-")
    hull = (
        '<path d="M12 44 C14 72 86 72 88 44 L79 44 C77 61 23 61 21 44 Z" fill="#C98A5B" stroke="#2B2E4A" '
        'stroke-width="2.4" stroke-linejoin="round"/>'
        '<path d="M6 80 Q18 74 30 80 T54 80 T78 80 T96 80" fill="none" stroke="#8EC1EC" stroke-width="3"/>'
    )
    spots = {
        "1-below": [(50, 91)],
        "1-above": [(50, 28)],
        "2-above": [(40, 30), (60, 30)],
        "2-below": [(40, 91), (60, 91)],
        "3-above": [(38, 33), (62, 33), (50, 18)],
    }[f"{count}-{where}"]
    return hull + "".join(f'<circle cx="{x}" cy="{y}" r="5.4" fill="#1C2140"/>' for x, y in spots)


def _item(word: str, x: float, y: float, size: float) -> str:
    if word.startswith("boat:"):
        return nested(boat(word[5:]), x, y, size)
    return picture(word, x, y, size)


@page_type("connect-pairs")
def connect_pairs(ctx: PageContext) -> Built:
    """Join each picture on the right to its partner on the left (an animal to its food, a boat to its
    twin)."""
    pairs = [(str(a), str(b)) for a, b in ctx.page.params.get("pairs", [])]
    order = list(range(len(pairs)))
    shuffler = ctx.rng("pairs")
    while order == list(range(len(pairs))) and len(pairs) > 1:
        shuffler.shuffle(order)
    answer = [order.index(i) for i in range(len(pairs))]
    body = join_columns(
        lambda i, x, y, s: _item(pairs[i][0], x, y, s),
        lambda j, x, y, s: _item(pairs[order[j]][1], x, y, s),
        len(pairs),
        answer,
    )

    def name(w: str) -> str:
        return boat_name(w[5:]) if w.startswith("boat:") else PICTURES[pid(w)].word_ar

    problems = [] if 2 <= len(pairs) <= 4 else ["join 2–4 pairs"]
    return Built({"svg": svg(body)}, [f"{name(a)} ← {name(b)}" for a, b in pairs], problems)


def _figure(spec: dict[str, Any], x: float, y: float, size: float, shadow: bool) -> str:
    """A child with a prop (a ball, a balloon, a kite), standing in a size × size box, or its shadow."""
    kid = figure(spec.get("figure", "girl"), str(spec.get("outfit", "#E98AA6")))
    out = person(kid, x + size * 0.4, y + size, size * 0.95, shadow=shadow)
    prop = spec.get("prop")
    if prop:
        s = size * 0.36
        px, py = x + size * 0.62, y + (size * 0.08 if prop in ("balloon", "kite") else size * 0.64)
        out += silhouette(str(prop), px, py, s) if shadow else picture(str(prop), px, py, s)
    return out


@page_type("shadow-match")
def shadow_match(ctx: PageContext) -> Built:
    """Each picture on the right, the shadows on the left: join each to its own shadow."""
    raw = list(ctx.page.params.get("items", []))
    order = list(range(len(raw)))
    shuffler = ctx.rng("shadows")
    while order == list(range(len(raw))) and len(raw) > 1:
        shuffler.shuffle(order)

    def draw_item(i: int, x: float, y: float, s: float, shadow: bool) -> str:
        item = raw[i]
        if isinstance(item, dict):
            return _figure(item, x, y, s, shadow)
        return silhouette(str(item), x, y, s) if shadow else picture(str(item), x, y, s)

    body = join_columns(
        lambda i, x, y, s: draw_item(i, x, y, s, False),
        lambda j, x, y, s: draw_item(order[j], x, y, s, True),
        len(raw),
        [order.index(i) for i in range(len(raw))],
    )
    names = [
        PICTURES[pid(str(w))].word_ar if not isinstance(w, dict) else str(w.get("name", "")) for w in raw
    ]
    key = [f"{n}: الظل {ctx.num(order.index(i) + 1)}" for i, n in enumerate(names)]
    return Built({"svg": svg(body)}, key, [] if 2 <= len(raw) <= 4 else ["match 2–4 shadows"])


def road(d: str, width: float = 15.0) -> list[str]:
    return [
        draw.path(d, stroke=ROAD_EDGE, width=width + 2.6),
        draw.path(d, stroke=ROAD, width=width),
        draw.path(d, stroke="#FFFFFF", width=0.9, stroke_dasharray="2.6 3.4"),
    ]


def starter(ctx: PageContext, x: float, y_feet: float, height: float) -> str:
    """Who walks the road: the child's character, or a child figure when there is none."""
    if ctx.assets.character is not None:
        return character_image(ctx, x - height * ctx.assets.character_aspect / 2, y_feet, height)
    return person(figure("girl" if ctx.book.child.gender == "f" else "boy", "#6E95DB"), x, y_feet, height)


@page_type("shortest-path")
def shortest_path(ctx: PageContext) -> Built:
    """Two roads from the child (right) to the goal (left): a short one and a long winding one."""
    goal = pid(str(ctx.page.params.get("to", "school")))
    short_top = ctx.rng("roads").random() < 0.5

    def flip(y: float) -> float:  # the short road on top, or at the bottom
        return y if short_top else 216 - y

    start, end = (150.0, 108.0), (40.0, 108.0)
    short = f"M150 {flip(100)} C128 {flip(78)} 62 {flip(78)} 40 {flip(100)}"
    long = (
        f"M150 {flip(116)} C152 {flip(176)} 132 {flip(200)} 114 {flip(176)} C100 {flip(156)} 88 {flip(154)} "
        f"80 {flip(180)} C70 {flip(206)} 42 {flip(190)} 40 {flip(116)}"
    )
    a, b = Stroke(short).length, Stroke(long).length
    problems = (
        [] if b >= 1.4 * a else [f"the long road ({b:.0f} mm) is not clearly longer than the short ({a:.0f})"]
    )
    body = [card(0, 0, W, H, r=10, fill="#F4F9FD", stroke="none")]
    body += road(long) + road(short)
    body.append(draw.path(short, stroke=ANSWER, width=2, opacity=0.9, class_="key-line"))
    body.append(starter(ctx, start[0] + 16, start[1] + 18, 46))
    body.append(picture(goal, end[0] - 38, end[1] - 30, 44))
    return Built(
        {"svg": svg(body)}, [f"الطريق الأقصر هو الطريق {'العلوي' if short_top else 'السفلي'}"], problems
    )


def _crosses(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> bool:
    def side(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    for p1, p2 in pairwise(a):
        for q1, q2 in pairwise(b):
            if side(p1, p2, q1) * side(p1, p2, q2) < 0 and side(q1, q2, p1) * side(q1, q2, p2) < 0:
                return True
    return False


@page_type("overlapping-paths")
def overlapping_paths(ctx: PageContext) -> Built:
    """Balloons at the top, children at the bottom, strings that cross: follow each string to its owner."""
    colors = [str(c) for c in ctx.page.params.get("from", ["red", "blue"])]
    kids = [str(k) for k in ctx.page.params.get("to", ["boy", "girl"])]
    hexes = {"red": "#E5604E", "blue": "#5E86D6", "yellow": "#F7C84A", "green": "#7DB46C"}
    n = len(colors)
    tops = [W - 30 - k * (W - 60) / max(n - 1, 1) for k in range(n)]
    owner = list(reversed(range(n)))  # balloon k belongs to the child under the opposite balloon
    body = [card(0, 0, W, H, r=10, fill="#F4F9FD", stroke="none")]
    strings = []
    for k in range(n):
        x1, x2 = tops[k], tops[owner[k]]
        cx, mx = x2 + (30 if k % 2 else -30), (x1 + x2) / 2
        d = f"M{x1} 52 C{x1} 100 {cx} 110 {mx} 130 C{2 * mx - cx} 150 {x2} 150 {x2} 172"
        strings.append(Stroke(d))
        body.append(draw.path(d, stroke="#5B5F7A", width=1.5))
        body.append(
            draw.path(d, stroke=list(hexes.values())[k % 4], width=2.2, opacity=0.9, class_="key-line")
        )
        body.append(picture("balloon", x1 - 20, 8, 40, main=hexes.get(colors[k], colors[k])))
    for k, kid in enumerate(kids):
        body.append(
            person(
                figure("girl" if kid in ("girl", "بنت") else "boy", ("#6E95DB", "#E98AA6")[k % 2]),
                tops[k],
                202,
                36,
            )
        )
    crossed = n < 2 or _crosses(strings[0].polyline, strings[1].polyline)
    key = [f"البالون {c}: للطفل {ctx.num(owner[k] + 1)} من اليمين" for k, c in enumerate(colors)]
    return Built({"svg": svg(body)}, key, [] if crossed else ["the strings must cross"])


@page_type("spiral-path")
def spiral_path(ctx: PageContext) -> Built:
    """A wide spiral road from the snail (outside) to the leaf (centre): stay inside the road."""
    cx, cy, turns = W / 2, H / 2 + 4, 1.8
    pts = []
    for i in range(121):
        t = i / 120
        a = -math.pi / 2 + t * turns * 2 * math.pi
        r = 84 - 64 * t
        pts.append((cx + r * math.cos(a) * 1.05, cy + r * math.sin(a)))
    d = draw.polyline(pts)
    s = Stroke(d)
    body = [card(0, 0, W, H, r=10, fill="#F2F8EC", stroke="none"), *road(d, 16)]
    body.append(draw.dotted(s, spacing=5.0, r=1.2))
    body.append(draw.start_dot(s.start, 2.8))
    (px, py), angle = s.at(0.04)
    body.append(draw.arrow((px, py), angle, 4))
    body.append(picture(str(ctx.page.params.get("from", "snail")), s.start[0] - 44, s.start[1] - 16, 34))
    body.append(picture(str(ctx.page.params.get("to", "leaf")), s.end[0] - 13, s.end[1] - 13, 26))
    return Built({"svg": svg(body)})


@page_type("rtl-path")
def rtl_path(ctx: PageContext) -> Built:
    """Rows of pictures on a road from right to left: follow with a finger and name each picture in order."""
    stops = [str(w) for w in ctx.page.params.get("stops", [])]
    rows = int(ctx.page.params.get("rows", 3))
    per = max(1, math.ceil(len(stops) / rows))
    pitch = H / rows
    body = []
    for r in range(rows):
        y = r * pitch + pitch / 2 + 10
        d = f"M{W - 14} {y} L14 {y}"
        body += road(d, 13)
        body.append(draw.start_dot((W - 14, y), 3))
        body.append(draw.arrow((12, y), 180, 5))
        row = stops[r * per : (r + 1) * per]
        for k, w in enumerate(row):
            x = W - 30 - (k + 0.5) * (W - 60) / len(row)
            body.append(picture(w, x - 19, y - 44, 38))
        if r == 0 and ctx.page.example:
            body.append(draw.path(f"M{W - 14} {y} L{W - 70} {y}", stroke="#3D4262", width=1.6))
    body.append(ring_at(W - 14, pitch / 2 + 10, 6, 6))
    return Built(
        {"svg": svg(body)}, ["من اليمين إلى اليسار: " + "، ".join(PICTURES[pid(w)].word_ar for w in stops)]
    )


@page_type("journey-tangled")
def tangled(ctx: PageContext) -> Built:
    """Three or four tangled strings: kites (`from` colours) to children, or the child to places (`to`
    pictures, `answer` the right place). Every string crosses another; the key draws each in its colour."""
    colors = [str(c) for c in ctx.page.params.get("from", [])]
    ends = [str(k) for k in ctx.page.params.get("to", ["boy", "girl", "boy"])]
    n = len(ends)
    child_start = not colors
    hexes = ["#E5604E", "#5E86D6", "#F7C84A", "#7DB46C"]
    tops = [W - 26 - k * (W - 52) / max(n - 1, 1) for k in range(n)]
    owner = list(range(n))
    shuffler = ctx.rng("tangle")
    while any(owner[k] == k for k in range(n)):
        shuffler.shuffle(owner)
    body = [card(0, 0, W, H, r=10, fill="#F4F9FD", stroke="none")]
    strings = []
    for k in range(n):
        x1, x2 = tops[k], tops[owner[k]]
        cx, mx = x2 + (28 if k % 2 else -28), (x1 + x2) / 2
        d = f"M{x1} 50 C{x1} 96 {cx} 108 {mx} 126 C{2 * mx - cx} 146 {x2} 148 {x2} 168"
        strings.append(Stroke(d))
        body.append(draw.path(d, stroke="#5B5F7A", width=1.4))
        body.append(draw.path(d, stroke=hexes[k % 4], width=2.2, opacity=0.9, class_="key-line"))
        if child_start:
            if k == 0:
                body.append(starter(ctx, x1, 48, 40))
        else:
            body.append(picture("kite", x1 - 18, 8, 36, main=hexes[k % 4]))
    for k, end in enumerate(ends):
        if end in ("boy", "girl", "ولد", "بنت"):
            body.append(
                person(
                    figure(
                        "girl" if end in ("girl", "بنت") else "boy",
                        ("#6E95DB", "#E98AA6", "#86BF72", "#F2A65A")[k % 4],
                    ),
                    tops[k],
                    202,
                    34,
                )
            )
        else:
            body.append(picture(end, tops[k] - 16, 170, 32))
    crossed = all(
        any(_crosses(strings[a].polyline, strings[b].polyline) for b in range(n) if b != a) for a in range(n)
    )
    if child_start:
        answer = str(ctx.page.params.get("answer", ends[owner[0]]))
        key = [f"{ctx.text('{child}')} يصل إلى: {PICTURES[pid(ends[owner[0]])].word_ar}"]
        problems = (
            []
            if crossed and ends[owner[0]] == answer
            else ["the child's string must lead to the answer and cross the others"]
        )
        if ends[owner[0]] != answer and answer in ends:  # swap so the child's string ends at the answer
            j = ends.index(answer)
            ends[owner[0]], ends[j] = ends[j], ends[owner[0]]
            problems = [] if crossed else ["the strings must cross"]
            key = [f"{ctx.text('{child}')} يصل إلى: {PICTURES[pid(answer)].word_ar}"]
    else:
        key = [f"الطائرة {c}: للطفل {ctx.num(owner[k] + 1)} من اليمين" for k, c in enumerate(colors)]
        problems = [] if crossed else ["the strings must cross"]
    return Built({"svg": svg(body)}, key, problems)
