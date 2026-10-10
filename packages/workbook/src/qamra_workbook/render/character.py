"""The child's character on workbook pages: figures cut out of the character sheet.

A sheet is a front view plus two poses on plain paper (qamra_ai character sheets). The first figure from
the left is the front view, the second a pose (waving, on the sample sheets); a figure's paper background and
floor shadow are removed by qamra_pdf.cutout (light clothes stay whole), a thin white "sticker" edge that
follows the cut silhouette is added, and the result is scaled for 300 DPI at the largest printed size.

On textured (watercolour) paper a plain "off the paper colour" key takes the grain for drawing, so the figures
are found with the cut-out's noise-adapted ink map instead; a sheet whose figures still run together is split
near its thirds. When a figure cannot be cut out cleanly, qamra_pdf.cutout returns a framed portrait instead;
the PNG says so (`FALLBACK_KEY`, read by `is_fallback`) and the order jobs flag the book `cutout_fallback`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageStat
from PIL.PngImagePlugin import PngInfo

from qamra_pdf.cutout import GRAIN, Cutout, ink_mask, paper_grain
from qamra_pdf.cutout import VERSION as CUTOUT_VERSION
from qamra_pdf.cutout import cut_out as cut_out_figure

DIFF = 22  # how far (0–255, per channel) a pixel must be from the paper to count as drawing
GAP = 12  # px of empty paper that separates two figures
PAD = 16  # px of paper kept around the figure while cutting it out
MAX_PRINT_MM = 125.0  # tallest printed size the cut-out must cover at 300 DPI
MIN_PRINT_W_MM = 66.0  # widest printed size (a portrait frame crops by width), also at 300 DPI
DPI = 300
MERGED = 0.6  # one "figure" wider than this share of a wide sheet is the sheet's figures run together
FALLBACK_KEY = "qamra-cutout"  # PNG text: "fallback: <why>" when the figure is a framed portrait


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


def _ink(img: Image.Image, paper: tuple[int, int, int], textured: bool) -> np.ndarray:
    """What is drawn on the sheet: a plain key against the paper colour on clean paper (as it always was),
    the cut-out's noise-adapted map of what is clearly drawn on textured paper, where the grain itself passes
    the plain key."""
    if not textured:
        return np.asarray(_ink_mask(img, paper)) > 0
    ink = ink_mask(img, paper)
    ink &= (ink.sum(0) >= 2)[None, :]  # a column or row with one speck of grain in it is not drawing
    ink &= (ink.sum(1) >= 2)[:, None]
    return ink


def _split(columns: np.ndarray, w: int) -> list[tuple[int, int]]:
    """Figures that run together on a three-view sheet, split at the emptiest column near each third."""
    cuts = []
    for third in (w / 3, 2 * w / 3):
        lo, hi = round(third - w / 8), round(third + w / 8)
        cuts.append(lo + int(np.argmin(columns[lo:hi])))
    runs = []
    for a, b in zip([0, *cuts], [*cuts, w], strict=True):
        on = np.flatnonzero(columns[a:b] > 0)
        if on.size:
            runs.append((a + int(on[0]), a + int(on[-1]) + 1))
    return runs


def figure_box(img: Image.Image, paper: tuple[int, int, int], index: int = 0) -> tuple[int, int, int, int]:
    """Bounding box of the figure `index` from the left (0 is the front view)."""
    textured = paper_grain(img, paper) > GRAIN
    ink = _ink(img, paper, textured)
    h, w = ink.shape
    columns = ink.sum(0)
    figures = [run for run in _runs([bool(c) for c in columns]) if run[1] - run[0] > w * 0.05]
    if len(figures) == 1 and w >= 1.3 * h and figures[0][1] - figures[0][0] > MERGED * w:
        figures = [run for run in _split(columns, w) if run[1] - run[0] > w * 0.05]
    if len(figures) <= index:
        raise ValueError(f"no figure {index} on the character sheet ({len(figures)} found)")
    x0, x1 = figures[index]
    rows = np.flatnonzero(ink[:, x0:x1].any(1))
    top, bottom = (int(rows[0]), int(rows[-1]) + 1) if rows.size else (0, h)
    if textured:  # only the clearly drawn was found: keep a little of the real paper around a soft edge
        m = GAP // 2
        left = (figures[index - 1][1] + x0) // 2 if index > 0 else 0
        right = (x1 + figures[index + 1][0]) // 2 if index + 1 < len(figures) else w
        x0, x1, top, bottom = max(left, x0 - m), min(right, x1 + m), max(0, top - m), min(h, bottom + m)
    return x0, top, x1, bottom


def front_view_box(img: Image.Image, paper: tuple[int, int, int]) -> tuple[int, int, int, int]:
    """Bounding box of the first figure from the left."""
    return figure_box(img, paper, 0)


def cut_out(img: Image.Image, paper: tuple[int, int, int]) -> Cutout:
    """RGBA figure: paper and floor shadow transparent; light clothes and enclosed areas stay opaque (or the
    framed portrait, `fallback` set, when the figure cannot be cut out cleanly)."""
    padded = Image.new("RGB", (img.width + 2 * PAD, img.height + 2 * PAD), paper)
    padded.paste(img, (PAD, PAD))
    return cut_out_figure(padded, paper)


def is_fallback(path: Path) -> bool:
    """Whether a cut-out PNG made by `pose` is the framed portrait (the figure could not be cut out)."""
    with Image.open(path) as img:
        return str(img.info.get(FALLBACK_KEY, "")).startswith("fallback")


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


def pose(
    sheet: Path,
    out_dir: Path,
    index: int,
    max_print_mm: float = MAX_PRINT_MM,
    min_print_w_mm: float = MIN_PRINT_W_MM,
) -> Path:
    """The cut-out figure `index` (0: front view, 1: the first pose) as a print PNG; cached by content."""
    key = f"cutout-v{CUTOUT_VERSION}-w{min_print_w_mm:g}"
    if max_print_mm != MAX_PRINT_MM:  # a bigger print (the covers) is its own file
        key += f"-h{max_print_mm:g}"
    digest = hashlib.sha256(sheet.read_bytes() + key.encode()).hexdigest()[:12]
    out = out_dir / (f"character-{digest}.png" if index == 0 else f"character-{digest}-pose{index}.png")
    if out.exists():
        return out
    with Image.open(sheet) as src:
        img = src.convert("RGB")
    paper = paper_color(img)
    cut = cut_out(img.crop(figure_box(img, paper, index)), paper)
    figure = sticker_edge(cut.image, width=max(4, cut.image.height // 90))
    figure = figure.crop(figure.getchannel("A").getbbox() or (0, 0, figure.width, figure.height))
    target_h = round(max_print_mm / 25.4 * DPI)
    if figure.height < target_h:
        target_w = round(figure.width * target_h / figure.height)
        figure = figure.resize((target_w, target_h), Image.Resampling.LANCZOS)
    min_w = round(min_print_w_mm / 25.4 * DPI)
    if figure.width < min_w:  # a narrow figure: the width, not the height, sets the print size
        figure = figure.resize((min_w, round(figure.height * min_w / figure.width)), Image.Resampling.LANCZOS)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = PngInfo()
    if cut.fallback:
        info.add_text(FALLBACK_KEY, f"fallback: {cut.reason}")
    figure.save(out, format="PNG", dpi=(DPI, DPI), optimize=True, pnginfo=info)
    return out


def aspect(path: Path) -> float:
    """Width / height of an image."""
    with Image.open(path) as img:
        return img.width / img.height
