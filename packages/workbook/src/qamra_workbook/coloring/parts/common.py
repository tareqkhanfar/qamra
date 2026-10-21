"""Parts every coloring book shares: sky and ground, plants, birds and the friendly people.

All parts follow `coloring.ink`'s conventions (local mm, origin at the base for standing things, at the centre
for floating ones). People have simple faces only: two dot eyes and a smile (no noses, no detail).
"""

from __future__ import annotations

import math
import random
from typing import Literal

from qamra_workbook.coloring.ink import (
    CLOUD,
    EARTH,
    FINE,
    GRASS,
    GRASS_DEEP,
    HAIR,
    HILL,
    HILL_FAR,
    MAIN,
    NAVY,
    ORANGE,
    PINK,
    POPPY,
    RED,
    SKIN,
    SUN,
    TEAL,
    TRUNK,
    WHITE,
    YELLOW,
    Pen,
    Point,
    c,
    e,
    fmt,
    p,
    polar,
    rect,
    scallop,
    smooth,
)

# ---- sky -----------------------------------------------------------------------------------------------------


def cloud(pen: Pen, w: float = 46.0) -> str:
    """A puffy cloud centred on its origin, flat underneath."""
    h = w * 0.42
    d = (
        f"M{fmt(-w / 2)} {fmt(h * 0.3)} "
        f"C{fmt(-w * 0.62)} {fmt(-h * 0.1)} {fmt(-w * 0.36)} {fmt(-h * 0.42)} {fmt(-w * 0.2)} {fmt(-h * 0.2)} "
        f"C{fmt(-w * 0.16)} {fmt(-h * 0.85)} {fmt(w * 0.2)} {fmt(-h * 0.9)} {fmt(w * 0.16)} {fmt(-h * 0.28)} "
        f"C{fmt(w * 0.36)} {fmt(-h * 0.5)} {fmt(w * 0.6)} {fmt(-h * 0.2)} {fmt(w / 2)} {fmt(h * 0.3)} Z"
    )
    return pen.shape(p(d), fill=CLOUD)


def sun(pen: Pen, r: float = 16.0, rays: int = 10) -> str:
    """A round sun with rounded rays, centred on its origin."""
    out = []
    half = 100 / rays  # half the angle a ray's foot spans: wide, soft rays (≈ 6 mm at the foot)
    for i in range(rays):
        a = 360 * i / rays
        x1, y1 = polar(0, 0, r + 3.6, a - half)
        x2, y2 = polar(0, 0, r + 19, a)
        x3, y3 = polar(0, 0, r + 3.6, a + half)
        out.append(p(f"M{fmt(x1)} {fmt(y1)} Q{fmt(x2)} {fmt(y2)} {fmt(x3)} {fmt(y3)} Z"))
    return pen.shape(*out, fill=SUN) + pen.shape(c(0, 0, r), fill=SUN)


def bird_v(pen: Pen, w: float = 12.0) -> str:
    """A far-away bird: a soft «v» (an open line)."""
    return pen.stroke(
        p(
            f"M{fmt(-w / 2)} {fmt(-w * 0.1)} Q{fmt(-w / 4)} {fmt(-w * 0.42)} 0 0 Q{fmt(w / 4)} {fmt(-w * 0.42)} {fmt(w / 2)} {fmt(-w * 0.1)}"
        ),
        weight=FINE,
    )


# ---- ground --------------------------------------------------------------------------------------------------


def hills(
    pen: Pen,
    w: float,
    y: float,
    amp: float,
    n: int = 3,
    *,
    fill: str = HILL,
    seed: int = 1,
    floor: float = 400,
) -> str:
    """A band of rolling hills across 0…w whose ridge sits around `y` (`amp` up or down), down to `floor`."""
    rnd = random.Random(seed)
    xs = [w * i / n for i in range(n + 1)]
    pts: list[Point] = [(-10, y + amp * 0.3)]
    for i, x in enumerate(xs):
        pts.append((x, y - amp * (0.4 + 0.6 * rnd.random()) * (1 if i % 2 else -0.3)))
    pts.append((w + 10, y + amp * 0.2))
    ridge = smooth(pts, closed=False).removeprefix('<path d="').removesuffix('"/>')
    d = f"{ridge} L{fmt(w + 10)} {fmt(floor)} L-10 {fmt(floor)} Z"
    return pen.shape(p(d), fill=fill)


def ground(pen: Pen, w: float, y: float, floor: float = 400, fill: str = GRASS, wobble: float = 3.0) -> str:
    """The near ground: a gently wavy edge at `y`."""
    pts = [
        (-10.0, y),
        (w * 0.25, y - wobble),
        (w * 0.55, y + wobble * 0.6),
        (w * 0.8, y - wobble * 0.8),
        (w + 10, y),
    ]
    ridge = smooth(pts, closed=False).removeprefix('<path d="').removesuffix('"/>')
    return pen.shape(p(f"{ridge} L{fmt(w + 10)} {fmt(floor)} L-10 {fmt(floor)} Z"), fill=fill)


def tuft(pen: Pen, w: float = 10.0) -> str:
    """Three blades of grass standing on the origin (open lines)."""
    h = w * 0.9
    return pen.stroke(
        p(f"M{fmt(-w * 0.3)} 0 Q{fmt(-w * 0.35)} {fmt(-h * 0.5)} {fmt(-w * 0.55)} {fmt(-h * 0.8)}"),
        p(f"M0 0 Q{fmt(w * 0.05)} {fmt(-h * 0.6)} 0 {fmt(-h)}"),
        p(f"M{fmt(w * 0.3)} 0 Q{fmt(w * 0.35)} {fmt(-h * 0.5)} {fmt(w * 0.55)} {fmt(-h * 0.8)}"),
    )


def stone(pen: Pen, w: float = 14.0, fill: str = "#D8D2C6") -> str:
    h = w * 0.55
    return pen.shape(
        smooth([(-w / 2, 0), (-w * 0.4, -h * 0.8), (0, -h), (w * 0.42, -h * 0.75), (w / 2, 0)]), fill=fill
    )


# ---- plants --------------------------------------------------------------------------------------------------


def leaf_d(x: float, y: float, length: float, width: float, angle: float) -> str:
    """A pointed leaf from its stalk at (x, y), pointing at `angle` degrees."""
    tip = polar(x, y, length, angle)
    side1 = polar(x, y, length * 0.5, angle - 90 * width / length * 1.4)
    side2 = polar(x, y, length * 0.5, angle + 90 * width / length * 1.4)
    m1 = polar(side1[0], side1[1], width * 0.45, angle - 90)
    m2 = polar(side2[0], side2[1], width * 0.45, angle + 90)
    return (
        f"M{fmt(x)} {fmt(y)} Q{fmt(m1[0])} {fmt(m1[1])} {fmt(tip[0])} {fmt(tip[1])} "
        f"Q{fmt(m2[0])} {fmt(m2[1])} {fmt(x)} {fmt(y)} Z"
    )


def flower(pen: Pen, h: float = 30.0, petals: int = 5, fill: str = PINK, centre: str = YELLOW) -> str:
    """A simple garden flower on a stem with two leaves; origin at the stem's foot."""
    top = -h
    r = h * 0.2
    out = [pen.stroke(p(f"M0 0 Q{fmt(h * 0.06)} {fmt(-h * 0.5)} 0 {fmt(top)}"), weight=MAIN)]
    out.append(
        pen.shape(
            p(leaf_d(0, -h * 0.3, h * 0.32, h * 0.13, -30)),
            p(leaf_d(0, -h * 0.45, h * 0.3, h * 0.12, 200)),
            fill=GRASS_DEEP,
        )
    )
    for i in range(petals):
        cx, cy = polar(0, top, r * 1.05, -90 + 360 * i / petals)
        out.append(pen.shape(e(cx, cy, r * 0.75, r * 0.95, -90 + 360 * i / petals + 90), fill=fill))
    out.append(pen.shape(c(0, top, r * 0.62), fill=centre))
    return "".join(out)


def poppy(pen: Pen, h: float = 34.0, fill: str = POPPY) -> str:
    """A wild poppy («شَقائِقُ / دَحْنون» family): a bowl of four round petals with a dark heart, on a curved
    hairy stem (drawn as a clean line) with a feathery leaf."""
    top = -h
    r = h * 0.24
    out = [
        pen.stroke(
            p(
                f"M0 0 C{fmt(h * 0.12)} {fmt(-h * 0.35)} {fmt(-h * 0.1)} {fmt(-h * 0.7)} 0 {fmt(top + r * 0.4)}"
            ),
            weight=MAIN,
        )
    ]
    out.append(pen.shape(p(leaf_d(0, -h * 0.18, h * 0.3, h * 0.12, -40)), fill=GRASS_DEEP))
    back = e(0, top - r * 0.35, r * 1.05, r * 0.75)
    out.append(pen.shape(back, fill=fill))
    out.append(
        pen.shape(
            e(-r * 0.62, top + r * 0.05, r * 0.72, r * 0.82, -20),
            e(r * 0.62, top + r * 0.05, r * 0.72, r * 0.82, 20),
            fill=fill,
        )
    )
    out.append(pen.shape(e(0, top + r * 0.25, r * 0.7, r * 0.75), fill=fill))
    out.append(pen.shape(e(0, top - r * 0.35, r * 0.34, r * 0.22), fill="#2E2A33"))
    return "".join(out)


def bush(pen: Pen, w: float = 40.0, fill: str = GRASS_DEEP) -> str:
    h = w * 0.55
    return pen.shape(
        p(
            f"M{fmt(-w / 2)} 0 C{fmt(-w * 0.62)} {fmt(-h * 0.7)} {fmt(-w * 0.22)} {fmt(-h * 1.05)} {fmt(-w * 0.08)} {fmt(-h * 0.8)} "
            f"C{fmt(w * 0.02)} {fmt(-h * 1.2)} {fmt(w * 0.42)} {fmt(-h * 1.1)} {fmt(w * 0.36)} {fmt(-h * 0.6)} "
            f"C{fmt(w * 0.6)} {fmt(-h * 0.5)} {fmt(w * 0.6)} {fmt(-h * 0.1)} {fmt(w / 2)} 0 Z"
        ),
        fill=fill,
    )


# ---- people --------------------------------------------------------------------------------------------------

Pose = Literal["down", "up", "wave", "hold", "reach", "hips"]
Hair = Literal["pigtails", "ponytail", "bob", "short", "curly", "none"]


def limb(x1: float, y1: float, x2: float, y2: float, width: float) -> str:
    """A rounded capsule from (x1, y1) to (x2, y2): an arm or a leg."""
    a = math.atan2(y2 - y1, x2 - x1)
    nx, ny = -math.sin(a) * width / 2, math.cos(a) * width / 2
    r = width / 2
    return p(
        f"M{fmt(x1 + nx)} {fmt(y1 + ny)} L{fmt(x2 + nx)} {fmt(y2 + ny)} "
        f"A{fmt(r)} {fmt(r)} 0 0 0 {fmt(x2 - nx)} {fmt(y2 - ny)} L{fmt(x1 - nx)} {fmt(y1 - ny)} "
        f"A{fmt(r)} {fmt(r)} 0 0 0 {fmt(x1 + nx)} {fmt(y1 + ny)} Z"
    )


def face(pen: Pen, cx: float, cy: float, r: float, *, look: float = 0.0, happy: bool = True) -> str:
    """Two dot eyes and a smile on a head of radius `r` centred at (cx, cy); `look` shifts them sideways."""
    ex = r * 0.36
    ey = cy - r * 0.02
    dx = look * r * 0.18
    eye_r = max(r * 0.11, 1.4)
    smile_w = r * 0.32
    sy = cy + r * 0.34
    mouth = (
        f"M{fmt(cx + dx - smile_w)} {fmt(sy)} Q{fmt(cx + dx)} {fmt(sy + r * 0.3)} {fmt(cx + dx + smile_w)} {fmt(sy)}"
        if happy
        else f"M{fmt(cx + dx - smile_w * 0.6)} {fmt(sy + 1)} L{fmt(cx + dx + smile_w * 0.6)} {fmt(sy + 1)}"
    )
    return (
        pen.solid(e(cx - ex + dx, ey, eye_r, eye_r * 1.25), e(cx + ex + dx, ey, eye_r, eye_r * 1.25))
        + pen.stroke(p(mouth), weight=FINE)
        + pen.tint(
            e(cx - r * 0.56 + dx, cy + r * 0.28, r * 0.17, r * 0.11),
            e(cx + r * 0.56 + dx, cy + r * 0.28, r * 0.17, r * 0.11),
            fill="#F08A7E",
        )
    )


_ARMS: dict[str, tuple[Point, Point]] = {
    # (left hand, right hand) relative to the shoulders, for a child 100 units tall
    "down": ((-15, -38), (15, -38)),
    "up": ((-20, -86), (20, -86)),
    "wave": ((-15, -38), (21, -84)),
    "hold": ((-6, -48), (6, -48)),
    "reach": ((-15, -38), (24, -70)),
    "hips": ((-16, -46), (16, -46)),
}


def child(
    pen: Pen,
    *,
    girl: bool = True,
    hair: Hair | None = None,
    pose: Pose = "down",
    dress: str = PINK,
    shirt: str = TEAL,
    trousers: str = NAVY,
    skin: str = SKIN,
    hair_color: str = HAIR,
    look: float = 0.0,
    shoes: str = RED,
    pattern: bool = False,
    hands: tuple[Point, Point] | None = None,
) -> str:
    """A friendly child about 100 units tall, standing on the origin. A girl wears a dress (no headscarf:
    the owner's marketing rule for girls), a boy a shirt and trousers. `pose` sets the arms; `pattern` adds a
    simple embroidered band to the hem (the tatreez look); `hands` (left, right) places the hands anywhere
    instead of a pose (to hold or reach for something)."""
    hair = hair or ("pigtails" if girl else "short")
    head_y, head_r = -72.0, 14.0
    shoulder_y = -54.0
    out: list[str] = []
    left, right = hands or _ARMS[pose]
    # hair behind the head
    if hair == "ponytail":
        out.append(
            pen.shape(
                p(
                    f"M8 {fmt(head_y - 8)} C26 {fmt(head_y - 10)} 24 {fmt(head_y + 14)} 16 {fmt(head_y + 20)} C18 {fmt(head_y + 8)} 14 {fmt(head_y)} 8 {fmt(head_y - 2)} Z"
                ),
                fill=hair_color,
            )
        )
    if hair == "bob":
        out.append(
            pen.shape(
                p(
                    f"M-16 {fmt(head_y + 10)} C-20 {fmt(head_y - 14)} 20 {fmt(head_y - 14)} 16 {fmt(head_y + 10)} Z"
                ),
                fill=hair_color,
            )
        )
    # legs and shoes
    hem = -26.0
    for sx in (-1, 1):
        out.append(pen.shape(limb(sx * 6, hem - 4, sx * 6.5, -6, 7.5), fill=skin if girl else trousers))
        out.append(
            pen.shape(
                p(
                    f"M{fmt(sx * 6.5 - 5)} -1 C{fmt(sx * 6.5 - 5)} -8 {fmt(sx * 6.5 + 5)} -8 {fmt(sx * 6.5 + 5 + sx * 3)} -1 Z"
                ),
                fill=shoes,
            )
        )

    # arms behind the body when they hang down
    def arm(hand: Point, sx: int) -> str:
        sh = (sx * 10.0, shoulder_y + 3)
        hx, hy = hand
        return pen.shape(limb(sh[0], sh[1], hx, hy, 7.0), fill=dress if girl else shirt) + pen.shape(
            c(hx, hy, 3.9), fill=skin
        )

    body_d = (
        f"M-9 {fmt(shoulder_y)} C-4 {fmt(shoulder_y - 3)} 4 {fmt(shoulder_y - 3)} 9 {fmt(shoulder_y)} "
        f"L{fmt(19 if girl else 13)} {fmt(hem if girl else hem - 4)} "
        f"Q0 {fmt((hem if girl else hem - 4) + 4)} {fmt(-19 if girl else -13)} {fmt(hem if girl else hem - 4)} Z"
    )
    if not girl:  # trousers' top under the shirt
        out.append(pen.shape(rect(-12, hem - 12, 24, 10, 3), fill=trousers))
    out.append(pen.shape(p(body_d), fill=dress if girl else shirt))
    if girl and pattern:
        out.append(
            pen.stroke(p(f"M-16.5 {fmt(hem - 5)} Q0 {fmt(hem - 1.5)} 16.5 {fmt(hem - 5)}"), weight=FINE)
        )
    # collar line
    out.append(
        pen.stroke(
            p(f"M-5 {fmt(shoulder_y - 1)} Q0 {fmt(shoulder_y + 4)} 5 {fmt(shoulder_y - 1)}"), weight=FINE
        )
    )
    out.append(arm(left, -1))
    out.append(arm(right, 1))
    # head
    out.append(pen.shape(c(0, head_y, head_r), fill=skin))
    out.append(_hair_front(pen, hair, head_y, head_r, hair_color))
    out.append(face(pen, 0, head_y + 2, head_r, look=look))
    return "".join(out)


def _hair_front(pen: Pen, hair: str, y: float, r: float, color: str) -> str:
    if hair == "none":
        return ""
    cap = (
        f"M{fmt(-r - 0.6)} {fmt(y + 2)} C{fmt(-r - 1)} {fmt(y - r - 4)} {fmt(r + 1)} {fmt(y - r - 4)} {fmt(r + 0.6)} {fmt(y + 2)} "
        f"C{fmt(r * 0.5)} {fmt(y - r * 0.55)} {fmt(-r * 0.2)} {fmt(y - r * 0.4)} {fmt(-r * 0.15)} {fmt(y - r * 0.75)} "
        f"C{fmt(-r * 0.4)} {fmt(y - r * 0.35)} {fmt(-r * 0.8)} {fmt(y - r * 0.4)} {fmt(-r - 0.6)} {fmt(y + 2)} Z"
    )
    out = [pen.shape(p(cap), fill=color)]
    if hair == "pigtails":
        for sx in (-1, 1):
            out.insert(0, pen.shape(e(sx * (r + 5), y + 2, 5.5, 8, sx * -20), fill=color))
            out.append(pen.shape(c(sx * (r + 0.8), y - 4, 2.6), fill=RED))
    if hair == "curly":
        out = [pen.shape(scallop(0, y - r * 0.35, r + 2, r * 0.75, 9, 0.7), fill=color)]
    return "".join(out)


def woman(
    pen: Pen,
    *,
    scarf: str = "#E9D9B8",
    dress: str = NAVY,
    skin: str = SKIN,
    pose: Pose = "down",
    embroidered: bool = True,
) -> str:
    """A grown woman about 150 units tall in a long embroidered thob and a soft headscarf (natural village and
    family scenes), standing on the origin."""
    out: list[str] = []
    head_y, head_r = -126.0, 15.0
    sh = -106.0
    hands = {
        "down": ((-24, -62), (24, -62)),
        "hold": ((-9, -80), (9, -80)),
        "up": ((-26, -150), (26, -150)),
        "reach": ((-24, -62), (32, -128)),
        "wave": ((-24, -62), (30, -140)),
        "hips": ((-24, -78), (24, -78)),
    }[pose]
    for sx in (-1, 1):
        out.append(
            pen.shape(
                p(
                    f"M{fmt(sx * 9 - 6)} -1 C{fmt(sx * 9 - 6)} -8 {fmt(sx * 9 + 6)} -8 {fmt(sx * 9 + 6 + sx * 3)} -1 Z"
                ),
                fill="#8F5E36",
            )
        )
    thob = f"M-13 {fmt(sh)} C-5 {fmt(sh - 4)} 5 {fmt(sh - 4)} 13 {fmt(sh)} C19 -70 24 -30 27 -5 Q0 -1 -27 -5 C-24 -30 -19 -70 -13 {fmt(sh)} Z"
    out.append(pen.shape(p(thob), fill=dress))
    if embroidered:  # a chest panel and a hem band: big cross-stitch diamonds to colour
        out.append(
            pen.shape(
                p(f"M-8 {fmt(sh + 2)} L8 {fmt(sh + 2)} L7 {fmt(sh + 26)} L-7 {fmt(sh + 26)} Z"), fill=RED
            )
        )
        out.append(
            pen.stroke(
                p(f"M0 {fmt(sh + 6)} L5 {fmt(sh + 14)} L0 {fmt(sh + 22)} L-5 {fmt(sh + 14)} Z"), weight=FINE
            )
        )
        out.append(pen.stroke(p("M-26 -17 Q0 -12 26 -17"), weight=FINE))
        for i in range(-2, 3):
            x = i * 9.5
            out.append(
                pen.stroke(
                    p(f"M{fmt(x)} -14 L{fmt(x + 3.5)} -9.5 L{fmt(x)} -5 L{fmt(x - 3.5)} -9.5 Z"), weight=FINE
                )
            )
    for sx, hand in ((-1, hands[0]), (1, hands[1])):
        out.append(
            pen.shape(limb(sx * 12, sh + 4, hand[0], hand[1], 9), fill=dress)
            + pen.shape(c(hand[0], hand[1], 4.6), fill=skin)
        )
    # the scarf frames the face and falls to the shoulders
    out.append(
        pen.shape(
            p(
                f"M-21 {fmt(head_y + 4)} C-23 {fmt(head_y - 26)} 23 {fmt(head_y - 26)} 21 {fmt(head_y + 4)} C22 {fmt(head_y + 18)} 18 {fmt(sh + 4)} 14 {fmt(sh + 6)} L-14 {fmt(sh + 6)} C-18 {fmt(sh + 4)} -22 {fmt(head_y + 18)} -21 {fmt(head_y + 4)} Z"
            ),
            fill=scarf,
        )
    )
    out.append(pen.shape(e(0, head_y + 2, head_r * 0.82, head_r * 0.95), fill=skin))
    out.append(face(pen, 0, head_y + 3, head_r * 0.85))
    return "".join(out)


def man(
    pen: Pen,
    *,
    keffiyeh: bool = False,
    robe: str = "#E8E1D2",
    skin: str = SKIN,
    pose: Pose = "down",
    beard: bool = False,
    hair_color: str = "#3A2D28",
) -> str:
    """A grown man about 155 units tall in a long robe; with `keffiyeh` a grandfather's white headcloth and
    black cord (a natural village look), standing on the origin."""
    out: list[str] = []
    head_y, head_r = -132.0, 15.0
    sh = -112.0
    hands = {
        "down": ((-25, -66), (25, -66)),
        "hold": ((-9, -84), (9, -84)),
        "up": ((-27, -156), (27, -156)),
        "reach": ((-25, -66), (33, -132)),
        "wave": ((-25, -66), (31, -146)),
        "hips": ((-25, -82), (25, -82)),
    }[pose]
    for sx in (-1, 1):
        out.append(
            pen.shape(
                p(
                    f"M{fmt(sx * 9 - 6)} -1 C{fmt(sx * 9 - 6)} -8 {fmt(sx * 9 + 6)} -8 {fmt(sx * 9 + 6 + sx * 3)} -1 Z"
                ),
                fill="#5B3A29",
            )
        )
    robe_d = f"M-15 {fmt(sh)} C-6 {fmt(sh - 4)} 6 {fmt(sh - 4)} 15 {fmt(sh)} C20 -70 23 -30 24 -5 Q0 -2 -24 -5 C-23 -30 -20 -70 -15 {fmt(sh)} Z"
    out.append(pen.shape(p(robe_d), fill=robe))
    out.append(pen.stroke(p(f"M0 {fmt(sh + 2)} L0 {fmt(sh + 30)}"), weight=FINE))
    for sx, hand in ((-1, hands[0]), (1, hands[1])):
        out.append(
            pen.shape(limb(sx * 13, sh + 4, hand[0], hand[1], 9.5), fill=robe)
            + pen.shape(c(hand[0], hand[1], 4.8), fill=skin)
        )
    if keffiyeh:
        out.append(
            pen.shape(
                p(
                    f"M-19 {fmt(head_y - 6)} C-26 {fmt(head_y + 14)} -24 {fmt(sh + 2)} -18 {fmt(sh + 10)} L18 {fmt(sh + 10)} C24 {fmt(sh + 2)} 26 {fmt(head_y + 14)} 19 {fmt(head_y - 6)} Z"
                ),
                fill=WHITE,
            )
        )
    out.append(pen.shape(c(0, head_y, head_r), fill=skin))
    if beard:
        # a chin beard round the jaw, its top edge passing just under the smile
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-head_r + 0.5)} {fmt(head_y + 3)} C{fmt(-head_r)} {fmt(head_y + 25)} {fmt(head_r)} {fmt(head_y + 25)} {fmt(head_r - 0.5)} {fmt(head_y + 3)} C{fmt(head_r * 0.5)} {fmt(head_y + 14)} {fmt(-head_r * 0.5)} {fmt(head_y + 14)} {fmt(-head_r + 0.5)} {fmt(head_y + 3)} Z"
                ),
                fill="#E6E2DA" if keffiyeh else hair_color,
            )
        )
    if keffiyeh:
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-head_r - 4)} {fmt(head_y - 2)} C{fmt(-head_r - 4)} {fmt(head_y - 26)} {fmt(head_r + 4)} {fmt(head_y - 26)} {fmt(head_r + 4)} {fmt(head_y - 2)} C{fmt(head_r)} {fmt(head_y - 9)} {fmt(-head_r)} {fmt(head_y - 9)} {fmt(-head_r - 4)} {fmt(head_y - 2)} Z"
                ),
                fill=WHITE,
            )
        )
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-head_r - 2)} {fmt(head_y - 13)} C{fmt(-head_r)} {fmt(head_y - 18)} {fmt(head_r)} {fmt(head_y - 18)} {fmt(head_r + 2)} {fmt(head_y - 13)} L{fmt(head_r + 2)} {fmt(head_y - 9.5)} C{fmt(head_r)} {fmt(head_y - 14)} {fmt(-head_r)} {fmt(head_y - 14)} {fmt(-head_r - 2)} {fmt(head_y - 9.5)} Z"
                ),
                fill="#2E2A33",
            )
        )
    else:
        out.append(_hair_front(pen, "short", head_y, head_r, hair_color))
    out.append(face(pen, 0, head_y + 2, head_r))
    return "".join(out)


__all__ = [
    "EARTH",
    "ORANGE",
    "RED",
    "TRUNK",
    "bird_v",
    "bush",
    "child",
    "cloud",
    "face",
    "flower",
    "ground",
    "hills",
    "leaf_d",
    "limb",
    "man",
    "poppy",
    "stone",
    "sun",
    "tuft",
    "woman",
]

_ = (HILL_FAR,)
