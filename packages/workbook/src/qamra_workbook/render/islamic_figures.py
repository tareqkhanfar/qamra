"""The cast of «قلبي يعرف الله» on a page (Addendum 10 §4.6, §8): the recurring characters, drawn the same
on every
page from `render.people` (huda the storytelling grandmother in a headscarf, reem the big sister, salem the
little
brother), and the reader: the child's character cut out of the character sheet. None of them is a prophet,
an angel or a Companion, and the narrator panel is the only place a
prophet's story shows them.
"""

from __future__ import annotations

from pathlib import Path

from qamra_workbook.render import draw, people
from qamra_workbook.render.character import aspect, front_view
from qamra_workbook.render.spec import Figure

# who → (the figure's kind in `people`, outfit, headscarf). Reem wears a light scarf only for prayer scenes.
CAST: dict[str, tuple[Figure, str, str | None]] = {
    "huda": ("grandma", "#8E7CC3", "#C9B5E8"),
    "reem": ("girl", "#E98AA6", None),
    "salem": ("boy", "#6E95DB", None),
}
EDGE = 0.9  # the white sticker edge round a figure, in the scene's own units


class Kit:
    """Who can stand in a scene: `figure(who, x, y_feet, height)` as SVG elements in the scene's units."""

    def __init__(self, character: Path | None = None, character_aspect: float = 0.47) -> None:
        self.character = character
        self.aspect = character_aspect

    def figure(self, who: str, x: float, y_feet: float, height: float) -> str:
        if who in CAST:
            kind, outfit, scarf = CAST[who]
            return people.place(people.person(kind, outfit, scarf=scarf), x, y_feet, height, EDGE)
        if who != "reader":
            raise KeyError(f"no character {who!r} in the cast (huda, reem, salem, reader)")
        path = self.character
        if path is None:
            return ""  # no character sheet yet: the scene is drawn without the reader
        width = height * self.aspect
        return draw.el(
            "image",
            href=path.resolve().as_uri(),
            x=x - width / 2,
            y=y_feet - height,
            width=width,
            height=height,
            preserveAspectRatio="xMidYMax meet",
        )


def kit_for(sheet: Path | None, out_dir: Path) -> Kit:
    """The cast with the reader taken from a character sheet (front view); without a sheet, the reader is
    left out."""
    if sheet is None:
        return Kit()
    cut = front_view(sheet, out_dir)
    return Kit(cut, aspect(cut))


SAMPLE_SHEET = Path(__file__).resolve().parents[5] / "content/workbook/samples/sample-character.png"


def sample_kit(out_dir: Path | None = None) -> Kit:
    """The cast with the sample child's character (an AI-drawn sample, never a real child)."""
    folder = out_dir or Path("/tmp/qamra-islamic-kit")
    return kit_for(SAMPLE_SHEET if SAMPLE_SHEET.is_file() else None, folder)


def listeners(kit: Kit, who: list[str], width: float = 64.0, height: float = 30.0) -> str:
    """The narrator panel's cast on a rug, as SVG elements in a `width` × `height` box: the grandmother a
    little
    taller than the children, all standing close together. Only the recurring characters appear here, never
    in the
    scenes of a prophet's story."""
    heights = {"huda": 0.98, "reem": 0.84, "salem": 0.72, "reader": 0.9}
    count = max(len(who), 1)
    step = (width - 14) / count
    parts = [
        f'<ellipse cx="{width / 2:.1f}" cy="{height - 1.2:.1f}" '
        f'rx="{width / 2 - 1:.1f}" ry="2.4" fill="#C98E64" opacity="0.55"/>'
    ]
    for i, name in enumerate(who):
        x = width - 7 - step * (i + 0.5)  # right to left, the first at the start of the line
        parts.append(kit.figure(name, x, height - 1.6, height * heights.get(name, 0.8)))
    return "".join(parts)
