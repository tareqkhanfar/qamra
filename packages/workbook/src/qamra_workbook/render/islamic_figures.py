"""The cast of «قلبي يعرف الله» on a page (Addendum 10 §4.6, §8): the recurring characters, drawn the same on
every page from `render.people` (huda the storytelling grandmother in a headscarf, reem the big sister, salem
the little brother), Naanaa the family's cat (the library's cat picture), and the reader: the child's
character cut out of the character sheet. None of them is a prophet, an angel or a Companion, and the narrator
panel is the only place a prophet's story shows them."""

from __future__ import annotations

import functools
import itertools
from dataclasses import dataclass
from pathlib import Path

import yaml

from qamra_workbook.pictures import get as picture
from qamra_workbook.render import draw, people
from qamra_workbook.render.character import aspect, front_view
from qamra_workbook.render.spec import Figure

# who → (the figure's kind in `people`, outfit, headscarf). The girls wear no headscarf (owner decision);
# the grandmother's is a cream scarf with its fall and hem over a sage coat, as in her character sheet (a
# lavender hood over a lavender dress read as hair).
CAST: dict[str, tuple[Figure, str, str | None]] = {
    "huda": ("grandma", "#6F9C7C", "#F3ECDF"),
    "reem": ("girl", "#E98AA6", None),
    "salem": ("boy", "#6E95DB", None),
}
EDGE = 0.9  # the white sticker edge round a figure, in the scene's own units
CAT = "naanaa"  # the family's cat: the library's cat picture, as big as a figure's `height`
PLAN_FILE = Path(__file__).resolve().parents[5] / "content/islamic/plan.yaml"


def cast_names() -> dict[str, str]:
    """Each character's name as printed (plan.yaml `characters`); the reader's is `{child}`."""
    rows = yaml.safe_load(PLAN_FILE.read_text(encoding="utf-8"))["characters"]
    return {str(r["id"]): str(r["ar"]) for r in rows}


class Kit:
    """Who can stand in a scene: `figure(who, x, y_feet, height)` as SVG elements in the scene's units."""

    def __init__(self, character: Path | None = None, character_aspect: float = 0.47) -> None:
        self.character = character
        self.aspect = character_aspect

    def figure(self, who: str, x: float, y_feet: float, height: float, barefoot: bool = False) -> str:
        """`barefoot`: in the prayer hall or on a prayer mat, shoes off (the reader's drawn shoes are cut off
        at the hem of its legs and bare feet drawn in the child's skin tone)."""
        if who in CAST:
            kind, outfit, scarf = CAST[who]
            drawing = people.person(kind, outfit, scarf=scarf, barefoot=barefoot, draped=True)
            return people.place(drawing, x, y_feet, height, EDGE)
        if who == CAT:
            inner = picture("cat").inner("color")
            return draw.el(
                "svg",
                inner,
                x=x - height / 2,
                y=y_feet - height,
                width=height,
                height=height,
                viewBox="0 0 100 100",
            )
        if who != "reader":
            raise KeyError(f"no character {who!r} in the cast (huda, reem, salem, naanaa, reader)")
        path = self.character
        if path is None:
            return ""  # no character sheet yet: the scene is drawn without the reader
        width = height * self.aspect
        image = draw.el(
            "image",
            href=path.resolve().as_uri(),
            x=x - width / 2,
            y=y_feet - height,
            width=width,
            height=height,
            preserveAspectRatio="xMidYMax meet",
        )
        feet = bare_feet(path) if barefoot else None
        if feet is None:
            return image
        return _barefoot_reader(image, feet, x - width / 2, y_feet - height, width, height)


@dataclass(frozen=True)
class Feet:
    """Where the reader's drawn shoes start (`hem`, a fraction of its height), its legs' centres and widths
    (fractions of its width) and its skin tone: what bare feet in their place need."""

    hem: float
    legs: tuple[tuple[float, float], ...]
    skin: str


@functools.lru_cache(maxsize=32)
def bare_feet(cut: Path) -> Feet | None:
    """The reader's feet as `Feet`, from the cut-out (None when its legs cannot be found: the reader is then
    drawn as it is). The shoes are the rows under the legs whose colour is not the legs' (trousers or
    skin)."""
    import numpy as np
    from PIL import Image

    with Image.open(cut) as img:
        a = np.asarray(img.convert("RGBA")).astype(np.float32)
    h, w = a.shape[:2]
    rgb, alpha = a[..., :3], a[..., 3]
    content = (alpha > 200) & (rgb.min(axis=2) < 232)  # the figure without its white sticker edge
    band = content[int(h * 0.78) : int(h * 0.84)]
    if band.sum() < 50:
        return None
    ref = np.median(rgb[int(h * 0.78) : int(h * 0.84)][band], axis=0)
    near = content & (np.linalg.norm(rgb - ref, axis=2) < 48)
    hem = None
    for y in range(int(h * 0.97), int(h * 0.80), -1):  # the lowest row that is still mostly legs
        if content[y].sum() > 4 and near[y].sum() > 0.6 * content[y].sum():
            hem = y
            break
    if hem is None or hem < h * 0.84:
        return None
    xs = np.flatnonzero(near[hem - 2])
    if xs.size == 0:
        return None
    runs, start = [], int(xs[0])
    for prev, cur in itertools.pairwise(xs):
        if cur - prev > 3:
            runs.append((start, int(prev)))
            start = int(cur)
    runs.append((start, int(xs[-1])))
    legs = tuple(((a0 + a1) / 2 / w, (a1 - a0 + 1) / w) for a0, a1 in runs if a1 - a0 > w * 0.04)
    if not 1 <= len(legs) <= 2:
        return None
    if len(legs) == 1:  # a long dress: the two feet under it
        c, lw = legs[0]
        legs = ((c - lw * 0.22, lw * 0.4), (c + lw * 0.22, lw * 0.4))
    top, bottom, left, right = int(h * 0.2), int(h * 0.36), int(w * 0.3), int(w * 0.7)
    px = rgb[top:bottom, left:right][content[top:bottom, left:right]]
    px = px[(px[:, 0] > px[:, 1]) & (px[:, 1] > px[:, 2]) & (px[:, 0] > 110)]
    if px.size == 0:
        return None
    r, g, b = (int(v) for v in np.median(px, axis=0))
    return Feet(hem / h, legs, f"#{r:02X}{g:02X}{b:02X}")


_CLIP = itertools.count()


def _barefoot_reader(image: str, feet: Feet, x: float, y: float, width: float, height: float) -> str:
    """The reader cut off at the hem of its legs, standing on bare feet drawn in its skin tone (with the same
    white sticker edge)."""
    clip = f"reader-hem-{next(_CLIP)}"
    hem_y = y + height * feet.hem
    ground = y + height * 0.995
    parts = [
        f'<clipPath id="{clip}"><rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" '
        f'height="{height * feet.hem + height * 0.004:.2f}"/></clipPath>'
    ]
    shapes = []
    for centre, leg in feet.legs:
        rx = max(width * leg * 0.5, height * 0.018)
        ry = max((ground - hem_y) * 0.5, height * 0.011)
        shapes.append((x + width * centre, ground - ry, rx, ry))
    edge = max(height * 0.008, 0.25)
    for cx, cy, rx, ry in shapes:  # the white edge first, under both feet
        parts.append(
            f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx + edge:.2f}" ry="{ry + edge:.2f}" fill="#FFFFFF"/>'
        )
    tone = people.shade(feet.skin, 1.12)  # the face's median is in its shade: the feet a little lighter
    for cx, cy, rx, ry in shapes:
        parts.append(f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" fill="{tone}"/>')
        for i in range(3):  # little toes
            parts.append(
                f'<circle cx="{cx - rx * 0.45 + i * rx * 0.45:.2f}" cy="{cy + ry * 0.35:.2f}" '
                f'r="{rx * 0.13:.2f}" fill="{people.shade(tone, 0.82)}"/>'
            )
    parts.append(f'<g clip-path="url(#{clip})">{image}</g>')
    return "".join(parts)


def kit_for(sheet: Path | None, out_dir: Path) -> Kit:
    """The cast with the reader taken from a character sheet (front view); without a sheet, the reader is left
    out."""
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
    little taller than the children, all standing close together. Only the recurring characters appear here,
    never in the scenes of a prophet's story."""
    heights = {"huda": 0.98, "reem": 0.84, "salem": 0.72, "reader": 0.9, CAT: 0.4}
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
