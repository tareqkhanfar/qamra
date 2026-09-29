"""Line art for the family book's drawing frames: the child draws or colors inside it, so it is light, open
and never busy (a glass to fill with layers, a theatre stage, a room corner, hills under a sky).
Every drawing is sized in millimetres and stretches with its box (`preserveAspectRatio="none"` is never used
for shapes that must stay round)."""

from __future__ import annotations

from markupsafe import Markup

from qamra_workbook.pictures.model import OUTLINE
from qamra_workbook.render import draw

LIGHT = "#CDBF9F"  # guide lines the child draws over


def cup_svg(layers: int, challenge: int) -> Markup:
    """A tall clear glass with dashed lines for the layers: `layers` for ⭐, `challenge` more for ⭐⭐."""
    w, h = 90.0, 120.0
    total = layers + challenge
    top, bottom = 8.0, 112.0
    glass = "M12 8 L78 8 L70 108 C69.4 111 67 113 64 113 L26 113 C23 113 20.6 111 20 108 Z"
    body = [
        draw.el("path", d=glass, fill="#FFFFFF", stroke=OUTLINE, stroke_width=1.1, stroke_linejoin="round"),
        draw.el("ellipse", cx=45, cy=8, rx=33, ry=3.2, fill="#F4F8FB", stroke=OUTLINE, stroke_width=1.1),
        draw.path("M17 20 L22.5 96", stroke="#DDEAF3", width=2.4),
    ]
    step = (bottom - top - 8) / total
    for i in range(1, total):
        y = bottom - i * step
        k = (y - 8) / 105  # the glass narrows toward the bottom
        x0, x1 = 12 + 8 * k + 1.5, 78 - 8 * k - 1.5
        color = "#E8C77F" if i >= layers else LIGHT
        line = f"M{x0:.1f} {y:.1f} L{x1:.1f} {y:.1f}"
        body.append(draw.path(line, stroke=color, width=0.7, stroke_dasharray="2.4 2"))
    body.append(
        draw.el("rect", x=58, y=-2, width=4, height=40, rx=2, fill="#F2B33D", transform="rotate(18 60 18)")
    )
    return draw.svg(w, h, "".join(body), "cup-art")


def stage_svg() -> Markup:
    """A little theatre: curtains on both sides, a scalloped valance and the stage floor."""
    w, h = 170.0, 120.0
    red, deep = "#E4675A", "#B8483D"
    body = [
        draw.el("rect", x=0, y=100, width=w, height=20, rx=3, fill="#E7B070"),
        draw.el("rect", x=0, y=100, width=w, height=3.2, fill="#C98A4B"),
        draw.el("path", d="M0 0 L30 0 C26 40 30 80 38 100 L0 100 Z", fill=red),
        draw.el("path", d=f"M{w} 0 L{w - 30} 0 C{w - 26} 40 {w - 30} 80 {w - 38} 100 L{w} 100 Z", fill=red),
        draw.path("M10 4 C8 40 12 76 18 98 M20 4 C18 40 22 76 28 99", stroke=deep, width=0.8),
        draw.path(
            f"M{w - 10} 4 C{w - 8} 40 {w - 12} 76 {w - 18} 98 "
            f"M{w - 20} 4 C{w - 18} 40 {w - 22} 76 {w - 28} 99",
            stroke=deep,
            width=0.8,
        ),
    ]
    scallops = "".join(f"M{x} 0 L{x + 17} 0 L{x + 17} 8 A8.5 8.5 0 0 1 {x} 8 Z" for x in range(0, int(w), 17))
    body += [
        draw.el("path", d=scallops, fill=deep),
        draw.el("rect", x=0, y=0, width=w, height=3, fill="#962C22"),
    ]
    for x in (40, 85, 130):
        body.append(draw.el("path", d=draw.star_points(x, 112, 2.6, 1.2), fill="#FFF1C9"))
    return draw.svg(w, h, "".join(body), "stage-art")


def room_svg() -> Markup:
    """A room corner in perspective: two walls, the floor, a window; empty for the child's calm corner."""
    w, h = 170.0, 120.0
    body = [
        draw.el("path", d="M0 0 L85 16 L85 92 L0 120 Z", fill="#FFF8EC"),
        draw.el("path", d=f"M{w} 0 L85 16 L85 92 L{w} 120 Z", fill="#FDF3E3"),
        draw.el("path", d=f"M0 120 L85 92 L{w} 120 Z", fill="#F6E7CB"),
        draw.path(f"M85 16 L85 92 M0 120 L85 92 L{w} 120", stroke=LIGHT, width=0.8),
        draw.el(
            "path", d="M118 30 L148 26 L148 58 L118 60 Z", fill="#E7F2FA", stroke=LIGHT, stroke_width=0.8
        ),
        draw.path("M133 28 L133 59 M118 45 L148 42", stroke=LIGHT, width=0.6),
    ]
    return draw.svg(w, h, "".join(body), "room-art")


def landscape_svg() -> Markup:
    """Hills under a big sky with the sun in the corner, in light outline to draw over and color."""
    w, h = 170.0, 120.0
    body = [
        draw.el("circle", cx=w - 18, cy=16, r=9, fill="#FFF6D8", stroke="#F2C14E", stroke_width=0.8),
        draw.path(
            f"M0 {h - 22} C30 {h - 36} 60 {h - 30} 85 {h - 24} C110 {h - 18} 140 {h - 34} {w} {h - 26}",
            stroke="#B9DDA6",
            width=1,
        ),
        draw.el(
            "path", d=f"M0 {h - 8} C40 {h - 20} 120 {h - 14} {w} {h - 12} L{w} {h} L0 {h} Z", fill="#EAF5E2"
        ),
    ]
    for x in (22, 60, 128):
        body.append(
            draw.path(f"M{x} {h - 4} l1.5 -4 m1.5 4 l1.5 -5 m1.5 5 l1.5 -3.5", stroke="#9CCB88", width=0.7)
        )
    return draw.svg(w, h, "".join(body), "land-art")


def corner_stars() -> Markup:
    """The portrait frame's four corner stars (drawn once, placed by CSS)."""
    star = draw.el(
        "path", d=draw.star_points(6, 6, 5.6, 2.6), fill="#F2B33D", stroke="#FFFFFF", stroke_width=0.8
    )
    return draw.svg(12, 12, star, "corner-star")
