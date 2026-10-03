"""Composed scenes of «قلبي يعرف الله»: a backdrop (a room, the garden, the mosque, the sea…) with things from
the picture library on it and the cast standing in it, so a page can say

    scene: {backdrop: kitchen, props: [cup, bread, dates], figures: [reader, huda]}

instead of needing a scene drawn for it. Backdrops are flat gradients and simple shapes in the 180 × 104 box
of `islamic_scenes`, with no person, no writing and no beams of light from above (Addendum 10 §3.5). People
come only from the `Kit` (the recurring characters and the reader); a library picture of a person is never a
prop (`PERSON_PICTURES`)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from markupsafe import Markup

from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.islamic_icons import UNIT_GLYPHS
from qamra_workbook.pictures.islamic_scenes import (
    Kit,
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

W, H = 180.0, 104.0
# A scene fills its box from the bottom (slice, YMax): the widest box (54 mm high on a 180 mm line, about 3.4:1)
# shows only y ≥ ~51 of the 104 units, so the tallest figure's head must stay below this line.
HEAD_ROOM_TOP = 54.0
# library pictures that draw a person: never a prop (people are only the cast, drawn by the Kit)
PERSON_CATEGORIES = frozenset({"person", "people", "family", "action"})
PERSON_PICTURES = frozenset(k for k, p in PICTURES.items() if p.category in PERSON_CATEGORIES)
# body parts: allowed as props on everyday pages (the wudu cards use them), never on a prophet's page
BODY_PICTURES = frozenset(k for k, p in PICTURES.items() if p.category == "body")
GLYPH_PREFIX = "isl:"  # a prop that is one of the series' icons: isl:lantern, isl:prayer-mat…
GLYPH_COLORS = ("#1F7A5A", "#C9962B", "#5B6FC0", "#C0265B", "#14606E", "#D9822B")


@dataclass(frozen=True)
class Backdrop:
    name: str
    back: Callable[[str], str]  # (unique id prefix) → SVG elements behind everything
    front: Callable[[str], str] | None = None  # drawn over the figures (a table's edge)
    floor: float = 100.0  # where the figures' feet are
    figure_h: float = 62.0  # the tallest figure (the grandmother); the children are a little shorter
    spots: tuple[tuple[float, float, float], ...] = ()  # where props go, in order: x, y (top-left), size
    people_x: tuple[float, ...] = (66.0, 94.0, 122.0, 150.0)
    note: str = ""


def prop_known(prop: str) -> bool:
    if prop.startswith(GLYPH_PREFIX):
        return prop[len(GLYPH_PREFIX) :] in UNIT_GLYPHS
    return prop in PICTURES


def prop_svg(prop: str, x: float, y: float, size: float, i: int = 0) -> str:
    """A prop placed with its top-left at (x, y): a library picture, or a series icon on a soft disc."""
    if prop.startswith(GLYPH_PREFIX):
        from qamra_workbook.pictures.islamic import glyph_svg

        name = prop[len(GLYPH_PREFIX) :]
        color = GLYPH_COLORS[i % len(GLYPH_COLORS)]
        k = size / 24
        return (
            circle(x + size / 2, y + size / 2, size / 2, "#FFFFFF", 0.92, color, size / 40)
            + f'<g transform="translate({n(x + size * 0.18)} {n(y + size * 0.18)}) scale({n(k * 0.64)})">'
            + f"{glyph_svg(name, color, 1.8)}</g>"
        )
    return pic(prop, x, y, size)


# ---- the backdrops -------------------------------------------------------------------------------------


def _home(uid: str) -> str:
    out = [
        f"<defs>{vgrad(uid, 'wall', (0, '#FCEBD0'), (1, '#F6DCB4'))}</defs>",
        rect(0, 0, W, 80, f"url(#{uid}-wall)"),
        rect(0, 80, W, 24, "#D9AE7A"),
        rect(0, 79, W, 1.8, "#C2925C"),
    ]
    out += [path(f"M0 {y} L{W} {y}", stroke="#C99A62", sw=0.5) for y in (87, 95)]
    out += [pic("window", 8, 8, 40), pic("lamp", 150, 34, 22)]
    out.append('<ellipse cx="104" cy="96" rx="58" ry="6.5" fill="#C0265B" opacity="0.28"/>')
    out.append('<ellipse cx="104" cy="96" rx="50" ry="4.6" fill="none" stroke="#F2B33D" stroke-width="0.8"/>')
    return "".join(out)


def _kitchen(uid: str) -> str:
    out = [rect(0, 0, W, H, "#E6F3F1")]
    for row, y in enumerate(range(0, 62, 8)):
        out.append(path(f"M0 {y} L{W} {y}", stroke="#C9E2DE", sw=0.5))
        out.append(
            path(
                "".join(f"M{x} {y} L{x} {y + 8}" for x in range(4 if row % 2 else 0, int(W), 16)),
                stroke="#C9E2DE",
                sw=0.5,
            )
        )
    out += [pic("window", 10, 6, 34), rect(0, 60, W, 32, "#C9966A"), rect(0, 56, W, 6, "#F1E6D2")]
    for x in (6, 54, 102, 150):
        out += [rect(x, 66, 40, 22, "#D8A877", 1.5), circle(x + 17, 77, 1.1, "#8A6A3D")]
        out.append(circle(x + 23, 77, 1.1, "#8A6A3D"))
    out.append(rect(0, 92, W, 12, "#F3EBDD"))
    return "".join(out)


def _table_back(uid: str) -> str:
    out = [
        f"<defs>{vgrad(uid, 'wall', (0, '#FCEBD0'), (1, '#F8DDB6'))}</defs>",
        rect(0, 0, W, H, f"url(#{uid}-wall)"),
        rect(0, 52, W, 26, "#EBCBA0"),
        rect(0, 52, W, 1.6, "#D9AE7A"),
        pic("window", 6, 6, 34),
        path("M152 0 L152 13", stroke="#8A6A3D", sw=0.8),
        path("M141 13 L163 13 L158 24 L146 24 Z", "#F2B33D"),
        circle(152, 26, 14, "#FFE9A8", 0.28),
    ]
    return "".join(out)


def _table_front(uid: str) -> str:
    return rect(6, 82, 168, 6, "#FFFFFF") + rect(6, 88, 168, 16, "#FFF6E0") + rect(6, 96, 168, 3.2, "#E4675A")


def _bedroom(night: bool) -> Callable[[str], str]:
    def draw(uid: str) -> str:
        wall = ("#2E3A73", "#3F4C8A") if night else ("#FFF4DE", "#FBE6C2")
        out = [
            f"<defs>{vgrad(uid, 'wall', (0, wall[0]), (1, wall[1]))}</defs>",
            rect(0, 0, W, 82, f"url(#{uid}-wall)"),
            rect(0, 82, W, 22, "#8C6A4A" if night else "#D9AE7A"),
        ]
        sky = "#1A2456" if night else "#BFE3F6"
        out += [rect(18, 10, 44, 36, sky, 3), rect(18, 10, 44, 36, "none", 3)]
        if night:
            out += [crescent(32, 24, 7, "#FFE9A0", -30), sparkle(50, 18, 2.2, "#FFF3C4")]
            out += [sparkle(54, 34, 1.6, "#FFF3C4"), sparkle(26, 38, 1.4, "#FFF3C4")]
        else:
            out += [sun_disc(44, 26, 6), pic("cloud", 20, 26, 18)]
        out += [path("M18 28 L62 28 M40 10 L40 46", stroke="#FFFFFF", sw=1.4)]
        out += [rect(16, 8, 48, 40, "none", 3), path("M16 8 h48 v40 h-48 Z", stroke="#B07F52", sw=1.6)]
        out += [pic("bed", 104, 48, 70), pic("lamp", 82, 58, 20)]
        return "".join(out)

    return draw


def _garden(uid: str) -> str:
    defs = vgrad(uid, "sky", (0, "#BFE3F6"), (1, "#FFF1D6")) + vgrad(
        uid, "hill", (0, "#9FD18B"), (1, "#7DBB6A")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, W, 70, f"url(#{uid}-sky)"), sun_disc(26, 20, 8)]
    out += [pic("cloud", 54, 6, 28), pic("cloud", 120, 18, 22), birds((96, 14, 3), (104, 20, 2.4))]
    out += [
        path("M0 56 C30 44 60 60 100 50 C140 40 160 54 180 48 L180 104 L0 104 Z", f"url(#{uid}-hill)"),
        path("M0 82 C40 74 90 86 180 78 L180 104 L0 104 Z", "#8CC678"),
        pic("tree", 136, 26, 46),
        pic("flower", 8, 84, 12),
        pic("flower", 24, 88, 10),
    ]
    return "".join(out)


def _night_sky(uid: str) -> str:
    out = [
        f"<defs>{vgrad(uid, 'sky', (0, '#121A45'), (1, '#33458F'))}</defs>",
        rect(0, 0, W, H, f"url(#{uid}-sky)"),
    ]
    out.append(crescent(140, 22, 10, "#FFE9A0", -30))
    for x, y, r in ((20, 14, 2.4), (44, 30, 1.6), (70, 12, 2), (96, 34, 1.4), (112, 10, 1.8), (164, 46, 1.6)):
        out.append(sparkle(x, y, r, "#FFF3C4"))
    out += [
        path("M0 78 C30 66 60 80 100 70 C140 60 160 74 180 68 L180 104 L0 104 Z", "#1B2A5C"),
        path("M0 90 C50 82 110 94 180 86 L180 104 L0 104 Z", "#22356E"),
        pic("palm", 6, 50, 40),
    ]
    return "".join(out)


def _mosque(uid: str) -> str:
    """Outside a mosque: a dome with a crescent finial, a minaret, arched doors and windows; no writing."""
    defs = vgrad(uid, "sky", (0, "#BFE3F6"), (1, "#FFF1D6"))
    stone, deep = "#F4E6C8", "#D9C29A"
    out = [f"<defs>{defs}</defs>", rect(0, 0, W, 82, f"url(#{uid}-sky)"), sun_disc(24, 18, 7)]
    out += [pic("cloud", 46, 8, 24), birds((70, 22, 2.6))]
    # the minaret
    out += [rect(152, 18, 12, 64, stone), rect(150, 34, 16, 3, deep), rect(150, 54, 16, 3, deep)]
    out += [path("M150 18 Q158 4 166 18 Z", "#1F7A5A"), crescent(158, 3.5, 2.6, "#C9962B", 0)]
    out.append(path("M155 26 q3 -4 6 0 v6 h-6 Z", "#8A6A3D"))
    # the prayer hall and its dome
    out += [rect(84, 50, 66, 32, stone), rect(84, 50, 66, 2.4, deep)]
    out += [path("M94 50 Q117 14 140 50 Z", "#1F7A5A"), rect(115.5, 18, 3, 7, "#C9962B")]
    out.append(crescent(117, 15, 3, "#C9962B", 0))
    out.append(path("M110 82 L110 68 Q117 58 124 68 L124 82 Z", "#8A6A3D"))
    for x in (92, 134):
        out.append(path(f"M{x} 74 L{x} 64 Q{x + 4} 58 {x + 8} 64 L{x + 8} 74 Z", "#5B8FA8"))
    # the courtyard
    out += [rect(0, 82, W, 22, "#E9D9B6"), rect(0, 82, W, 1.4, "#CDB48A")]
    out += [path(f"M{x} 82 L{x - 8} 104", stroke="#D9C29A", sw=0.6) for x in range(20, 190, 22)]
    out.append(pic("palm", 8, 40, 46))
    return "".join(out)


def _mosque_inside(uid: str) -> str:
    """The prayer hall: arches, hanging lanterns, a plain mihrab niche and the carpet's rows; no writing."""
    from qamra_workbook.pictures.islamic import glyph_svg

    out = [rect(0, 0, W, 76, "#F7EBD3")]
    for x in range(0, int(W), 36):  # arches along the back wall
        out.append(
            path(f"M{x + 4} 76 L{x + 4} 34 Q{x + 18} 14 {x + 32} 34 L{x + 32} 76", "#EFDDB8", "#D9C29A", 0.8)
        )
    out.append(path("M76 76 L76 30 Q90 10 104 30 L104 76 Z", "#E3CB9C", "#C9962B", 1.2))  # the mihrab
    out.append(path("M82 76 L82 34 Q90 22 98 34 L98 76 Z", "#D9BC86"))
    for x in (30, 150):  # lanterns on chains
        out.append(path(f"M{x} 0 L{x} 12", stroke="#8A6A3D", sw=0.6))
        out.append(
            f'<g transform="translate({x - 6} 11) scale(0.5)">{glyph_svg("lantern", "#C9962B", 2.2)}</g>'
        )
        out.append(circle(x, 18, 9, "#FFE9A8", 0.25))
    out += [rect(0, 76, W, 28, "#2E7D6B")]
    for y in (82, 90, 98):  # the rows of the carpet
        out.append(rect(0, y, W, 1.2, "#C9962B", opacity=0.7))
    return "".join(out)


def _classroom(uid: str) -> str:
    out = [rect(0, 0, W, 80, "#E8F1FA"), rect(0, 80, W, 24, "#C9A47A"), rect(0, 79, W, 1.6, "#A9845A")]
    out += [rect(54, 10, 72, 40, "#3E6B4D", 2), rect(52, 8, 76, 44, "none", 3)]
    out.append(path("M52 8 h76 v44 h-76 Z", stroke="#B07F52", sw=2))
    out += [rect(140, 30, 34, 4, "#B07F52"), pic("book", 142, 16, 14), pic("crayons", 158, 18, 13)]
    out += [pic("clock", 10, 10, 18), pic("pot-plant", 8, 62, 20)]
    return "".join(out)


def _street(uid: str) -> str:
    defs = vgrad(uid, "sky", (0, "#BFE3F6"), (1, "#FFF1D6"))
    out = [f"<defs>{defs}</defs>", rect(0, 0, W, 76, f"url(#{uid}-sky)"), sun_disc(160, 16, 7)]
    out += [
        pic("cloud", 30, 6, 26),
        pic("house", 2, 26, 54),
        pic("house", 52, 30, 48),
        pic("tree", 104, 30, 46),
    ]
    out += [pic("house", 138, 28, 50), rect(0, 76, W, 28, "#D7D2C8"), rect(0, 76, W, 3, "#B9B2A4")]
    out += [rect(x, 89, 14, 2, "#FFFFFF") for x in range(6, int(W), 30)]
    return "".join(out)


def _market(uid: str) -> str:
    defs = vgrad(uid, "sky", (0, "#BFE3F6"), (1, "#FFF1D6"))
    out = [f"<defs>{defs}</defs>", rect(0, 0, W, 78, f"url(#{uid}-sky)"), sun_disc(24, 16, 7)]
    out += [pic("stall", 4, 22, 60), pic("stall", 116, 22, 60), rect(0, 78, W, 26, "#E9D9B6")]
    out += [path(f"M{x} 78 L{x - 6} 104", stroke="#D9C29A", sw=0.6) for x in range(14, 190, 20)]
    return "".join(out)


def _sea(uid: str) -> str:
    defs = vgrad(uid, "sky", (0, "#9FD3F0"), (1, "#E8F6FC")) + vgrad(
        uid, "sea", (0, "#3E9AC8"), (1, "#2A6E9E")
    )
    out = [f"<defs>{defs}</defs>", rect(0, 0, W, 60, f"url(#{uid}-sky)"), sun_disc(150, 18, 7)]
    out += [pic("cloud", 30, 8, 26), birds((80, 18, 3), (90, 24, 2.4))]
    out.append(path(wave(56, 2.2, 30, W, 86), f"url(#{uid}-sea)"))
    out.append(path(wave(66, 1.6, 22, W, 86, 8), "#5BB0D8", opacity=0.5))
    out.append(path("M0 84 C40 78 120 90 180 82 L180 104 L0 104 Z", "#F1DDB0"))
    return "".join(out)


def _desert(uid: str) -> str:
    defs = vgrad(uid, "sky", (0, "#FBD9A0"), (1, "#FFF3DC"))
    out = [f"<defs>{defs}</defs>", rect(0, 0, W, 70, f"url(#{uid}-sky)"), sun_disc(30, 20, 9)]
    out += [
        path("M0 60 C30 48 60 62 96 54 C130 46 156 58 180 52 L180 104 L0 104 Z", "#E9C27F"),
        path("M0 78 C40 68 100 84 180 74 L180 104 L0 104 Z", "#DDAE63"),
        pic("palm", 132, 28, 44),
        pic("palm", 150, 38, 34),
    ]
    return "".join(out)


BACKDROPS: dict[str, Backdrop] = {
    b.name: b
    for b in (
        Backdrop(
            "home",
            _home,
            spots=((46, 66, 26), (160, 72, 18), (8, 72, 22), (130, 74, 16), (52, 30, 18), (176, 80, 14)),
            note="the living room: a window, a lamp, a rug",
        ),
        Backdrop(
            "kitchen",
            _kitchen,
            floor=101,
            spots=((60, 40, 18), (84, 42, 16), (106, 40, 18), (128, 42, 16), (150, 40, 18), (40, 44, 14)),
            note="the kitchen: tiles, the counter (props stand on it)",
        ),
        Backdrop(
            "table",
            _table_back,
            front=_table_front,
            floor=112,
            figure_h=76,
            people_x=(30.0, 70.0, 110.0, 150.0),
            spots=((24, 73, 16), (60, 73, 16), (96, 72, 18), (132, 73, 16), (150, 72, 16), (6, 70, 18)),
            note="the family table: the cast sit behind it, props stand on it",
        ),
        Backdrop(
            "bedroom-night",
            _bedroom(True),
            spots=((70, 76, 14), (8, 80, 18), (40, 82, 16), (150, 24, 16)),
            people_x=(46.0, 70.0, 94.0, 160.0),
            note="a bedroom at night: the window shows the crescent and stars",
        ),
        Backdrop(
            "bedroom-morning",
            _bedroom(False),
            spots=((70, 76, 14), (8, 80, 18), (40, 82, 16), (150, 24, 16)),
            people_x=(46.0, 70.0, 94.0, 160.0),
            note="a bedroom in the morning: the sun in the window",
        ),
        Backdrop(
            "garden",
            _garden,
            spots=((20, 70, 18), (100, 74, 16), (60, 62, 14), (160, 80, 16), (2, 52, 18), (82, 50, 12)),
            people_x=(52.0, 80.0, 108.0, 130.0),
            note="sky, sun, hills, a tree, flowers",
        ),
        Backdrop(
            "night-sky",
            _night_sky,
            spots=((60, 80, 14), (150, 80, 16), (40, 84, 12), (100, 84, 12)),
            note="a night sky with the crescent and stars over the hills",
        ),
        Backdrop(
            "mosque",
            _mosque,
            spots=((56, 76, 16), (36, 80, 14), (166, 82, 12), (70, 82, 12)),
            people_x=(40.0, 62.0, 84.0, 168.0),
            note="outside the mosque: dome, minaret, courtyard",
        ),
        Backdrop(
            "mosque-inside",
            _mosque_inside,
            spots=((20, 80, 14), (150, 80, 14), (40, 84, 12), (130, 84, 12)),
            people_x=(30.0, 54.0, 126.0, 150.0),
            note="the prayer hall: arches, lanterns, a plain mihrab, the carpet's rows",
        ),
        Backdrop(
            "classroom",
            _classroom,
            spots=((60, 30, 16), (80, 28, 16), (100, 30, 16), (34, 74, 18), (150, 76, 16)),
            note="the kindergarten class: a blank board, shelves",
        ),
        Backdrop(
            "street",
            _street,
            spots=((96, 78, 16), (20, 82, 14), (160, 80, 14)),
            note="the neighbourhood: houses, a tree, the road",
        ),
        Backdrop(
            "market",
            _market,
            spots=((14, 50, 14), (34, 52, 12), (126, 50, 14), (146, 52, 12), (76, 82, 14), (100, 84, 12)),
            people_x=(70.0, 94.0, 118.0, 46.0),
            note="the market: two stalls",
        ),
        Backdrop(
            "sea",
            _sea,
            spots=((20, 84, 14), (150, 84, 14), (60, 62, 18), (110, 66, 14)),
            note="the sea and the beach",
        ),
        Backdrop(
            "desert",
            _desert,
            spots=((20, 78, 16), (60, 80, 14), (100, 82, 12)),
            note="dunes and palms",
        ),
    )
}
HEIGHTS = {"huda": 1.0, "reem": 0.86, "salem": 0.74, "reader": 0.9, "naanaa": 0.36}


def composed_problems(
    backdrop: str, props: Sequence[str], figures: Sequence[str], *, people: bool
) -> list[str]:
    """What is wrong with a composed scene: an unknown backdrop or prop, a person among the props, too many
    things, or (`people=False`: a prophet's or a sira page) any figure or body part at all."""
    out: list[str] = []
    back = BACKDROPS.get(backdrop)
    if back is None:
        return [f"no backdrop {backdrop!r} (have: {', '.join(sorted(BACKDROPS))})"]
    if len(props) > len(back.spots):
        out.append(f"backdrop {backdrop!r} holds {len(back.spots)} props, not {len(props)}")
    for prop in props:
        if not prop_known(prop):
            out.append(f"no picture {prop!r} in the library (or isl:<icon>)")
        elif prop in PERSON_PICTURES:
            out.append(f"{prop!r} draws a person: people appear only as the recurring characters")
        elif not people and prop in BODY_PICTURES:
            out.append(f"{prop!r} draws a body part, and this page shows no person at all")
    if not people and figures:
        out.append(f"figures {list(figures)} on a page that shows no person (a prophet's or a sira story)")
    return out


def compose(backdrop: str, props: Sequence[str], figures: Sequence[str], uid: str, kit: Kit | None) -> str:
    """The composed scene's SVG elements in the 180 × 104 box."""
    back = BACKDROPS[backdrop]
    out = [back.back(uid)]
    things = list(zip(props, back.spots, strict=False))
    for i, (prop, (x, y, size)) in enumerate(things):
        out.append(prop_svg(prop, x, y, size, i))
    if figures and kit is None:
        raise ValueError(f"backdrop {backdrop!r} with figures needs a kit")
    fit = min(1.0, (back.floor - HEAD_ROOM_TOP) / back.figure_h)  # every head inside the widest box
    for who, x in zip(figures, back.people_x, strict=False):
        assert kit is not None
        out.append(kit.figure(who, x, back.floor, back.figure_h * fit * HEIGHTS.get(who, 0.85)))
    if back.front is not None:
        out.append(back.front(uid))
    return "".join(out)


def composed_svg(
    backdrop: str,
    props: Sequence[str],
    figures: Sequence[str],
    uid: str,
    kit: Kit | None,
    css_class: str = "scene",
    fit: str = "slice",
) -> Markup:
    align = "xMidYMax" if figures else "xMidYMid"
    return Markup(  # nosec B704 (static art; ids and names are checked against the registries)
        f'<svg class="{css_class}" viewBox="0 0 {W:g} {H:g}" preserveAspectRatio="{align} {fit}" '
        f'aria-hidden="true">{compose(backdrop, props, figures, uid, kit)}</svg>'
    )
