"""People on family-book pages (Addendum 7): friendly placeholder figures for the family members, and the
feelings faces.

Without the illustrated-family add-on (A7 §7) a member is drawn as a simple figure chosen by their role
(`spec.Member.drawn_as`): flat soft colors without dark outlines and a white sticker edge, so they stand
next to the child's cut-out character (which has the same edge) without competing with it. A family may
ask for a headscarf on a figure. Figures are drawn in a 60 × 120 unit box with the feet on y = 118;
`place` puts one on a page drawing in millimetres.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from qamra_workbook.pictures.model import OUTLINE
from qamra_workbook.render import draw
from qamra_workbook.render.spec import Figure

SKIN = "#F4C9A6"
HAIR = "#5B3A2C"
GRAY_HAIR = "#D2D2DD"
LEGS = "#4B5575"
SHOE = "#7A5240"
EYE = "#2F2A3A"
MOUTH = "#8A4637"
OUTFITS = ("#E98AA6", "#6E95DB", "#86BF72", "#F2A65A", "#A58BD8", "#5DB7A8")
SCARVES = ("#8FB9A8", "#C9A7D8", "#E8B4A0", "#A9C4E8")
BOX_W, BOX_H, FEET = 60.0, 120.0, 118.0

Feeling = Literal[
    "calm", "happy", "uneasy", "sad", "upset", "angry", "scared", "proud", "missing", "surprised"
]


def shade(color: str, k: float) -> str:
    """The color darkened (k < 1) or lightened toward white (k > 1)."""
    rgb = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    out = [round(c * k) if k <= 1 else round(c + (255 - c) * (k - 1)) for c in rgb]
    return "#" + "".join(f"{max(0, min(255, c)):02X}" for c in out)


def _oval(cx: float, cy: float, rx: float, ry: float | None = None) -> str:
    ry = rx if ry is None else ry
    arcs = draw.d_path(
        ("M", (cx - rx, cy)), ("A", (rx, ry, 0, 1, 0, cx + rx, cy)), ("A", (rx, ry, 0, 1, 0, cx - rx, cy))
    )
    return arcs + " Z"


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return draw.d_path(("M", (x1, y1)), ("L", (x2, y2)))


@dataclass(frozen=True)
class Mark:
    """One shape of a figure: a filled area, or a thick rounded line (arms and legs)."""

    d: str
    color: str
    width: float = 0.0  # > 0: a line this wide

    def svg(self, edge: float = 0.0) -> str:
        if self.width:
            return draw.path(self.d, stroke="#FFFFFF" if edge else self.color, width=self.width + 2 * edge)
        if edge:
            return draw.el(
                "path",
                d=self.d,
                fill="#FFFFFF",
                stroke="#FFFFFF",
                stroke_width=2 * edge,
                stroke_linejoin="round",
            )
        return draw.el("path", d=self.d, fill=self.color)


@dataclass(frozen=True)
class Drawing:
    marks: tuple[Mark, ...]  # the silhouette, back to front
    details: str  # the face and small lines, on top and not part of the sticker edge

    def svg(self, edge: float) -> str:
        return "".join(m.svg(edge) for m in self.marks) + "".join(m.svg() for m in self.marks) + self.details


def face(cx: float, cy: float, r: float, *, glasses: bool = False) -> str:
    """Eyes with glints, a small smile and cheeks, for a head of radius r centred on (cx, cy)."""
    ex, ey = r * 0.36, cy + r * 0.08
    smile = draw.d_path(
        ("M", (cx - r * 0.24, cy + r * 0.44)), ("Q", (cx, cy + r * 0.66, cx + r * 0.24, cy + r * 0.44))
    )
    out = [
        draw.el("ellipse", cx=cx - ex, cy=ey, rx=r * 0.11, ry=r * 0.14, fill=EYE),
        draw.el("ellipse", cx=cx + ex, cy=ey, rx=r * 0.11, ry=r * 0.14, fill=EYE),
        draw.el("circle", cx=cx - ex + r * 0.04, cy=ey - r * 0.05, r=r * 0.045, fill="#FFFFFF"),
        draw.el("circle", cx=cx + ex + r * 0.04, cy=ey - r * 0.05, r=r * 0.045, fill="#FFFFFF"),
        draw.el(
            "ellipse",
            cx=cx - r * 0.58,
            cy=cy + r * 0.42,
            rx=r * 0.17,
            ry=r * 0.11,
            fill="#F29A8A",
            opacity=0.6,
        ),
        draw.el(
            "ellipse",
            cx=cx + r * 0.58,
            cy=cy + r * 0.42,
            rx=r * 0.17,
            ry=r * 0.11,
            fill="#F29A8A",
            opacity=0.6,
        ),
        draw.path(smile, stroke=MOUTH, width=r * 0.09),
    ]
    if glasses:
        g, w = r * 0.24, r * 0.06
        out += [
            draw.el("circle", cx=cx - ex, cy=ey, r=g, fill="none", stroke="#5A5A6A", stroke_width=w),
            draw.el("circle", cx=cx + ex, cy=ey, r=g, fill="none", stroke="#5A5A6A", stroke_width=w),
            draw.path(_line(cx - ex + g, ey, cx + ex - g, ey), stroke="#5A5A6A", width=w),
        ]
    return "".join(out)


def _hair(kind: Figure, cx: float, cy: float, r: float, color: str) -> tuple[list[Mark], list[Mark]]:
    """(behind the head, over the head)."""
    back: list[Mark] = []
    front: list[Mark] = []
    if kind in ("woman", "adult"):
        low = cy + r * (1.55 if kind == "woman" else 0.95)
        d = draw.d_path(
            ("M", (cx - r * 1.1, cy + r * 0.1)),
            ("C", (cx - r * 1.25, cy - r * 1.55, cx + r * 1.25, cy - r * 1.55, cx + r * 1.1, cy + r * 0.1)),
            ("L", (cx + r * 1.16, low)),
            ("Q", (cx, low + r * 0.45, cx - r * 1.16, low)),
        )
        back.append(Mark(d + " Z", color))
    if kind == "girl":  # two pigtails
        back += [
            Mark(_oval(cx - r * 1.12, cy + r * 0.3, r * 0.45), color),
            Mark(_oval(cx + r * 1.12, cy + r * 0.3, r * 0.45), color),
        ]
    if kind == "grandma":  # a bun
        back.append(Mark(_oval(cx, cy - r * 1.02, r * 0.42), color))
    if kind == "baby":
        return back, front
    if kind == "grandpa":  # hair on the sides only
        for s in (-1, 1):
            d = draw.d_path(
                ("M", (cx + s * r * 0.98, cy + r * 0.3)),
                (
                    "C",
                    (
                        cx + s * r * 1.1,
                        cy - r * 0.3,
                        cx + s * r * 0.9,
                        cy - r * 0.62,
                        cx + s * r * 0.62,
                        cy - r * 0.8,
                    ),
                ),
                ("L", (cx + s * r * 0.7, cy + r * 0.05)),
            )
            front.append(Mark(d + " Z", color))
        return back, front
    # a side-swept fringe, or short hair over the forehead
    swept = kind in ("woman", "girl", "grandma", "adult")
    d = draw.d_path(
        ("M", (cx - r * 1.0, cy + r * 0.1)),
        ("C", (cx - r * 1.08, cy - r * 1.25, cx + r * 1.08, cy - r * 1.25, cx + r * 1.0, cy + r * 0.1)),
        (
            "C",
            (
                cx + r * 0.62,
                cy - r * (0.62 if swept else 0.42),
                cx - r * 0.1,
                cy - r * 0.72,
                cx - r * 1.0,
                cy + r * 0.1,
            ),
        ),
    )
    front.append(Mark(d + " Z", color))
    return back, front


def _baby(outfit: str) -> Drawing:
    cx, hy, r = BOX_W / 2, 80.0, 12.5
    sleeve = shade(outfit, 0.9)
    marks = (
        Mark(_line(cx - 11, 100, cx - 16.5, 108), sleeve, 5.4),
        Mark(_line(cx + 11, 100, cx + 16.5, 108), sleeve, 5.4),
        Mark(_oval(cx - 17, 109.5, 3), SKIN),
        Mark(_oval(cx + 17, 109.5, 3), SKIN),
        Mark(_oval(cx - 7, 115.5, 4.6, 3), SKIN),
        Mark(_oval(cx + 7, 115.5, 4.6, 3), SKIN),
        Mark(_oval(cx, 104, 13.5, 13), outfit),
        Mark(_oval(cx, hy, r), SKIN),
    )
    curl = draw.d_path(
        ("M", (cx - 1, hy - r * 0.95)), ("C", (cx - 1, hy - r * 1.45, cx + 5, hy - r * 1.4, cx + 4, hy - r))
    )
    return Drawing(marks, draw.path(curl, stroke=HAIR, width=1.6) + face(cx, hy + 1, r))


def person(kind: Figure, outfit: str, *, scarf: str | None = None) -> Drawing:
    """A friendly flat figure in the 60 × 120 box, feet on y = 118, facing the reader."""
    if kind == "baby":
        return _baby(outfit)
    if kind == "child":  # a young relative the family did not describe further: short hair, trousers
        return person("boy", outfit, scarf=scarf)
    cx = BOX_W / 2
    old = kind in ("grandma", "grandpa")
    child = kind in ("girl", "boy")
    skirt = kind in ("woman", "girl", "grandma")
    sleeve = shade(outfit, 0.9)
    dy = 4.0 if old else 0.0  # grandparents a little shorter
    r = 12.5 if child else 11.0
    hy = (50.0 if child else 20.0) + dy
    shoulder = hy + r + 2.5
    hem = shoulder + (29 if child else 52 - dy)
    waist = shoulder + (19 if child else 30)
    feet = 114.5
    arm = 18 if child else 25
    back, front = _hair(kind, cx, hy, r, GRAY_HAIR if old else HAIR)
    if scarf:  # a headscarf around the face and down to the shoulders
        hood = draw.d_path(
            ("M", (cx, hy - r * 1.32)),
            ("C", (cx - r * 1.5, hy - r * 1.32, cx - r * 1.55, hy + r * 0.4, cx - r * 1.3, hy + r * 1.4)),
            ("Q", (cx, hy + r * 2.1, cx + r * 1.3, hy + r * 1.4)),
            ("C", (cx + r * 1.55, hy + r * 0.4, cx + r * 1.5, hy - r * 1.32, cx, hy - r * 1.32)),
        )
        back, front = [Mark(hood + " Z", scarf)], []
    marks: list[Mark] = []
    if skirt:  # legs under the dress
        for s in (-1, 1):
            marks.append(
                Mark(_line(cx + s * 5, hem - 2, cx + s * 5, feet - 2), SKIN if kind == "girl" else LEGS, 5.2)
            )
    else:  # trousers
        d = draw.d_path(
            ("M", (cx - 10.5, waist - 1)),
            ("L", (cx + 10.5, waist - 1)),
            ("L", (cx + 10, feet - 2)),
            ("Q", (cx + 10, feet, cx + 8, feet)),
            ("L", (cx + 3, feet)),
            ("Q", (cx + 1.2, feet, cx + 1.1, feet - 2)),
            ("L", (cx + 0.5, waist + 9)),
            ("L", (cx - 0.5, waist + 9)),
            ("L", (cx - 1.1, feet - 2)),
            ("Q", (cx - 1.2, feet, cx - 3, feet)),
            ("L", (cx - 8, feet)),
            ("Q", (cx - 10, feet, cx - 10, feet - 2)),
        )
        marks.append(Mark(d + " Z", LEGS))
    for s in (-1, 1):  # shoes, arms, hands
        marks.append(Mark(_oval(cx + s * 5.8, feet + 0.8, 5, 2.9), SHOE))
        marks.append(Mark(_line(cx + s * 9.6, shoulder + 3.5, cx + s * 14.6, shoulder + arm), sleeve, 5.8))
        marks.append(Mark(_oval(cx + s * 15, shoulder + arm + 2.4, 3.1), SKIN))
    marks += back
    neck = draw.d_path(
        ("M", (cx - 2.6, hy + r - 2)),
        ("L", (cx + 2.6, hy + r - 2)),
        ("L", (cx + 2.6, shoulder + 1)),
        ("L", (cx - 2.6, shoulder + 1)),
    )
    marks.append(Mark(neck + " Z", SKIN))
    if skirt:
        torso = draw.d_path(
            ("M", (cx - 10, shoulder + 3)),
            ("Q", (cx - 10, shoulder - 0.5, cx - 6, shoulder - 0.5)),
            ("L", (cx + 6, shoulder - 0.5)),
            ("Q", (cx + 10, shoulder - 0.5, cx + 10, shoulder + 3)),
            ("L", (cx + 14.5, hem - 2.5)),
            ("Q", (cx + 15, hem + 0.5, cx + 11.5, hem + 0.5)),
            ("L", (cx - 11.5, hem + 0.5)),
            ("Q", (cx - 15, hem + 0.5, cx - 14.5, hem - 2.5)),
        )
    else:
        torso = draw.d_path(
            ("M", (cx - 10.8, shoulder + 3)),
            ("Q", (cx - 10.8, shoulder - 0.5, cx - 6.5, shoulder - 0.5)),
            ("L", (cx + 6.5, shoulder - 0.5)),
            ("Q", (cx + 10.8, shoulder - 0.5, cx + 10.8, shoulder + 3)),
            ("L", (cx + 11, waist + 1)),
            ("L", (cx - 11, waist + 1)),
        )
    marks.append(Mark(torso + " Z", outfit))
    marks.append(Mark(_oval(cx, hy + r * 0.08, r * 0.84, r * 0.93) if scarf else _oval(cx, hy, r), SKIN))
    marks += front
    details = ""
    if not skirt:  # a collar
        collar = draw.d_path(
            ("M", (cx - 3.6, shoulder - 0.4)), ("L", (cx, shoulder + 3)), ("L", (cx + 3.6, shoulder - 0.4))
        )
        details += draw.path(collar, stroke=shade(outfit, 0.78), width=1.1)
    details += face(cx, hy + (r * 0.08 if scarf else 0), r * (0.9 if scarf else 1), glasses=old)
    if kind == "grandpa":  # a moustache
        m = draw.d_path(
            ("M", (cx - r * 0.42, hy + r * 0.4)),
            ("C", (cx - r * 0.2, hy + r * 0.2, cx - r * 0.06, hy + r * 0.26, cx, hy + r * 0.36)),
            ("C", (cx + r * 0.06, hy + r * 0.26, cx + r * 0.2, hy + r * 0.2, cx + r * 0.42, hy + r * 0.4)),
            ("C", (cx + r * 0.24, hy + r * 0.56, cx + r * 0.08, hy + r * 0.52, cx, hy + r * 0.44)),
            ("C", (cx - r * 0.08, hy + r * 0.52, cx - r * 0.24, hy + r * 0.56, cx - r * 0.42, hy + r * 0.4)),
        )
        details += draw.el("path", d=m + " Z", fill=shade(GRAY_HAIR, 0.82))
    return Drawing(tuple(marks), details)


def place(figure: Drawing, x: float, y_feet: float, height: float, edge_mm: float = 1.1) -> str:
    """A figure on a page drawing: centred on x, feet at y_feet, `height` mm for the whole 120-unit box, with
    a white sticker edge `edge_mm` wide."""
    k = height / BOX_H
    move = f"translate({draw.n(x - BOX_W / 2 * k)} {draw.n(y_feet - FEET * k)}) scale({draw.n(k)})"
    return f'<g transform="{move}">{figure.svg(edge_mm / k)}</g>'


# ---- feelings faces ---------------------------------------------------------------------------------------

FEELING_COLORS: dict[Feeling, str] = {
    "calm": "#8FD3B6",
    "happy": "#F7D774",
    "uneasy": "#F9C46B",
    "sad": "#9DC3EA",
    "upset": "#F5A06B",
    "angry": "#EE8A7A",
    "scared": "#C5B3E6",
    "proud": "#F7C84A",
    "missing": "#F4B6C6",
    "surprised": "#A8DCD0",
}


def feeling_face(feeling: Feeling, cx: float, cy: float, r: float, color: str | None = None) -> str:
    """A round, gentle face showing a feeling (never scary: soft colors, small features)."""
    w = r * 0.075
    fill = color or FEELING_COLORS[feeling]
    out = [draw.el("circle", cx=cx, cy=cy, r=r, fill=fill, stroke=OUTLINE, stroke_width=w)]
    ex, ey = r * 0.36, cy - r * 0.08

    def eye(x: float) -> str:
        return draw.el("ellipse", cx=x, cy=ey, rx=r * 0.1, ry=r * 0.13, fill=OUTLINE) + draw.el(
            "circle", cx=x + r * 0.04, cy=ey - r * 0.05, r=r * 0.04, fill="#FFFFFF"
        )

    def brows(inner: float, outer: float) -> str:
        """Eyebrows: y offsets (from the eyes) at the inner and outer ends."""
        return "".join(
            draw.path(
                _line(cx + s * r * 0.14, ey + inner * r, cx + s * r * 0.55, ey + outer * r),
                stroke=OUTLINE,
                width=w,
            )
            for s in (-1, 1)
        )

    def mouth(*commands: tuple[str, tuple[float, ...]]) -> str:
        return draw.path(draw.d_path(*commands), stroke=OUTLINE, width=w)

    def filled(d: str) -> str:
        return draw.el(
            "path", d=d + " Z", fill="#FFFFFF", stroke=OUTLINE, stroke_width=w, stroke_linejoin="round"
        )

    my = cy + r * 0.38
    match feeling:
        case "calm":  # eyes closed, a soft smile
            for s in (-1, 1):
                x = cx + s * ex
                out.append(mouth(("M", (x - r * 0.13, ey)), ("Q", (x, ey + r * 0.12, x + r * 0.13, ey))))
            out.append(mouth(("M", (cx - r * 0.22, my)), ("Q", (cx, my + r * 0.18, cx + r * 0.22, my))))
        case "happy":
            out += [eye(cx - ex), eye(cx + ex)]
            out.append(
                filled(
                    draw.d_path(
                        ("M", (cx - r * 0.34, my - r * 0.06)),
                        ("Q", (cx, my + r * 0.46, cx + r * 0.34, my - r * 0.06)),
                    )
                )
            )
        case "uneasy":
            out += [eye(cx - ex), eye(cx + ex)]
            out.append(
                mouth(
                    ("M", (cx - r * 0.22, my + r * 0.04)),
                    ("Q", (cx - r * 0.08, my - r * 0.04, cx, my + r * 0.04)),
                    ("Q", (cx + r * 0.08, my + r * 0.12, cx + r * 0.22, my + r * 0.02)),
                )
            )
        case "sad":
            out += [eye(cx - ex), eye(cx + ex), brows(-0.3, -0.18)]
            out.append(
                mouth(
                    ("M", (cx - r * 0.22, my + r * 0.12)),
                    ("Q", (cx, my - r * 0.1, cx + r * 0.22, my + r * 0.12)),
                )
            )
            tear = draw.d_path(
                ("M", (cx + ex + r * 0.1, ey + r * 0.16)),
                ("Q", (cx + ex + r * 0.02, ey + r * 0.32, cx + ex + r * 0.1, ey + r * 0.36)),
                ("Q", (cx + ex + r * 0.18, ey + r * 0.32, cx + ex + r * 0.1, ey + r * 0.16)),
            )
            out.append(draw.el("path", d=tear + " Z", fill="#7FB2E5"))
        case "upset":
            out += [eye(cx - ex), eye(cx + ex), brows(-0.22, -0.28)]
            out.append(
                mouth(
                    ("M", (cx - r * 0.25, my + r * 0.12)),
                    ("Q", (cx, my - r * 0.08, cx + r * 0.25, my + r * 0.12)),
                )
            )
        case "angry":
            out += [eye(cx - ex), eye(cx + ex), brows(-0.14, -0.3)]
            out.append(
                filled(
                    draw.d_path(
                        ("M", (cx - r * 0.26, my + r * 0.16)),
                        ("Q", (cx, my - r * 0.14, cx + r * 0.26, my + r * 0.16)),
                        ("Q", (cx, my + r * 0.08, cx - r * 0.26, my + r * 0.16)),
                    )
                )
            )
        case "scared":
            out += [eye(cx - ex), eye(cx + ex), brows(-0.32, -0.22)]
            out.append(
                draw.el(
                    "ellipse",
                    cx=cx,
                    cy=my + r * 0.05,
                    rx=r * 0.13,
                    ry=r * 0.17,
                    fill="#FFFFFF",
                    stroke=OUTLINE,
                    stroke_width=w,
                )
            )
        case "proud":  # happy closed eyes, a big smile, chin up
            for sx in (-1, 1):
                x = cx + sx * ex
                out.append(
                    mouth(
                        ("M", (x - r * 0.13, ey + r * 0.04)),
                        ("Q", (x, ey - r * 0.12, x + r * 0.13, ey + r * 0.04)),
                    )
                )
            out.append(
                filled(
                    draw.d_path(
                        ("M", (cx - r * 0.3, my - r * 0.04)),
                        ("Q", (cx, my + r * 0.4, cx + r * 0.3, my - r * 0.04)),
                    )
                )
            )
            out.append(
                draw.el(
                    "path",
                    d=draw.star_points(cx + r * 0.72, cy - r * 0.72, r * 0.2, r * 0.09),
                    fill="#E2A32A",
                )
            )
        case "missing":  # eyes looking up, a small wistful smile, a little heart
            for sx in (-1, 1):
                out.append(
                    draw.el(
                        "ellipse", cx=cx + sx * ex, cy=ey - r * 0.06, rx=r * 0.1, ry=r * 0.13, fill=OUTLINE
                    )
                )
            out.append(brows(-0.28, -0.2))
            out.append(
                mouth(
                    ("M", (cx - r * 0.18, my + r * 0.04)),
                    ("Q", (cx, my + r * 0.1, cx + r * 0.18, my + r * 0.04)),
                )
            )
            out.append(
                draw.el(
                    "path", d=draw.heart_path(cx + r * 0.7, cy - r * 0.62, r * 0.36, r * 0.32), fill="#E4769D"
                )
            )
        case "surprised":
            out += [eye(cx - ex), eye(cx + ex), brows(-0.36, -0.34)]
            out.append(draw.el("ellipse", cx=cx, cy=my + r * 0.04, rx=r * 0.12, ry=r * 0.15, fill=OUTLINE))
    if feeling in ("calm", "happy", "proud"):
        for s in (-1, 1):
            out.append(
                draw.el(
                    "ellipse",
                    cx=cx + s * r * 0.58,
                    cy=cy + r * 0.24,
                    rx=r * 0.15,
                    ry=r * 0.1,
                    fill="#F08A7E",
                    opacity=0.55,
                )
            )
    return "".join(out)


# ---- people at work (the jobs adventure and the role cards) ------------------------------------------------

Job = Literal["doctor", "baker", "farmer", "teacher", "barber", "builder", "seller", "chef"]
# who is drawn for each job, their clothes, and what they wear on the head
JOBS: dict[str, tuple[Figure, str, str]] = {
    "doctor": ("woman", "#F4F6FA", "mirror"),
    "baker": ("man", "#FFFFFF", "toque"),
    "farmer": ("man", "#86BF72", "straw"),
    "teacher": ("woman", "#A58BD8", ""),
    "barber": ("man", "#5DB7A8", ""),
    "builder": ("man", "#F2A65A", "hardhat"),
    "seller": ("woman", "#E98AA6", ""),
    "chef": ("woman", "#FFFFFF", "toque"),
}
BUST_H = 70.0  # a bust shows the top 70 units of the 60 × 120 figure box


def _hat(kind: str, cx: float, top: float) -> str:
    """A hat over a head whose top is at `top` (figure units)."""
    match kind:
        case "toque":
            puff = "M19 5 C15 -6 24 -11 30 -6 C36 -11 45 -6 41 5 Z"
            return draw.el(
                "rect",
                x=cx - 10,
                y=top - 3,
                width=20,
                height=8,
                rx=1.5,
                fill="#FFFFFF",
                stroke=OUTLINE,
                stroke_width=0.8,
            ) + draw.el(
                "path",
                d=puff,
                fill="#FFFFFF",
                stroke=OUTLINE,
                stroke_width=0.8,
                transform=f"translate({cx - 30} {top - 8})",
            )
        case "hardhat":
            return draw.el(
                "path",
                d=f"M{cx - 12} {top + 6} C{cx - 12} {top - 7} {cx + 12} {top - 7} {cx + 12} {top + 6} Z",
                fill="#F7C84A",
                stroke=OUTLINE,
                stroke_width=0.8,
            ) + draw.el(
                "rect",
                x=cx - 15,
                y=top + 5,
                width=30,
                height=3.4,
                rx=1.7,
                fill="#F2B33D",
                stroke=OUTLINE,
                stroke_width=0.8,
            )
        case "straw":
            return draw.el(
                "ellipse", cx=cx, cy=top + 4, rx=20, ry=4.2, fill="#EBCB7A", stroke=OUTLINE, stroke_width=0.8
            ) + draw.el(
                "path",
                d=f"M{cx - 10} {top + 4} C{cx - 9} {top - 7} {cx + 9} {top - 7} {cx + 10} {top + 4} Z",
                fill="#EBCB7A",
                stroke=OUTLINE,
                stroke_width=0.8,
            )
        case "mirror":
            return draw.el(
                "path",
                d=f"M{cx - 11} {top + 6} Q{cx} {top - 1} {cx + 11} {top + 6}",
                fill="none",
                stroke="#6E6A7A",
                stroke_width=1.4,
            ) + draw.el("circle", cx=cx, cy=top + 3, r=3.6, fill="#E3F0FB", stroke=OUTLINE, stroke_width=0.8)
    return ""


def job_bust(job: str, edge_mm: float = 0.0) -> str:
    """The head and shoulders of someone at work (figure units: 60 wide, `BUST_H` tall)."""
    kind, outfit, hat = JOBS.get(job, ("adult", OUTFITS[0], ""))
    figure = person(kind, outfit)
    head_top = 20.0 - 11.0
    extra = ""
    if job == "doctor":  # the stethoscope on the white coat
        extra = draw.path("M24 36 C24 48 36 48 36 36 M30 46 L30 52", stroke="#4A5078", width=1.3) + draw.el(
            "circle", cx=30, cy=54, r=2.6, fill="#CFD2DC", stroke=OUTLINE, stroke_width=0.6
        )
    return figure.svg(edge_mm) + extra + _hat(hat, 30.0, head_top)
