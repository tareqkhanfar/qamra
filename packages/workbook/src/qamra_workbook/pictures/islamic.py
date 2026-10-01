"""«قلبي يعرف الله» (Addendum 10): programmatic art for the series: the unit icons (`UNIT_GLYPHS`), the
motif strips
that give each unit its small repeating identity, the body-part cards of the wudu pages, the ornaments of the
dignified verse frame, and the scenes (`SCENES`, in `islamic_scenes`).

Rules (Addendum 10 §3.5): nothing here depicts Allah, a prophet, an angel or a Companion: no face, figure,
silhouette or symbolic stand-in, and no divine light rays from above. A sun is a disc with a soft halo,
never beams
falling on a scene. The scenes that do contain people (the family at the table, the broken cup) say so
(`Scene.figures`), and the no-depiction check refuses them on a prophet page.
"""

from __future__ import annotations

import math

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.islamic_icons import FALLBACK_ICON, UNIT_GLYPHS
from qamra_workbook.pictures.islamic_scenes import BLESSING_SPOTS, SCENES, Kit, Scene, scene_svg
from qamra_workbook.pictures.model import OUTLINE, body, ink, line

__all__ = [
    "BLESSING_SPOTS",
    "SCENES",
    "UNIT_GLYPHS",
    "WUDU_ICONS",
    "Kit",
    "Scene",
    "body_icon",
    "glyph_svg",
    "motif_strip",
    "ribbon_svg",
    "scene_svg",
    "star8_svg",
    "unit_glyph",
]

# glyphs that only the motif strips use (the unit icons are in `islamic_icons`)
STRIP_GLYPHS: dict[str, str] = {
    "leaf": "M4 19 C4 10 10 4.5 20 4 C20 13 14 19.5 4 19 Z M4 19 L15 8.5",
    "date": (
        "M12 3.5 C17 3.5 19 9 19 13.5 C19 18.5 15.5 21 12 21 C8.5 21 5 18.5 5 13.5 C5 9 7 3.5 12 3.5 "
        "Z M12 6 L12 19"
    ),
    "heart": (
        "M12 20.5 C7 16.8 3.6 13.6 3.6 9.6 C3.6 6.6 5.8 4.8 8.2 4.8 C9.9 4.8 11.2 5.8 12 7.2 "
        "C12.8 5.8 14.1 4.8 15.8 4.8 C18.2 4.8 20.4 6.6 20.4 9.6 C20.4 13.6 17 16.8 12 20.5 Z"
    ),
    "cloud": (
        "M6.4 18 C3 18 2 14.8 4 12.8 C3.4 9.6 6.8 7.6 9.4 9 C10.4 5.8 15.6 5.6 16.8 9 C20 8.6 21.8 "
        "12.2 20 14.8 C21 16.8 19.6 18 17.6 18 Z"
    ),
    "wave": "M0 12 C4 6.5 8 6.5 12 12 C16 17.5 20 17.5 24 12",
    "dune": "M0 17 C3 17 5 9 9 9 C13 9 14 17 18 17 C21 17 22 14 24 13",
    "dot": "•M12 12 m-1.9 0 a1.9 1.9 0 1 0 3.8 0 a1.9 1.9 0 1 0 -3.8 0",
}
# motif name (units.yaml `motif`) → what repeats along the strip: glyph names, in turn
MOTIFS: dict[str, tuple[str, ...]] = {
    "stars": ("star", "dot"),
    "sun-and-dates": ("sun", "date"),
    "palm-leaves": ("leaf", "dot"),
    "footprint-trail": ("footprints", "dot"),
    "columns": ("five-columns", "dot"),
    "sun-moon-arc": ("sun", "crescent"),
    "bead-string": ("beads",),
    "tulips": ("tulip", "dot"),
    "mosque-skyline": ("dome", "dot"),
    "drops": ("water-drop", "dot"),
    "mat-pattern": ("prayer-mat", "dot"),
    "open-book": ("book-stand", "dot"),
    "bookmarks": ("ribbon", "dot"),
    "hearts": ("heart", "dot"),
    "clouds": ("cloud", "dot"),
    "keys": ("key", "dot"),
    "coins": ("coin-heart", "dot"),
    "crescents": ("crescent", "dot"),
    "sand-dunes": ("dune",),
    "book-stack": ("books", "dot"),
    "leaves": ("leaf", "dot"),
    "waves": ("wave",),
    "wheat": ("wheat", "dot"),
    "scales": ("scales", "dot"),
    "dots": ("dot",),
    "lanterns": ("lantern", "dot"),
    "balloons": ("balloon", "dot"),
}
CONTINUOUS = frozenset({"wave", "dune"})  # tiles that join into one line


def unit_glyph(icon: str) -> str:
    """The unit icon's glyph name, or the rosette while the icon is not drawn."""
    return icon if icon in UNIT_GLYPHS else FALLBACK_ICON


def glyph_svg(name: str, color: str = "currentColor", stroke: float = 1.9) -> str:
    """A 24 × 24 glyph's paths (a unit icon or a strip glyph)."""
    source = UNIT_GLYPHS.get(name) or STRIP_GLYPHS[name]
    lines, _, filled = source.partition("•")
    parts = []
    if lines.strip():
        parts.append(
            f'<path d="{lines.strip()}" fill="none" stroke="{color}" stroke-width="{stroke}" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )
    if filled.strip():
        parts.append(f'<path d="{filled.strip()}" fill="{color}"/>')
    return "".join(parts)


def motif_strip(motif: str, color: str, width: float, height: float, opacity: float = 0.9) -> Markup:
    """The unit's motif repeating along a strip `width` × `height` mm (an SVG in millimetres)."""
    names = MOTIFS.get(motif, MOTIFS["dots"])
    size = height * 0.74
    k = size / 24
    body_parts: list[str] = []
    if names[0] in CONTINUOUS:
        tiles = max(1, round(width / (size * 1.35)))
        step = width / tiles
        for i in range(tiles):
            body_parts.append(
                f'<g transform="translate({i * step:.2f} '
                f'{(height - size) / 2:.2f}) scale({step / 24:.4f} {k:.4f})">'
                f"{glyph_svg(names[0], color, 1.9 / k * 0.45)}</g>"
            )
    else:
        pitch = size * 1.6
        count = max(1, int(width // pitch))
        x0 = (width - (count - 1) * pitch) / 2
        for i in range(count):
            name = names[i % len(names)]
            small = name == "dot"
            s = k * (0.55 if small else 1.0)
            x, y = x0 + i * pitch - 12 * s, height / 2 - 12 * s
            body_parts.append(
                f'<g transform="translate({x:.2f} {y:.2f}) scale({s:.4f})">{glyph_svg(name, color, 1.9)}</g>'
            )
    return Markup(  # nosec B704 (static art)
        f'<svg viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" height="{height:.2f}mm" '
        f'aria-hidden="true" opacity="{opacity}">{"".join(body_parts)}</svg>'
    )


def ribbon_svg(motif: str, color: str, ink: str, width: float, height: float = 12.0) -> Markup:
    """The unit's ribbon across the top of a page: its colour, a scalloped lower edge and its motif in
    `ink`.
    """
    band = height - 3.4
    scallops = "".join(f'<circle cx="{x:.2f}" cy="{band:.2f}" r="3.4"/>' for x in _spaced(width, 6.8))
    strip = motif_strip(motif, ink, width - 8, band - 1.2, 0.92)
    return Markup(  # nosec B704 (static art)
        f'<svg viewBox="0 0 {width:.2f} {height:.2f}" preserveAspectRatio="none" aria-hidden="true">'
        f'<g fill="{color}"><rect x="0" y="0" width="{width:.2f}" height="{band:.2f}"/>{scallops}</g>'
        f'<g transform="translate(4 0.6)">{strip.replace("<svg ", '<svg overflow="visible" ')}</g></svg>'
    )


def _spaced(width: float, step: float) -> list[float]:
    count = int(width // step) + 1
    first = (width - (count - 1) * step) / 2
    return [first + i * step for i in range(count)]


def star8_svg(color: str, size: float = 10.0, inner: str = "#FFFFFF") -> Markup:
    """An eight-pointed star (two squares), the ornament of the verse frame's corners and the ayah markers."""
    pts = []
    for i in range(16):
        r = 1.0 if i % 2 == 0 else 0.62
        a = math.radians(-90 + 22.5 * i)
        pts.append(f"{50 + 46 * r * math.cos(a):.2f},{50 + 46 * r * math.sin(a):.2f}")
    return Markup(  # nosec B704 (static art)
        f'<svg viewBox="0 0 100 100" width="{size}mm" height="{size}mm" aria-hidden="true">'
        f'<polygon points="{" ".join(pts)}" fill="{color}"/><circle '
        f'cx="50" cy="50" r="22" fill="{inner}"/></svg>'
    )


# ---- the wudu cards: a body part with a little water (never a person)
# ---------------------------------------


def _nested(pic_id: str, x: float, y: float, size: float) -> str:
    return (
        f'<svg x="{x}" y="{y}" width="{size}" height="{size}" '
        f'viewBox="0 0 100 100">{picture(pic_id).inner("color")}</svg>'
    )


def _drops(*spots: tuple[float, float, float]) -> str:
    return "".join(_nested("raindrop", x, y, s) for x, y, s in spots)


def _forearm() -> str:
    """A forearm from the elbow (bottom left) to the hand (top right): the arms are washed up to the
    elbows.
    """
    skin = "#F4C9A6"
    arm = body(skin, '<path d="M16 76 L58 34 L72 48 L30 90 Z"/>')
    elbow = line('<path d="M18 74 C24 70 28 76 32 88" />')
    cuff = line('<path d="M62 38 L76 52"/>')
    hand = body(
        skin,
        (
            '<path d="M60 36 L68 16 C70 12 75 13 74 18 L74 28 L80 12 C82 8 87 10 85 15 L81 32 L90 22 C93 19 '
            '97 22 94 26 L84 42 L76 52 Z"/>'
        ),
    )
    return "".join(part_svg(p) for p in (arm, hand, elbow, cuff))


def part_svg(part: object) -> str:
    """One `Part` of the picture model as an outlined SVG group (same painting as `Picture.inner`)."""
    from qamra_workbook.pictures.model import Picture

    return Picture("x", "", "", "", (part,)).inner("color")  # type: ignore[arg-type]


def _bubble() -> str:
    pane = body(
        "#FFF4D6",
        (
            '<path d="M14 24 C14 15 20 10 30 10 L70 10 C80 10 86 15 86 24 L86 50 C86 59 80 64 70 64 L46 64 '
            'L30 82 L32 64 L30 64 C20 64 14 59 14 50 Z"/>'
        ),
    )
    dots = ink(
        '<circle cx="34" cy="37" r="5"/><circle cx="50" cy="37" r="5"/><circle cx="66" cy="37" r="5"/>'
    )
    return part_svg(pane) + part_svg(dots)


WUDU_ICONS: dict[str, str] = {
    "speech-bubble": _bubble() + _drops((62, 56, 30)),
    "hands": _nested("faucet", 2, 2, 58) + _nested("hand", 28, 34, 66) + _drops((66, 6, 18), (78, 22, 15)),
    "mouth": _nested("mouth", 8, 24, 84) + _drops((12, 4, 22), (70, 2, 20)),
    "nose": _nested("nose", 12, 12, 76) + _drops((70, 8, 22), (4, 60, 18)),
    "face": _nested("face", 10, 14, 80) + _drops((4, 2, 22), (74, 2, 22)),
    "arms": _forearm() + _drops((2, 8, 22), (30, 4, 18)),
    "head": _nested("head", 10, 20, 80) + _drops((6, 2, 20), (72, 4, 22)),
    "feet": _nested("foot", 4, 12, 62) + _nested("foot", 38, 22, 58) + _drops((70, 2, 22)),
}


def body_icon(name: str, css_class: str = "wudu-art") -> Markup:
    """A wudu card's picture: a body part with water, in the library's outlined style."""
    return Markup(  # nosec B704 (static art)
        f'<svg class="{css_class}" viewBox="0 0 100 100" '
        f'aria-hidden="true" stroke="{OUTLINE}">{WUDU_ICONS[name]}</svg>'
    )
