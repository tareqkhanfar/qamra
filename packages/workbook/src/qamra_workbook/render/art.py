"""Page art that is not a vocabulary picture: line icons (sections, journey stops, labels), the Qamra moon
mascot and small decorations. All inline SVG, so everything prints sharp and needs no image files.
"""

from __future__ import annotations

from markupsafe import Markup

from qamra_workbook.pictures.model import OUTLINE

# 24 × 24 line icons, drawn with currentColor. `•` marks a part that is filled instead of stroked.
ICONS: dict[str, str] = {
    "flag": "M5 21 L5 3.5 M5 4 L17 4 L14.5 8 L17 12 L5 12",
    "brain": (
        "M8 19.2 C5.2 19.2 3.6 16.8 4.4 14.4 C2.8 13.1 2.8 10 4.9 8.9 C4.6 6.1 7.1 4.1 9.6 4.9 C10.8 3.3 "
        "13.4 3.3 14.6 4.7 C16.9 3.9 19.4 5.5 19.2 7.9 C21.2 8.9 21.6 11.8 20.1 13.4 C20.9 15.7 19.3 18.1"
        " 16.9 18.1 C16.1 19.7 13.9 20.3 12.5 19.2 C11.3 20.1 9.3 20.2 8 19.2 Z M12.3 5 C11.4 6.6 12.6 "
        "8.2 11.6 9.8 M8.1 9.2 C9.6 9.6 10.4 11.1 9.8 12.7 M16 8.7 C14.6 9.6 14.4 11.2 15.4 12.4 M12.4 "
        "13.2 C11.9 14.8 12.9 16.6 12.5 19.2 M7.6 15.2 C8.8 15 10 15.6 10.4 16.8 M17.1 14.6 C15.9 14.3 "
        "14.9 15.1 14.7 16.3"
    ),
    "eye": "M2.5 12 C5.5 6.5 18.5 6.5 21.5 12 C18.5 17.5 5.5 17.5 2.5 12 Z •M12 9 A3 3 0 1 0 12.01 9 Z",
    "ear": (
        "M8 20 C9.6 20.6 11.1 19.6 11.6 18 C12.2 16.1 14 15.4 15.6 13.9 C18.2 11.5 18.1 6.1 13.6 4.6 C9.5"
        " 3.2 5.9 6 6 9.6 M9.2 9.6 C9.1 7.6 11.1 6.6 12.6 7.3 C14.1 8 14.2 10.1 12.9 11.1 C12.1 11.8 12 "
        "13 13 13.6"
    ),
    "hand": (
        "M8 12.5 L8 6 A1.5 1.5 0 0 1 11 6 L11 11 M11 10.5 L11 4.5 A1.5 1.5 0 0 1 14 4.5 L14 11 M14 10.5 "
        "L14 6 A1.5 1.5 0 0 1 17 6 L17 13.5 C17 18 15 21 11.6 21 C8.6 21 7.1 19.6 5.6 17.2 L3.9 13.9 A1.4"
        " 1.4 0 0 1 6.3 12.5 L8 14.5"
    ),
    "pencil": "M4 20 L5 15.5 L16 4.5 A2.1 2.1 0 0 1 19.5 8 L8.5 19 Z M14 6.5 L17.5 10 M4 20 L8.5 19",
    "trace": (
        "•M4.2 17.0 A2.2 2.2 0 1 0 4.21 17.0 Z M8.6 14.25 A1.35 1.35 0 1 0 8.61 14.25 Z M11.6 10.05 A1.35"
        " 1.35 0 1 0 11.61 10.05 Z M15.2 7.25 A1.35 1.35 0 1 0 15.21 7.25 Z M19.2 6.85 A1.35 1.35 0 1 0 "
        "19.21 6.85 Z"
    ),
    "write": "M3 21 L21 21 M7 17 L8 13.5 L16.2 5.3 A1.8 1.8 0 0 1 18.7 7.8 L10.5 16 Z",
    "book": (
        "M12 6.6 C10 5 7 4.6 3.5 5 L3.5 18.6 C7 18.1 10 18.6 12 20.1 C14 18.6 17 18.1 20.5 18.6 L20.5 5 "
        "C17 4.6 14 5 12 6.6 Z M12 6.6 L12 20.1"
    ),
    "rainbow": "M2.5 18 A9.5 9.5 0 0 1 21.5 18 M6 18 A6 6 0 0 1 18 18 M9.5 18 A2.5 2.5 0 0 1 14.5 18",
    "puzzle": (
        "M4.5 8.5 L8.5 8.5 C8.3 6.4 9.2 5 11 5 C12.8 5 13.7 6.4 13.5 8.5 L17.5 8.5 L17.5 12.2 C19.6 12 21"
        " 12.9 21 14.7 C21 16.5 19.6 17.4 17.5 17.2 L17.5 20.5 L4.5 20.5 Z"
    ),
    "star": (
        "M12 3 L14.6 8.6 L20.6 9.3 L16.1 13.4 L17.4 19.4 L12 16.3 L6.6 19.4 L7.9 13.4 L3.4 9.3 L9.4 8.6 Z"
    ),
    "heart": (
        "M12 20 C7 16.5 3.5 13.5 3.5 9.5 C3.5 6.7 5.6 4.8 8 4.8 C9.8 4.8 11.1 5.8 12 7.2 C12.9 5.8 14.2 4.8 "
        "16 4.8 C18.4 4.8 20.5 6.7 20.5 9.5 C20.5 13.5 17 16.5 12 20 Z"
    ),
    "crayon": "M6.5 14 L15.5 5 L19.5 9 L10.5 18 Z M6.5 14 L4 20.5 L10.5 18 M13.2 7.3 L17.2 11.3",
    "shapes": "M11.5 7.5 A4 4 0 1 0 11.49 7.5 Z M16.5 3.5 L21 11 L12 11 Z M4 14 L11 14 L11 21 L4 21 Z",
    "pattern": "M5 9.2 A2.8 2.8 0 1 0 5.01 9.2 Z M12 9 L15 15 L9 15 Z M19 9.2 A2.8 2.8 0 1 0 19.01 9.2 Z",
    "abacus": (
        "M3.5 4 L20.5 4 L20.5 20 L3.5 20 Z M3.5 9.3 L20.5 9.3 M3.5 14.7 L20.5 14.7 •M7.5 7.8 A1.6 1.6 0 1"
        " 0 7.51 7.8 Z M11 7.8 A1.6 1.6 0 1 0 11.01 7.8 Z M7.5 13.2 A1.6 1.6 0 1 0 7.51 13.2 Z M11 13.2 "
        "A1.6 1.6 0 1 0 11.01 13.2 Z M14.5 13.2 A1.6 1.6 0 1 0 14.51 13.2 Z"
    ),
    "letter-ba": (
        "M19.5 7.5 C19.8 10.8 20 13.6 18 14.8 C16.5 15.7 14.5 15.8 11.5 15.8 L8 15.8 C5.6 15.8 4.2 14.6 "
        "3.9 10.8 •M12 18.2 A1.6 1.6 0 1 0 12.01 18.2 Z"
    ),
    "letter-a": "M6 20 L12 4 L18 20 M8.6 14 L15.4 14",
    "speaker": (
        "M4 9 L8 9 L13 5 L13 19 L8 15 L4 15 Z M16.5 9 C18 10.5 18 13.5 16.5 15 M19 6.5 C22 9.5 22 14.5 19"
        " 17.5"
    ),
    "cap": "M2 9 L12 4.5 L22 9 L12 13.5 Z M6 11 L6 16 C8 18.2 16 18.2 18 16 L18 11 M22 9 L22 15",
    "check": "M5 12.5 L10 17 L19 7",
    "cross": "M6.5 6.5 L17.5 17.5 M17.5 6.5 L6.5 17.5",
    "target": "M12 3 A9 9 0 1 0 12.01 3 Z M12 7 A5 5 0 1 0 12.01 7 Z •M12 10.4 A1.6 1.6 0 1 0 12.01 10.4 Z",
    "sticker": (
        "M5 4 L15 4 L20 9 L20 19 A1 1 0 0 1 19 20 L5 20 A1 1 0 0 1 4 19 L4 5 A1 1 0 0 1 5 4 Z M15 4 L15 9"
        " L20 9"
    ),
    "scan": (
        "M4 8 L4 5 A1 1 0 0 1 5 4 L8 4 M16 4 L19 4 A1 1 0 0 1 20 5 L20 8 M20 16 L20 19 A1 1 0 0 1 19 20 "
        "L16 20 M8 20 L5 20 A1 1 0 0 1 4 19 L4 16 M8 12 L16 12"
    ),
}


def glyph(name: str, color: str = "currentColor", stroke: float = 2.0) -> str:
    """The icon's paths (24 × 24 units), for drawing inside another SVG."""
    lines, _, filled = ICONS[name].partition("•")
    parts = []
    if lines.strip():
        parts.append(
            f'<path d="{lines.strip()}" fill="none" stroke="{color}" stroke-width="{stroke}" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )
    if filled.strip():
        parts.append(f'<path d="{filled.strip()}" fill="{color}"/>')
    return "".join(parts)


def icon(name: str, css_class: str = "ico", stroke: float = 2.0) -> Markup:
    return Markup(  # nosec B704 (static icon data)
        f'<svg class="{css_class}" viewBox="0 0 24 24" aria-hidden="true">{glyph(name, stroke=stroke)}</svg>'
    )


# The Qamra moon (logo crescent) as a friendly guide: opening to the right, face on its round side.
_MOON = "M64.69 12.79 A40 40 0 1 0 76.85 79.65 A34 34 0 0 1 64.69 12.79 Z"


def mascot(css_class: str = "mascot", flip: bool = False) -> Markup:
    turn = ' transform="translate(100 0) scale(-1 1)"' if flip else ""
    stroke = f'stroke="{OUTLINE}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"'
    return Markup(  # nosec B704 (static art)
        f'<svg class="{css_class}" viewBox="0 0 100 100" aria-hidden="true"><g{turn}>'
        f'<path d="M86 22 L88 28 L94 30 L88 32 L86 38 L84 32 L78 30 L84 28 Z" fill="#F2B33D" {stroke}/>'
        f'<path d="{_MOON}" fill="#F7C84A" {stroke}/>'
        '<path d="M22 30 C26 22 34 17 42 16" fill="none" stroke="#FFFFFF" stroke-width="4" '
        'stroke-linecap="round" opacity="0.6"/>'
        f'<ellipse cx="19.5" cy="50" rx="3.6" ry="4.3" fill="{OUTLINE}"/>'
        f'<ellipse cx="31" cy="49" rx="3.6" ry="4.3" fill="{OUTLINE}"/>'
        '<circle cx="20.8" cy="48.4" r="1.4" fill="#FFFFFF"/>'
        '<circle cx="32.3" cy="47.4" r="1.4" fill="#FFFFFF"/>'
        '<ellipse cx="14.5" cy="58" rx="4.4" ry="3" fill="#F08A7E" opacity="0.55"/>'
        '<ellipse cx="35" cy="57" rx="4" ry="2.8" fill="#F08A7E" opacity="0.55"/>'
        f'<path d="M20.5 58.5 Q25.5 63.5 30.5 58" fill="none" {stroke}/>'
        "</g></svg>"
    )
