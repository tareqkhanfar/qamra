"""Qamra's own line-art pieces for the coloring books' front and closing pages: the moon friend, crayons,
stars, a medal and the small vignettes the title pages use.
"""

from __future__ import annotations

from qamra_workbook.coloring.ink import (
    BLUE,
    FINE,
    GOLD,
    GREEN,
    ORANGE,
    PINK,
    PURPLE,
    RED,
    SUN,
    YELLOW,
    Pen,
    c,
    e,
    fmt,
    p,
    place,
    rounded_star,
    svg,
)

CRAYONS = (RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, PINK)


def moon_friend(pen: Pen, r: float = 30.0, *, wave: bool = True) -> str:
    """Qamra's moon (the brand's mascot, render/art.py): a crescent with its face on its thick left side,
    horns to the right, centred on its origin, with a small star at its horn."""
    k = r / 40  # the mascot is drawn in a 100-unit box, its circle of radius 40 centred near (45, 50)
    q = pen.at(k)
    out = [q.shape(p(MOON_D), fill=SUN)]
    out.append(q.solid(e(19.5, 50, 3.6, 4.3), e(31, 49, 3.6, 4.3)))
    out.append(q.stroke(p("M20.5 58.5 Q25.5 63.5 30.5 58")))
    out.append(q.tint(e(14.5, 58, 4.4, 3), e(35, 57, 4, 2.8), fill="#F08A7E"))
    if wave:
        out.append(q.shape(rounded_star(84, 25, 9), fill=GOLD))
    return f'<g transform="scale({fmt(k)}) translate(-45 -50)">{"".join(out)}</g>'


MOON_D = "M64.69 12.79 A40 40 0 1 0 76.85 79.65 A34 34 0 0 1 64.69 12.79 Z"


def crayon(pen: Pen, length: float = 70.0, fill: str = RED) -> str:
    """A wax crayon lying along +x from the origin (its tip at the right), 12 mm thick."""
    w = 12.0
    body = length - 16
    return pen.shape(
        p(
            f"M0 {-w / 2} L{fmt(body)} {-w / 2} L{fmt(length)} 0 L{fmt(body)} {w / 2} L0 {w / 2} Q-3 0 0 {-w / 2} Z"
        ),
        fill=fill,
    ) + pen.stroke(
        p(f"M{fmt(body)} {-w / 2} L{fmt(body)} {w / 2}"),
        p(f"M10 {-w / 2} L10 {w / 2}"),
        p(f"M{fmt(body - 10)} {-w / 2} L{fmt(body - 10)} {w / 2}"),
        weight=FINE,
    )


def crayon_fan(pen: Pen, n: int = 5, length: float = 62.0) -> str:
    """Crayons spread like a fan from the origin (upward)."""
    out = []
    for i in range(n):
        angle = -90 + (i - (n - 1) / 2) * 16
        out.append(place(pen, crayon, 0, 0, 1, rotate=angle, length=length, fill=CRAYONS[i % len(CRAYONS)]))
    return "".join(out)


def star_field(pen: Pen, points: list[tuple[float, float, float]]) -> str:
    return pen.shape(*(rounded_star(x, y, r) for x, y, r in points), fill=GOLD)


def medal(pen: Pen, r: float = 34.0) -> str:
    """A rosette medal with two ribbons, centred on its origin."""
    out = [
        pen.shape(
            p(
                f"M{fmt(-r * 0.55)} {fmt(r * 0.5)} L{fmt(-r * 0.85)} {fmt(r * 1.75)} L{fmt(-r * 0.45)} {fmt(r * 1.5)} L{fmt(-r * 0.2)} {fmt(r * 1.85)} L{fmt(-r * 0.05)} {fmt(r * 0.7)} Z"
            ),
            fill=RED,
        ),
        pen.shape(
            p(
                f"M{fmt(r * 0.55)} {fmt(r * 0.5)} L{fmt(r * 0.85)} {fmt(r * 1.75)} L{fmt(r * 0.45)} {fmt(r * 1.5)} L{fmt(r * 0.2)} {fmt(r * 1.85)} L{fmt(r * 0.05)} {fmt(r * 0.7)} Z"
            ),
            fill=BLUE,
        ),
    ]
    from qamra_workbook.coloring.ink import scallop

    out.append(pen.shape(scallop(0, 0, r, r, 14, 0.62), fill=YELLOW))
    out.append(pen.shape(c(0, 0, r * 0.66), fill=GOLD))
    out.append(pen.shape(rounded_star(0, 2, r * 0.42), fill=SUN))
    return "".join(out)


def crayon_box(pen: Pen, w: float = 92.0, n: int = 5) -> str:
    """An open box of crayons standing on the origin: `n` crayons of stepped heights behind the box's front,
    a flap on each side."""
    h = w * 0.5
    out = []
    cw = (w - 12) / n
    for i in range(n):
        x = -w / 2 + 6 + cw * i
        top = -h - 30 - (9 if i % 2 else 0) - (6 if i == n // 2 else 0)
        body_top = top + 13
        fill = CRAYONS[i % len(CRAYONS)]
        out.append(
            pen.shape(
                p(
                    f"M{fmt(x + 1)} {fmt(-h + 4)} L{fmt(x + 1)} {fmt(body_top)} L{fmt(x + cw / 2)} {fmt(top)} "
                    f"L{fmt(x + cw - 1)} {fmt(body_top)} L{fmt(x + cw - 1)} {fmt(-h + 4)} Z"
                ),
                fill=fill,
            )
        )
        out.append(
            pen.stroke(p(f"M{fmt(x + 1)} {fmt(body_top)} L{fmt(x + cw - 1)} {fmt(body_top)}"), weight=FINE)
        )
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w / 2)} {fmt(-h)} L{fmt(-w / 2 - 9)} {fmt(-h - 12)} L{fmt(-w / 2 + 6)} {fmt(-h - 4)} Z"
            ),
            fill=BLUE,
        )
    )
    out.append(
        pen.shape(
            p(f"M{fmt(w / 2)} {fmt(-h)} L{fmt(w / 2 + 9)} {fmt(-h - 12)} L{fmt(w / 2 - 6)} {fmt(-h - 4)} Z"),
            fill=BLUE,
        )
    )
    out.append(
        pen.shape(
            p(f"M{fmt(-w / 2)} {fmt(-h)} L{fmt(w / 2)} {fmt(-h)} L{fmt(w / 2 - 3)} 0 L{fmt(-w / 2 + 3)} 0 Z"),
            fill=YELLOW,
        )
    )
    out.append(pen.shape(rounded_star(0, -h / 2, h * 0.26), fill=RED))
    return "".join(out)


def title_vignette(mode: str = "line", w: float = 180.0, h: float = 120.0) -> str:
    """The title pages' picture: an open box of crayons, the moon friend smiling beside it, among stars."""
    pen = Pen(mode="line" if mode == "line" else "color")
    body = (
        place(pen, crayon_box, w * 0.42, h - 3, 1.0)
        + place(pen, moon_friend, w * 0.83, h * 0.3, 0.85)
        + star_field(
            pen,
            [
                (w * 0.08, h * 0.2, 7.5),
                (w * 0.2, h * 0.06, 5),
                (w * 0.9, h * 0.75, 7),
                (w * 0.06, h * 0.7, 6),
            ],
        )
    )
    return svg(w, h, body, css_class="cb-vignette", pad=3)


def medal_svg(mode: str = "line", size: float = 80.0) -> str:
    pen = Pen(mode="line" if mode == "line" else "color")
    s = size / 80
    body = place(pen, medal, 40 * s, 30 * s, s) + star_field(
        pen,
        [(6 * s, 8 * s, 6 * s), (74 * s, 10 * s, 6 * s), (10 * s, 60 * s, 5 * s), (72 * s, 62 * s, 5 * s)],
    )
    return svg(80 * s, 95 * s, body, css_class="cb-medal", pad=3)
