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
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VERSION = 2  # bump when the result changes, so cached cut-outs are redone

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
    """Pixels reachable from the image border through `passable` ones (the frame itself counts)."""
    h, w = passable.shape
    canvas = np.zeros((h + 2, w + 2), np.uint8)
    canvas[1:-1, 1:-1] = np.where(passable, 0, 255)
    img = Image.fromarray(canvas).copy()  # a copy: an image over a numpy buffer is read-only
    ImageDraw.floodfill(img, (0, 0), 128)
    reached: np.ndarray = np.asarray(img)[1:-1, 1:-1] == 128
    return reached


def _grow(mask: np.ndarray, size: int) -> np.ndarray:
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(size))) > 127


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


def figure_mask(img: Image.Image, paper: tuple[int, int, int] | None = None) -> np.ndarray:
    """Boolean mask of the figure on a plain paper image (see the module docstring)."""
    rgb_img = img.convert("RGB")
    rgb = np.asarray(rgb_img, dtype=np.float32)
    h, w = rgb.shape[:2]
    if paper is None:
        border = np.concatenate(
            [
                rgb[:4].reshape(-1, 3),
                rgb[-4:].reshape(-1, 3),
                rgb[:, :4].reshape(-1, 3),
                rgb[:, -4:].reshape(-1, 3),
            ]
        )
        paper_rgb = np.median(border, axis=0)
    else:
        paper_rgb = np.array(paper, np.float32)

    # 1. the paper field, from the paper a coarse key reaches from the border
    coarse = _border_flood(np.abs(rgb - paper_rgb).max(-1) <= 22)
    field = _paper_field(rgb, coarse)
    residual = np.abs(rgb - field).max(-1)
    edge_strength = _gradient(rgb_img)
    frame = np.zeros((h, w), bool)  # the noise level of the paper, measured on the outer frame only
    m = max(2, min(h, w) // 40)
    frame[:m], frame[-m:], frame[:, :m], frame[:, -m:] = True, True, True, True
    frame &= coarse
    noise = float(np.percentile(residual[frame], 99)) if frame.any() else 0.0
    threshold = max(MIN_RESIDUAL, noise + 3.0)

    # 2. ink: off the paper, or an edge
    ink = (residual > threshold) | (edge_strength > EDGE)

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
        shadow = band & paper_hue & (residual < SHADOW_MAX) & (edge_strength <= SHADOW_EDGE)
        ink &= ~shadow

    # 4. background = flooded from the border through the thickened wall, then given back what the
    #    thickening took: the shadow it walled off, and the paper-coloured rim around the outline
    radius = max(2, round(min(h, w) / 150))
    background = _border_flood(~_grow(ink, 2 * radius + 1))
    background = _border_flood(background | shadow)
    paper_like = residual <= threshold
    for _ in range(radius + 2):  # peel paper-coloured pixels from the outside in; the outline stops it
        rim = _grow(background, 3) & paper_like & ~background
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
    if noise > POCKET_NOISE:
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


def cut_out_figure(
    img: Image.Image, paper: tuple[int, int, int] | None = None, feather: float = 0.8
) -> Image.Image:
    """RGBA: the figure opaque (light clothes included), the paper and the floor shadow transparent."""
    mask = figure_mask(img, paper)
    # the outermost pixel ring is the anti-aliased blend with the paper: drop it, then soften the edge
    alpha = Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))
    if feather > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    out = img.convert("RGBA")
    out.putalpha(alpha)
    return out
