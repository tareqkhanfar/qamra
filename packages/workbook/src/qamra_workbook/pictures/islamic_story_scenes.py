"""The drawn scenes of the prophets' stories and the sira (Addendum 10 §3.5), one for each moment a story
needs to show: Nuh's wooden ark being built, the animals coming two by two, the ark on the high waves and
resting on the mountain; Yusuf's dream of eleven stars with the sun and the moon; the well in the desert; the
basket on the river and the sea split with a dry path; Makkah's valley, the hill of al-Safa and the cave in
the mountain.
They replace the generic garden and desert backdrops that repeated from panel to panel.

Places, nature and things only: no person, no silhouette, no figure, no beams of light from above, and no
object standing for a prophet (no staff, no sandals). Each draws in the 180 × 104 box of `islamic_scenes`."""

from __future__ import annotations

import math

from qamra_workbook.pictures.islamic_scenes import (
    Kit,
    Scene,
    birds,
    circle,
    crescent,
    n,
    path,
    pic,
    rect,
    sparkle,
    sun_disc,
    vgrad,
    wave,
)
from qamra_workbook.pictures.model import OUTLINE

WOOD, WOOD_DARK, WOOD_LIGHT = "#A86F3D", "#7E4E26", "#C98E57"
STONE, STONE_DARK = "#D8C3A0", "#B59A72"
ROCK, ROCK_DARK = "#B98E66", "#8F6A49"


def _sky(uid: str, top: str, bottom: str, height: float = 104) -> str:
    return f"<defs>{vgrad(uid, 'sky', (0, top), (1, bottom))}</defs>" + rect(
        0, 0, 180, height, f"url(#{uid}-sky)"
    )


def _stars(spots: tuple[tuple[float, float, float], ...], color: str = "#FFF3C4") -> str:
    return "".join(sparkle(x, y, r, color, 0.95) for x, y, r in spots)


def ark(x: float, y: float, w: float, *, done: bool = True) -> str:
    """Nuh's ark: a long wooden hull with its planks and a cabin with a roof and small windows (never sails, a
    funnel or an engine). (x, y) is the middle of the keel line, `w` the hull's length. `done=False`: the hull
    only, its ribs showing where the planks are not on yet."""
    h = w * 0.26
    left, right, deck = x - w / 2, x + w / 2, y - h
    hull = (
        f"M{n(left - w * 0.04)} {n(deck)} L{n(right + w * 0.04)} {n(deck)} "
        f"C{n(right)} {n(deck + h * 0.6)} {n(x + w * 0.32)} {n(y)} {n(x + w * 0.22)} {n(y)} "
        f"L{n(x - w * 0.22)} {n(y)} C{n(x - w * 0.32)} {n(y)} {n(left)} {n(deck + h * 0.6)} "
        f"{n(left - w * 0.04)} {n(deck)} Z"
    )
    out = [path(hull, WOOD, OUTLINE, 1.1)]
    for k in (0.3, 0.55, 0.8):
        yy = deck + h * k
        span = w * (0.5 - 0.16 * k)
        out.append(path(f"M{n(x - span)} {n(yy)} L{n(x + span)} {n(yy)}", stroke=WOOD_DARK, sw=0.7))
    if not done:
        for i in range(-3, 4):
            xx = x + i * w * 0.11
            out.append(path(f"M{n(xx)} {n(deck)} L{n(xx)} {n(y - 0.5)}", stroke=WOOD_DARK, sw=1.1))
        return "".join(out)
    cw, ch = w * 0.46, h * 0.95
    out.append(rect(x - cw / 2, deck - ch, cw, ch, WOOD_LIGHT))
    out.append(path(f"M{n(x - cw / 2)} {n(deck - ch)} h{n(cw)} v{n(ch)} h{n(-cw)} Z", stroke=OUTLINE, sw=0.9))
    top = deck - ch
    roof = f"M{n(x - cw / 2 - 3)} {n(top)} L{n(x)} {n(top - h * 0.55)} L{n(x + cw / 2 + 3)} {n(top)} Z"
    out.append(path(roof, "#8C4A2F", OUTLINE, 0.9))
    for i in (-1, 0, 1):
        out.append(rect(x + i * cw * 0.3 - 2.2, deck - ch * 0.66, 4.4, 4.4, "#FFE3A0", 0.8))
    return "".join(out)


def _hills(color: str, top: float, phase: float = 0) -> str:
    return path(
        f"M0 {n(top + 8)} C{n(30 + phase)} {n(top - 4)} {n(60 + phase)} {n(top + 10)} "
        f"{n(100 + phase)} {n(top)} "
        f"C140 {n(top - 10)} 160 {n(top + 4)} 180 {n(top - 2)} L180 104 L0 104 Z",
        color,
    )


# ---- Nuh, peace be upon him ------------------------------------------------------------------------------


def ark_building(uid: str, kit: Kit | None) -> str:
    """The ark being built on dry land, far from any sea: the hull on its props, planks, a hammer and rope."""
    out = [_sky(uid, "#BFE3F6", "#FFF1D6"), sun_disc(26, 20, 7), pic("cloud", 120, 8, 26)]
    out += [_hills("#B7D98F", 56), path("M0 80 C50 72 120 84 180 76 L180 104 L0 104 Z", "#D9C28F")]
    for x in (52, 74, 106, 128):  # the props under the hull
        out.append(path(f"M{x} 86 L{x + 4} 74", stroke=WOOD_DARK, sw=1.6))
    out.append(ark(90, 76, 100, done=False))
    for i in range(3):  # a stack of planks
        out.append(rect(14, 86 - i * 3.2, 34, 3, WOOD_LIGHT if i % 2 else WOOD, 0.6))
        out.append(path(f"M14 {86 - i * 3.2} h34", stroke=OUTLINE, sw=0.5))
    out += [pic("hammer", 140, 80, 16, rotate=-20), pic("rope", 156, 84, 16)]
    return "".join(out)


def ark_finished(uid: str, kit: Kit | None) -> str:
    """The ark finished on dry land under a calm sky, a few clouds gathering far away."""
    out = [_sky(uid, "#B9DCF0", "#FFF3DA"), sun_disc(150, 18, 7)]
    out += [pic("cloud", 10, 6, 30), pic("cloud", 46, 14, 22), birds((110, 20, 3), (120, 16, 2.4))]
    out += [_hills("#A9D188", 58, 10), path("M0 84 C50 76 120 88 180 80 L180 104 L0 104 Z", "#D6BE8A")]
    out.append(ark(92, 82, 90))
    out += [pic("hammer", 22, 86, 14, rotate=-15), pic("palm", 150, 50, 34)]
    return "".join(out)


def animals_pairs(uid: str, kit: Kit | None) -> str:
    """The animals coming two by two to the ark, its ramp let down."""
    out = [_sky(uid, "#BFE3F6", "#FFF1D6"), sun_disc(24, 18, 6), pic("cloud", 70, 6, 24)]
    out += [_hills("#B7D98F", 50), path("M0 76 C50 70 120 80 180 74 L180 104 L0 104 Z", "#CDE3A0")]
    out.append(ark(134, 68, 70))
    out.append(path("M110 54 L92 84 L98 86 L114 57 Z", WOOD_LIGHT, OUTLINE, 0.8))
    pairs = (("elephant", 4, 66, 22), ("giraffe", 26, 56, 30), ("camel", 52, 70, 20), ("sheep", 70, 82, 14))
    for name, x, y, s in pairs:
        out.append(pic(name, x, y, s, flip=True))
        out.append(pic(name, x + s * 0.45, y + 8, s * 0.9, flip=True))
    out.append(birds((60, 30, 3), (66, 26, 3)))
    return "".join(out)


def ark_waves(uid: str, kit: Kit | None) -> str:
    """The ark on high waves under rain clouds; Allah keeps it safe."""
    defs = vgrad(uid, "sky", (0, "#5E6E8C"), (1, "#9FB1C8")) + vgrad(
        uid, "sea", (0, "#3D7FB0"), (1, "#1F4F7A")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, 180, 104, f"url(#{uid}-sky)")]
    for x, y, s in ((4, 2, 40), (52, 0, 46), (110, 4, 40), (148, 0, 36)):
        out.append(pic("cloud", x, y, s))
    for x in range(8, 180, 11):  # the rain
        for y0 in (30, 48):
            out.append(path(f"M{x + (y0 % 7)} {y0} l-2 6", stroke="#DCE8F5", sw=0.8, opacity=0.8))
    out.append(rect(0, 70, 180, 34, f"url(#{uid}-sea)"))
    out.append(path(wave(70, 6, 40, 180, 104), "#2F6E9E"))
    out.append(ark(90, 74, 78))
    out.append(path(wave(80, 5, 34, 180, 104, 10), "#2A6596"))
    out.append(path(wave(92, 4, 26, 180, 104, 4), "#1F4F7A"))
    for x, y in ((20, 80), (140, 84), (70, 96)):
        out.append(path(f"M{x} {y} q5 -3 10 0", stroke="#FFFFFF", sw=0.9, opacity=0.8))
    return "".join(out)


def ark_mountain(uid: str, kit: Kit | None) -> str:
    """The water going down and the ark resting on a mountain top (al-Judi); a clear sky after the rain."""
    out = [
        _sky(uid, "#A9D8F2", "#FFF1D6"),
        sun_disc(30, 22, 8),
        pic("cloud", 120, 6, 30),
        pic("cloud", 64, 16, 20),
    ]
    out.append(path("M14 104 L72 58 Q90 48 108 58 L172 104 Z", ROCK))
    out.append(path("M72 58 Q90 48 108 58 L120 70 Q96 64 66 68 Z", ROCK_DARK, opacity=0.5))
    out.append(path("M0 104 L0 92 C40 88 80 96 120 90 C150 86 170 92 180 90 L180 104 Z", "#4F95C2"))
    out.append(path(wave(94, 1.6, 20, 180, 104), "#6AACD4", opacity=0.9))
    out.append(ark(90, 56, 50))
    out += [path("M40 86 L48 76 L56 86 Z", "#8CC678"), path("M126 88 L134 78 L142 88 Z", "#8CC678")]
    out.append(birds((140, 30, 3), (150, 26, 2.4)))
    return "".join(out)


# ---- Yusuf, peace be upon him ----------------------------------------------------------------------------


def dream_eleven_stars(uid: str, kit: Kit | None) -> str:
    """The dream: eleven stars, the sun and the moon in a soft night, set in an arc (no faces, nobody)."""
    defs = vgrad(uid, "sky", (0, "#1A2257"), (1, "#4A3F8F"))
    out = [f"<defs>{defs}</defs>", rect(0, 0, 180, 104, f"url(#{uid}-sky)")]
    out.append(path("M0 92 C40 84 120 98 180 88 L180 104 L0 104 Z", "#2A2F6A", opacity=0.8))
    for x, y in ((14, 16), (40, 8), (150, 10), (170, 30), (8, 44)):
        out.append(circle(x, y, 0.8, "#FFFFFF", 0.7))
    cx, cy, r = 90, 92, 62
    for i in range(11):  # eleven stars along the arc
        a = math.radians(180 + 16 + i * (148 / 10))
        sx, sy = cx + r * math.cos(a), cy + r * 0.95 * math.sin(a)
        out.append(sparkle(sx, sy, 5.2, "#FFE07A"))
    out.append(sun_disc(64, 66, 8, "#FFC94A", "#FFE9A8"))
    out.append(crescent(116, 66, 9, "#FFF3C4", -20))
    return "".join(out)


def desert_well(uid: str, kit: Kit | None) -> str:
    """A stone well in the desert, its rope and bucket, a palm far off."""
    out = [_sky(uid, "#FBD9A0", "#FFF3DC"), sun_disc(30, 20, 8)]
    out += [
        path("M0 60 C30 48 60 62 96 54 C130 46 156 58 180 52 L180 104 L0 104 Z", "#E9C27F"),
        path("M0 80 C40 70 100 86 180 76 L180 104 L0 104 Z", "#DDAE63"),
        pic("palm", 140, 30, 36),
    ]
    out.append('<ellipse cx="80" cy="66" rx="24" ry="6" fill="#5A4632"/>')
    out.append(path("M56 66 L56 90 Q80 98 104 90 L104 66 Q80 74 56 66 Z", STONE, OUTLINE, 1))
    for y in (74, 82):
        out.append(path(f"M56 {y} Q80 {y + 8} 104 {y}", stroke=STONE_DARK, sw=0.8))
    for x in (68, 92):
        out.append(path(f"M{x} 70 l0 8 M{x - 6} 80 l0 8", stroke=STONE_DARK, sw=0.6))
    out.append(path("M60 66 L60 40 M100 66 L100 40 M56 40 L104 40", stroke=WOOD_DARK, sw=2.4))
    out.append(path("M80 40 L80 56", stroke="#8A6A3D", sw=0.8))
    out.append(path("M75 56 L85 56 L83 63 L77 63 Z", WOOD, OUTLINE, 0.7))
    return "".join(out)


# ---- Musa, peace be upon him -----------------------------------------------------------------------------


def river_basket(uid: str, kit: Kit | None) -> str:
    """A closed basket floating on the river between the reeds (no one is seen in it)."""
    defs = vgrad(uid, "sky", (0, "#BDE2F4"), (1, "#FFF4DD")) + vgrad(
        uid, "river", (0, "#5DB0D3"), (1, "#2F7FAE")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, 180, 60, f"url(#{uid}-sky)"), sun_disc(150, 16, 7)]
    out += [
        path("M0 52 C40 46 120 56 180 48 L180 64 L0 64 Z", "#9FCB7C"),
        rect(0, 60, 180, 44, f"url(#{uid}-river)"),
    ]
    out.append(path(wave(62, 1.6, 22, 180, 104), "#7CC2E0", opacity=0.8))
    for x in (6, 14, 22, 150, 160, 170):  # reeds
        out.append(path(f"M{x} 104 C{x - 2} 80 {x + 2} 66 {x} 52", stroke="#4E9A63", sw=1.6))
        out.append(f'<ellipse cx="{x}" cy="54" rx="1.6" ry="5" fill="#8A6A3D"/>')
    out.append(path("M66 78 Q90 92 114 78 L110 70 Q90 76 70 70 Z", "#D9B26E", OUTLINE, 1))
    out.append(path("M70 70 Q90 60 110 70 Q90 76 70 70 Z", "#C99A55", OUTLINE, 1))
    for x in (78, 90, 102):
        out.append(path(f"M{x} 72 l0 12", stroke="#A57A3C", sw=0.6))
    for x, y in ((40, 86), (130, 90), (60, 98)):
        out.append(path(f"M{x} {y} q5 -2.4 10 0", stroke="#FFFFFF", sw=0.8, opacity=0.8))
    return "".join(out)


def sea_split(uid: str, kit: Kit | None) -> str:
    """The sea split in two high walls of water, a dry path between them to the far shore."""
    defs = vgrad(uid, "sky", (0, "#A9D8F2"), (1, "#FFF1D6")) + vgrad(
        uid, "wall", (0, "#2C76A6"), (1, "#5DB0D3")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, 180, 104, f"url(#{uid}-sky)"), pic("cloud", 70, 4, 26)]
    out.append(path("M60 40 L120 40 L150 104 L30 104 Z", "#E8D3A2"))
    out.append(path("M84 40 L96 40 L100 104 L80 104 Z", "#F2E2BC", opacity=0.7))
    left = "M0 104 L0 22 C10 16 20 26 30 18 C40 12 50 22 58 30 L60 40 L30 104 Z"
    right = "M180 104 L180 22 C170 16 160 26 150 18 C140 12 130 22 122 30 L120 40 L150 104 Z"
    out += [path(left, f"url(#{uid}-wall)"), path(right, f"url(#{uid}-wall)")]
    for k in range(4):
        y = 34 + k * 16
        out.append(path(f"M{4 + k * 3} {y} q8 -4 16 0 t16 0", stroke="#BFE3F6", sw=1, opacity=0.7))
        out.append(path(f"M{142 - k * 3} {y + 6} q8 -4 16 0 t16 0", stroke="#BFE3F6", sw=1, opacity=0.7))
    out.append(path("M58 30 q2 4 2 10 M122 30 q-2 4 -2 10", stroke="#FFFFFF", sw=1.2, opacity=0.9))
    out += [
        pic("stone", 70, 86, 10),
        pic("stone", 104, 92, 9),
        path("M60 40 L120 40", stroke="#D9BE86", sw=1),
    ]
    return "".join(out)


# ---- the sira: Makkah, al-Safa and the cave --------------------------------------------------------------


def _makkah_houses(y: float, color: str = STONE, shade: str = STONE_DARK) -> str:
    """Flat-roofed houses of old Makkah in its valley."""
    out = []
    for x, w, h in ((8, 22, 18), (32, 18, 24), (52, 26, 16), (100, 22, 20), (124, 18, 14), (144, 28, 22)):
        out.append(rect(x, y - h, w, h, color))
        out.append(path(f"M{x} {y - h} h{w}", stroke=shade, sw=1.4))
        out.append(rect(x + w * 0.4, y - h * 0.5, w * 0.2, h * 0.5, shade))
    return "".join(out)


def makkah_valley(uid: str, kit: Kit | None) -> str:
    """Makkah's valley between bare mountains, its houses; morning."""
    out = [_sky(uid, "#BFE3F6", "#FFF1D6"), sun_disc(150, 18, 7), birds((60, 18, 3), (70, 14, 2.4))]
    out.append(path("M0 70 L24 34 L46 56 L70 26 L96 60 L120 30 L150 52 L180 28 L180 104 L0 104 Z", ROCK))
    out.append(
        path(
            "M24 34 L34 50 L46 56 Z M70 26 L82 44 L96 60 Z M120 30 L134 42 L150 52 Z", ROCK_DARK, opacity=0.5
        )
    )
    out.append(path("M0 84 C50 78 120 88 180 80 L180 104 L0 104 Z", "#E3CFA4"))
    out.append(_makkah_houses(90))
    return "".join(out)


def safa_hill(uid: str, kit: Kit | None) -> str:
    """The hill of al-Safa: a rocky rise with a flat stony top above the valley; nobody on it."""
    out = [_sky(uid, "#B5DDF3", "#FFF3DC"), sun_disc(28, 20, 7), pic("cloud", 110, 8, 24)]
    out.append(path("M0 104 L0 70 L50 44 Q60 36 76 36 L104 36 Q118 36 128 46 L180 76 L180 104 Z", ROCK))
    out.append(path("M50 44 Q60 36 76 36 L104 36 Q118 36 128 46 Q96 42 50 44 Z", ROCK_DARK, opacity=0.4))
    for x, y, s in ((36, 62, 9), (62, 52, 11), (96, 48, 10), (128, 60, 9), (150, 74, 8)):
        out.append(pic("stone", x, y, s))
    out.append(path("M0 92 C50 86 120 96 180 88 L180 104 L0 104 Z", "#E3CFA4"))
    out.append(_makkah_houses(100))
    return "".join(out)


def _mountain_with_cave(dark: bool) -> str:
    rock, shade = ("#6E5A7E", "#4F4062") if dark else (ROCK, ROCK_DARK)
    out = [path("M0 104 L30 52 L58 30 Q74 18 92 26 L128 44 L160 70 L180 84 L180 104 Z", rock)]
    out.append(path("M58 30 Q74 18 92 26 L104 40 Q80 34 58 30 Z", shade, opacity=0.5))
    out.append(path("M82 70 Q82 54 96 52 Q110 54 110 70 Q96 66 82 70 Z", "#241C2E"))
    out.append(path("M80 70 Q96 64 112 70", stroke=shade, sw=1.4))
    for x, y, s in ((50, 74, 10), (118, 76, 9), (30, 88, 9)):
        out.append(pic("stone", x, y, s))
    return "".join(out)


def cave_night(uid: str, kit: Kit | None) -> str:
    """A mountain at night, a cave's dark mouth in its side; stars and a crescent."""
    defs = vgrad(uid, "sky", (0, "#121A45"), (1, "#3B4C93"))
    out = [
        f"<defs>{defs}</defs>",
        rect(0, 0, 180, 104, f"url(#{uid}-sky)"),
        crescent(150, 18, 9, "#FFE9A0", -30),
    ]
    out.append(
        _stars(((16, 12, 2.2), (40, 24, 1.6), (64, 8, 1.8), (110, 14, 2.2), (126, 34, 1.4), (170, 44, 1.6)))
    )
    out.append(_mountain_with_cave(dark=True))
    return "".join(out)


def cave_dawn(uid: str, kit: Kit | None) -> str:
    """The same mountain at dawn, quiet: the cave kept safe."""
    defs = vgrad(uid, "sky", (0, "#9FC9EA"), (0.7, "#FFE0B8"), (1, "#FFC79A"))
    out = [f"<defs>{defs}</defs>", rect(0, 0, 180, 104, f"url(#{uid}-sky)"), sun_disc(150, 40, 9)]
    out.append(birds((30, 20, 3), (40, 16, 2.4)))
    out.append(_mountain_with_cave(dark=False))
    return "".join(out)


def makkah_night(uid: str, kit: Kit | None) -> str:
    """Makkah's houses at night under a crescent: the setting out."""
    defs = vgrad(uid, "sky", (0, "#121A45"), (1, "#33458F"))
    out = [
        f"<defs>{defs}</defs>",
        rect(0, 0, 180, 104, f"url(#{uid}-sky)"),
        crescent(36, 20, 9, "#FFE9A0", -30),
    ]
    out.append(_stars(((80, 10, 1.8), (110, 22, 2.2), (140, 12, 1.6), (164, 30, 2))))
    out.append(path("M0 74 L30 44 L56 62 L84 38 L112 64 L140 40 L180 70 L180 104 L0 104 Z", "#2B2A4F"))
    out.append(path("M0 86 C50 80 120 90 180 82 L180 104 L0 104 Z", "#3A3A5E"))
    out.append(_makkah_houses(94, "#5C5A80", "#45436A"))
    for x, y in ((14, 84), (40, 80), (110, 82), (154, 82)):
        out.append(rect(x, y, 3, 3, "#FFD98A", 0.4))
    return "".join(out)


# ---- Adam, peace be upon him -----------------------------------------------------------------------------


def lush_garden(uid: str, kit: Kit | None) -> str:
    """A lush garden with fruit trees, a stream and flowers."""
    out = [_sky(uid, "#BFE6F5", "#FFF6DE"), sun_disc(150, 18, 7), birds((60, 16, 3), (70, 12, 2.4))]
    out += [_hills("#A8D888", 50), path("M0 72 C50 64 120 76 180 68 L180 104 L0 104 Z", "#8CC678")]
    out.append(
        path(
            "M70 104 C80 90 100 86 110 76 C118 70 140 70 180 72 L180 80 C150 78 126 78 118 84 "
            "C106 92 92 96 86 104 Z",
            "#7CC4E8",
        )
    )
    for x, y, s in ((2, 30, 44), (40, 36, 36), (122, 32, 40), (150, 38, 34)):
        out.append(pic("tree", x, y, s))
    for x, y, s in ((20, 84, 12), (34, 90, 10), (56, 86, 11), (130, 88, 10), (150, 92, 11)):
        out.append(pic("flower", x, y, s))
    return "".join(out)


SCENES_EXTRA: dict[str, Scene] = {
    s.name: s
    for s in (
        Scene("ark-building", ark_building, note="Nuh's ark being built on dry land, no people"),
        Scene("ark-finished", ark_finished, note="the ark finished on dry land"),
        Scene("animals-pairs", animals_pairs, note="the animals coming two by two to the ark"),
        Scene("ark-waves", ark_waves, note="the ark on the high waves in the rain"),
        Scene("ark-mountain", ark_mountain, note="the ark resting on the mountain as the water goes down"),
        Scene("dream-eleven-stars", dream_eleven_stars, note="eleven stars, the sun and the moon"),
        Scene("desert-well", desert_well, note="a stone well in the desert"),
        Scene("river-basket", river_basket, note="a closed basket on the river between reeds"),
        Scene("sea-split", sea_split, note="the sea split with a dry path"),
        Scene("makkah-valley", makkah_valley, note="Makkah's valley and houses between mountains"),
        Scene("safa-hill", safa_hill, note="the rocky hill of al-Safa above the valley"),
        Scene("cave-night", cave_night, note="a mountain with a cave's mouth at night"),
        Scene("cave-dawn", cave_dawn, note="the mountain and its cave at dawn"),
        Scene("makkah-night", makkah_night, note="Makkah's houses at night under a crescent"),
        Scene("lush-garden", lush_garden, note="a garden with fruit trees and a stream"),
    )
}
