"""The child's character on workbook pages: figures cut out of the character sheet.

A sheet is a front view plus two poses on plain paper (qamra_ai character sheets). The first figure from
the left is the front view, the second a pose (waving, on the sample sheets); a figure's paper background is
removed by flood-filling from the border, a thin white "sticker" edge is added, and the result is scaled
for 300 DPI at the largest printed size.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

DIFF = 22  # how far (0–255, per channel) a pixel must be from the paper to count as drawing
GAP = 12  # px of empty paper that separates two figures
PAD = 16  # px of paper kept around the figure while cutting it out
MAX_PRINT_MM = 125.0  # tallest printed size the cut-out must cover at 300 DPI
DPI = 300


def _ink_mask(img: Image.Image, paper: tuple[int, int, int]) -> Image.Image:
    diff = ImageChops.difference(img, Image.new("RGB", img.size, paper))
    r, g, b = diff.split()
    strongest = ImageChops.lighter(ImageChops.lighter(r, g), b)
    return strongest.point(lambda v: 255 if v > DIFF else 0)


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    """[start, end) runs of True, merging runs split by fewer than GAP False values."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, on in enumerate([*flags, False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            if runs and start - runs[-1][1] < GAP:
                runs[-1] = (runs[-1][0], i)
            else:
                runs.append((start, i))
            start = None
    return runs


def paper_color(img: Image.Image) -> tuple[int, int, int]:
    w, h = img.size
    strips = [(0, 0, w, 8), (0, h - 8, w, h), (0, 0, 8, h), (w - 8, 0, w, h)]
    means = [ImageStat.Stat(img.crop(box)).mean for box in strips]
    return (
        round(sum(m[0] for m in means) / 4),
        round(sum(m[1] for m in means) / 4),
        round(sum(m[2] for m in means) / 4),
    )


def figure_box(img: Image.Image, paper: tuple[int, int, int], index: int = 0) -> tuple[int, int, int, int]:
    """Bounding box of the figure `index` from the left (0 is the front view)."""
    mask = _ink_mask(img, paper)
    w, h = mask.size
    column_ink = [mask.crop((x, 0, x + 1, h)).getbbox() is not None for x in range(w)]
    figures = [run for run in _runs(column_ink) if run[1] - run[0] > w * 0.05]
    if len(figures) <= index:
        raise ValueError(f"no figure {index} on the character sheet ({len(figures)} found)")
    x0, x1 = figures[index]
    _, top, _, bottom = mask.crop((x0, 0, x1, h)).getbbox() or (0, 0, 0, h)
    return x0, top, x1, bottom


def front_view_box(img: Image.Image, paper: tuple[int, int, int]) -> tuple[int, int, int, int]:
    """Bounding box of the first figure from the left."""
    return figure_box(img, paper, 0)


def cut_out(img: Image.Image, paper: tuple[int, int, int]) -> Image.Image:
    """RGBA figure: paper connected to the border becomes transparent; enclosed light areas stay."""
    padded = Image.new("RGB", (img.width + 2 * PAD, img.height + 2 * PAD), paper)
    padded.paste(img, (PAD, PAD))
    ink = _ink_mask(padded, paper).filter(ImageFilter.MaxFilter(5))  # close hairline gaps in the outline
    ImageDraw.floodfill(ink, (0, 0), 128)
    background = ink.point(lambda v: 255 if v == 128 else 0).filter(ImageFilter.MaxFilter(3))
    alpha = ImageChops.invert(background).filter(ImageFilter.GaussianBlur(1.0))
    out = padded.convert("RGBA")
    out.putalpha(alpha)
    return out


def sticker_edge(figure: Image.Image, width: int) -> Image.Image:
    """A white margin around the figure (reads as a die-cut sticker on colored backgrounds)."""
    alpha = figure.getchannel("A")
    grown = alpha.filter(ImageFilter.GaussianBlur(width / 2)).point(lambda v: 255 if v > 8 else 0)
    grown = grown.filter(ImageFilter.GaussianBlur(1.2))
    edge = Image.new("RGBA", figure.size, (255, 255, 255, 0))
    edge.putalpha(grown)
    return Image.alpha_composite(edge, figure)


def front_view(sheet: Path, out_dir: Path, max_print_mm: float = MAX_PRINT_MM) -> Path:
    """The cut-out front view as a PNG ready for print; cached by the sheet's content."""
    return pose(sheet, out_dir, 0, max_print_mm)


def pose(sheet: Path, out_dir: Path, index: int, max_print_mm: float = MAX_PRINT_MM) -> Path:
    """The cut-out figure `index` (0: front view, 1: the first pose) as a print PNG; cached by content."""
    digest = hashlib.sha256(sheet.read_bytes()).hexdigest()[:12]
    out = out_dir / (f"character-{digest}.png" if index == 0 else f"character-{digest}-pose{index}.png")
    if out.exists():
        return out
    with Image.open(sheet) as src:
        img = src.convert("RGB")
    paper = paper_color(img)
    figure = cut_out(img.crop(figure_box(img, paper, index)), paper)
    figure = sticker_edge(figure, width=max(4, figure.height // 90))
    figure = figure.crop(figure.getchannel("A").getbbox() or (0, 0, figure.width, figure.height))
    target_h = round(max_print_mm / 25.4 * DPI)
    if figure.height < target_h:
        target_w = round(figure.width * target_h / figure.height)
        figure = figure.resize((target_w, target_h), Image.Resampling.LANCZOS)
    out_dir.mkdir(parents=True, exist_ok=True)
    figure.save(out, format="PNG", dpi=(DPI, DPI), optimize=True)
    return out


def aspect(path: Path) -> float:
    """Width / height of an image."""
    with Image.open(path) as img:
        return img.width / img.height
