"""«قلبي يعرف الله»: the series' things as they stand in a scene (a prayer mat laid on the floor, a
lantern, the stand with the mushaf, a sheaf of wheat, the Kaaba, prayer beads), drawn in colour in the picture
library's outlined style on a 100 × 100 box with their foot at the bottom. In a scene a series icon used to be
drawn on a white disc, and the prayer mat and the wheat floated over the floor like badges.

Nothing here depicts a person; the Kaaba is drawn with its kiswa, its gold band and its door, standing on the
white floor of the mataf, with nobody round it."""

from __future__ import annotations

import math

from qamra_workbook.pictures.model import OUTLINE

GOLD = "#C9962B"
GOLD_DEEP = "#A87A1E"


def _p(d: str, fill: str, stroke: str = OUTLINE, width: float = 2.2, extra: str = "") -> str:
    return (
        f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" '
        f'stroke-linecap="round"{extra}/>'
    )


def _line(d: str, stroke: str, width: float) -> str:
    return _p(d, "none", stroke, width)


def _shadow(cx: float, cy: float, rx: float) -> str:
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{rx * 0.16:.1f}" fill="#000000" opacity="0.13"/>'


def prayer_mat() -> str:
    """A prayer mat laid flat on the floor, seen from in front: its niche at the far end, a fringe at the near
    end."""
    out = [_p("M16 60 L84 60 L97 92 L3 92 Z", "#B23A48")]
    out.append(_line("M22 64 L78 64 L88 88 L12 88 Z", "#F2C14E", 2))
    out.append(_p("M37 80 L37 71 Q50 61 63 71 L63 80 Z", "#7A1F2B", "#F2C14E", 1.6))
    out.append(_line("M30 84 L70 84", "#F2C14E", 1.4))
    out += [_line(f"M{x} 92 L{x - 0.6} 97", "#F2C14E", 1.6) for x in range(8, 95, 6)]
    return "".join(out)


def lantern() -> str:
    """A Ramadan lantern standing on its base: a gold frame, warm glass, a small flame; no cross bars."""
    out = ['<circle cx="50" cy="52" r="36" fill="#FFE9A8" opacity="0.28"/>', _shadow(50, 95, 18)]
    out.append(_p("M50 4 a5 5 0 1 0 0.01 0", "none", GOLD_DEEP, 2.4))
    out.append(_p("M36 24 L64 24 L57 12 L43 12 Z", GOLD))
    out.append(_p("M36 24 C29 38 29 62 36 76 L64 76 C71 62 71 38 64 24 Z", "#FFE3A0"))
    out.append(_line("M45 24 C42 38 42 62 45 76 M55 24 C58 38 58 62 55 76", GOLD_DEEP, 2.2))
    out.append(_p("M50 39 C57 47 57 54 50 60 C43 54 43 47 50 39 Z", "#F28C28", "#D9622B", 1.4))
    out.append(_p("M38 76 L62 76 L59 85 L41 85 Z", GOLD))
    out.append(_p("M44 85 L56 85 L55 94 L45 94 Z", GOLD_DEEP))
    return "".join(out)


def book_stand() -> str:
    """The mushaf open on its wooden stand (a rahl): green covers, cream pages, no writing."""
    out = [_shadow(50, 94, 34)]
    out.append(_line("M24 93 L72 46", "#8A5A2B", 7))
    out.append(_line("M76 93 L28 46", "#A06A35", 7))
    out.append(_p("M12 50 Q31 39 50 49 Q69 39 88 50 L88 66 Q69 55 50 65 Q31 55 12 66 Z", "#2E7D5B"))
    out.append(_p("M16 48 Q33 39 50 47 L50 62 Q33 53 16 61 Z", "#FFF8E6", OUTLINE, 1.6))
    out.append(_p("M84 48 Q67 39 50 47 L50 62 Q67 53 84 61 Z", "#FFF8E6", OUTLINE, 1.6))
    return "".join(out)


def wheat() -> str:
    """A sheaf of wheat standing on the ground, tied with a band."""
    out = [_shadow(50, 95, 26)]
    stalks = (-26, -13, 0, 13, 26)
    for a in stalks:
        r = math.radians(a)
        x, y = 50 + 60 * math.sin(r), 92 - 62 * math.cos(r)
        out.append(_line(f"M50 92 L{x:.1f} {y:.1f}", "#B8862A", 2.6))
    for a in stalks:
        r = math.radians(a)
        for k in (0, 1, 2, 3):
            t = 50 + 9 * k
            x, y = 50 + t * math.sin(r), 92 - t * math.cos(r) - 6
            for side in (-1, 1):
                ex, ey = x + side * 3.4 * math.cos(r), y + side * 3.4 * math.sin(r)
                out.append(
                    f'<ellipse cx="{ex:.1f}" cy="{ey:.1f}" rx="3.2" ry="6" '
                    f'transform="rotate({a + side * 22} {ex:.1f} {ey:.1f})" fill="#E9B949" '
                    f'stroke="{OUTLINE}" stroke-width="1.2"/>'
                )
    out.append(_p("M40 66 L60 66 L60 74 L40 74 Z", "#8A5A2B"))
    return "".join(out)


def kaaba() -> str:
    """The Kaaba on the white floor of the mataf: the black kiswa, the gold band near the top, the gold door
    raised on its face, the low marble base; nobody round it."""
    out = ['<ellipse cx="50" cy="88" rx="48" ry="9" fill="#F1ECE2" stroke="#D8D0C0" stroke-width="1.2"/>']
    out.append(_p("M10 82 L48 92 L90 80 L90 84 L48 96 L10 86 Z", "#E3DCCD", OUTLINE, 1.4))
    out.append(_p("M12 30 L48 40 L48 90 L12 80 Z", "#26262A"))
    out.append(_p("M48 40 L88 28 L88 78 L48 90 Z", "#17171A"))
    out.append(_p("M12 30 L52 20 L88 28 L48 40 Z", "#34343A"))
    out.append(_p("M12 39 L48 49 L48 55 L12 45 Z", GOLD, GOLD_DEEP, 1))
    out.append(_p("M48 49 L88 37 L88 43 L48 55 Z", "#B8862A", GOLD_DEEP, 1))
    out.append(_p("M62 62 L76 58 L76 80 L62 84 Z", "#D4A93A", GOLD_DEEP, 1.2))
    out.append(_line("M69 60 L69 82", GOLD_DEEP, 1))
    return "".join(out)


def beads() -> str:
    """Prayer beads lying in a loop, with their tassel."""
    out = [_shadow(50, 90, 34)]
    for i in range(22):
        a = 2 * math.pi * i / 22
        x, y = 50 + 34 * math.cos(a), 66 + 18 * math.sin(a)
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6" fill="#8E5B3A" stroke="{OUTLINE}" stroke-width="1"/>'
        )
    out.append(_p("M50 84 L44 96 L56 96 Z", "#2E7D5B"))
    return "".join(out)


def kaaba_picture() -> str:
    """A framed picture of the Kaaba standing on a small side table: how a home shows it (the Kaaba itself
    never stands in a living room)."""
    out = [_shadow(50, 96, 30)]
    out.append(_p("M22 70 L78 70 L78 76 L22 76 Z", "#A06A35"))
    out.append(_line("M28 76 L28 95 M72 76 L72 95", "#7E4E26", 3))
    out.append(_p("M26 20 L74 20 L74 70 L26 70 Z", "#C98E57"))
    out.append(_p("M31 25 L69 25 L69 65 L31 65 Z", "#DCEBF5", OUTLINE, 1.2))
    out.append(f'<svg x="31" y="27" width="38" height="38" viewBox="0 0 100 100">{kaaba()}</svg>')
    return "".join(out)


# a series icon → the thing as it stands in a scene; the others stand as their library picture
OBJECTS = {
    "prayer-mat": prayer_mat,
    "lantern": lantern,
    "book-stand": book_stand,
    "wheat": wheat,
    "cube": kaaba,
    "beads": beads,
    "kaaba-picture": kaaba_picture,  # a scene-only thing (no unit icon of its own)
}
AS_PICTURE = {"gift": "gift", "palm": "palm", "crescent": "crescent", "water-drop": "water", "whale": "whale"}


def object_svg(name: str, x: float, y: float, size: float) -> str | None:
    """The thing `name` (a series icon's name) drawn in its scene box, or None when it has no scene
    drawing."""
    draw = OBJECTS.get(name)
    if draw is None:
        return None
    box = f'x="{x:.2f}" y="{y:.2f}" width="{size:.2f}" height="{size:.2f}"'
    return f'<svg {box} viewBox="0 0 100 100">{draw()}</svg>'
