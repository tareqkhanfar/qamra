"""Cut a drawn figure (a character or companion on a plain paper sheet) out of its background.

The image model draws the child on cream/white paper, often in a cream or white sweater, with a soft floor
shadow under the feet. A plain "far enough from the paper colour" key cannot work there: the lit side of a
light sweater has the paper's exact colour, so a flood fill from the border leaks through the faint outline
into the chest, and the shadow (clearly darker than the paper) is kept as a pale blob at the feet.

What this does instead (Pillow + numpy only):

1. The paper is modelled as a smooth colour field (a surface fitted to the border-connected paper), so the
   residual of every pixel against the paper underneath it is at noise level on the background.
2. "Ink" is any pixel clearly off that field (a low, noise-adapted threshold) or on an edge (gradient), so
   the faint outline of a light garment still forms a wall; the wall is thickened by a few pixels (about
   1/150 of the figure) for the flood, so it cannot slip through a gap in a soft outline.
3. Floor shadow: in the figure's bottom band, soft pixels with the paper's own hue are let through (a
   shadow is the paper, darker; shoes, trousers and outlines are not), and thin contact lines there go too.
4. The background is what a flood from the border reaches; everything else is the figure, so light areas
   enclosed by the figure (a white sweater, a collar) stay opaque. Only the largest connected piece (and
   pieces nearly as large) is kept, which drops specks and the neighbouring figure's shadow.
5. On clean paper, small pockets of plain paper ringed by hard outlines (between a raised arm and the hair,
   between the legs) are see-through.

Textured paper (watercolour sheets, 2026-10-09). The grain of a watercolour sheet is an edge on every pixel
and steps off the paper colour by as much as a faint outline does, so with the clean-paper thresholds the
whole picture is "ink" and the flood never starts: the whole sheet was pasted onto the cover. The paper is
measured first, on plain paper well away from anything drawn (and inside the flat margin a caller may pad the
crop with): its grain is the 90th percentile of the gradient there. On clean paper (grain at most `GRAIN`)
everything above runs exactly as before. On textured paper the picture is first smoothed in proportion to the
grain (a Gaussian, which keeps a thin outline as a weaker line where a median would erase it), and the ink and
edge thresholds are set from the noise measured on that same plain paper; the rim is peeled through the
paper's grain too, and step 5 is skipped (a white garment and grainy paper cannot be told apart by colour).

Safety check: a result that covers implausibly much of the picture (`COVER_MAX`), touches all four edges of
it, or is next to nothing is not a cut-out. `cut_out` then returns a framed portrait instead (the figure's
region in a rounded rectangle with a soft vignette) and says so (`Cutout.fallback`), so a book can carry a
flag for the reviewer instead of the whole sheet being pasted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VERSION = 3  # bump when the result changes, so cached cut-outs are redone

MIN_RESIDUAL = 7.0  # 0–255 per channel: the smallest step off the paper that counts as ink
EDGE = 6.0  # gradient (max channel, over 2 px) that counts as an edge
SHADOW_BAND = 0.16  # the bottom fraction of the figure where a floor shadow may lie
SHADOW_HUE = 0.06  # chromaticity distance from the paper that still reads as "paper in shade"
SHADOW_MAX = 130.0  # a shadow is never further than this from the paper (dark shoes are)
SHADOW_EDGE = 22.0  # a shadow is soft: its gradient stays under this (the outline of a shoe does not)
KEEP_PIECE = 0.15  # keep detached pieces at least this fraction of the largest one
POCKET_MAX = 0.025  # a see-through pocket of paper is smaller than this fraction of the figure
POCKET_MIN = 0.001  # ... and larger than this one (smaller specks are left alone)
POCKET_RING = 0.85  # ... and nearly all of its rim is a hard outline
POCKET_NOISE = 4.0  # ... on paper this clean (the 99th-percentile residual of the frame)

# textured paper
GRAIN = 4.0  # the paper's grain (90th-percentile gradient on plain paper) above which it counts as textured
GRAIN_BLUR = 5.0  # ... and is smoothed with a Gaussian of radius grain / GRAIN_BLUR px
GRAIN_BLUR_MAX = 2.0  # ... at most (a hair's thin outline must survive the smoothing)
SAMPLE_GAP = 6  # plain paper for the measurements is at least this many px from anything else
SAMPLE_MIN = 400  # px: fewer than this and the measurement falls back to all the border-connected paper
EDGE_MARGIN = 2.0  # an edge on textured paper is this much above the grain's 99th-percentile gradient
PEEL_MARGIN = 3.0  # the rim is peeled through paper up to this much above its 99.9th-percentile residual

# the safety check
COVER_MAX = 0.78  # a figure never covers more than this share of its picture (the whole sheet did: 0.91)
COVER_MIN = 0.01  # ... nor less than this one (nothing was found)
FRAME_RADIUS = 0.08  # the fallback portrait: corner radius as a share of its shorter side
FRAME_MARGIN = 0.05  # ... paper kept around the figure's region, as a share of its size
VIGNETTE = 0.1  # ... how much darker its corners are than its middle


@dataclass(frozen=True)
class Cutout:
    """A cut-out figure, or the framed portrait that stands in for it when the cut failed the safety check."""

    image: Image.Image  # RGBA
    fallback: bool = False  # `image` is a framed portrait: the figure could not be cut out cleanly
    reason: str = ""  # why the cut failed (for the logs)


@dataclass(frozen=True)
class _Paper:
    """The paper behind a figure, measured (see the module docstring)."""

    rgb: np.ndarray  # the picture analysed (smoothed on textured paper), float32 h × w × 3
    field: np.ndarray  # the paper colour under every pixel
    residual: np.ndarray  # max-channel distance from the paper field
    edges: np.ndarray  # gradient magnitude
    threshold: float  # residual that counts as ink
    edge: float  # gradient that counts as an edge
    peel: float  # residual the rim may still be peeled through
    noise: float  # the paper's 99th-percentile residual
    grain: float  # the paper's 90th-percentile gradient (before smoothing)

    @property
    def textured(self) -> bool:
        return self.grain > GRAIN


def _paper_field(rgb: np.ndarray, background: np.ndarray) -> np.ndarray:
    """The paper colour under every pixel: a smooth (quadratic) surface fitted to the known paper.

    Smooth on purpose: a local average would copy a light garment that a coarse key mistook for paper into
    the field and hide it (its residual would be zero)."""
    h, w = background.shape
    ys, xs = np.nonzero(background)
    if ys.size < 50:
        return np.broadcast_to(np.median(rgb.reshape(-1, 3), axis=0), rgb.shape).copy()
    step = max(1, ys.size // 40000)
    ys, xs = ys[::step], xs[::step]

    def basis(y: np.ndarray, x: np.ndarray) -> np.ndarray:
        v, u = y / h - 0.5, x / w - 0.5
        return np.stack([np.ones_like(u), u, v, u * u, u * v, v * v], axis=-1)

    a = basis(ys.astype(np.float32), xs.astype(np.float32))
    values = rgb[ys, xs]
    use = np.ones(ys.size, bool)
    for _ in range(3):  # refit without the outliers (shadows, stray ink)
        coef, *_ = np.linalg.lstsq(a[use], values[use], rcond=None)
        error = np.abs(a @ coef - values).max(-1)
        use = error < max(4.0, float(np.percentile(error, 80)))
    yy, xx = np.mgrid[0:h, 0:w]
    field: np.ndarray = (basis(yy.astype(np.float32), xx.astype(np.float32)) @ coef).astype(np.float32)
    return field


def _gradient(rgb_img: Image.Image) -> np.ndarray:
    a = np.asarray(rgb_img.filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32)
    gx = np.zeros(a.shape[:2], np.float32)
    gy = np.zeros(a.shape[:2], np.float32)
    gx[:, 1:-1] = np.abs(a[:, 2:] - a[:, :-2]).max(-1)
    gy[1:-1] = np.abs(a[2:] - a[:-2]).max(-1)
    magnitude: np.ndarray = np.hypot(gx, gy)
    return magnitude


def _border_flood(passable: np.ndarray) -> np.ndarray:
    """Pixels reachable from the image border through `passable` ones (4-connected): the pieces of
    `passable` that touch the border. Labelled by row runs (the same result as a flood fill from a frame
    around the picture, which Pillow does pixel by pixel in Python, some 30× slower)."""
    labels, _ = _components(passable)
    edge = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    reached: np.ndarray = np.isin(labels, np.unique(edge[edge != 0]))
    return reached


def _grow(mask: np.ndarray, size: int) -> np.ndarray:
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(size))) > 127


def _near(mask: np.ndarray, radius: int) -> np.ndarray:
    """Pixels within `radius` (a square) of a `mask` pixel; a box blur, so a wide radius stays fast."""
    blurred = Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.BoxBlur(radius))
    near: np.ndarray = np.asarray(blurred) > 0
    return near


def _components(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """4-connected labels (0 = background) and the size of each label, by row runs and union-find."""
    h, _ = mask.shape
    parent: list[int] = [0]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    runs: list[list[tuple[int, int, int]]] = []  # per row: (start, end, label)
    for y in range(h):
        row = np.concatenate(([0], mask[y].astype(np.int8), [0]))
        edges = np.flatnonzero(np.diff(row))
        current: list[tuple[int, int, int]] = []
        prev = runs[-1] if runs else []
        j = 0
        for s, e in zip(edges[::2], edges[1::2], strict=True):
            label = 0
            while j < len(prev) and prev[j][1] <= s:
                j += 1
            k = j
            while k < len(prev) and prev[k][0] < e:
                other = find(prev[k][2])
                if label == 0:
                    label = other
                elif other != label:
                    parent[max(other, label)] = min(other, label)
                    label = min(other, label)
                k += 1
            if label == 0:
                label = len(parent)
                parent.append(label)
            current.append((int(s), int(e), label))
        runs.append(current)
    labels = np.zeros(mask.shape, np.int32)
    for y, row_runs in enumerate(runs):
        for s, e, label in row_runs:
            labels[y, s:e] = find(label)
    sizes = np.bincount(labels.ravel(), minlength=len(parent))
    return labels, sizes


def _flat_margin(rgb: np.ndarray) -> int:
    """The width of a perfectly flat outer margin (a crop padded with the paper colour), 0 if none."""
    h, w = rgb.shape[:2]
    colour = rgb[0, 0]
    k = 0
    while k < min(h, w) // 4:
        ring = (rgb[k, k : w - k], rgb[h - 1 - k, k : w - k], rgb[k : h - k, k], rgb[k : h - k, w - 1 - k])
        if not all(bool((part == colour).all()) for part in ring):
            break
        k += 1
    return k


def _plain_paper(rgb: np.ndarray, paper_rgb: np.ndarray) -> np.ndarray:
    """Where to measure the paper: border-connected paper at least SAMPLE_GAP px from anything else, inside
    any flat margin. Keyed on a lightly smoothed copy, so the grain itself does not break the paper up."""
    h, w = rgb.shape[:2]
    soft = np.asarray(Image.fromarray(rgb.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), np.float32)
    paper = _border_flood(np.abs(soft - paper_rgb).max(-1) <= 22)
    inner = np.zeros((h, w), bool)
    k = _flat_margin(rgb)
    inner[k : h - k, k : w - k] = True
    sample: np.ndarray = paper & inner & ~_near(~paper, SAMPLE_GAP)
    if sample.sum() < SAMPLE_MIN:
        sample = paper & inner
    if sample.sum() < SAMPLE_MIN:
        sample = paper
    return sample


def _frame(h: int, w: int) -> np.ndarray:
    frame = np.zeros((h, w), bool)
    m = max(2, min(h, w) // 40)
    frame[:m], frame[-m:], frame[:, :m], frame[:, -m:] = True, True, True, True
    return frame


def _border_paper(rgb: np.ndarray) -> np.ndarray:
    strips = (rgb[:4], rgb[-4:], rgb[:, :4], rgb[:, -4:])
    border = np.concatenate([strip.reshape(-1, 3) for strip in strips])
    median: np.ndarray = np.median(border, axis=0)
    return median


def _measure(img: Image.Image, paper: tuple[int, int, int] | None = None) -> _Paper:
    """The paper model of a picture (steps 1–2 of the module docstring, with the textured-paper branch)."""
    rgb_img = img.convert("RGB")
    rgb = np.asarray(rgb_img, dtype=np.float32)
    h, w = rgb.shape[:2]
    paper_rgb = _border_paper(rgb) if paper is None else np.array(paper, np.float32)
    raw_edges = _gradient(rgb_img)
    sample = _plain_paper(rgb, paper_rgb)
    grain = float(np.percentile(raw_edges[sample], 90)) if sample.any() else 0.0

    if grain <= GRAIN:  # clean paper: exactly as before textured paper was handled
        coarse = _border_flood(np.abs(rgb - paper_rgb).max(-1) <= 22)
        field = _paper_field(rgb, coarse)
        residual = np.abs(rgb - field).max(-1)
        frame = _frame(h, w) & coarse  # the noise level of the paper, measured on the outer frame only
        noise = float(np.percentile(residual[frame], 99)) if frame.any() else 0.0
        threshold = max(MIN_RESIDUAL, noise + 3.0)
        return _Paper(rgb, field, residual, raw_edges, threshold, EDGE, threshold, noise, grain)

    # textured paper: smooth the grain away, then measure the paper on the smoothed picture
    work = rgb_img.filter(ImageFilter.GaussianBlur(min(GRAIN_BLUR_MAX, grain / GRAIN_BLUR)))
    rgb = np.asarray(work, dtype=np.float32)
    coarse = _border_flood(np.abs(rgb - paper_rgb).max(-1) <= 22)
    field = _paper_field(rgb, coarse | sample)
    residual = np.abs(rgb - field).max(-1)
    edges = _gradient(work)
    noise = float(np.percentile(residual[sample], 99))
    threshold = max(MIN_RESIDUAL, noise + 3.0)
    edge = max(EDGE, float(np.percentile(edges[sample], 99)) + EDGE_MARGIN)
    peel = max(threshold, float(np.percentile(residual[sample], 99.9)) + PEEL_MARGIN)
    return _Paper(rgb, field, residual, edges, threshold, edge, peel, noise, grain)


def paper_grain(img: Image.Image, paper: tuple[int, int, int] | None = None) -> float:
    """The paper's grain: the 90th-percentile gradient on plain paper (above `GRAIN`: textured paper)."""
    rgb_img = img.convert("RGB")
    rgb = np.asarray(rgb_img, dtype=np.float32)
    paper_rgb = _border_paper(rgb) if paper is None else np.array(paper, np.float32)
    sample = _plain_paper(rgb, paper_rgb)
    return float(np.percentile(_gradient(rgb_img)[sample], 90)) if sample.any() else 0.0


def _clearly_drawn(p: _Paper) -> np.ndarray:
    drawn: np.ndarray = p.residual > max(p.threshold, 2 * p.noise)
    return drawn


def ink_mask(img: Image.Image, paper: tuple[int, int, int] | None = None) -> np.ndarray:
    """Boolean mask of what is clearly drawn (off the paper by twice its noise at least), grain or not; for
    finding the figures on a sheet before any of them is cut out."""
    return _clearly_drawn(_measure(img, paper))


def _figure(p: _Paper) -> np.ndarray:
    """Steps 2–6 of the module docstring on a measured picture."""
    rgb, field, residual, edge_strength = p.rgb, p.field, p.residual, p.edges
    h, w = residual.shape
    threshold = p.threshold

    # 2. ink: off the paper, or an edge
    ink = (residual > threshold) | (edge_strength > p.edge)

    # 3. the floor shadow: paper hue, soft, in the bottom band of the figure
    shadow = np.zeros((h, w), bool)
    band = np.zeros((h, w), bool)
    solid_rows = np.flatnonzero((residual > 40).any(axis=1))
    if solid_rows.size:
        top, bottom = int(solid_rows[0]), int(solid_rows[-1])
        band[max(0, round(bottom - SHADOW_BAND * (bottom - top))) :] = True
        chroma = rgb / (rgb.sum(-1, keepdims=True) + 1.0)
        paper_chroma = field / (field.sum(-1, keepdims=True) + 1.0)
        paper_hue = np.abs(chroma - paper_chroma).max(-1) < SHADOW_HUE
        shadow = band & paper_hue & (residual < SHADOW_MAX) & (edge_strength <= max(SHADOW_EDGE, p.edge))
        ink &= ~shadow

    # 4. background = flooded from the border through the thickened wall, then given back what the
    #    thickening took: the shadow it walled off, and the paper-coloured rim around the outline
    radius = max(2, round(min(h, w) / 150))
    background = _border_flood(~_grow(ink, 2 * radius + 1))
    background = _border_flood(background | shadow)
    paper_like = residual <= threshold
    # on textured paper the rim is peeled through the grain as well (paper up to its own worst residual)
    peelable = (residual <= p.peel) & (edge_strength <= p.edge) if p.textured else paper_like
    for _ in range(radius + 2):  # peel paper-coloured pixels from the outside in; the outline stops it
        rim = _grow(background, 3) & peelable & ~background
        if not rim.any():
            break
        background |= rim
    # on the floor, strokes thinner than the wall are the shadow's dark contact line, not the figure:
    # open the figure there, then let the shadow they fenced in (between the shoes) out as well
    size = 2 * radius + 1
    solid = Image.fromarray((~background).astype(np.uint8) * 255)
    opened = np.asarray(solid.filter(ImageFilter.MinFilter(size)).filter(ImageFilter.MaxFilter(size))) > 127
    background |= band & ~opened
    background = _border_flood(background | shadow)

    # 5. the figure: the largest piece (and any nearly as large), with every hole filled
    figure = ~background
    labels, sizes = _components(figure)
    sizes[0] = 0
    if sizes.max() == 0:
        return figure
    keep = np.flatnonzero(sizes >= KEEP_PIECE * sizes.max())
    figure = ~_border_flood(~np.isin(labels, keep))

    # 6. paper seen through the figure (between a raised arm and the hair, between the legs): a small
    #    pocket of plain paper ringed by hard outlines. A lit patch of a light garment is ringed by soft
    #    shading instead, and the chest is far bigger than POCKET_MAX, so both stay.
    #    Only on clean paper: on textured (watercolour) paper a white garment and the paper cannot be told
    #    apart by colour, so nothing is taken out there.
    if p.textured or p.noise > POCKET_NOISE:
        return figure
    pockets, pocket_sizes = _components(figure & paper_like & (edge_strength <= EDGE))
    area = int(figure.sum())
    for label in np.flatnonzero((pocket_sizes >= POCKET_MIN * area) & (pocket_sizes < POCKET_MAX * area)):
        if label == 0:
            continue
        ys, xs = np.nonzero(pockets == label)
        y0, y1, x0, x1 = max(0, ys.min() - 3), ys.max() + 4, max(0, xs.min() - 3), xs.max() + 4
        piece = pockets[y0:y1, x0:x1] == label
        ring = _grow(piece, 5) & ~piece
        hard = float((edge_strength[y0:y1, x0:x1][ring] > EDGE).mean()) if ring.any() else 0.0
        if hard >= POCKET_RING:
            figure[y0:y1, x0:x1] &= ~_grow(piece, 3) | ~paper_like[y0:y1, x0:x1]
    return figure


def figure_mask(img: Image.Image, paper: tuple[int, int, int] | None = None) -> np.ndarray:
    """Boolean mask of the figure on a plain paper image (see the module docstring)."""
    return _figure(_measure(img, paper))


def mask_problem(mask: np.ndarray) -> str:
    """Why a figure mask is not a cut-out ("" when it is plausible): the safety check."""
    cover = float(mask.mean()) if mask.size else 0.0
    if cover > COVER_MAX:
        return f"covers {cover:.0%} of the picture"
    if cover < COVER_MIN:
        return f"covers only {cover:.1%} of the picture"
    if mask[0].any() and mask[-1].any() and mask[:, 0].any() and mask[:, -1].any():
        return "touches all four edges of the picture"
    return ""


def _region(p: _Paper, flat: int) -> tuple[int, int, int, int]:
    """The figure's region for the framed portrait: rows and columns with a few clearly drawn pixels, plus
    a margin of paper; the whole picture (inside a flat margin) when nothing stands out."""
    h, w = p.residual.shape
    ink = _clearly_drawn(p)
    ink[:flat], ink[h - flat :], ink[:, :flat], ink[:, w - flat :] = False, False, False, False
    cols = np.flatnonzero(ink.sum(0) >= max(3, h // 200))
    rows = np.flatnonzero(ink.sum(1) >= max(3, w // 200))
    if cols.size < 2 or rows.size < 2:
        return flat, flat, w - flat, h - flat
    x0, x1, y0, y1 = int(cols[0]), int(cols[-1]) + 1, int(rows[0]), int(rows[-1]) + 1
    mx, my = round(FRAME_MARGIN * (x1 - x0)), round(FRAME_MARGIN * (y1 - y0))
    return max(flat, x0 - mx), max(flat, y0 - my), min(w - flat, x1 + mx), min(h - flat, y1 + my)


def framed_portrait(img: Image.Image, paper: tuple[int, int, int] | None = None) -> Image.Image:
    """The fallback: the figure's region on its own paper, in a rounded rectangle with a soft vignette
    (RGBA, the size of `img`, transparent outside the frame), for when the figure cannot be cut out."""
    rgb_img = img.convert("RGB")
    p = _measure(rgb_img, paper)
    flat = _flat_margin(np.asarray(rgb_img))
    x0, y0, x1, y1 = _region(p, flat)
    w, h = x1 - x0, y1 - y0
    # the vignette: the corners a little darker (a multiply, so the paper keeps its hue)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((xx - (w - 1) / 2) / max(1.0, w / 2), (yy - (h - 1) / 2) / max(1.0, h / 2)) / np.sqrt(2)
    shade = 1.0 - VIGNETTE * np.clip((d - 0.45) / 0.55, 0, 1) ** 2
    region = np.asarray(rgb_img.crop((x0, y0, x1, y1)), np.float32) * shade[..., None]
    out = Image.new("RGBA", rgb_img.size, (0, 0, 0, 0))
    out.paste(Image.fromarray(np.clip(region, 0, 255).astype(np.uint8)).convert("RGBA"), (x0, y0))
    # the frame: a rounded rectangle, drawn at 4× and scaled down for a smooth edge
    scale = 4
    alpha = Image.new("L", (rgb_img.width * scale, rgb_img.height * scale), 0)
    corner = round(FRAME_RADIUS * min(w, h) * scale)
    box = (x0 * scale, y0 * scale, x1 * scale - 1, y1 * scale - 1)
    ImageDraw.Draw(alpha).rounded_rectangle(box, radius=corner, fill=255)
    out.putalpha(alpha.resize(rgb_img.size, Image.Resampling.LANCZOS))
    return out


def cut_out(img: Image.Image, paper: tuple[int, int, int] | None = None, feather: float = 0.8) -> Cutout:
    """The figure cut out (RGBA), or the framed portrait when the cut fails the safety check."""
    p = _measure(img, paper)
    mask = _figure(p)
    problem = mask_problem(mask)
    if problem:
        return Cutout(framed_portrait(img, paper), fallback=True, reason=problem)
    # the outermost pixel ring is the anti-aliased blend with the paper: drop it, then soften the edge
    alpha = Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))
    if feather > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    out = img.convert("RGBA")
    out.putalpha(alpha)
    return Cutout(out)


def cut_out_figure(
    img: Image.Image, paper: tuple[int, int, int] | None = None, feather: float = 0.8
) -> Image.Image:
    """RGBA: the figure opaque (light clothes included), the paper and the floor shadow transparent (or the
    framed portrait when the figure cannot be cut out: see `cut_out`)."""
    return cut_out(img, paper, feather).image
