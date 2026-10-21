"""«دَفْتَري» (My Sketchbook): the art of the interior pages, drawn in code as line art (no AI).

Every interior page has a prompt band at the top (the text, set by the page template in a font, never here),
then this module's drawing: one SVG of exactly 186 × 238 mm holding the page's frame, small decorations that
belong to the prompt, and, on the «أَكْمِلِ الرَّسْمَةَ» pages, the half-drawing the child finishes.

    art_svg("frame-stars")              # the complete <svg> of a blank framed page (line mode: K only)
    ART["finish-butterfly"](pen, w, h)  # the body only, for composing

House rules on top of `coloring.ink`'s:

- most of the page stays free to draw: decorations live in the corners and along the edges;
- decorations are line art the child can colour too (white shapes, black outlines); the frame itself and
  pure ornament may use thinner lines (1.2–1.6 mm) than a colouring area's 2.6 mm outline;
- a half-drawing uses the normal 2.6 mm line for the drawn part and a dotted guide (≥ 1.4 mm dots) where a
  younger child may trace the rest;
- no text, letters or digits inside a drawing (the prompt and the page number are the template's).

The date page's writing lines are drawn here too; `DATE_LINES` tells the template where they are so it can
set their labels («عُمْري … سَنَوات», «التّاريخ») next to them.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from qamra_workbook.coloring.ink import (
    FINE,
    INK,
    MAIN,
    PAPER,
    Mode,
    Pen,
    Point,
    c,
    crescent_d,
    e,
    fmt,
    p,
    place,
    polar,
    poly,
    rect,
    rounded_star,
    scallop,
    scallop_d,
    seg,
    smooth,
    svg,
    wave_d,
)
from qamra_workbook.coloring.parts.common import bird_v, cloud, flower, leaf_d, poppy, tuft

W, H = 186.0, 238.0  # mm: the drawing area under the prompt band
FRAME = 1.6  # mm: the frame line
ORNAMENT = 1.3  # mm: thin ornament lines (an inner frame, dashes)
DECO = 2.0  # mm: outlines of small decorations
INSET = 2.0  # the frame's distance from the edge of the drawing area (its line stays inside)
RADIUS = 9.0  # the frame's corner radius

Art = Callable[[Pen, float, float], str]
ART: dict[str, Art] = {}


def art(art_id: str) -> Callable[[Art], Art]:
    def register(draw: Art) -> Art:
        if art_id in ART:
            raise ValueError(f"sketchbook art {art_id} is registered twice")
        ART[art_id] = draw
        return draw

    return register


def art_svg(art_id: str, mode: Mode = "line", w: float = W, h: float = H) -> str:
    """The complete `<svg>` (w × h mm) of one page's art: white paper, the frame, its decorations."""
    try:
        draw = ART[art_id]
    except KeyError:
        raise KeyError(f"no sketchbook art {art_id!r}") from None
    background = f'<rect x="0" y="0" width="{fmt(w)}" height="{fmt(h)}" fill="{PAPER}"/>'
    return svg(w, h, background + draw(Pen(mode=mode), w, h))


# ---- line helpers ------------------------------------------------------------------------------------------


def dotted(pen: Pen, *elements: str, weight: float = 1.7, gap: float = 4.4) -> str:
    """A dotted guide (round dots `weight` mm across, `gap` mm apart) the child traces or finishes."""
    return (
        f'<g fill="none" stroke="{INK}" stroke-width="{pen.w(weight)}" stroke-linecap="round" '
        f'stroke-linejoin="round" stroke-dasharray="0 {pen.w(gap)}">{"".join(elements)}</g>'
    )


def dashed(pen: Pen, *elements: str, weight: float = ORNAMENT, dash: float = 4.0, gap: float = 3.4) -> str:
    """A dashed ornament line (a stitched inner frame, a writing line)."""
    return (
        f'<g fill="none" stroke="{INK}" stroke-width="{pen.w(weight)}" stroke-linecap="round" '
        f'stroke-linejoin="round" stroke-dasharray="{pen.w(dash)} {pen.w(gap)}">{"".join(elements)}</g>'
    )


def border(
    pen: Pen, w: float, h: float, inset: float = INSET, r: float = RADIUS, weight: float = FRAME
) -> str:
    """The plain rounded frame line around the drawing area."""
    return pen.stroke(rect(inset, inset, w - 2 * inset, h - 2 * inset, r), weight=weight)


def heart_d(cx: float, cy: float, s: float) -> str:
    """A plump heart `s` wide centred on (cx, cy)."""
    hw = s / 2
    top, dip, tip = cy - s * 0.36, cy - s * 0.2, cy + s * 0.46
    return (
        f"M{fmt(cx)} {fmt(dip)} "
        f"C{fmt(cx - hw * 0.25)} {fmt(top - s * 0.12)} {fmt(cx - hw * 1.08)} {fmt(top - s * 0.06)} "
        f"{fmt(cx - hw)} {fmt(cy - s * 0.04)} "
        f"C{fmt(cx - hw * 0.94)} {fmt(cy + s * 0.2)} "
        f"{fmt(cx - hw * 0.4)} {fmt(cy + s * 0.3)} {fmt(cx)} {fmt(tip)} "
        f"C{fmt(cx + hw * 0.4)} {fmt(cy + s * 0.3)} {fmt(cx + hw * 0.94)} {fmt(cy + s * 0.2)} "
        f"{fmt(cx + hw)} {fmt(cy - s * 0.04)} "
        f"C{fmt(cx + hw * 1.08)} {fmt(top - s * 0.06)} {fmt(cx + hw * 0.25)} {fmt(top - s * 0.12)} "
        f"{fmt(cx)} {fmt(dip)} Z"
    )


def heart(cx: float, cy: float, s: float) -> str:
    return p(heart_d(cx, cy, s))


def sparkle(cx: float, cy: float, r: float) -> str:
    """A four-point twinkle (a soft diamond star)."""
    k = r * 0.22
    return p(
        f"M{fmt(cx)} {fmt(cy - r)} Q{fmt(cx + k)} {fmt(cy - k)} {fmt(cx + r)} {fmt(cy)} "
        f"Q{fmt(cx + k)} {fmt(cy + k)} {fmt(cx)} {fmt(cy + r)} "
        f"Q{fmt(cx - k)} {fmt(cy + k)} {fmt(cx - r)} {fmt(cy)} "
        f"Q{fmt(cx - k)} {fmt(cy - k)} {fmt(cx)} {fmt(cy - r)} Z"
    )


def stars(pen: Pen, spots: Sequence[tuple[float, float, float]], weight: float = DECO) -> str:
    """Soft five-point stars at (x, y, r)."""
    return pen.shape(*(rounded_star(x, y, r) for x, y, r in spots), weight=weight)


def specks(pen: Pen, spots: Sequence[tuple[float, float]], r: float = 1.3) -> str:
    """Tiny solid dots: a sprinkle around a decoration."""
    return pen.solid(*(c(x, y, r) for x, y in spots))


# ---- small parts (local mm, see `coloring.ink` for the origin convention) ----------------------------------

_MOON = "M64.69 12.79 A40 40 0 1 0 76.85 79.65 A34 34 0 0 1 64.69 12.79 Z"


def moon_friend(pen: Pen, *, sleepy: bool = False, star: bool = True) -> str:
    """Qamra's smiling crescent moon («قمورة») about 80 units tall, centred on its origin."""
    body = [pen.shape(p(_MOON))]
    if star:
        body.append(pen.shape(p("M86 18 L88.4 25.6 L96 28 L88.4 30.4 L86 38 L83.6 30.4 L76 28 L83.6 25.6 Z")))
    if sleepy:
        body.append(pen.stroke(p("M15.5 49 Q19.5 53 23.5 49"), p("M27.5 48 Q31.5 52 35.5 48"), weight=FINE))
    else:
        body.append(pen.solid(e(19.5, 49, 3.4, 4.2), e(31, 48, 3.4, 4.2)))
        body.append(f'<g fill="{PAPER}">{c(20.6, 47.6, 1.2)}{c(32.1, 46.6, 1.2)}</g>')
    body.append(pen.stroke(p("M20 58 Q25.5 63.5 31 57.5"), weight=FINE))
    return f'<g transform="translate(-50 -50)">{"".join(body)}</g>'


def crayon(pen: Pen, length: float = 62.0, width: float = 11.0) -> str:
    """A wax crayon lying along +x, centred on its origin (the tip to the right)."""
    hw, back, tip_l = width / 2, -length / 2, width * 1.15
    neck = length / 2 - tip_l
    body = p(
        f"M{fmt(back + 2.5)} {fmt(-hw)} L{fmt(neck)} {fmt(-hw)} "
        f"L{fmt(neck)} {fmt(hw)} L{fmt(back + 2.5)} {fmt(hw)} "
        f"Q{fmt(back)} {fmt(hw)} {fmt(back)} {fmt(hw - 2.5)} L{fmt(back)} {fmt(-hw + 2.5)} "
        f"Q{fmt(back)} {fmt(-hw)} {fmt(back + 2.5)} {fmt(-hw)} Z"
    )
    cone = p(
        f"M{fmt(neck)} {fmt(-hw)} L{fmt(length / 2 - 2.2)} {fmt(-1.6)} "
        f"Q{fmt(length / 2 + 0.6)} 0 {fmt(length / 2 - 2.2)} {fmt(1.6)} L{fmt(neck)} {fmt(hw)} Z"
    )
    band1, band2 = back + length * 0.2, neck - length * 0.14
    wrapper = [seg(band1, -hw, band1, hw), seg(band2, -hw, band2, hw)]
    wave = p(
        f"M{fmt(band1 + 4)} 0 Q{fmt(band1 + 8)} {fmt(-hw * 0.55)} {fmt(band1 + 12)} 0 "
        f"T{fmt(band1 + 20)} 0 T{fmt(band1 + 28)} 0"
    )
    return pen.shape(body) + pen.shape(cone) + pen.stroke(*wrapper, wave, weight=1.6)


def pencil(pen: Pen, length: float = 70.0, width: float = 10.0) -> str:
    """A pencil lying along +x, centred on its origin: an eraser, a hexagon body (two facet lines), a tip."""
    hw, back, tip_l = width / 2, -length / 2, width * 1.6
    neck = length / 2 - tip_l
    eraser = p(
        f"M{fmt(back + 9)} {fmt(-hw)} L{fmt(back + 3)} {fmt(-hw)} "
        f"Q{fmt(back)} {fmt(-hw)} {fmt(back)} {fmt(-hw + 3)} "
        f"L{fmt(back)} {fmt(hw - 3)} Q{fmt(back)} {fmt(hw)} "
        f"{fmt(back + 3)} {fmt(hw)} L{fmt(back + 9)} {fmt(hw)} Z"
    )
    ferrule = rect(back + 9, -hw, 6, width)
    body = rect(back + 15, -hw, neck - back - 15, width)
    wood = p(
        f"M{fmt(neck)} {fmt(-hw)} L{fmt(length / 2 - tip_l * 0.36)} {fmt(-hw * 0.36)} "
        f"L{fmt(length / 2 - tip_l * 0.36)} {fmt(hw * 0.36)} L{fmt(neck)} {fmt(hw)} Z"
    )
    lead = p(
        f"M{fmt(length / 2 - tip_l * 0.36)} {fmt(-hw * 0.36)} L{fmt(length / 2)} 0 "
        f"L{fmt(length / 2 - tip_l * 0.36)} {fmt(hw * 0.36)} Z"
    )
    facets = [seg(back + 15, -hw / 3, neck, -hw / 3), seg(back + 15, hw / 3, neck, hw / 3)]
    return (
        pen.shape(eraser, ferrule, body, wood)
        + pen.stroke(*facets, weight=1.4)
        + pen.solid(lead)
        + pen.stroke(lead, weight=1.4)
    )


def balloon(pen: Pen, r: float = 12.0, string: float = 34.0, sway: float = 1.0, lean: float = 0.0) -> str:
    """A balloon with its knot and a wavy string, the balloon's centre on the origin."""
    ry = r * 1.18
    body = p(
        f"M0 {fmt(ry)} C{fmt(-r * 1.38)} {fmt(ry * 0.72)} {fmt(-r * 1.18)} {fmt(-ry * 1.02)} 0 {fmt(-ry)} "
        f"C{fmt(r * 1.18)} {fmt(-ry * 1.02)} {fmt(r * 1.38)} {fmt(ry * 0.72)} 0 {fmt(ry)} Z"
    )
    knot = p(f"M0 {fmt(ry)} L{fmt(-2.6)} {fmt(ry + 3.6)} L{fmt(2.6)} {fmt(ry + 3.6)} Z")
    y0 = ry + 3.6
    cord = p(
        f"M0 {fmt(y0)} C{fmt(5 * sway)} {fmt(y0 + string * 0.3)} {fmt(-5 * sway)} {fmt(y0 + string * 0.6)} "
        f"{fmt(1.5 * sway + lean)} {fmt(y0 + string)}"
    )
    shine = p(
        f"M{fmt(-r * 0.55)} {fmt(-ry * 0.25)} Q{fmt(-r * 0.5)} "
        f"{fmt(-ry * 0.7)} {fmt(-r * 0.1)} {fmt(-ry * 0.78)}"
    )
    return pen.stroke(cord, weight=1.4) + pen.shape(body, knot) + pen.stroke(shine, weight=1.6)


def gift(pen: Pen, w: float = 26.0) -> str:
    """A wrapped present standing on its origin: a box, a lid, a ribbon and a bow."""
    h = w * 0.78
    lid_h = w * 0.22
    box = rect(-w / 2 + 1.5, -h, w - 3, h - 0, 1.5)
    lid = rect(-w / 2, -h - lid_h + 1, w, lid_h, 1.8)
    band = rect(-w * 0.09, -h - lid_h + 1, w * 0.18, h + lid_h - 1)
    top = -h - lid_h + 1
    bow = [
        p(
            f"M0 {fmt(top)} C{fmt(-w * 0.12)} {fmt(top - w * 0.32)} {fmt(-w * 0.42)} {fmt(top - w * 0.2)} "
            f"{fmt(-w * 0.2)} {fmt(top)} Z"
        ),
        p(
            f"M0 {fmt(top)} C{fmt(w * 0.12)} {fmt(top - w * 0.32)} {fmt(w * 0.42)} {fmt(top - w * 0.2)} "
            f"{fmt(w * 0.2)} {fmt(top)} Z"
        ),
    ]
    return pen.shape(box, lid, weight=DECO) + pen.shape(band, *bow, weight=DECO)


def paw(pen: Pen, size: float = 14.0) -> str:
    """A paw print (a pad and four toes) centred on its origin, toes up."""
    s = size
    pad = p(
        f"M0 {fmt(-s * 0.08)} C{fmt(s * 0.36)} {fmt(-s * 0.08)} "
        f"{fmt(s * 0.52)} {fmt(s * 0.34)} {fmt(s * 0.34)} "
        f"{fmt(s * 0.44)} C{fmt(s * 0.18)} {fmt(s * 0.52)} {fmt(-s * 0.18)} {fmt(s * 0.52)} {fmt(-s * 0.34)} "
        f"{fmt(s * 0.44)} C{fmt(-s * 0.52)} {fmt(s * 0.34)} "
        f"{fmt(-s * 0.36)} {fmt(-s * 0.08)} 0 {fmt(-s * 0.08)} Z"
    )
    toes = [
        e(-s * 0.46, -s * 0.2, s * 0.14, s * 0.18, -25),
        e(-s * 0.17, -s * 0.46, s * 0.14, s * 0.19, -8),
        e(s * 0.17, -s * 0.46, s * 0.14, s * 0.19, 8),
        e(s * 0.46, -s * 0.2, s * 0.14, s * 0.18, 25),
    ]
    return pen.shape(pad, *toes, weight=DECO)


def olive_branch(pen: Pen, length: float = 72.0, olives: int = 3, bend: float = -8.0) -> str:
    """An olive twig growing from the origin along +x: slim leaves on both sides, olives on short stalks."""
    end = (length, bend * 0.4)

    def at(t: float) -> Point:
        return length * t, 2 * t * (1 - t) * bend * 1.6 + t * t * bend * 0.4

    stem = p(f"M0 0 Q{fmt(length * 0.5)} {fmt(bend * 1.6)} {fmt(end[0])} {fmt(end[1])}")
    leaves, stalks, fruit = [], [], []
    n = 6
    for i in range(n):
        t = 0.12 + 0.82 * i / n
        x, y = at(t)
        side = -1 if i % 2 == 0 else 1
        leaves.append(leaf_d(x, y, length * 0.24, length * 0.065, side * 42))
    for k in range(olives):
        t = 0.3 + 0.5 * k / max(1, olives - 1) if olives > 1 else 0.5
        x, y = at(t)
        side = 1 if k % 2 == 0 else -1
        ox, oy = x + 3, y + side * 8.5
        stalks.append(
            p(f"M{fmt(x)} {fmt(y)} Q{fmt(x + 3)} {fmt(y + side * 3)} {fmt(ox)} {fmt(oy - side * 3.6)}")
        )
        fruit.append(e(ox, oy, 3.6, 4.8, -15))
    leaves.append(leaf_d(end[0], end[1], length * 0.22, length * 0.06, bend * 0.4))
    return (
        pen.stroke(stem, *stalks, weight=DECO)
        + pen.shape(*(p(d) for d in leaves), weight=DECO)
        + pen.shape(*fruit, weight=DECO)
    )


def raindrop(cx: float, cy: float, s: float) -> str:
    return p(
        f"M{fmt(cx)} {fmt(cy - s)} C{fmt(cx + s * 0.25)} "
        f"{fmt(cy - s * 0.4)} {fmt(cx + s * 0.62)} {fmt(cy - s * 0.05)} "
        f"{fmt(cx + s * 0.62)} {fmt(cy + s * 0.32)} A{fmt(s * 0.62)} "
        f"{fmt(s * 0.62)} 0 0 1 {fmt(cx - s * 0.62)} "
        f"{fmt(cy + s * 0.32)} C{fmt(cx - s * 0.62)} "
        f"{fmt(cy - s * 0.05)} {fmt(cx - s * 0.25)} {fmt(cy - s * 0.4)} "
        f"{fmt(cx)} {fmt(cy - s)} Z"
    )


def umbrella(pen: Pen, w: float = 40.0) -> str:
    """An open umbrella standing on its handle's hook (origin at the hook's bottom)."""
    r = w / 2
    top = -w * 1.15
    canopy_y = top + r * 0.95
    scallops = ""
    n = 4
    for i in range(n):
        x1 = r - w * i / n
        x2 = r - w * (i + 1) / n
        scallops += f" Q{fmt((x1 + x2) / 2)} {fmt(canopy_y - r * 0.18)} {fmt(x2)} {fmt(canopy_y)}"
    canopy = p(
        f"M{fmt(-r)} {fmt(canopy_y)} C{fmt(-r)} {fmt(top - r * 0.25)} "
        f"{fmt(r)} {fmt(top - r * 0.25)} {fmt(r)} "
        f"{fmt(canopy_y)}{scallops} Z"
    )
    ribs = [
        p(
            f"M0 {fmt(top + 0.5)} Q{fmt(-r * 0.3)} {fmt(top + r * 0.4)} "
            f"{fmt(-r * 0.5)} {fmt(canopy_y - r * 0.17)}"
        ),
        p(f"M0 {fmt(top + 0.5)} L0 {fmt(canopy_y - r * 0.17)}"),
        p(
            f"M0 {fmt(top + 0.5)} Q{fmt(r * 0.3)} {fmt(top + r * 0.4)} "
            f"{fmt(r * 0.5)} {fmt(canopy_y - r * 0.17)}"
        ),
    ]
    handle = p(f"M0 {fmt(canopy_y - r * 0.12)} L0 {fmt(-6)} A4 4 0 0 1 -8 -6")
    tip = c(0, top - 1.8, 1.8)
    return (
        pen.stroke(handle, weight=MAIN) + pen.shape(canopy) + pen.stroke(*ribs, weight=1.6) + pen.shape(tip)
    )


def puddle(pen: Pen, w: float = 34.0) -> str:
    h = w * 0.2
    return pen.shape(
        smooth(
            [(-w / 2, 0), (-w * 0.3, -h), (w * 0.1, -h * 0.8), (w * 0.45, -h * 0.9), (w / 2, 0), (0, h * 0.6)]
        ),
        weight=DECO,
    )


def shell(pen: Pen, w: float = 22.0) -> str:
    """A scallop shell standing on its hinge (the origin)."""
    h = w * 0.9
    fan = p(
        f"M{fmt(-w * 0.14)} 0 L{fmt(-w / 2)} {fmt(-h * 0.55)} Q{fmt(-w * 0.45)} {fmt(-h)} 0 {fmt(-h)} "
        f"Q{fmt(w * 0.45)} {fmt(-h)} {fmt(w / 2)} {fmt(-h * 0.55)} L{fmt(w * 0.14)} 0 Z"
    )
    hinge = p(
        f"M{fmt(-w * 0.14)} 0 L{fmt(-w * 0.3)} {fmt(h * 0.12)} "
        f"L{fmt(w * 0.3)} {fmt(h * 0.12)} L{fmt(w * 0.14)} 0 Z"
    )
    ribs = [p(f"M0 0 L{fmt(x * w)} {fmt(-h * (0.9 - abs(x) * 0.5))}") for x in (-0.3, -0.12, 0.12, 0.3)]
    return pen.shape(hinge, fan, weight=DECO) + pen.stroke(*ribs, weight=1.4)


def starfish(pen: Pen, r: float = 13.0) -> str:
    return pen.shape(rounded_star(0, 0, r, r * 0.46), weight=DECO) + pen.solid(
        *(c(*polar(0, 0, r * 0.45, -90 + 72 * i), 1.0) for i in range(5)), c(0, 0, 1.1)
    )


def basket(pen: Pen, w: float = 40.0) -> str:
    """A woven harvest basket standing on its origin, with a handle and olives inside."""
    h = w * 0.55
    top = -h
    handle = p(
        f"M{fmt(-w * 0.38)} {fmt(top)} C{fmt(-w * 0.38)} {fmt(top - h * 1.1)} "
        f"{fmt(w * 0.38)} {fmt(top - h * 1.1)} {fmt(w * 0.38)} {fmt(top)}"
    )
    olives = [e(x * w, top - 1.5 + abs(x) * 6, 4.2, 3.2, x * 60) for x in (-0.28, -0.1, 0.08, 0.26)]
    body = p(
        f"M{fmt(-w / 2)} {fmt(top)} L{fmt(w / 2)} {fmt(top)} "
        f"L{fmt(w * 0.38)} 0 Q0 {fmt(2)} {fmt(-w * 0.38)} 0 Z"
    )
    rim = rect(-w / 2 - 1.5, top - 2.5, w + 3, 5, 2.5)
    weave = [
        p(f"M{fmt(-w * 0.46)} {fmt(top + h * 0.38)} L{fmt(w * 0.46)} {fmt(top + h * 0.38)}"),
        p(f"M{fmt(-w * 0.42)} {fmt(top + h * 0.7)} L{fmt(w * 0.42)} {fmt(top + h * 0.7)}"),
    ]
    weave += [seg(x * w, top + 2.5, x * w * 0.82, -0.5) for x in (-0.25, 0, 0.25)]
    return (
        pen.stroke(handle, weight=MAIN)
        + pen.shape(*olives, weight=DECO)
        + pen.shape(body)
        + pen.stroke(*weave, weight=1.4)
        + pen.shape(rim, weight=DECO)
    )


def sun_face(pen: Pen, r: float = 14.0, rays: int = 10, smile: bool = True) -> str:
    """A round sun with soft rays and, with `smile`, a happy face; centred on its origin."""
    out = []
    for i in range(rays):
        a = 360 * i / rays
        x1, y1 = polar(0, 0, r + 3, a - 8)
        x2, y2 = polar(0, 0, r + 10, a)
        x3, y3 = polar(0, 0, r + 3, a + 8)
        out.append(p(f"M{fmt(x1)} {fmt(y1)} Q{fmt(x2)} {fmt(y2)} {fmt(x3)} {fmt(y3)} Z"))
    face = ""
    if smile:
        face = pen.solid(
            e(-r * 0.33, -r * 0.1, r * 0.09, r * 0.12), e(r * 0.33, -r * 0.1, r * 0.09, r * 0.12)
        )
        face += pen.stroke(
            p(f"M{fmt(-r * 0.35)} {fmt(r * 0.25)} Q0 {fmt(r * 0.58)} {fmt(r * 0.35)} {fmt(r * 0.25)}"),
            weight=FINE,
        )
    return pen.shape(*out, weight=DECO) + pen.shape(c(0, 0, r)) + face


def tin_plant(pen: Pen, w: float = 22.0, kind: str = "geranium") -> str:
    """A flower growing in an old tin can, as on a grandmother's steps; the can stands on the origin."""
    h = w * 0.95
    can = rect(-w / 2, -h, w, h, 2)
    ridges = [seg(-w / 2, -h * 0.25, w / 2, -h * 0.25), seg(-w / 2, -h * 0.75, w / 2, -h * 0.75)]
    rim = rect(-w / 2 - 1.5, -h - 3, w + 3, 5, 2)
    out = []
    top = -h - 3
    if kind == "geranium":
        leaves = [scallop(-w * 0.42, top - 6, 8, 6, 6, 0.7), scallop(w * 0.42, top - 7, 8, 6, 6, 0.7)]
        stems = [
            p(f"M{fmt(-2)} {fmt(top)} Q{fmt(-4)} {fmt(top - 16)} {fmt(-6)} {fmt(top - 24)}"),
            p(f"M{fmt(2)} {fmt(top)} Q{fmt(5)} {fmt(top - 12)} {fmt(8)} {fmt(top - 18)}"),
        ]
        out += [pen.stroke(*stems, weight=DECO), pen.shape(*leaves, weight=DECO)]
        for bx, by, br in ((-6, top - 28, 3.6), (9, top - 21, 3.1)):  # a round head of small florets
            florets = [c(*polar(bx, by, br * 1.25, -90 + 72 * i), br) for i in range(5)]
            out.append(pen.shape(*florets, c(bx, by, br * 0.9), weight=1.6))
    else:  # basil (حَبَق): a round bush of small leaves
        bush_leaves = [p(leaf_d(0, top, 18, 7, a)) for a in (-160, -130, -105, -80, -55, -25)] + [
            p(leaf_d(0, top - 9, 12, 5.5, a)) for a in (-140, -90, -40)
        ]
        out += [pen.shape(*bush_leaves, weight=DECO)]
    return (
        "".join(out)
        + pen.shape(can, weight=DECO)
        + pen.stroke(*ridges, weight=1.4)
        + pen.shape(rim, weight=DECO)
    )


def school_bag(pen: Pen, w: float = 34.0) -> str:
    """A school backpack standing on its origin."""
    h = w * 1.15
    handle = p(f"M{fmt(-w * 0.18)} {fmt(-h)} Q0 {fmt(-h - w * 0.32)} {fmt(w * 0.18)} {fmt(-h)}")
    body = rect(-w / 2, -h, w, h, w * 0.22)
    flap = p(
        f"M{fmt(-w / 2 + 0.5)} {fmt(-h * 0.62)} L{fmt(-w / 2 + 0.5)} {fmt(-h + w * 0.22)} "
        f"Q{fmt(-w / 2 + 0.5)} {fmt(-h)} {fmt(-w * 0.28)} {fmt(-h)} L{fmt(w * 0.28)} {fmt(-h)} "
        f"Q{fmt(w / 2 - 0.5)} {fmt(-h)} {fmt(w / 2 - 0.5)} "
        f"{fmt(-h + w * 0.22)} L{fmt(w / 2 - 0.5)} {fmt(-h * 0.62)} "
        f"Q0 {fmt(-h * 0.5)} {fmt(-w / 2 + 0.5)} {fmt(-h * 0.62)} Z"
    )
    pocket = rect(-w * 0.3, -h * 0.4, w * 0.6, h * 0.3, 3)
    clasp = rect(-w * 0.07, -h * 0.6, w * 0.14, h * 0.1, 1)
    return (
        pen.stroke(handle, weight=MAIN)
        + pen.shape(body, flap, pocket, weight=DECO)
        + pen.shape(clasp, weight=DECO)
    )


def block(pen: Pen, size: float = 20.0, mark: str = "star") -> str:
    """A toy building block (a cube in a little perspective), a shape on its face; stands on its origin."""
    s = size
    d = s * 0.28
    face = rect(-s / 2, -s, s, s, 2)
    top = poly([(-s / 2, -s), (-s / 2 + d, -s - d), (s / 2 + d, -s - d), (s / 2, -s)])
    side = poly([(s / 2, -s), (s / 2 + d, -s - d), (s / 2 + d, -d), (s / 2, 0)])
    if mark == "star":
        sign = rounded_star(0, -s / 2, s * 0.3)
    elif mark == "heart":
        sign = heart(0, -s / 2, s * 0.5)
    else:
        sign = c(0, -s / 2, s * 0.24)
    return pen.shape(top, side, face, weight=DECO) + pen.shape(sign, weight=1.6)


def ball(pen: Pen, r: float = 14.0) -> str:
    """A beach ball centred on its origin: three curved bands."""
    bands = [
        p(f"M{fmt(-r * 0.15)} {fmt(-r * 0.99)} Q{fmt(-r * 0.75)} 0 {fmt(-r * 0.15)} {fmt(r * 0.99)}"),
        p(f"M{fmt(r * 0.15)} {fmt(-r * 0.99)} Q{fmt(r * 0.75)} 0 {fmt(r * 0.15)} {fmt(r * 0.99)}"),
    ]
    return (
        pen.shape(c(0, 0, r))
        + pen.stroke(*bands, weight=1.6)
        + pen.shape(e(0, -r * 0.8, r * 0.2, r * 0.12), weight=1.4)
    )


def teddy(pen: Pen) -> str:
    """A sitting teddy bear about 40 units tall, standing on its origin."""
    out = [
        pen.shape(e(-9, -5, 6, 5), e(9, -5, 6, 5), weight=DECO),  # feet
        pen.shape(e(0, -15, 12, 13), weight=DECO),  # body
        pen.shape(e(-12, -18, 4.5, 7.5, 30), e(12, -18, 4.5, 7.5, -30), weight=DECO),  # arms
        pen.shape(e(0, -12, 6.5, 7), weight=1.6),  # tummy
        pen.shape(c(-8.5, -40, 4.6), c(8.5, -40, 4.6), weight=DECO),  # ears
        pen.shape(c(0, -32, 10.5), weight=DECO),  # head
        pen.shape(e(0, -28.5, 4.8, 3.6), weight=1.6),  # muzzle
        pen.solid(c(-3.8, -34, 1.3), c(3.8, -34, 1.3), e(0, -29.6, 1.6, 1.1)),
        pen.stroke(p("M-1.8 -27 Q0 -25.6 1.8 -27"), weight=1.2),
    ]
    return "".join(out)


def kite(pen: Pen, size: float = 30.0) -> str:
    """A diamond kite centred on its origin with a ribboned tail falling to the lower left."""
    s = size
    pts = [(0, -s * 0.62), (s * 0.4, -s * 0.05), (0, s * 0.62), (-s * 0.4, -s * 0.05)]
    tail = p(
        f"M0 {fmt(s * 0.62)} C{fmt(-s * 0.1)} {fmt(s * 0.95)} {fmt(s * 0.3)} {fmt(s * 1.15)} {fmt(s * 0.05)} "
        f"{fmt(s * 1.5)}"
    )
    bows = []
    for bx, by in ((0.03, 0.9), (0.16, 1.2)):
        x, y = s * bx, s * by
        bows.append(poly([(x, y), (x - 4.5, y - 2.8), (x - 4.5, y + 2.8)]))
        bows.append(poly([(x, y), (x + 4.5, y - 2.8), (x + 4.5, y + 2.8)]))
    return (
        pen.stroke(tail, weight=1.6)
        + pen.shape(poly(pts), weight=DECO)
        + pen.stroke(seg(0, -s * 0.62, 0, s * 0.62), seg(-s * 0.4, -s * 0.05, s * 0.4, -s * 0.05), weight=1.4)
        + pen.shape(*bows, weight=1.4)
    )


def planet(pen: Pen, r: float = 13.0) -> str:
    """A ringed planet centred on its origin (the ring's front passes over the ball)."""
    ring = e(0, 0, r * 1.75, r * 0.5, -12)
    return pen.shape(ring, weight=DECO) + pen.shape(c(0, 0, r)) + _ring_front(pen, r)


def _ring_front(pen: Pen, r: float) -> str:
    """The lower half of the planet's ring, drawn over the ball."""
    a = math.radians(-12)
    rx, ry = r * 1.75, r * 0.5
    irx, iry = r * 1.2, r * 0.26

    def pt(rr: float, qq: float, t: float) -> Point:
        x, y = rr * math.cos(t), qq * math.sin(t)
        return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)

    outer = [pt(rx, ry, math.pi * i / 16) for i in range(17)]
    inner = [pt(irx, iry, math.pi * (16 - i) / 16) for i in range(17)]
    return pen.shape(poly(outer + inner), weight=DECO)


def rosette(pen: Pen, r: float = 16.0) -> str:
    """A prize rosette (a frilled disc, a star in its middle, two ribbon tails), centred on its origin."""
    tails = [
        poly(
            [
                (-r * 0.45, r * 0.3),
                (-r * 0.85, r * 2.1),
                (-r * 0.5, r * 1.85),
                (-r * 0.3, r * 2.25),
                (r * 0.05, r * 0.5),
            ]
        ),
        poly(
            [
                (r * 0.45, r * 0.3),
                (r * 0.85, r * 2.1),
                (r * 0.5, r * 1.85),
                (r * 0.3, r * 2.25),
                (-r * 0.05, r * 0.5),
            ]
        ),
    ]
    return (
        pen.shape(*tails, weight=DECO)
        + pen.shape(scallop(0, 0, r, r, 14, 0.7))
        + pen.shape(c(0, 0, r * 0.66), weight=DECO)
        + pen.shape(rounded_star(0, 0, r * 0.46), weight=1.6)
    )


def calendar(pen: Pen, size: float = 18.0) -> str:
    """A small wall-calendar icon (no digits: a grid of dots), centred on its origin."""
    s = size
    body = rect(-s / 2, -s * 0.42, s, s * 0.9, 2.2)
    head = rect(-s / 2, -s * 0.42, s, s * 0.26, 2.2)
    rings = [
        rect(-s * 0.28 - 1.2, -s * 0.56, 2.4, s * 0.24, 1.2),
        rect(s * 0.28 - 1.2, -s * 0.56, 2.4, s * 0.24, 1.2),
    ]
    dots = [
        c(-s * 0.3 + col * s * 0.2, -s * 0.02 + row * s * 0.2, 1.0) for row in range(3) for col in range(4)
    ]
    return (
        pen.shape(body, weight=DECO)
        + pen.shape(head, weight=DECO)
        + pen.shape(*rings, weight=1.4)
        + pen.solid(*dots)
    )


def candle(pen: Pen, h: float = 18.0) -> str:
    """A birthday candle with its flame, standing on its origin."""
    w = h * 0.3
    body = rect(-w / 2, -h, w, h, 1.2)
    stripes = [p(f"M{fmt(-w / 2)} {fmt(-h * f)} L{fmt(w / 2)} {fmt(-h * (f + 0.18))}") for f in (0.2, 0.5)]
    flame = p(
        f"M0 {fmt(-h - 2)} C{fmt(w * 0.8)} {fmt(-h - 4)} {fmt(w * 0.4)} {fmt(-h - 9)} 0 {fmt(-h - 12)} "
        f"C{fmt(-w * 0.4)} {fmt(-h - 9)} {fmt(-w * 0.8)} {fmt(-h - 4)} 0 {fmt(-h - 2)} Z"
    )
    wick = seg(0, -h, 0, -h - 2.2)
    return (
        pen.shape(body, weight=DECO) + pen.stroke(*stripes, wick, weight=1.4) + pen.shape(flame, weight=1.6)
    )


def bee(pen: Pen) -> str:
    """A friendly bee about 22 units long, centred on its origin, flying to the left."""
    return (
        pen.shape(e(-1, -8, 5, 7.5, -25), e(5, -8, 5, 7.5, 25), weight=1.6)
        + pen.shape(e(0, 0, 10, 7), weight=DECO)
        + pen.stroke(p("M-1 -6.5 Q-3 0 -1 6.5"), p("M4 -6 Q2 0 4 6"), weight=1.6)
        + pen.shape(p("M10 -0.8 L13.5 0 L10 0.8 Z"), weight=1.2)
        + pen.solid(c(-6, -1.5, 1.2))
        + pen.stroke(p("M-8 2.2 Q-6.5 3.6 -5 2.6"), weight=1.1)
    )


def butterfly_small(pen: Pen) -> str:
    """A small butterfly about 26 units wide, centred on its origin."""
    wings = [
        p("M0 -1 C-6 -14 -16 -14 -13 -5 C-12 -1 -6 0 0 0 Z"),
        p("M0 -1 C6 -14 16 -14 13 -5 C12 -1 6 0 0 0 Z"),
        p("M0 0 C-5 1 -12 3 -10 9 C-8 13 -2 8 0 2 Z"),
        p("M0 0 C5 1 12 3 10 9 C8 13 2 8 0 2 Z"),
    ]
    feelers = [p("M-0.5 -5 Q-2 -10 -4.5 -12"), p("M0.5 -5 Q2 -10 4.5 -12")]
    return (
        pen.shape(*wings, weight=DECO)
        + pen.stroke(*feelers, weight=1.3)
        + pen.shape(e(0, -0.5, 1.7, 6.5), weight=1.4)
    )


# ---- frames ------------------------------------------------------------------------------------------------


def frame_stitched(pen: Pen, w: float, h: float) -> str:
    """A rounded frame with a stitched (dashed) line just inside it."""
    i = INSET + 4.5
    return border(pen, w, h) + dashed(pen, rect(i, i, w - 2 * i, h - 2 * i, RADIUS - 3))


def frame_stars(pen: Pen, w: float, h: float) -> str:
    """Stars gathered at two opposite corners (top right, bottom left)."""
    return (
        frame_stitched(pen, w, h)
        + stars(pen, [(w - 16, 16, 11), (w - 36, 10.5, 5.5), (w - 10, 37, 5)])
        + stars(pen, [(16, h - 16, 11), (36, h - 10.5, 5.5), (10, h - 37, 5)])
        + pen.shape(
            sparkle(w - 46, 20, 3.4),
            sparkle(w - 22, 44, 3),
            sparkle(46, h - 20, 3.4),
            sparkle(22, h - 44, 3),
            weight=1.4,
        )
    )


def frame_crayons(pen: Pen, w: float, h: float) -> str:
    """Crossed crayons in the bottom corner, a pencil at the top, stars in the other corner."""
    return (
        border(pen, w, h)
        + place(pen, crayon, 34, h - 22, rotate=-28)
        + place(pen, crayon, 40, h - 14, rotate=-8, length=56)
        + place(pen, pencil, w - 34, 15, rotate=18, length=58)
        + stars(pen, [(w - 22, h - 22, 8), (w - 42, h - 14, 4.5), (w - 14, h - 42, 4.5)])
    )


def scallop_border_d(x: float, y: float, w: float, h: float, step: float = 13.0, bulge: float = 0.62) -> str:
    """Path data of a rectangle whose sides are rows of outward bumps (a lace or cloud edge)."""
    nx = max(2, round(w / step))
    ny = max(2, round(h / step))
    pts: list[Point] = [(x + w * i / nx, y) for i in range(nx)]
    pts += [(x + w, y + h * i / ny) for i in range(ny)]
    pts += [(x + w - w * i / nx, y + h) for i in range(nx)]
    pts += [(x, y + h - h * i / ny) for i in range(ny)]
    d = f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"
    for i in range(len(pts)):
        x2, y2 = pts[(i + 1) % len(pts)]
        r = math.dist(pts[i], (x2, y2)) * bulge
        d += f" A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x2)} {fmt(y2)}"
    return d + " Z"


def frame_scallop(pen: Pen, w: float, h: float) -> str:
    """A lace frame: an edge of soft bumps, with a dot in every bump."""
    m = 6.5
    d = scallop_border_d(m, m, w - 2 * m, h - 2 * m, step=13)
    return pen.stroke(p(d), weight=FRAME) + dashed(pen, rect(m + 5, m + 5, w - 2 * m - 10, h - 2 * m - 10, 4))


def frame_moon(pen: Pen, w: float, h: float) -> str:
    """The moon friend leaning on the top corner, a trail of little stars, a cloud at the bottom."""
    return (
        border(pen, w, h)
        + place(pen, puffy_cloud, w - 34, h - 6, w=56)
        + place(pen, puffy_cloud, w - 72, h - 6, w=28, bumps=3)
        + place(pen, moon_friend, 34, 34, s=0.72)
        + stars(pen, [(80, 14, 5.5), (100, 22, 3.8)], weight=1.6)
        + pen.shape(sparkle(116, 12, 3.4), sparkle(16, 82, 3.4), weight=1.3)
        + specks(pen, [(90, 10), (110, 20), (20, 70)])
    )


def olive_corner(pen: Pen, x: float, y: float, turn: float) -> str:
    """Two olive twigs from one corner point: one along the top edge, one down the side (turned by `turn`)."""
    return (
        place(pen, olive_branch, x, y, rotate=turn + 182, length=70, bend=6)
        + place(pen, olive_branch, x, y, rotate=turn + 92, length=56, olives=2, bend=-6)
        + place(pen, _knot, x, y)
    )


def _knot(pen: Pen) -> str:
    return pen.shape(c(0, 0, 3.2), weight=DECO)


def frame_leaves(pen: Pen, w: float, h: float) -> str:
    """Olive twigs growing round two opposite corners."""
    return frame_stitched(pen, w, h) + olive_corner(pen, w - 13, 13, 0) + olive_corner(pen, 13, h - 13, 180)


def tatreez_star(pen: Pen, cx: float, cy: float, r: float) -> str:
    """An embroidery-style eight-point star (two squares) with a diamond at its heart: a corner ornament."""
    sq1 = poly([polar(cx, cy, r, 45 + 90 * i) for i in range(4)])
    sq2 = poly([polar(cx, cy, r, 90 * i) for i in range(4)])
    inner = poly([polar(cx, cy, r * 0.42, 90 * i) for i in range(4)])
    return (
        pen.shape(sq1, sq2, weight=1.4)
        + pen.shape(
            p(
                f"M{fmt(cx - r * 0.72)} {fmt(cy)} L{fmt(cx + r * 0.72)} {fmt(cy)} "
                f"M{fmt(cx)} {fmt(cy - r * 0.72)} L{fmt(cx)} {fmt(cy + r * 0.72)}"
            ),
            weight=1.2,
        )
        + pen.shape(inner, weight=1.4)
    )


def frame_tatreez(pen: Pen, w: float, h: float) -> str:
    """A double frame: an embroidery star in each corner, a small diamond in the middle of each side."""
    i = INSET + 5.5
    out = [border(pen, w, h), pen.stroke(rect(i, i, w - 2 * i, h - 2 * i, 4), weight=ORNAMENT)]
    corners = [(i, i), (w - i, i), (i, h - i), (w - i, h - i)]
    out += [tatreez_star(pen, x, y, 9) for x, y in corners]
    mids = [(w / 2, i), (w / 2, h - i), (i, h / 2), (w - i, h / 2)]
    out.append(
        pen.shape(
            *(poly([(x, y - 4.5), (x + 4.5, y), (x, y + 4.5), (x - 4.5, y)]) for x, y in mids), weight=1.4
        )
    )
    return "".join(out)


def frame_flowers(pen: Pen, w: float, h: float) -> str:
    """Flowers and grass growing up from the bottom corners, a butterfly at the top."""
    return (
        border(pen, w, h)
        + place(pen, flower, 18, h - 4, h=34)
        + place(pen, flower, 34, h - 4, h=22, petals=6)
        + place(pen, tuft, 46, h - 4, w=10)
        + place(pen, tuft, w - 46, h - 4, w=10)
        + place(pen, flower, w - 30, h - 4, h=28, petals=6)
        + place(pen, flower, w - 15, h - 4, h=18)
        + place(pen, butterfly_small, w - 24, 24, s=1.15, rotate=12)
    )


def frame_clouds(pen: Pen, w: float, h: float) -> str:
    """Clouds over the top corners, two birds, a kite flying in the bottom corner."""
    return (
        border(pen, w, h)
        + place(pen, cloud, 30, 18, w=48)
        + place(pen, cloud, w - 26, 26, w=34)
        + place(pen, bird_v, 66, 18, w=11)
        + place(pen, bird_v, 80, 26, w=8)
        + place(pen, kite, w - 26, h - 44, size=28, rotate=-14)
    )


def frame_hearts(pen: Pen, w: float, h: float) -> str:
    """Hearts at all four corners (the family page)."""
    out = [frame_stitched(pen, w, h)]
    for x, y, sx, sy in ((14, 14, 1, 1), (w - 14, 14, -1, 1), (14, h - 14, 1, -1), (w - 14, h - 14, -1, -1)):
        out.append(pen.shape(heart(x + sx * 1, y + sy * 2, 15), weight=DECO))
        out.append(
            pen.shape(
                heart(x + sx * 17, y + sy * 0.5, 7.5), heart(x + sx * 1.5, y + sy * 17, 7.5), weight=1.6
            )
        )
    return "".join(out)


ART.update(
    {
        "frame-stars": frame_stars,
        "frame-crayons": frame_crayons,
        "frame-scallop": frame_scallop,
        "frame-moon": frame_moon,
        "frame-leaves": frame_leaves,
        "frame-tatreez": frame_tatreez,
        "frame-flowers": frame_flowers,
        "frame-clouds": frame_clouds,
        "frame-hearts": frame_hearts,
    }
)


# ---- more parts --------------------------------------------------------------------------------------------


def puffy_cloud(pen: Pen, w: float = 46.0, bumps: int = 5, weight: float = DECO) -> str:
    """A cloud of round puffs on a flat base; the origin is the middle of the base."""
    h = w * 0.5
    angles = [math.pi + math.pi * i / bumps for i in range(bumps + 1)]
    pts = [(math.cos(a) * w / 2, math.sin(a) * h) for a in angles]
    d = f"M{fmt(pts[0][0])} 0"
    for i in range(bumps):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        r = math.dist((x1, y1), (x2, y2)) * (0.62 if 0 < i < bumps - 1 else 0.58)
        d += f" A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x2)} {fmt(y2)}"
    return pen.shape(p(d + " Z"), weight=weight)


def apple(pen: Pen, r: float = 12.0) -> str:
    """An apple with a stalk and a leaf, standing on its origin."""
    body = p(
        f"M0 {fmt(-r * 1.55)} C{fmt(-r * 0.6)} {fmt(-r * 2.0)} "
        f"{fmt(-r * 1.3)} {fmt(-r * 1.5)} {fmt(-r * 1.1)} "
        f"{fmt(-r * 0.8)} C{fmt(-r * 0.95)} {fmt(-r * 0.15)} {fmt(-r * 0.45)} 0 0 {fmt(-r * 0.12)} "
        f"C{fmt(r * 0.45)} 0 {fmt(r * 0.95)} {fmt(-r * 0.15)} {fmt(r * 1.1)} {fmt(-r * 0.8)} "
        f"C{fmt(r * 1.3)} {fmt(-r * 1.5)} {fmt(r * 0.6)} {fmt(-r * 2.0)} 0 {fmt(-r * 1.55)} Z"
    )
    stalk = p(f"M0 {fmt(-r * 1.5)} Q{fmt(r * 0.05)} {fmt(-r * 1.9)} {fmt(r * 0.25)} {fmt(-r * 2.1)}")
    leaf = p(leaf_d(r * 0.1, -r * 1.75, r * 0.9, r * 0.38, -25))
    return pen.stroke(stalk, weight=DECO) + pen.shape(body) + pen.shape(leaf, weight=DECO)


def cup(pen: Pen, w: float = 20.0) -> str:
    """A glass of juice with a bent straw, standing on its origin."""
    h = w * 1.3
    glass = p(f"M{fmt(-w / 2)} {fmt(-h)} L{fmt(w / 2)} {fmt(-h)} L{fmt(w * 0.4)} 0 L{fmt(-w * 0.4)} 0 Z")
    straw = p(
        f"M{fmt(w * 0.05)} {fmt(-h * 0.3)} L{fmt(w * 0.2)} {fmt(-h - 6)} L{fmt(w * 0.55)} {fmt(-h - 10)}"
    )
    level = p(f"M{fmt(-w * 0.47)} {fmt(-h * 0.72)} L{fmt(w * 0.47)} {fmt(-h * 0.72)}")
    return pen.stroke(straw, weight=MAIN) + pen.shape(glass, weight=DECO) + pen.stroke(level, weight=1.4)


def fork(pen: Pen, length: float = 84.0) -> str:
    """A table fork standing upright, its handle's end on the origin."""
    head_top = -length
    neck = -length * 0.62
    handle = rect(-3.2, neck, 6.4, length * 0.62, 3.2)
    head = p(
        f"M-7.5 {fmt(head_top)} L-7.5 {fmt(neck - 12)} Q-7.5 "
        f"{fmt(neck - 4)} -2.4 {fmt(neck)} L2.4 {fmt(neck)} "
        f"Q7.5 {fmt(neck - 4)} 7.5 {fmt(neck - 12)} L7.5 "
        f"{fmt(head_top)} L4.4 {fmt(head_top)} L4.4 {fmt(neck - 13)} "
        f"L1.55 {fmt(neck - 13)} L1.55 {fmt(head_top)} L-1.55 {fmt(head_top)} L-1.55 {fmt(neck - 13)} "
        f"L-4.4 {fmt(neck - 13)} L-4.4 {fmt(head_top)} Z"
    )
    return pen.shape(handle, weight=DECO) + pen.shape(head, weight=DECO)


def spoon(pen: Pen, length: float = 84.0) -> str:
    """A spoon standing upright, its handle's end on the origin."""
    bowl_cy = -length + 13
    return pen.shape(rect(-3.2, bowl_cy + 8, 6.4, length - 21, 3.2), weight=DECO) + pen.shape(
        e(0, bowl_cy, 9, 13.5), weight=DECO
    )


def spinning_top(pen: Pen, w: float = 30.0) -> str:
    """A wooden spinning top on its point (the origin), with bands to colour."""
    h = w * 0.95
    body = p(
        f"M0 0 L{fmt(-w / 2)} {fmt(-h * 0.62)} Q{fmt(-w * 0.42)} {fmt(-h * 0.9)} 0 {fmt(-h * 0.9)} "
        f"Q{fmt(w * 0.42)} {fmt(-h * 0.9)} {fmt(w / 2)} {fmt(-h * 0.62)} Z"
    )
    knob = rect(-w * 0.09, -h * 1.12, w * 0.18, h * 0.26, 2)
    bands = [
        p(f"M{fmt(-w * 0.42)} {fmt(-h * 0.5)} Q0 {fmt(-h * 0.4)} {fmt(w * 0.42)} {fmt(-h * 0.5)}"),
        p(f"M{fmt(-w * 0.27)} {fmt(-h * 0.3)} Q0 {fmt(-h * 0.22)} {fmt(w * 0.27)} {fmt(-h * 0.3)}"),
    ]
    whoosh = [
        p(f"M{fmt(-w * 0.7)} {fmt(-h * 0.2)} L{fmt(-w * 0.95)} {fmt(-h * 0.2)}"),
        p(f"M{fmt(-w * 0.62)} {fmt(-h * 0.05)} L{fmt(-w * 0.85)} {fmt(-h * 0.05)}"),
    ]
    return (
        pen.shape(knob, weight=DECO)
        + pen.shape(body)
        + pen.stroke(*bands, weight=1.6)
        + pen.stroke(*whoosh, weight=1.6)
    )


def limb(x1: float, y1: float, x2: float, y2: float, width: float) -> str:
    """A rounded capsule from (x1, y1) to (x2, y2)."""
    a = math.atan2(y2 - y1, x2 - x1)
    nx, ny = -math.sin(a) * width / 2, math.cos(a) * width / 2
    r = width / 2
    return p(
        f"M{fmt(x1 + nx)} {fmt(y1 + ny)} L{fmt(x2 + nx)} {fmt(y2 + ny)} "
        f"A{fmt(r)} {fmt(r)} 0 0 0 {fmt(x2 - nx)} {fmt(y2 - ny)} L{fmt(x1 - nx)} {fmt(y1 - ny)} "
        f"A{fmt(r)} {fmt(r)} 0 0 0 {fmt(x1 + nx)} {fmt(y1 + ny)} Z"
    )


def hand_bird(pen: Pen) -> str:
    """A traced hand turned into a bird: fingers for tail feathers, the thumb for the neck and head.
    About 60 units wide, standing on its origin (the feet)."""
    fingers = [(-14, -40, -30, -84), (-6, -42, -10, -94), (3, -42, 10, -92), (11, -40, 27, -80)]
    return (
        pen.shape(*(limb(x1, y1, x2, y2, 11.5) for x1, y1, x2, y2 in fingers), weight=DECO)
        + pen.shape(limb(14, -26, 34, -48, 12.5), weight=DECO)  # the thumb: the neck
        + pen.shape(e(0, -30, 19, 17), weight=DECO)  # the palm: the body
        + pen.shape(p("M38 -54 L46 -50 L38 -46 Z"), weight=1.6)  # beak
        + pen.shape(scallop(32, -56.5, 5, 2.6, 3, 0.8, start=-160), weight=1.6)  # comb
        + pen.solid(c(35, -49.5, 1.5))
        + pen.stroke(p("M-8 -32 Q0 -22 8 -32"), weight=1.6)  # wing
        + pen.stroke(p("M-4 -13 L-4 0 M-7 0 L-1 0"), p("M5 -13 L5 0 M2 0 L8 0"), weight=DECO)
    )


def garland(pen: Pen, x0: float, x1: float, y: float, sag: float, items: int) -> str:
    """A string hung between (x0, y) and (x1, y) with stars and crescents alternating along it."""
    out = [
        pen.stroke(
            p(f"M{fmt(x0)} {fmt(y)} Q{fmt((x0 + x1) / 2)} {fmt(y + sag * 2)} {fmt(x1)} {fmt(y)}"), weight=1.6
        )
    ]
    shapes = []
    for i in range(items):
        t = (i + 0.5) / items
        x = x0 + (x1 - x0) * t
        yy = y + 2 * sag * 2 * t * (1 - t)
        out.append(pen.stroke(seg(x, yy, x, yy + 5), weight=1.4))
        if i % 2 == 0:
            shapes.append(rounded_star(x, yy + 12, 7.5))
        else:
            shapes.append(p(crescent_d(x, yy + 12.5, 7.5, 0.7, turn=-60)))
    return "".join(out) + pen.shape(*shapes, weight=DECO)


def creature(pen: Pen) -> str:
    """A friendly three-eyed creature peeking over a ledge (the origin is the ledge's middle), its hands
    holding on. About 100 units wide."""
    head = p("M-34 0 C-36 -30 -20 -46 0 -46 C20 -46 36 -30 34 0 Z")
    antennae = [p("M-12 -44 Q-18 -56 -14 -64"), p("M12 -44 Q18 -56 14 -64")]
    tips = [c(-14, -66, 4), c(14, -66, 4)]
    eyes = [c(-15, -24, 7), c(0, -31, 8), c(15, -24, 7)]
    hands = []
    for sx in (-1, 1):
        x = sx * 44
        hands.append(
            p(
                f"M{fmt(x - 9)} 1 Q{fmt(x - 9)} -9 {fmt(x - 4)} -9 Q{fmt(x)} -12 {fmt(x + 4)} -9 "
                f"Q{fmt(x + 9)} -9 {fmt(x + 9)} 1 Z"
            )
        )
    fingers = [seg(sx * 44 + dx, -6, sx * 44 + dx, 0.5) for sx in (-1, 1) for dx in (-3, 3)]
    return (
        pen.stroke(*antennae, weight=DECO)
        + pen.shape(*tips, weight=DECO)
        + pen.shape(head)
        + pen.shape(*eyes, weight=DECO)
        + pen.solid(c(-14, -23, 3), c(1, -30, 3.4), c(16, -23, 3))
        + pen.stroke(p("M-8 -8 Q0 -2 8 -8"), weight=FINE)
        + pen.shape(*hands, weight=DECO)
        + pen.stroke(*fingers, weight=1.3)
    )


def swing(pen: Pen, x0: float, x1: float, top: float, seat_y: float) -> str:
    """An empty swing hanging from the frame's top edge: two ropes and a wooden seat."""
    ropes = [seg(x0, top, x0, seat_y), seg(x1, top, x1, seat_y)]
    hooks = [c(x0, top + 2, 2.4), c(x1, top + 2, 2.4)]
    seat = rect(x0 - 7, seat_y - 1, x1 - x0 + 14, 7, 3)
    return pen.stroke(*ropes, weight=DECO) + pen.shape(*hooks, weight=1.4) + pen.shape(seat, weight=DECO)


def fence(pen: Pen, x0: float, x1: float, base: float, height: float, picket: float = 13.0) -> str:
    """A garden fence of pointed pickets from x0 to x1 standing on `base`, with two rails behind."""
    rails = [rect(x0, base - height * 0.78, x1 - x0, 6, 2), rect(x0, base - height * 0.36, x1 - x0, 6, 2)]
    n = max(2, int((x1 - x0) // (picket + 3)))
    gap = ((x1 - x0) - n * picket) / (n - 1)
    pickets = []
    for i in range(n):
        x = x0 + i * (picket + gap)
        pickets.append(
            p(
                f"M{fmt(x)} {fmt(base)} L{fmt(x)} "
                f"{fmt(base - height + picket * 0.55)} L{fmt(x + picket / 2)} "
                f"{fmt(base - height)} L{fmt(x + picket)} {fmt(base - height + picket * 0.55)} "
                f"L{fmt(x + picket)} {fmt(base)} Z"
            )
        )
    return pen.shape(*rails, weight=DECO) + pen.shape(*pickets, weight=DECO)


def watering_can(pen: Pen, w: float = 30.0) -> str:
    """A watering can standing on its origin, its spout to the right."""
    h = w * 0.72
    body = rect(-w / 2, -h, w * 0.7, h, 3)
    spout = poly([(w * 0.18, -h * 0.25), (w * 0.62, -h * 1.05), (w * 0.7, -h * 0.98), (w * 0.2, -h * 0.05)])
    rose = e(w * 0.68, -h * 1.05, 3, 5, 40)
    handle = p(f"M{fmt(-w * 0.38)} {fmt(-h)} Q{fmt(-w * 0.15)} {fmt(-h * 1.55)} {fmt(w * 0.08)} {fmt(-h)}")
    return pen.stroke(handle, weight=MAIN) + pen.shape(spout, rose, weight=DECO) + pen.shape(body)


def falling_leaf(pen: Pen, size: float = 14.0) -> str:
    """An autumn leaf with its midrib, centred on its origin."""
    return pen.shape(p(leaf_d(-size / 2, 0, size, size * 0.42, 0)), weight=DECO) + pen.stroke(
        seg(-size / 2 - 2, 0, size * 0.32, 0), weight=1.3
    )


def _bunch(pen: Pen, r: float = 4.2) -> str:
    """A bunch of grapes hanging from its stalk (the origin)."""
    rows = [3, 4, 3, 2, 1]
    berries = []
    y = r * 1.6
    for n in rows:
        for i in range(n):
            berries.append(c((i - (n - 1) / 2) * r * 1.8, y, r))
        y += r * 1.55
    return pen.stroke(seg(0, -1, 0, r * 1.2), weight=DECO) + pen.shape(*reversed(berries), weight=DECO)


def vine_leaf(pen: Pen, size: float = 18.0) -> str:
    """A three-lobed grape leaf hanging from its stalk (the origin), with three veins."""
    s = size
    outline: list[Point] = [
        (0, s * 0.08),
        (-s * 0.3, -s * 0.02),
        (-s * 0.5, s * 0.3),
        (-s * 0.28, s * 0.42),
        (-s * 0.3, s * 0.72),
        (0, s * 0.98),
        (s * 0.3, s * 0.72),
        (s * 0.28, s * 0.42),
        (s * 0.5, s * 0.3),
        (s * 0.3, -s * 0.02),
    ]
    veins = [
        seg(0, s * 0.1, 0, s * 0.75),
        seg(0, s * 0.18, -s * 0.34, s * 0.3),
        seg(0, s * 0.18, s * 0.34, s * 0.3),
    ]
    return pen.shape(smooth(outline, tension=0.75), weight=DECO) + pen.stroke(*veins, weight=1.2)


def vine(pen: Pen, x0: float, x1: float, y: float) -> str:
    """A grapevine running along the top edge with leaves and three hanging bunches."""
    pts: list[Point] = []
    n = 8
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        pts.append((x, y + (5 if i % 2 else -1)))
    out = [pen.stroke(smooth(pts, closed=False), weight=MAIN)]
    for i, (x, yy) in enumerate(pts[1:-1]):
        if i % 2 == 0:
            out.append(place(pen, vine_leaf, x + 2, yy + 1, rotate=-25 if i % 4 else 25, size=22))
    for k, frac in enumerate((0.16, 0.5, 0.84)):
        x = x0 + (x1 - x0) * frac
        yy = y + (3 if k % 2 else 1)
        out.append(place(pen, _bunch, x, yy, s=0.95 if k == 1 else 0.8))
    return "".join(out)


def sprout(pen: Pen, h: float = 18.0) -> str:
    """A seedling with two leaves standing on its origin."""
    return pen.stroke(p(f"M0 0 Q1 {fmt(-h * 0.5)} 0 {fmt(-h)}"), weight=DECO) + pen.shape(
        p(leaf_d(0, -h, h * 0.6, h * 0.32, -150)), p(leaf_d(0, -h, h * 0.6, h * 0.32, -30)), weight=DECO
    )


def palette(pen: Pen, w: float = 34.0) -> str:
    """A painter's palette with paint spots and a thumb hole, centred on its origin."""
    h = w * 0.72
    board = smooth(
        [
            (-w / 2, 0),
            (-w * 0.3, -h / 2),
            (w * 0.2, -h / 2),
            (w / 2, -h * 0.1),
            (w * 0.35, h * 0.42),
            (0, h / 2),
            (-w * 0.12, h * 0.25),
            (-w * 0.34, h * 0.4),
        ],
        tension=0.9,
    )
    spots = [
        c(-w * 0.22, -h * 0.15, 3.6),
        c(0, -h * 0.28, 3.6),
        c(w * 0.24, -h * 0.12, 3.6),
        c(w * 0.22, h * 0.2, 3.6),
    ]
    return (
        pen.shape(board)
        + pen.shape(*spots, weight=1.6)
        + pen.shape(e(-w * 0.27, h * 0.14, 3.4, 2.6), weight=1.4)
    )


def drops(pen: Pen, spots: Sequence[tuple[float, float, float]]) -> str:

    return pen.shape(*(raindrop(x, y, s) for x, y, s in spots), weight=DECO)


def poppy_part(pen: Pen, h: float = 34.0) -> str:
    return poppy(pen, h=h)


def _on_ellipse(cx: float, cy: float, rx: float, ry: float, deg: float) -> Point:
    a = math.radians(deg)
    return cx + rx * math.cos(a), cy + ry * math.sin(a)


def _arc_d(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float) -> str:
    x0, y0 = _on_ellipse(cx, cy, rx, ry, a0)
    x1, y1 = _on_ellipse(cx, cy, rx, ry, a1)
    return f"M{fmt(x0)} {fmt(y0)} A{fmt(rx)} {fmt(ry)} 0 0 1 {fmt(x1)} {fmt(y1)}"


def _arch_path(x0: float, x1: float, base: float, top: float) -> str:
    """A round-topped opening from x0 to x1, its sides down to `base`, the crown at `top`."""
    r = (x1 - x0) / 2
    return (
        f"M{fmt(x0)} {fmt(base)} L{fmt(x0)} {fmt(top + r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x1)} {fmt(top + r)} "
        f"L{fmt(x1)} {fmt(base)} Z"
    )


# ---- the prompt pages --------------------------------------------------------------------------------------


@art("mirror")
def mirror_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم نفسك»: a standing oval mirror whose glass is the drawing area, a beaded rim, a heart crest."""
    cx, cy, rx, ry = w / 2, h * 0.46, w / 2 - 9, h * 0.42
    beads = [c(*_on_ellipse(cx, cy, rx - 4.5, ry - 4.5, 360 * i / 40), 1.35) for i in range(40)]
    stand = p(
        f"M{fmt(cx - 12)} {fmt(cy + ry - 2)} L{fmt(cx - 8)} {fmt(h - 18)} L{fmt(cx + 8)} {fmt(h - 18)} "
        f"L{fmt(cx + 12)} {fmt(cy + ry - 2)} Z"
    )
    foot = e(cx, h - 12, 36, 7)
    shine = [p(_arc_d(cx, cy, rx - 16, ry - 16, 200, 222)), p(_arc_d(cx, cy, rx - 16, ry - 16, 228, 236))]
    corners = [
        sparkle(12, 14, 5),
        sparkle(w - 12, 14, 5),
        sparkle(12, h - 30, 4.5),
        sparkle(w - 12, h - 30, 4.5),
    ]
    return (
        pen.shape(stand, foot, weight=DECO)
        + pen.shape(e(cx, cy, rx, ry), weight=FRAME + 0.4)
        + pen.shape(e(cx, cy, rx - 9, ry - 9), weight=FRAME)
        + pen.solid(*beads)
        + pen.shape(heart(cx, cy - ry + 1, 20), weight=DECO)
        + pen.stroke(*shine, weight=FINE)
        + pen.shape(*corners, weight=1.4)
    )


@art("home")
def home_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم بيتك»: a sun and a cloud above, a flower and grass at the foot."""
    return (
        border(pen, w, h)
        + place(pen, puffy_cloud, 42, 34, w=60)
        + place(pen, sun_face, w - 28, 28, r=15)
        + place(pen, bird_v, 86, 24, w=12)
        + place(pen, flower, 20, h - 4, h=38)
        + place(pen, tuft, 36, h - 4, w=12)
        + place(pen, tuft, w - 22, h - 4, w=13)
        + place(pen, flower, w - 38, h - 4, h=26, petals=6)
    )


@art("balloons")
def friends_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم صديقك»: two balloons tied together at the top corner, small hearts at the bottom."""
    return (
        border(pen, w, h)
        + place(pen, balloon, w - 48, 30, r=14, string=44, sway=1, lean=12)
        + place(pen, balloon, w - 22, 40, r=12.5, string=34, sway=-1, lean=-12)
        + pen.shape(heart(w - 35, 96, 11), weight=1.6)
        + pen.shape(heart(22, h - 22, 18), heart(44, h - 14, 10), heart(15, h - 46, 10), weight=DECO)
        + pen.shape(sparkle(30, 18, 4), sparkle(48, 12, 3), weight=1.4)
    )


@art("plate")
def food_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم ما تحب أن تأكل»: a big plate to draw the food on, a fork, a spoon, a glass of juice, an apple."""
    cx, cy, r = w / 2, h * 0.53, 66.0
    rim = [c(*polar(cx, cy, r - 6.5, 10 * i), 1.2) for i in range(36)]
    return (
        border(pen, w, h)
        + pen.shape(c(cx, cy, r), weight=FRAME + 0.4)
        + pen.shape(c(cx, cy, r - 13), weight=FRAME)
        + pen.solid(*rim)
        + place(pen, fork, 13.5, cy + 48, length=96)
        + place(pen, spoon, w - 13.5, cy + 48, length=96)
        + place(pen, cup, w - 26, 46, w=18)
        + place(pen, apple, 24, 42, r=10)
    )


@art("paws")
def animal_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم حيوانك المفضل»: a trail of paw prints walking in at one corner and out at the other."""
    trail = [(22, h - 20, 28), (50, h - 34, 34), (36, h - 64, 28), (64, h - 78, 34)]
    top = [(w - 66, 58, 34), (w - 50, 30, 28), (w - 24, 46, 34)]
    out = [border(pen, w, h)]
    out += [place(pen, paw, x, y, rotate=a, size=22) for x, y, a in trail]
    out += [place(pen, paw, x, y, rotate=a, size=18) for x, y, a in top]
    return "".join(out)


@art("window")
def window_page(pen: Pen, w: float, h: float) -> str:
    """«ماذا ترى من نافذتك؟»: an arched stone window (the view is the drawing area) with flowers in tin cans
    on its sill."""
    x0, x1, base = 12.0, w - 12, h - 30
    band = 10.0
    outer = p(_arch_path(x0, x1, base, 8))
    inner = p(_arch_path(x0 + band, x1 - band, base, 8 + band))
    r_out = (x1 - x0) / 2
    spring = 8 + r_out
    cx = w / 2
    joints = []
    for i in range(1, 8):  # the arch's stones
        a = 180 + 180 * i / 8
        ax, ay = polar(cx, spring, r_out - band, a)
        bx, by = polar(cx, spring, r_out, a)
        joints.append(seg(ax, ay, bx, by))
    for yy in (spring + 26, spring + 60, spring + 94):  # the jambs' stones
        if yy < base - 6:
            joints.append(seg(x0, yy, x0 + band, yy))
            joints.append(seg(x1 - band, yy, x1, yy))
    sill = rect(x0 - 6, base, x1 - x0 + 12, 9, 2.5)
    wall = rect(x0 + 4, base + 9, x1 - x0 - 8, 10, 0)
    return (
        pen.shape(outer, weight=FRAME + 0.4)
        + pen.shape(inner, weight=FRAME)
        + pen.stroke(*joints, weight=ORNAMENT)
        + pen.shape(wall, weight=FRAME)
        + pen.shape(sill, weight=FRAME + 0.4)
        + place(pen, tin_plant, x1 - 18, base, w=20)
        + place(pen, tin_plant, x0 + 16, base, w=18, kind="basil")
    )


@art("rain")
def rain_page(pen: Pen, w: float, h: float) -> str:
    """Winter, «ارسم يومًا ممطرًا»: rain clouds over the top corners, an umbrella and a puddle at the foot."""
    rain = [(22, 50, 4.5), (38, 60, 4), (54, 48, 4.5), (w - 48, 46, 4), (w - 30, 56, 4.5), (w - 14, 44, 3.5)]
    return (
        border(pen, w, h)
        + place(pen, puffy_cloud, 38, 34, w=62)
        + place(pen, puffy_cloud, w - 32, 30, w=48, bumps=4)
        + drops(pen, rain)
        + place(pen, umbrella, w - 30, h - 12, w=40, rotate=8)
        + place(pen, puddle, 34, h - 10, w=40)
        + place(pen, puddle, 64, h - 7, w=18)
    )


@art("poppies")
def spring_page(pen: Pen, w: float, h: float) -> str:
    """Spring, «ارسم أزهارًا وفراشات»: poppies and daisies in the bottom corners, a bee, a butterfly."""
    return (
        border(pen, w, h)
        + place(pen, poppy_part, 18, h - 4, h=40)
        + place(pen, flower, 35, h - 4, h=26, petals=7)
        + place(pen, tuft, 50, h - 4, w=10)
        + place(pen, poppy_part, w - 18, h - 4, h=34)
        + place(pen, flower, w - 34, h - 4, h=22)
        + place(pen, tuft, w - 50, h - 4, w=9)
        + place(pen, bee, 36, 28)
        + place(pen, butterfly_small, w - 26, 26, rotate=-10, s=1.1)
        + pen.stroke(p("M48 30 Q58 22 64 32 T80 30"), weight=1.3)
    )


@art("seaside")
def sea_page(pen: Pen, w: float, h: float) -> str:
    """Summer, «ارسم البحر»: the sun, gulls, a row of waves along the foot with a shell and a starfish."""
    wave_top = h - 26
    lo, hi, b = INSET + 1, w - INSET - 1, h - INSET - 1
    waves = p(
        wave_d(lo, hi, wave_top, 5, 7)
        + f" L{fmt(hi)} {fmt(b - 6)} Q{fmt(hi)} {fmt(b)} {fmt(hi - 6)} {fmt(b)} L{fmt(lo + 6)} {fmt(b)} "
        f"Q{fmt(lo)} {fmt(b)} {fmt(lo)} {fmt(b - 6)} Z"
    )
    crest = p(wave_d(INSET + 14, w - INSET - 14, wave_top + 11, 3.5, 6))
    return (
        border(pen, w, h)
        + pen.shape(waves, weight=FRAME)
        + pen.stroke(crest, weight=1.4)
        + place(pen, sun_face, w - 25, 25, r=13)
        + place(pen, bird_v, 34, 26, w=12)
        + place(pen, bird_v, 52, 36, w=9)
        + place(pen, shell, 30, h - 30, w=20)
        + place(pen, starfish, w - 34, h - 38, r=10)
    )


@art("olive-harvest")
def autumn_page(pen: Pen, w: float, h: float) -> str:
    """Autumn, «ارسم قطف الزيتون»: an olive twig from the top corner, falling leaves, a full basket."""
    return (
        border(pen, w, h)
        + olive_corner(pen, 13, 13, 270)
        + place(pen, falling_leaf, w - 30, 26, rotate=30, size=14)
        + place(pen, falling_leaf, w - 52, 44, rotate=-40, size=12)
        + place(pen, falling_leaf, w - 20, 58, rotate=110, size=12)
        + place(pen, basket, w - 34, h - 8, w=42)
    )


@art("garden-fence")
def garden_page(pen: Pen, w: float, h: float) -> str:
    """«لوّن وارسم حديقتك»: a picket fence along the foot with flowers in front, a sun, a watering can."""
    base = h - INSET - 2
    return (
        border(pen, w, h)
        + fence(pen, INSET + 4, w - INSET - 4, base, 46)
        + place(pen, flower, 30, base, h=36)
        + place(pen, flower, 76, base, h=28, petals=6)
        + place(pen, flower, 122, base, h=34, petals=5)
        + place(pen, tuft, 52, base, w=11)
        + place(pen, tuft, 100, base, w=11)
        + place(pen, watering_can, w - 34, base, w=30)
        + place(pen, sun_face, 26, 26, r=12, smile=False)
        + place(pen, butterfly_small, w - 30, 30, rotate=10)
    )


@art("grape-vine")
def grandma_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم بيت جدتك»: a grapevine along the top edge, geraniums and basil in tin cans at the foot."""
    return (
        border(pen, w, h)
        + vine(pen, INSET + 2, w - INSET - 2, 8)
        + place(pen, tin_plant, 22, h - 5, w=22)
        + place(pen, tin_plant, 46, h - 5, w=17, kind="basil")
        + place(pen, tin_plant, w - 24, h - 5, w=20)
    )


@art("hand-bird")
def hand_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم حول يدك واجعلها حيوانًا»: a stitched frame and a small example (a hand that became a bird)."""

    return (
        frame_stitched(pen, w, h)
        + pen.shape(c(w - 42, h - 46, 36), weight=ORNAMENT)
        + place(pen, hand_bird, w - 44, h - 18, s=0.74)
        + pen.shape(sparkle(20, 22, 5), sparkle(36, 16, 3.5), sparkle(w - 76, h - 18, 3.5), weight=1.4)
    )


@art("school")
def kindergarten_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم روضتك»: a school bag, building blocks and crayons around the corners."""
    return (
        border(pen, w, h)
        + place(pen, school_bag, 30, h - 6, w=38)
        + place(pen, block, w - 58, h - 6, size=25, mark="star")
        + place(pen, block, w - 28, h - 6, size=25, mark="circle")
        + place(pen, block, w - 43, h - 35, size=25, mark="heart")
        + place(pen, pencil, w - 40, 18, rotate=-12, length=60)
        + place(pen, crayon, 34, 18, rotate=12, length=50, width=10)
    )


@art("night")
def night_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم السماء في الليل»: the moon friend in the top corner, a few stars along the edges."""
    spots = [
        (22, 20, 7),
        (42, 32, 4.5),
        (18, 120, 4.5),
        (w - 18, 140, 5),
        (28, h - 22, 6),
        (w - 40, h - 18, 4.5),
    ]
    return (
        border(pen, w, h)
        + place(pen, moon_friend, w - 34, 34, s=0.62)
        + stars(pen, spots)
        + pen.shape(
            sparkle(70, 16, 3.5),
            sparkle(14, 70, 3),
            sparkle(w - 14, 90, 3),
            sparkle(80, h - 14, 3),
            weight=1.3,
        )
        + specks(pen, [(56, 22), (30, 52), (w - 22, 110), (48, h - 30), (w - 62, h - 26)])
    )


@art("space")
def space_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم صاروخًا إلى القمر»: the moon friend waiting at the top, a ringed planet below, stars."""
    return (
        border(pen, w, h)
        + place(pen, moon_friend, 40, 40, s=0.7)
        + stars(pen, [(20, h - 24, 5), (36, h - 14, 3.4)], weight=1.6)
        + place(pen, planet, w - 36, h - 40, r=13)
        + stars(pen, [(w - 24, 22, 6), (w - 50, 40, 4), (w - 18, 120, 4.5)])
        + pen.shape(sparkle(w - 70, 18, 3.4), sparkle(w - 64, h - 20, 3), sparkle(110, 16, 3), weight=1.3)
    )


@art("toys")
def toys_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم لعبتك المفضلة»: a teddy bear, a beach ball and a spinning top in the corners."""
    return (
        border(pen, w, h)
        + place(pen, teddy, 36, h - 6, s=1.35)
        + place(pen, ball, w - 28, h - 24, r=17)
        + place(pen, spinning_top, w - 34, 50, w=32, rotate=12)
        + pen.shape(sparkle(22, 22, 5), sparkle(40, 16, 3.4), weight=1.4)
    )


@art("swing")
def play_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم نفسك تلعب»: an empty swing hanging from the top edge, a ball and grass at the foot, a kite."""
    return (
        border(pen, w, h)
        + swing(pen, 22, 52, INSET, 78)
        + place(pen, ball, w - 26, h - 19, r=12)
        + place(pen, tuft, w - 48, h - 4, w=11)
        + place(pen, tuft, 20, h - 4, w=11)
        + place(pen, tuft, 34, h - 4, w=8)
        + place(pen, kite, w - 30, 40, size=26, rotate=12)
    )


@art("eid")
def eid_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم يوم العيد»: a garland of stars and crescents across the top, balloons and presents below."""
    return (
        border(pen, w, h)
        + garland(pen, INSET + 4, w - INSET - 4, INSET + 3, 7, 9)
        + place(pen, balloon, 20, h - 64, r=10, string=36)
        + place(pen, balloon, 38, h - 72, r=11, string=44, sway=-1)
        + place(pen, gift, w - 46, h - 5, w=26)
        + place(pen, gift, w - 20, h - 5, w=18)
    )


@art("creature")
def creature_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم مخلوقًا مضحكًا»: a three-eyed friend peeking over the bottom edge."""
    return (
        border(pen, w, h)
        + place(pen, creature, w - 70, h - INSET, s=1.05)
        + pen.shape(sparkle(18, 20, 5), sparkle(34, 14, 3.4), sparkle(w - 18, 22, 4), weight=1.4)
    )


@art("sunshine")
def happy_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم شيئًا يفرحك»: a smiling sun at the top corner, hearts and twinkles at the bottom."""
    return (
        border(pen, w, h)
        + place(pen, sun_face, 32, 32, r=17)
        + pen.shape(
            heart(w - 24, h - 24, 19), heart(w - 50, h - 16, 11), heart(w - 17, h - 52, 11), weight=DECO
        )
        + pen.shape(sparkle(w - 22, 20, 4.5), sparkle(18, h - 20, 4), sparkle(36, h - 14, 3), weight=1.4)
    )


@art("dream")
def dream_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم حلمًا جميلًا»: the moon friend asleep on a cloud in the top corner, stars, clouds below."""
    return (
        border(pen, w, h)
        + place(pen, puffy_cloud, w - 36, 52, w=56)
        + place(pen, moon_friend, w - 40, 30, s=0.42, sleepy=True, star=False)
        + stars(pen, [(22, 22, 6), (42, 14, 3.6), (w - 80, 18, 4)], weight=1.6)
        + place(pen, puffy_cloud, 34, h - 6, w=50)
        + place(pen, puffy_cloud, 70, h - 6, w=30, bumps=3)
        + pen.shape(sparkle(18, 50, 3.4), sparkle(w - 20, h - 24, 4), weight=1.3)
    )


@art("growth-chart")
def grow_page(pen: Pen, w: float, h: float) -> str:
    """«ارسم نفسك عندما تكبر»: a growth chart at the side with a star on top, a sprout and a palette."""
    x0, x1, top, base = w - 26, w - 10, 30.0, h - 8
    chart = rect(x0, top, x1 - x0, base - top, 3)
    ticks = []
    y = base - 10
    i = 0
    while y > top + 8:
        ticks.append(seg(x0, y, x0 + (9 if i % 2 == 0 else 5), y))
        y -= 10
        i += 1
    return (
        border(pen, w, h)
        + pen.shape(chart, weight=DECO)
        + pen.stroke(*ticks, weight=1.4)
        + stars(pen, [((x0 + x1) / 2, top - 8, 11)])
        + place(pen, sprout, 20, h - 4, h=20)
        + place(pen, palette, 34, 26, w=34)
    )


# ---- the date page and the favourite drawing ---------------------------------------------------------------

DATE_LINES: tuple[tuple[float, float, float], ...] = ((16.0, 150.0, 176.0), (16.0, 150.0, 212.0))
"""The date page's writing lines as (x from, x to, y) in mm inside the art: the age, then the date. The
template sets their labels at the right end (the start of an Arabic line), beside the icons."""


def cake(pen: Pen, w: float = 110.0) -> str:
    """A two-layer birthday cake on a stand with no candles yet (the child draws as many as their age);
    stands on its origin."""
    plate = e(0, -6, w * 0.62, 5)
    foot = p(f"M{fmt(-w * 0.14)} 0 L{fmt(-w * 0.08)} -6 L{fmt(w * 0.08)} -6 L{fmt(w * 0.14)} 0 Z")
    low_h, top_h = w * 0.36, w * 0.3
    low = rect(-w / 2, -6 - low_h, w, low_h, 4)
    top_w = w * 0.72
    top = rect(-top_w / 2, -6 - low_h - top_h, top_w, top_h, 4)
    out = [pen.shape(foot, plate, weight=DECO), pen.shape(low), pen.shape(top)]
    for y0, ww, n in ((-6 - low_h, w, 7), (-6 - low_h - top_h, top_w, 5)):
        icing = f"M{fmt(-ww / 2)} {fmt(y0)} L{fmt(ww / 2)} {fmt(y0)} L{fmt(ww / 2)} {fmt(y0 + 7)}"
        for i in range(n):
            xa = ww / 2 - ww * i / n
            xb = ww / 2 - ww * (i + 1) / n
            drip = 11 if i % 2 == 0 else 7
            icing += f" Q{fmt((xa + xb) / 2)} {fmt(y0 + drip + 5)} {fmt(xb)} {fmt(y0 + 7)}"
        out.append(pen.shape(p(icing + " Z"), weight=DECO))
    hearts = [heart(x * w, -6 - low_h * 0.42, 9) for x in (-0.3, 0, 0.3)]
    dots = [c(x * top_w, -6 - low_h - top_h * 0.32, 2.4) for x in (-0.3, -0.1, 0.1, 0.3)]
    out.append(pen.shape(*hearts, weight=1.6))
    out.append(pen.shape(*dots, weight=1.4))
    return "".join(out)


@art("date-cake")
def date_page(pen: Pen, w: float, h: float) -> str:
    """The first page: a cake waiting for its candles, balloons at the top corners, and two writing lines
    (the age, the date) with a candle and a calendar as their signs."""
    out = [
        frame_stitched(pen, w, h),
        place(pen, balloon, 24, 30, r=11, string=34),
        place(pen, balloon, w - 24, 30, r=11, string=34, sway=-1),
        place(pen, cake, w / 2, 146, w=112),
        pen.shape(sparkle(48, 26, 4), sparkle(w - 48, 26, 4), sparkle(w / 2, 24, 3.2), weight=1.4),
    ]
    for (x0, x1, y), sign in zip(DATE_LINES, ("candle", "calendar"), strict=True):
        out.append(pen.stroke(seg(x0, y, x1, y), weight=ORNAMENT + 0.2))
        if sign == "candle":
            out.append(place(pen, candle, w - 22, y + 1, h=17))
        else:
            out.append(place(pen, calendar, w - 22, y - 8, size=20))
    return "".join(out)


@art("gallery")
def favourite_page(pen: Pen, w: float, h: float) -> str:
    """«رسمتي المفضلة»: a gallery picture frame hung on a nail, with a prize rosette on its corner."""
    x0, y0, x1, y1 = 8.0, 26.0, w - 8, h - 6
    m = 13.0
    outer = rect(x0, y0, x1 - x0, y1 - y0, 2)
    inner = rect(x0 + m, y0 + m, x1 - x0 - 2 * m, y1 - y0 - 2 * m, 1)
    mitres = [
        seg(x0, y0, x0 + m, y0 + m),
        seg(x1, y0, x1 - m, y0 + m),
        seg(x0, y1, x0 + m, y1 - m),
        seg(x1, y1, x1 - m, y1 - m),
    ]
    beads = []
    for i in range(1, 12):
        beads.append(c(x0 + m / 2 + (x1 - x0 - m) * i / 12, y0 + m / 2, 1.5))
        beads.append(c(x0 + m / 2 + (x1 - x0 - m) * i / 12, y1 - m / 2, 1.5))
    for i in range(1, 16):
        beads.append(c(x0 + m / 2, y0 + m / 2 + (y1 - y0 - m) * i / 16, 1.5))
        beads.append(c(x1 - m / 2, y0 + m / 2 + (y1 - y0 - m) * i / 16, 1.5))
    cord = p(f"M{fmt(w * 0.3)} {fmt(y0 + 1)} L{fmt(w / 2)} 7 L{fmt(w * 0.7)} {fmt(y0 + 1)}")
    return (
        pen.stroke(cord, weight=1.6)
        + pen.shape(c(w / 2, 6, 3.2), weight=1.6)
        + pen.shape(outer, weight=FRAME + 0.6)
        + pen.shape(inner, weight=FRAME)
        + pen.stroke(*mitres, weight=ORNAMENT)
        + pen.solid(*beads)
        + place(pen, rosette, x1 - 12, y0 + 10, r=15)
    )


# ---- «أَكْمِلِ الرَّسْمَةَ»: half-drawings to finish --------------------------------------------------------

_WING_UP: list[Point] = [(-4, -6), (-20, -40), (-48, -70), (-78, -66), (-84, -36), (-62, -8), (-30, 0)]
_WING_LOW: list[Point] = [(-4, 2), (-30, 2), (-62, 14), (-70, 44), (-46, 70), (-18, 56), (-5, 28)]


def _mirror(points: list[Point]) -> list[Point]:
    return [(-x, y) for x, y in points]


@art("finish-butterfly")
def finish_butterfly(pen: Pen, w: float, h: float) -> str:
    """Half a butterfly: the left wings drawn with their patterns, the right wings as a dotted guide, the
    body on the dashed line of symmetry."""
    cx, cy = w / 2, h * 0.5

    def at(pts: list[Point]) -> list[Point]:
        return [(cx + x, cy + y) for x, y in pts]

    left = pen.shape(smooth(at(_WING_UP), tension=0.85)) + pen.shape(smooth(at(_WING_LOW), tension=0.85))
    patterns = pen.shape(
        e(cx - 52, cy - 44, 13, 10, -20),
        c(cx - 28, cy - 22, 6),
        c(cx - 70, cy - 26, 5),
        e(cx - 42, cy + 34, 10, 13, 20),
        c(cx - 22, cy + 18, 5),
        weight=1.8,
    )
    right = dotted(
        pen,
        smooth(at(_mirror(_WING_UP)), tension=0.85),
        smooth(at(_mirror(_WING_LOW)), tension=0.85),
        weight=1.9,
        gap=5,
    )
    body = pen.shape(e(cx, cy + 6, 6.5, 40))
    head = pen.shape(c(cx, cy - 40, 9))
    feelers = pen.stroke(
        p(f"M{fmt(cx - 4)} {fmt(cy - 47)} Q{fmt(cx - 10)} {fmt(cy - 66)} {fmt(cx - 22)} {fmt(cy - 72)}"),
        p(f"M{fmt(cx + 4)} {fmt(cy - 47)} Q{fmt(cx + 10)} {fmt(cy - 66)} {fmt(cx + 22)} {fmt(cy - 72)}"),
        weight=FINE,
    )
    tips = pen.shape(c(cx - 23, cy - 73, 3.2), c(cx + 23, cy - 73, 3.2), weight=FINE)
    face = pen.solid(c(cx - 3.2, cy - 41, 1.4), c(cx + 3.2, cy - 41, 1.4)) + pen.stroke(
        p(f"M{fmt(cx - 3)} {fmt(cy - 36.5)} Q{fmt(cx)} {fmt(cy - 34)} {fmt(cx + 3)} {fmt(cy - 36.5)}"),
        weight=1.3,
    )
    axis = dashed(pen, seg(cx, 16, cx, cy - 84), seg(cx, cy + 54, cx, h - 14), weight=1.4, dash=5, gap=4)
    return border(pen, w, h) + axis + left + patterns + right + body + feelers + tips + head + face


@art("finish-house")
def finish_house(pen: Pen, w: float, h: float) -> str:
    """A house waiting for its roof and windows: the walls, an arched door with a step, a tree, the sun."""
    ground = h - 30
    x0, x1, top = 36.0, 150.0, 116.0
    walls = rect(x0, top, x1 - x0, ground - top, 1)
    door = p(_arch_path(w / 2 - 17, w / 2 + 11, ground, ground - 52))
    step = rect(w / 2 - 25, ground - 1, 44, 6, 2)
    knob = c(w / 2 + 5, ground - 24, 2)
    trunk = rect(w - 23, ground - 46, 8, 46, 2)
    crown = scallop(w - 19, ground - 66, 15, 22, 7, 0.7)
    grass = seg(INSET + 1, ground, w - INSET - 1, ground)
    return (
        border(pen, w, h)
        + pen.stroke(grass, weight=MAIN)
        + pen.shape(walls)
        + pen.shape(door)
        + pen.shape(step, weight=DECO)
        + pen.solid(knob)
        + pen.shape(trunk)
        + pen.shape(crown)
        + place(pen, tuft, 20, ground, w=10)
        + place(pen, flower, 26, ground, h=22)
        + place(pen, tuft, w / 2 + 40, ground, w=9)
        + place(pen, sun_face, 26, 26, r=11, smile=False)
    )


@art("finish-car")
def finish_car(pen: Pen, w: float, h: float) -> str:
    """A car with no wheels yet: the body with its windows, empty wheel arches and dotted circles to trace."""
    road = h * 0.7
    wr = 19.0
    xa, xb = 56.0, 134.0
    axle = road - wr
    body = p(
        f"M18 {fmt(axle)} L18 {fmt(axle - 22)} Q18 {fmt(axle - 32)} 30 {fmt(axle - 34)} L52 {fmt(axle - 36)} "
        f"L70 {fmt(axle - 66)} Q74 {fmt(axle - 72)} 82 {fmt(axle - 72)} L124 {fmt(axle - 72)} "
        f"Q132 {fmt(axle - 72)} 136 {fmt(axle - 66)} L150 {fmt(axle - 38)} L162 {fmt(axle - 34)} "
        f"Q170 {fmt(axle - 32)} 170 {fmt(axle - 22)} L170 {fmt(axle)} "
        f"L{fmt(xb + wr + 4)} {fmt(axle)} A{fmt(wr + 4)} {fmt(wr + 4)} 0 0 0 {fmt(xb - wr - 4)} {fmt(axle)} "
        f"L{fmt(xa + wr + 4)} {fmt(axle)} A{fmt(wr + 4)} {fmt(wr + 4)} 0 0 0 {fmt(xa - wr - 4)} {fmt(axle)} Z"
    )
    windows = [
        p(f"M60 {fmt(axle - 38)} L74 {fmt(axle - 63)} L98 {fmt(axle - 63)} L98 {fmt(axle - 38)} Z"),
        p(f"M106 {fmt(axle - 38)} L106 {fmt(axle - 63)} L128 {fmt(axle - 63)} L140 {fmt(axle - 38)} Z"),
    ]
    door = p(f"M102 {fmt(axle - 36)} L102 {fmt(axle - 6)}")
    handle = rect(84, axle - 30, 10, 3.4, 1.7)
    lamp = e(165, axle - 26, 3.5, 5)
    back_lamp = rect(18, axle - 28, 4, 9, 1.5)
    road_line = dashed(pen, seg(INSET + 8, road + 14, w - INSET - 8, road + 14), weight=2.0, dash=12, gap=8)
    return (
        border(pen, w, h)
        + pen.stroke(seg(INSET + 1, road, w - INSET - 1, road), weight=MAIN)
        + road_line
        + pen.shape(body)
        + pen.shape(*windows, weight=DECO)
        + pen.stroke(door, weight=FINE)
        + pen.shape(handle, lamp, back_lamp, weight=1.6)
        + dotted(pen, c(xa, axle, wr), c(xb, axle, wr), weight=2.0, gap=5)
        + place(pen, puffy_cloud, 40, 48, w=44)
        + place(pen, puffy_cloud, w - 40, 36, w=30, bumps=3)
    )


@art("finish-fishbowl")
def finish_fishbowl(pen: Pen, w: float, h: float) -> str:
    """An empty fish bowl to fill with fish: water, pebbles, a water plant and a few bubbles."""
    cx, cy, r = w / 2, h * 0.5, 74.0
    open_y = cy - r * 0.78
    half = math.sqrt(r * r - (cy - open_y) ** 2)
    bottom_y = cy + r * 0.86
    bh = math.sqrt(r * r - (bottom_y - cy) ** 2)
    bowl = p(
        f"M{fmt(cx - half)} {fmt(open_y)} A{fmt(r)} {fmt(r)} 0 0 0 {fmt(cx - bh)} {fmt(bottom_y)} "
        f"L{fmt(cx + bh)} {fmt(bottom_y)} A{fmt(r)} {fmt(r)} 0 0 0 {fmt(cx + half)} {fmt(open_y)} Z"
    )
    lip = e(cx, open_y, half + 4, 6)
    water_y = cy - r * 0.55
    wx = math.sqrt(r * r - (water_y - cy) ** 2) - 2
    water = p(wave_d(cx - wx, cx + wx, water_y, 2.5, 6))
    pebbles = [
        e(cx + dx, bottom_y - 5, rx, 5)
        for dx, rx in ((-34, 8), (-18, 7), (-3, 8.5), (13, 7), (29, 8), (43, 6))
    ]
    weed = [
        p(leaf_d(cx - 40, bottom_y - 4, 40, 13, -114)),
        p(leaf_d(cx - 34, bottom_y - 4, 62, 16, -93)),
        p(leaf_d(cx - 28, bottom_y - 4, 44, 13, -70)),
    ]
    bubbles = [c(cx + 30, water_y + 18, 3.2), c(cx + 36, water_y + 32, 2.4), c(cx + 27, water_y + 44, 2)]
    table = rect(cx - 84, bottom_y, 168, 8, 3)
    return (
        border(pen, w, h)
        + pen.shape(table, weight=DECO)
        + pen.shape(bowl, weight=MAIN + 0.4)
        + pen.stroke(water, weight=FINE)
        + pen.shape(*weed, weight=DECO)
        + pen.shape(*pebbles, weight=DECO)
        + pen.shape(*bubbles, weight=1.4)
        + pen.shape(lip, weight=MAIN)
    )


@art("finish-tree")
def finish_tree(pen: Pen, w: float, h: float) -> str:
    """A bare tree: a trunk and branches waiting for leaves and fruit, a dotted crown to fill, grass below."""
    ground = h - 22
    cx = w / 2
    crown = scallop_d(cx, 96, 78, 66, 13, 0.62)
    outline: list[Point] = [
        (cx - 20, ground),
        (cx - 12, ground - 30),
        (cx - 11, ground - 70),
        (cx - 14, 128),
        (cx - 34, 110),
        (cx - 56, 96),
        (cx - 66, 88),
        (cx - 62, 82),
        (cx - 50, 86),
        (cx - 30, 98),
        (cx - 12, 108),
        (cx - 12, 88),
        (cx - 18, 62),
        (cx - 16, 48),
        (cx - 10, 50),
        (cx - 4, 64),
        (cx + 2, 92),
        (cx + 8, 104),
        (cx + 26, 88),
        (cx + 46, 72),
        (cx + 60, 62),
        (cx + 65, 68),
        (cx + 54, 80),
        (cx + 34, 98),
        (cx + 14, 122),
        (cx + 11, ground - 70),
        (cx + 12, ground - 30),
        (cx + 22, ground),
    ]
    lo, hi = INSET + 1, w - INSET - 1
    hill = p(f"M{fmt(lo)} {fmt(ground + 4)} Q{fmt(w / 2)} {fmt(ground - 8)} {fmt(hi)} {fmt(ground + 4)}")
    bark = [
        p(
            f"M{fmt(cx - 3)} {fmt(ground - 22)} Q{fmt(cx + 1)} "
            f"{fmt(ground - 32)} {fmt(cx - 1)} {fmt(ground - 44)}"
        ),
        p(
            f"M{fmt(cx + 4)} {fmt(ground - 64)} Q{fmt(cx + 6)} "
            f"{fmt(ground - 72)} {fmt(cx + 4)} {fmt(ground - 80)}"
        ),
    ]
    return (
        border(pen, w, h)
        + dotted(pen, p(crown), weight=1.8, gap=5)
        + pen.shape(smooth(outline, tension=0.7))
        + pen.stroke(*bark, weight=1.6)
        + pen.stroke(hill, weight=MAIN)
        + place(pen, tuft, 30, ground, w=11)
        + place(pen, flower, 44, ground + 1, h=20)
        + place(pen, basket, w - 36, h - 9, w=32)
    )


@art("finish-lion")
def finish_lion(pen: Pen, w: float, h: float) -> str:
    """A sitting lion with no face yet: the mane, the ears, the empty face to draw on; legs, paws, a tail."""
    cx, cy = w / 2, 100.0
    ground = h - 12
    body = p(
        f"M{fmt(cx - 50)} {fmt(ground)} C{fmt(cx - 58)} "
        f"{fmt(cy + 70)} {fmt(cx - 40)} {fmt(cy + 40)} {fmt(cx)} "
        f"{fmt(cy + 40)} C{fmt(cx + 40)} {fmt(cy + 40)} {fmt(cx + 58)} "
        f"{fmt(cy + 70)} {fmt(cx + 50)} {fmt(ground)} Z"
    )
    legs = [seg(cx, cy + 74, cx, ground - 12), seg(cx - 30, cy + 72, cx - 31, ground - 12)]
    legs.append(seg(cx + 30, cy + 72, cx + 31, ground - 12))
    paws = [e(cx - 16, ground - 6, 16, 8.5), e(cx + 16, ground - 6, 16, 8.5)]
    toes = [seg(cx + x + dx, ground - 2.5, cx + x + dx, ground - 8) for x in (-16, 16) for dx in (-5, 5)]

    tail = p(
        f"M{fmt(cx + 46)} {fmt(ground - 8)} C{fmt(cx + 72)} "
        f"{fmt(ground - 8)} {fmt(cx + 66)} {fmt(ground - 50)} "
        f"{fmt(cx + 76)} {fmt(ground - 58)}"
    )
    mane = scallop(cx, cy, 74, 70, 18, 0.7)
    ears = [c(cx - 34, cy - 40, 12), c(cx + 34, cy - 40, 12)]
    ear_in = [c(cx - 36, cy - 42, 5.5), c(cx + 36, cy - 42, 5.5)]
    face = e(cx, cy + 4, 48, 45)
    haunches = [
        p(
            f"M{fmt(cx - 34)} {fmt(ground - 2)} C{fmt(cx - 50)} "
            f"{fmt(ground - 20)} {fmt(cx - 46)} {fmt(ground - 44)} "
            f"{fmt(cx - 32)} {fmt(ground - 48)}"
        ),
        p(
            f"M{fmt(cx + 34)} {fmt(ground - 2)} C{fmt(cx + 50)} "
            f"{fmt(ground - 20)} {fmt(cx + 46)} {fmt(ground - 44)} "
            f"{fmt(cx + 32)} {fmt(ground - 48)}"
        ),
    ]
    return (
        border(pen, w, h)
        + pen.stroke(tail, weight=MAIN)
        + pen.shape(scallop(cx + 77, ground - 61, 6.5, 6.5, 5, 0.7), weight=DECO)
        + pen.shape(body)
        + pen.stroke(*haunches, weight=FINE)
        + pen.stroke(*legs, weight=FINE)
        + pen.shape(*paws)
        + pen.stroke(*toes, weight=1.6)
        + pen.shape(mane)
        + pen.shape(*ears)
        + pen.shape(*ear_in, weight=FINE)
        + pen.shape(face)
    )
