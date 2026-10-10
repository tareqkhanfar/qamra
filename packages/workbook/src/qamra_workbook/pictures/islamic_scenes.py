"""The scenes of «قلبي يعرف الله» (Addendum 10 §3.5): illustrations built from flat gradients and the picture
library, in a 180 × 104 box (or the box a scene names). The scenes of a prophet's story show nature, places
and
objects only: no person, no silhouette, no beams of light from above (a sun is a disc with a soft halo). The
few
scenes with people (`figures=True`) ask the page for them through a `Kit`, so the checks can tell them apart.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import OUTLINE


class Kit(Protocol):
    """Who can stand in a scene with people: the recurring characters and the reader."""

    def figure(self, who: str, x: float, y_feet: float, height: float) -> str: ...


@dataclass(frozen=True)
class Scene:
    name: str
    draw: Callable[[str, Kit | None], str]  # (unique id prefix, kit) → SVG elements
    figures: bool = False  # does it draw people?
    box: tuple[float, float] = (180.0, 104.0)  # the viewBox
    align: str = "xMidYMid"  # which part a cropped scene keeps: people scenes keep the floor (xMidYMax)
    note: str = ""


def scene_svg(
    name: str, uid: str, kit: Kit | None = None, css_class: str = "scene", fit: str = "slice"
) -> Markup:
    """The scene as an SVG that fills its box (`fit`: slice crops the overflow, meet shows it all)."""
    scene = SCENES[name]
    if scene.figures and kit is None:
        raise ValueError(f"scene {name!r} draws people: it needs a kit")
    w, h = scene.box
    return Markup(  # nosec B704 (static art)
        f'<svg class="{css_class}" viewBox="0 0 {w:g} {h:g}" '
        f'preserveAspectRatio="{scene.align} {fit}" aria-hidden="true">'
        f"{scene.draw(uid, kit)}</svg>"
    )


# ---- drawing helpers -----------------------------------------------------------------------------------


def n(x: float) -> str:
    text = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def vgrad(uid: str, name: str, *stops: tuple[float, str]) -> str:
    items = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{uid}-{name}" x1="0" y1="0" x2="0" y2="1">{items}</linearGradient>'


def rect(x: float, y: float, w: float, h: float, fill: str, rx: float = 0, opacity: float = 1.0) -> str:
    return (
        f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
        f'rx="{n(rx)}" fill="{fill}" opacity="{opacity}"/>'
    )


def circle(
    cx: float, cy: float, r: float, fill: str, opacity: float = 1.0, stroke: str = "none", sw: float = 0
) -> str:
    return (
        f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}" opacity="{opacity}" '
        f'stroke="{stroke}" stroke-width="{n(sw)}"/>'
    )


def path(d: str, fill: str = "none", stroke: str = "none", sw: float = 0, opacity: float = 1.0) -> str:
    return (
        f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{n(sw)}" stroke-linecap="round" '
        f'stroke-linejoin="round" opacity="{opacity}"/>'
    )


def wave(y: float, amp: float, length: float, width: float, bottom: float, phase: float = 0.0) -> str:
    """Path data of a wavy surface at `y`, closed down to `bottom`."""
    x = -length + phase
    d = f"M{n(x)} {n(y)}"
    while x < width + length:
        d += f" q{n(length / 4)} {n(-amp)} {n(length / 2)} 0 t{n(length / 2)} 0"
        x += length
    return d + f" L{n(width + length)} {n(bottom)} L{n(-length)} {n(bottom)} Z"


def sparkle(cx: float, cy: float, r: float, fill: str, opacity: float = 1.0) -> str:
    d = (
        f"M{n(cx)} {n(cy - r)} L{n(cx + r * 0.28)} {n(cy - r * 0.28)} "
        f"L{n(cx + r)} {n(cy)} L{n(cx + r * 0.28)} {n(cy + r * 0.28)} "
        f"L{n(cx)} {n(cy + r)} L{n(cx - r * 0.28)} {n(cy + r * 0.28)} "
        f"L{n(cx - r)} {n(cy)} L{n(cx - r * 0.28)} {n(cy - r * 0.28)} Z"
    )
    return path(d, fill, opacity=opacity)


def pic(
    picture_id: str,
    x: float,
    y: float,
    size: float,
    style: str = "color",
    rotate: float = 0,
    flip: bool = False,
) -> str:
    """A library picture placed in a scene; `rotate` turns it about its centre, `flip` mirrors it."""
    inner = picture(picture_id).inner("line" if style == "line" else "color")
    if flip:
        inner = f'<g transform="translate(100 0) scale(-1 1)">{inner}</g>'
    turn = f' transform="rotate({n(rotate)} {n(x + size / 2)} {n(y + size / 2)})"' if rotate else ""
    return (
        f'<svg x="{n(x)}" y="{n(y)}" width="{n(size)}" '
        f'height="{n(size)}" viewBox="0 0 100 100"{turn}>{inner}</svg>'
    )


def sun_disc(cx: float, cy: float, r: float, core: str = "#FFD25E", halo: str = "#FFE9A8") -> str:
    """A sun: a disc in soft concentric halos. No rays and no beams: it is a sign in the sky, not a light on
    a scene."""
    return (
        circle(cx, cy, r * 2.0, halo, 0.18)
        + circle(cx, cy, r * 1.6, halo, 0.3)
        + circle(cx, cy, r * 1.25, halo, 0.5)
        + circle(cx, cy, r, core)
    )


def crescent(cx: float, cy: float, r: float, fill: str = "#FFE9A0", turn: float = -25) -> str:
    """A crescent moon of outer radius r (the lit rim of a disc seen past a second disc), turned by `turn`."""
    inner, shift = r * 0.82, r * 0.46  # the second disc's radius and its offset to the right
    tip_x = (r * r - inner * inner + shift * shift) / (2 * shift)
    tip_y = math.sqrt(r * r - tip_x * tip_x)
    far = 1 if tip_x > shift else 0
    d = (
        f"M{n(cx + tip_x)} {n(cy - tip_y)} A{n(r)} {n(r)} 0 1 0 {n(cx + tip_x)} {n(cy + tip_y)} "
        f"A{n(inner)} {n(inner)} 0 {far} 1 {n(cx + tip_x)} {n(cy - tip_y)} Z"
    )
    return f'<g transform="rotate({n(turn)} {n(cx)} {n(cy)})">{path(d, fill)}</g>'


def birds(*spots: tuple[float, float, float], color: str = "#3D4262") -> str:
    out = []
    for x, y, s in spots:
        out.append(
            path(
                f"M{n(x - s)} {n(y)} q{n(s * 0.5)} {n(-s * 0.7)} {n(s)} "
                f"{n(s * 0.1)} q{n(s * 0.5)} {n(-s * 0.8)} {n(s)} {n(-s * 0.1)}",
                stroke=color,
                sw=0.9,
            )
        )
    return "".join(out)


# ---- the four scenes of the story of Yunus ------------------------------------------------------------


def ship_at_sea(uid: str, kit: Kit | None) -> str:
    defs = vgrad(uid, "sky", (0, "#A8D9F1"), (1, "#FDF0D2")) + vgrad(
        uid, "sea", (0, "#53A5CE"), (1, "#2C76A6")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, 180, 64, f"url(#{uid}-sky)"), sun_disc(140, 28, 8)]
    out += [
        pic("cloud", 18, 6, 36),
        pic("cloud", 86, 2, 28),
        pic("cloud", 150, 44, 22),
        birds((66, 24, 4), (78, 19, 3.2), (54, 17, 3)),
    ]
    out += [
        rect(0, 60, 180, 44, f"url(#{uid}-sea)"),
        path(wave(62, 2.4, 24, 180, 104), "#6AB5DA", opacity=0.95),
    ]
    out += [
        pic("boat", 52, 12, 76),
        path(wave(80, 2.8, 20, 180, 104, 6), "#3F8FBF"),
        path(wave(91, 3.2, 28, 180, 104, 2), "#2C76A6"),
    ]
    for x, y in ((24, 74), (118, 70), (150, 88), (60, 96)):
        out.append(path(f"M{n(x)} {n(y)} q4 -2.4 8 0", stroke="#FFFFFF", sw=0.8, opacity=0.8))
    return "".join(out)


def dark_sea_whale(uid: str, kit: Kit | None) -> str:
    defs = vgrad(uid, "deep", (0, "#0A1F4D"), (0.6, "#133A72"), (1, "#1A4E86"))
    out = [
        f"<defs>{defs}</defs>",
        rect(0, 0, 180, 104, f"url(#{uid}-deep)"),
        path(wave(7, 2.6, 30, 180, 0), "#2468AA", opacity=0.55),
    ]
    for x, y, r in (
        (22, 30, 3),
        (30, 42, 1.8),
        (18, 56, 2.2),
        (150, 24, 2.6),
        (160, 40, 1.6),
        (142, 58, 2),
        (96, 12, 1.6),
        (120, 20, 2.2),
    ):
        out.append(circle(x, y, r, "none", 0.7, "#9CC9F0", 0.5))
    out.append(
        path("M0 92 C30 84 60 98 90 90 C120 82 150 96 180 88 L180 104 L0 104 Z", "#6F5F4D", opacity=0.9)
    )
    for x, h in ((12, 22), (24, 16), (156, 24), (168, 17)):
        out.append(
            path(
                f"M{x} 100 C{x - 5} {100 - h * 0.5} {x + 5} {100 - h * 0.7} {x} {100 - h}",
                stroke="#4E9A63",
                sw=2.4,
            )
        )
    out += [pic("whale", 36, 4, 98), pic("fish", 6, 60, 15, flip=True), pic("fish", 156, 70, 12)]
    for x, y, r in ((70, 64, 1.5), (110, 70, 1.2), (130, 36, 1.4), (50, 40, 1.2), (84, 22, 1.1)):
        out.append(sparkle(x, y, r * 1.8, "#FFF1B8", 0.85))
    return "".join(out)


def moonlit_sea(uid: str, kit: Kit | None) -> str:
    defs = vgrad(uid, "night", (0, "#0B1540"), (0.7, "#2A3C86"), (1, "#667FC9")) + vgrad(
        uid, "sea", (0, "#1C2E6A"), (1, "#0B1740")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, 180, 70, f"url(#{uid}-night)")]
    for x, y, r in (
        (14, 14, 2.6),
        (34, 30, 1.8),
        (52, 10, 2.2),
        (70, 26, 1.6),
        (88, 12, 2.4),
        (24, 46, 1.4),
        (62, 48, 1.8),
        (100, 38, 1.5),
        (160, 12, 2),
        (170, 36, 1.6),
        (112, 8, 1.4),
    ):
        out.append(sparkle(x, y, r * 1.7, "#FFF6D6", 0.92))
    out += [
        circle(134, 26, 30, "#FFF3C4", 0.08),
        circle(134, 26, 22, "#FFF3C4", 0.12),
        circle(134, 26, 16, "#FFF3C4", 0.18),
        crescent(134, 26, 13),
    ]
    out += [
        rect(0, 66, 180, 38, f"url(#{uid}-sea)"),
        path(wave(67, 1.8, 22, 180, 104), "#2B3F86", opacity=0.9),
    ]
    for y, w in ((72, 22), (77, 30), (83, 38), (90, 44), (97, 48)):
        out.append(rect(134 - w / 2, y, w, 1.3, "#FFF1B8", 0.5, 0.55))
    out += [
        path("M22 80 C24 66 42 64 52 78 C44 79 32 80 22 80 Z", "#14385F"),
        path("M36 66 C34 60 30 58 27 59 M36 66 C38 60 42 58 45 59", stroke="#BFD8F2", sw=0.9, opacity=0.8),
    ]
    for x, y in ((29, 57), (44, 57), (33, 53), (39, 53)):
        out.append(circle(x, y, 0.9, "#BFD8F2", 0.8))
    out.append(path(wave(84, 2.4, 26, 180, 104, 4), "#12265F", opacity=0.8))
    return "".join(out)


def shore_gourd_sunrise(uid: str, kit: Kit | None) -> str:
    defs = vgrad(uid, "sky", (0, "#9ED2EC"), (0.55, "#FFE3B9"), (1, "#FFB98F")) + vgrad(
        uid, "sea", (0, "#6CC0CE"), (1, "#2E90B5")
    )
    out = [
        f"<defs>{defs}</defs>",
        rect(0, 0, 180, 54, f"url(#{uid}-sky)"),
        sun_disc(100, 55, 13),
        rect(0, 53, 180, 28, f"url(#{uid}-sea)"),
    ]
    for y, w in ((58, 26), (63, 18), (69, 12)):
        out.append(rect(100 - w, y, w * 2, 1.1, "#FFE9A8", 0.55, 0.7))
    out += [
        path(wave(55, 1.4, 16, 180, 60), "#FFFFFF", opacity=0.25),
        birds((30, 20, 4), (44, 14, 3), (146, 24, 3.6), (156, 18, 2.8)),
    ]
    out += [
        path("M0 104 L0 77 C30 69 70 75 110 73 C140 72 160 65 180 63 L180 104 Z", "#F3DDB1"),
        path("M0 104 L0 92 C40 86 100 94 180 86 L180 104 Z", "#EBCF98", opacity=0.9),
    ]
    out.append(path("M0 78 C30 71 70 77 110 74 C140 73 160 66 180 64", stroke="#FFFFFF", sw=1.6, opacity=0.9))
    out += [
        pic("palm", 138, 40, 44),
        path("M140 92 C150 90 160 91 170 93", stroke="#D9BE86", sw=1, opacity=0.8),
    ]
    vine = "M-4 99 C14 90 30 92 46 86 C60 81 72 84 84 80 C94 77 102 80 100 85 C98 88 94 86 96 83"
    out.append(path(vine, stroke="#5E9B45", sw=1.8))
    for x, y, s, r in (
        (6, 74, 30, -35),
        (24, 80, 26, 30),
        (42, 70, 28, -20),
        (60, 76, 24, 38),
        (74, 66, 22, -30),
    ):
        out.append(pic("leaf", x, y, s, rotate=r))
    out += [pic("pumpkin", 36, 77, 24), pic("pumpkin", 62, 83, 17), pic("pumpkin", 12, 84, 14)]
    return "".join(out)


# the scene registry; the figure scenes and the blessings scenes are added by `islamic_scenes_people`
SCENES: dict[str, Scene] = {
    "ship-at-sea": Scene("ship-at-sea", ship_at_sea, note="a ship on a calm sea, nobody aboard"),
    "dark-sea-whale": Scene("dark-sea-whale", dark_sea_whale, note="a gentle whale in the deep sea"),
    "moonlit-sea": Scene("moonlit-sea", moonlit_sea, note="a night sea under a crescent moon"),
    "shore-gourd-sunrise": Scene(
        "shore-gourd-sunrise", shore_gourd_sunrise, note="a shore at sunrise with a gourd vine"
    ),
}
# ---- scenes with people: the reader and the recurring characters (never on a prophet's page)
# ----------------


def family_meal(uid: str, kit: Kit | None) -> str:
    assert kit is not None
    defs = vgrad(uid, "wall", (0, "#FCEBD0"), (1, "#F8DDB6"))
    out = [
        f"<defs>{defs}</defs>",
        rect(0, 0, 180, 104, f"url(#{uid}-wall)"),
        rect(0, 52, 180, 26, "#EBCBA0"),
        rect(0, 52, 180, 1.6, "#D9AE7A"),
    ]
    out += [rect(0, 78, 180, 26, "#D9AE7A")] + [
        path(f"M0 {y} L180 {y}", stroke="#C99A62", sw=0.5) for y in (84, 91, 98)
    ]
    out += [
        pic("window", 6, 6, 34),
        path("M152 0 L152 13", stroke="#8A6A3D", sw=0.8),
        path("M141 13 L163 13 L158 24 L146 24 Z", "#F2B33D"),
        circle(152, 26, 14, "#FFE9A8", 0.28),
    ]
    # seated: the table (y 82) hides them from the chest down. Every head stays below y ~54, inside the
    # widest box a story page gives a scene (54 mm high: it shows only y >= ~51; the grandmother and the
    # reader, drawn 78 and 76 high, lost their heads there), and every face above the plates (y 79). The
    # children's drawings fill only the lower part of their box, so they keep their size.
    for who, x, feet, h in (
        ("reem", 30, 108, 74),
        ("huda", 70, 118, 64),
        ("reader", 110, 120, 64),
        ("salem", 150, 108, 68),
    ):
        out.append(kit.figure(who, x, feet, h))
    out += [rect(6, 82, 168, 6, "#FFFFFF"), rect(6, 88, 168, 16, "#FFF6E0"), rect(6, 96, 168, 3.2, "#E4675A")]
    for x in (21, 61, 101, 141):
        out.append(pic("plate", x, 79, 17))
    out += [
        pic("loaf", 84, 73, 18),
        pic("dates", 124, 72, 18),
        pic("jug", 2, 69, 20),
        pic("fruit-bowl", 44, 72, 18),
    ]
    return "".join(out)


def kitchen_broken_cup(uid: str, kit: Kit | None) -> str:
    assert kit is not None
    out = [rect(0, 0, 180, 104, "#E6F3F1")]
    for row, y in enumerate(range(0, 62, 8)):
        out.append(path(f"M0 {y} L180 {y}", stroke="#C9E2DE", sw=0.5))
        out.append(
            path(
                "".join(f"M{x} {y} L{x} {y + 8}" for x in range(4 if row % 2 else 0, 180, 16)),
                stroke="#C9E2DE",
                sw=0.5,
            )
        )
    out += [
        pic("window", 10, 6, 36),
        rect(0, 60, 180, 32, "#C9966A"),
        rect(0, 56, 180, 6, "#F1E6D2"),
        rect(0, 61.5, 180, 1.2, "#B07F52"),
    ]
    for x in (6, 54, 102, 150):
        out += [
            rect(x, 66, 40, 22, "#D8A877", 1.5),
            rect(x + 3, 69, 34, 16, "none", 1),
            path(f"M{x + 20} 70 L{x + 20} 84", stroke="#B07F52", sw=0.5),
            circle(x + 17, 77, 1.1, "#8A6A3D"),
            circle(x + 23, 77, 1.1, "#8A6A3D"),
        ]
    out.append(rect(0, 92, 180, 12, "#F3EBDD"))
    out += [rect(x, 92 + (y % 2) * 0, 12, 6, "#DCCFB6") for x in range(0, 180, 24) for y in (0,)] + [
        rect(x, 98, 12, 6, "#DCCFB6") for x in range(12, 180, 24)
    ]
    out.append('<ellipse cx="86" cy="98" rx="27" ry="5.6" fill="#D6E8F6"/>')
    shards = (
        ("M62 92 L74 88 L77 97 L65 100 Z", "#FFFFFF"),
        ("M77 96 L90 92 L93 101 L80 102 Z", "#F4F8FD"),
        ("M94 94 L105 96 L102 102 L92 101 Z", "#FFFFFF"),
        ("M70 99 Q76 93 84 99 Q76 102 70 99 Z", "#7FB7E0"),
    )
    out += [path(d, f, OUTLINE, 0.8) for d, f in shards]
    out += [pic("cat", 6, 74, 22), kit.figure("reader", 142, 101, 47)]  # the head below y 54, as above
    return "".join(out)


def blessings_garden(uid: str, kit: Kit | None) -> str:
    """Line art to colour (no person, no text): the sun, a fruit tree, a palm, a house, a bird, water and
    fish, flowers,
    a basket of fruit and bread."""
    out = [circle(32, 30, 13, "#FFFFFF", 1, OUTLINE, 1.3)]
    for i in range(12):
        a = math.radians(i * 30)
        out.append(
            path(
                f"M{n(32 + 17 * math.cos(a))} {n(30 + 17 * math.sin(a))} "
                f"L{n(32 + 24 * math.cos(a))} {n(30 + 24 * math.sin(a))}",
                stroke=OUTLINE,
                sw=1.3,
            )
        )
    out += [
        pic("cloud", 74, 8, 46, "line"),
        pic("cloud", 140, 34, 36, "line"),
        pic("bird", 80, 38, 26, "line", flip=True),
        pic("butterfly", 148, 6, 22, "line"),
    ]
    out += [
        pic("tree", 110, 40, 76, "line"),
        pic("palm", 66, 62, 58, "line"),
        pic("house", 2, 66, 66, "line"),
    ]
    out.append(path("M0 142 C30 136 64 146 100 140 C130 135 160 142 186 138", stroke=OUTLINE, sw=1.3))
    out += [
        pic("flower", 20, 118, 24, "line"),
        pic("flower", 46, 124, 18, "line"),
        pic("flower", 92, 122, 20, "line"),
        pic("grass", 150, 120, 28, "line"),
    ]
    out.append(
        path(
            "M8 164 C8 152 34 150 52 156 C72 162 90 154 98 168 C104 182 78 192 50 190 C22 192 6 178 8 164 Z",
            "#FFFFFF",
            OUTLINE,
            1.3,
        )
    )
    for x, y in ((24, 166), (44, 175), (64, 164)):
        out.append(path(f"M{x} {y} q4 -3 8 0 t8 0", stroke=OUTLINE, sw=1))
    out += [pic("fish", 28, 170, 17, "line"), pic("fish", 58, 156, 13, "line", flip=True)]
    out += [
        pic("fruit-bowl", 112, 150, 44, "line"),
        pic("loaf", 108, 176, 26, "line"),
        pic("dates", 150, 168, 28, "line"),
        pic("apple", 160, 148, 20, "line"),
    ]
    return "".join(out)


BLESSING_SPOTS: dict[str, tuple[float, float, float]] = {  # the hidden blessings: centre and ring radius
    "sun": (26, 22, 13), "water": (38, 92, 17), "tree": (146, 52, 22), "fruit": (110, 88, 9),
    "bird": (96, 34, 10), "bread": (88, 100, 10), "moon": (156, 18, 11), "family": (112, 80, 28),
}  # fmt: skip


def blessings_scene(uid: str, kit: Kit | None) -> str:
    assert kit is not None
    defs = vgrad(uid, "sky", (0, "#BFE3F6"), (1, "#FFF1D6")) + vgrad(
        uid, "hill", (0, "#9FD18B"), (1, "#7DBB6A")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, 186, 70, f"url(#{uid}-sky)"), sun_disc(26, 22, 8.5)]
    out += [crescent(156, 18, 8, "#F8F4E4", -35), pic("cloud", 54, 8, 30), pic("cloud", 118, 30, 24)]
    out += [
        path("M0 52 C30 40 60 56 100 46 C140 36 160 50 186 44 L186 118 L0 118 Z", f"url(#{uid}-hill)"),
        path("M0 76 C40 66 90 80 186 70 L186 118 L0 118 Z", "#8CC678"),
    ]
    out += [pic("tree", 124, 28, 52), pic("bird", 88, 26, 18, flip=True)]
    out.append('<ellipse cx="38" cy="92" rx="26" ry="10" fill="#7CC4E8"/>')
    out += [
        path("M22 90 q4 -2.4 8 0 t8 0 t8 0", stroke="#FFFFFF", sw=1, opacity=0.9),
        path("M30 96 q4 -2.4 8 0 t8 0", stroke="#FFFFFF", sw=1, opacity=0.8),
    ]
    for who, x, h in (("reem", 80, 40), ("huda", 100, 44), ("reader", 122, 46), ("salem", 142, 36)):
        out.append(kit.figure(who, x, 104, h))
    out += [
        '<ellipse cx="112" cy="106" rx="50" ry="10" fill="#FFF6E0"/>',
        rect(62, 104, 100, 14, "#FFF6E0"),
        rect(62, 112, 100, 2.4, "#E4675A"),
    ]
    out += [
        pic("loaf", 80, 92, 17),
        pic("apple", 102, 96, 12),
        pic("dates", 122, 94, 15),
        pic("jug", 144, 90, 18),
    ]
    return "".join(out)


SCENES.update(
    {
        "family-meal": Scene(
            "family-meal", family_meal, figures=True, align="xMidYMax", note="the family at the table"
        ),
        "kitchen-broken-cup": Scene(
            "kitchen-broken-cup",
            kitchen_broken_cup,
            figures=True,
            align="xMidYMax",
            note="a broken cup in the kitchen",
        ),
        "blessings-garden": Scene(
            "blessings-garden", blessings_garden, box=(186.0, 200.0), note="line art to colour, no person"
        ),
        "blessings-scene": Scene(
            "blessings-scene", blessings_scene, figures=True, box=(186.0, 118.0), note="find the blessings"
        ),
    }
)
__all__ = ["BLESSING_SPOTS", "SCENES", "Kit", "Scene", "scene_svg"]
