"""Clean a raster drawing (an AI line-art candidate) into print line art in the code-drawn house style.

    from qamra_workbook.coloring.lineart import clean, save
    body = clean(Path("aqsa-dome-1.png"), 186, 232)          # SVG body in mm: white rect + one black path
    save(Path("aqsa-dome-1.png"), "palestine", "aqsa-dome")  # content/coloring/art/palestine/aqsa-dome.svg

The drawn pages (`coloring.ink`) print every outline at 2.6 mm, pure black on white, closed shapes, nothing
tiny. A model's drawing has none of that for sure: lines of any width, grey anti-aliasing, specks, solid
black hair, small gaps. The cleaning keeps only the *centre lines* of the drawing and redraws them at one
width:

1. fit: cover-crop the picture to the box's ratio and resample it to `ppm` pixels per mm at print size;
2. ink: grayscale → light blur → Otsu threshold (dark = ink);
3. specks: ink blobs smaller than `speck_mm2` go; white holes smaller than `hole_mm2` fill (too small to
   colour, so their outline collapses to a line in step 5); then small round blobs up to `dot_max_mm2`
   (eyes, with their pupils and highlights filled) are set aside and come back in step 8 as round dots
   `dot_mm` wide;
4. masses: ink thicker than `mass_mm` (solid hair, a black shadow) becomes its outline, so the page has no
   black areas (`masses="skeleton"` instead thins a mass to its middle line);
5. thinning: Zhang-Suen to a one-pixel skeleton (vectorised with a 3×3 neighbour code and lookup tables);
6. spurs: skeleton branches shorter than `spur_mm` that hang off a junction go, and so do loose bits shorter
   than `dust_mm`;
7. gaps: a line end that comes within `gap_mm` of another line joins it (closed regions to colour), then
   the lines closing off areas smaller than `region_mm2` or narrower than `narrow_mm` go (`merge_regions`:
   the picture gets simpler where it was too busy for a 2.6 mm line);
8. width: the skeleton is redrawn with a round brush `width_mm` wide (2.6 mm = `ink.MAIN`), pinholes fill;
9. vectors: `cv2.findContours` (outer edges and holes) → light smoothing → `approxPolyDP` → quadratic
   curves through the mid-points → one `<path fill="#000000" fill-rule="evenodd">` in mm.

Everything is deterministic (no random state): the same PNG and parameters give the same SVG.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from numpy.typing import NDArray

from qamra_workbook.coloring.ink import INK, MAIN, PAPER, fmt, svg

Mask = NDArray[np.bool_]
ROOT = Path(__file__).resolve().parents[5]
ART = ROOT / "content" / "coloring" / "art"
BOX_W, BOX_H = 186.0, 232.0  # mm: the scene box on the A4 page (`scenes.registry.SCENE_W/H`)


@dataclass(frozen=True)
class Params:
    """The cleaning's knobs, all in mm at print size (so they do not depend on the input's resolution)."""

    width_mm: float = MAIN  # the printed outline
    ppm: float = 8.0  # working pixels per mm (8 → 0.125 mm per pixel; 186 × 232 mm → 1488 × 1856)
    blur_mm: float = 0.25  # smoothing before the threshold
    speck_mm2: float = 2.5  # ink blobs smaller than this go (dust, stray dots)
    hole_mm2: float = 20.0  # enclosed white areas smaller than this fill (≈ 5 mm across: too small to colour)
    mass_mm: float = 5.5  # ink thicker than this is a solid mass (hair, shadow): kept as its outline
    masses: Literal["outline", "skeleton"] = "outline"
    spur_mm: float = 3.0  # skeleton branches shorter than this that hang off a junction go
    dust_mm: float = 4.0  # loose skeleton bits (no junction) shorter than this go (a smile is ~5 mm)
    gap_mm: float = 5.0  # a line end this close to another line joins it
    region_mm2: float = 40.0  # areas to colour smaller than this merge into a neighbour (0: keep all)
    narrow_mm: float = 4.5  # … and so do areas nowhere wider than this between centre lines
    dot_max_mm2: float = 24.0  # small round blobs up to this size (after the hole fill) are dots (eyes) …
    dot_mm: float = 3.0  # … as round dots this wide
    pinhole_mm2: float = 4.0  # white holes left between redrawn lines smaller than this fill
    smooth_px: int = 2  # half window of the contour smoothing (pixels at `ppm`)
    epsilon_mm: float = 0.08  # approxPolyDP tolerance


DEFAULT = Params()


# ---- raster steps ------------------------------------------------------------------------------------------


def load_gray(png: Path) -> NDArray[np.uint8]:
    img = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"cannot read image {png}")
    if img.ndim == 3 and img.shape[2] == 4:  # transparent pixels are paper
        alpha = img[:, :, 3:4].astype(np.float32) / 255.0
        rgb = img[:, :, :3].astype(np.float32) * alpha + 255.0 * (1.0 - alpha)
        img = rgb.astype(np.uint8)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return np.asarray(img, dtype=np.uint8)


def fit(gray: NDArray[np.uint8], w_mm: float, h_mm: float, ppm: float) -> NDArray[np.uint8]:
    """`gray` cover-cropped to the box's ratio (centred) and resampled to `ppm` pixels per mm."""
    h, w = gray.shape
    want = w_mm / h_mm
    if w / h > want:  # too wide: crop the sides
        cw = round(h * want)
        x0 = (w - cw) // 2
        gray = gray[:, x0 : x0 + cw]
    else:
        ch = round(w / want)
        y0 = (h - ch) // 2
        gray = gray[y0 : y0 + ch, :]
    size = (round(w_mm * ppm), round(h_mm * ppm))
    interp = cv2.INTER_CUBIC if size[0] > gray.shape[1] else cv2.INTER_AREA
    return np.asarray(cv2.resize(gray, size, interpolation=interp), dtype=np.uint8)


def ink_mask(gray: NDArray[np.uint8], ppm: float, blur_mm: float) -> Mask:
    k = max(1, round(blur_mm * ppm)) * 2 + 1
    blurred = cv2.GaussianBlur(gray, (k, k), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return np.asarray(binary > 0)


def _u8(mask: Mask) -> NDArray[np.uint8]:
    return mask.astype(np.uint8) * 255


def drop_small(mask: Mask, min_px: float, *, connectivity: int = 8) -> Mask:
    """`mask` without its connected components smaller than `min_px` pixels."""
    _n, labels, stats, _ = cv2.connectedComponentsWithStats(_u8(mask), connectivity=connectivity)
    keep = stats[:, cv2.CC_STAT_AREA] >= min_px
    keep[0] = False
    return np.asarray(keep[labels])


def fill_holes(ink: Mask, max_px: float) -> Mask:
    """`ink` with its enclosed white areas (not touching the edge) smaller than `max_px` filled."""
    _n, labels, stats, _ = cv2.connectedComponentsWithStats(_u8(~ink), connectivity=4)
    h, w = ink.shape
    x, y = stats[:, cv2.CC_STAT_LEFT], stats[:, cv2.CC_STAT_TOP]
    bw, bh = stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_HEIGHT]
    edge = (x == 0) | (y == 0) | (x + bw == w) | (y + bh == h)
    small = (stats[:, cv2.CC_STAT_AREA] < max_px) & ~edge
    small[0] = False  # label 0 is the ink itself
    return np.asarray(ink | small[labels])


def _dist(mask: Mask) -> NDArray[np.float32]:
    """Euclidean distance of every `mask` pixel to the nearest non-mask pixel (0 outside)."""
    return np.asarray(cv2.distanceTransform(_u8(mask), cv2.DIST_L2, 5), dtype=np.float32)


def solid_masses(ink: Mask, thick_px: float) -> Mask:
    """The parts of `ink` thicker than `thick_px` (a morphological opening with a disc, via distances)."""
    core = _dist(ink) > thick_px / 2
    if not core.any():
        return np.zeros_like(ink)
    return np.asarray((_dist(~core) <= thick_px / 2) & ink)


def outline_masses(ink: Mask, thick_px: float) -> Mask:
    """`ink` with every solid mass replaced by a one-pixel outline (white inside, to colour)."""
    mass = solid_masses(ink, thick_px)
    if not mass.any():
        return ink
    inner = cv2.erode(_u8(mass), np.ones((3, 3), np.uint8)) > 0
    return np.asarray((ink & ~mass) | (mass & ~inner))


# ---- thinning (Zhang-Suen with lookup tables) --------------------------------------------------------------

# The 8 neighbours as bits, in Zhang-Suen's order p2..p9 (N, NE, E, SE, S, SW, W, NW).
_CODE = np.array([[128, 1, 2], [64, 0, 4], [32, 16, 8]], dtype=np.float32)


def _bits(code: int) -> list[int]:
    return [(code >> i) & 1 for i in range(8)]


def _crossings(b: list[int]) -> int:
    """0 → 1 transitions around the pixel (p2, p3, … p9, p2): the number of line branches it touches."""
    return sum(1 for i in range(8) if b[i] == 0 and b[(i + 1) % 8] == 1)


_N, _E, _S, _W = 1, 4, 16, 64
# A staircase corner: exactly two 4-neighbours at a right angle (N+E, E+S, S+W, W+N), which touch diagonally,
# so the pixel is redundant for 8-connectivity.
_STAIR = {_N | _E, _E | _S, _S | _W, _W | _N}


def _tables() -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.uint8]]:
    first = np.zeros(256, dtype=bool)
    second = np.zeros(256, dtype=bool)
    stair = np.zeros(256, dtype=bool)
    count = np.zeros(256, dtype=np.uint8)
    for code in range(256):
        b = _bits(code)
        p2, _p3, p4, _p5, p6, _p7, p8, _p9 = b
        n, a = sum(b), _crossings(b)
        count[code] = n
        stair[code] = code in _STAIR
        if 2 <= n <= 6 and a == 1:
            first[code] = p2 * p4 * p6 == 0 and p4 * p6 * p8 == 0
            second[code] = p2 * p4 * p8 == 0 and p2 * p6 * p8 == 0
    return first, second, stair, count


_FIRST, _SECOND, _STAIRS, _COUNT = _tables()


def neighbour_code(mask: Mask) -> NDArray[np.intp]:
    code = cv2.filter2D(mask.astype(np.float32), -1, _CODE, borderType=cv2.BORDER_CONSTANT)
    return np.asarray(np.rint(code), dtype=np.intp)


def thin(mask: Mask) -> Mask:
    """A one-pixel-wide skeleton of `mask`, strictly 8-connected (no staircase corners).

    Zhang & Suen (1984), then the staircase corners go in two checkerboard passes (two corners of one
    staircase are 4-neighbours, so they never go in the same pass and the line stays connected). On the
    result a pixel with one neighbour is a line end and one with three or more is a junction.
    """
    sk = mask.copy()
    while True:
        changed = False
        for table in (_FIRST, _SECOND):
            delete = sk & table[neighbour_code(sk)]
            if delete.any():
                sk &= ~delete
                changed = True
        if not changed:
            break
    yy, xx = np.indices(sk.shape)
    parity = (yy + xx) % 2 == 0
    for side in (parity, ~parity):
        sk &= ~(side & _STAIRS[neighbour_code(sk)])
    return sk


def endpoints(sk: Mask) -> Mask:
    return np.asarray(sk & (_COUNT[neighbour_code(sk)] == 1))


def junctions(sk: Mask) -> Mask:
    return np.asarray(sk & (_COUNT[neighbour_code(sk)] >= 3))


def prune(sk: Mask, spur_px: float, dust_px: float, rounds: int = 2) -> Mask:
    """`sk` without short spurs (branches hanging off a junction) and short loose bits."""
    for _ in range(rounds):
        junc = junctions(sk)
        near_junc = cv2.dilate(_u8(junc), np.ones((3, 3), np.uint8)) > 0
        ends = endpoints(sk)
        branches = sk & ~junc
        n, found, stats, _ = cv2.connectedComponentsWithStats(_u8(branches), connectivity=8)
        if n <= 1:
            return sk
        labels = np.asarray(found, dtype=np.int32)
        size = stats[:, cv2.CC_STAT_AREA]
        has_end = np.bincount(labels[ends], minlength=n) > 0
        touches = np.bincount(labels[near_junc & branches], minlength=n) > 0
        spur = has_end & touches & (size < spur_px)
        dust = ~touches & (size < dust_px)
        drop = spur | dust
        drop[0] = False
        if not drop.any():
            return sk
        sk = sk & ~drop[labels]
        sk = thin(drop_small(sk, 2))  # re-thin the junctions the spurs left behind
    return sk


_STEPS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _near_along(sk: Mask, start: tuple[int, int], depth: int) -> set[tuple[int, int]]:
    """Skeleton pixels within `depth` steps of `start` along the skeleton (its own line)."""
    h, w = sk.shape
    seen = {start}
    todo = deque([(start, 0)])
    while todo:
        (y, x), d = todo.popleft()
        if d == depth:
            continue
        for dy, dx in _STEPS:
            q = (y + dy, x + dx)
            if 0 <= q[0] < h and 0 <= q[1] < w and sk[q] and q not in seen:
                seen.add(q)
                todo.append((q, d + 1))
    return seen


def bridge_gaps(sk: Mask, gap_px: float) -> Mask:
    """Join every line end to the nearest other line within `gap_px` (closing the regions to colour)."""
    out = sk.copy()
    r = math.ceil(gap_px)
    h, w = sk.shape
    ys, xs = np.nonzero(endpoints(sk))
    for y, x in zip(ys.tolist(), xs.tolist(), strict=True):
        own = _near_along(sk, (y, x), round(gap_px * 2.5))
        y0, y1, x0, x1 = max(0, y - r), min(h, y + r + 1), max(0, x - r), min(w, x + r + 1)
        wy, wx = np.nonzero(sk[y0:y1, x0:x1])
        best: tuple[float, int, int] | None = None
        for py, px in zip((wy + y0).tolist(), (wx + x0).tolist(), strict=True):
            if (py, px) in own:
                continue
            d = math.hypot(py - y, px - x)
            if d <= gap_px and (best is None or d < best[0]):
                best = (d, py, px)
        if best is not None:
            line = np.zeros((h, w), np.uint8)
            cv2.line(line, (x, y), (best[2], best[1]), 255, 1, cv2.LINE_8)
            out |= line > 0
    return out


_SIDES = ((0, 1), (0, -1), (1, 0), (-1, 0))


def _shifted(labels: NDArray[np.int32], dy: int, dx: int) -> NDArray[np.int32]:
    """`labels` moved by (dy, dx): out[y, x] = labels[y + dy, x + dx] (0 beyond the edge)."""
    out = np.zeros_like(labels)
    h, w = labels.shape
    out[max(0, -dy) : h - max(0, dy), max(0, -dx) : w - max(0, dx)] = labels[
        max(0, dy) : h - max(0, -dy), max(0, dx) : w - max(0, -dx)
    ]
    return out


def merge_regions(sk: Mask, min_px: float, narrow_px: float, rounds: int = 12) -> Mask:
    """Simplify: delete the lines that close off areas too small or too narrow to colour.

    The white areas between the skeleton's lines are what a child colours. An area smaller than `min_px`
    pixels, or nowhere wider than `narrow_px` (a strip between two close lines: stairs, the ribs of a dome,
    the slats of a basket), would print as a black clump once the lines are 2.6 mm wide. Each round deletes,
    for each such area, the one line (junction to junction) it shares longest with a neighbour area, the
    smallest areas first and each area at most once per round, so it merges into its neighbour.
    """
    for _ in range(rounds):
        n_reg, found = cv2.connectedComponents(_u8(~sk), connectivity=4)
        regions = np.asarray(found, dtype=np.int32)
        area = np.bincount(regions.ravel(), minlength=n_reg).astype(np.float64)
        dist = cv2.distanceTransform(_u8(~sk), cv2.DIST_L2, 5)
        wide = np.zeros(n_reg, dtype=bool)
        wide[np.unique(regions[dist > narrow_px / 2])] = True
        bad = (area < min_px) | ~wide
        bad[0] = False  # label 0 is the skeleton itself
        if not bad.any():
            return sk
        junc = junctions(sk)
        n_br, found = cv2.connectedComponents(_u8(sk & ~junc), connectivity=8)
        branches = np.asarray(found, dtype=np.int32)
        on = branches > 0
        # (branch, region) contacts through the 4 sides of every branch pixel
        pairs = np.concatenate(
            [np.stack([branches[on], _shifted(regions, dy, dx)[on]], axis=1) for dy, dx in _SIDES]
        )
        pairs = pairs[pairs[:, 1] > 0]
        if len(pairs) == 0:
            return sk
        key, contact = np.unique(pairs[:, 0].astype(np.int64) * n_reg + pairs[:, 1], return_counts=True)
        br, reg = key // n_reg, key % n_reg
        sides: dict[int, list[tuple[int, int]]] = {}
        for b, r, k in zip(br.tolist(), reg.tolist(), contact.tolist(), strict=True):
            sides.setdefault(b, []).append((k, r))
        # each bad area's best line to delete: one it shares with another bad area if it can (an inner
        # line of a busy patch, not the patch's outline), else the one it shares longest
        best: dict[int, tuple[bool, int, int, int]] = {}
        for b, touching in sides.items():
            touching.sort(reverse=True)
            if len(touching) < 2 or touching[1][0] < 2:
                continue  # a line inside one area (an open stroke): `prune` decides
            (ka, ra), (kb, rb) = touching[0], touching[1]
            for r, other in ((ra, rb), (rb, ra)):
                if bad[r]:
                    choice = (not bad[other], -min(ka, kb), b, other)
                    if r not in best or choice < best[r]:
                        best[r] = choice
        merged: set[int] = set()
        drop = np.zeros(n_br, dtype=bool)
        for r in sorted(best, key=lambda r: (area[r], r)):  # the smallest areas first
            _good, _k, b, other = best[r]
            if r in merged or other in merged:
                continue
            drop[b] = True
            merged.update((r, other))
        if not drop.any():
            return sk
        sk = thin(sk & ~drop[branches])
    return sk


def dots(ink: Mask, min_px: float, max_px: float) -> tuple[Mask, list[tuple[float, float]]]:
    """Small round ink blobs (eyes, the dots of a face) taken out of `ink`: (ink without them, centres)."""
    _n, labels, stats, centroids = cv2.connectedComponentsWithStats(_u8(ink), connectivity=8)
    area = stats[:, cv2.CC_STAT_AREA]
    bw, bh = stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_HEIGHT]
    fill = area / np.maximum(1, bw * bh)
    round_ = (np.minimum(bw, bh) >= 0.5 * np.maximum(bw, bh)) & (fill >= 0.55)
    keep = (area >= min_px) & (area <= max_px) & round_
    keep[0] = False
    centres = [(float(centroids[i][0]), float(centroids[i][1])) for i in np.nonzero(keep)[0]]
    return np.asarray(ink & ~keep[labels]), centres


def redraw(sk: Mask, width_px: float) -> Mask:
    """The skeleton drawn with a round brush `width_px` wide (the centre pixel counts: radius (w − 1) / 2)."""
    return np.asarray(cv2.distanceTransform(_u8(~sk), cv2.DIST_L2, 5) <= (width_px - 1) / 2)


@dataclass(frozen=True)
class Cleaned:
    """The cleaned line art as a mask at `ppm` (True = ink) plus its skeleton, for checks and tests."""

    ink: Mask
    skeleton: Mask
    ppm: float
    w_mm: float
    h_mm: float


def clean_gray(gray: NDArray[np.uint8], w_mm: float, h_mm: float, params: Params = DEFAULT) -> Cleaned:
    """Steps 1–8 on a grayscale picture: the cleaned ink at `params.ppm` pixels per mm."""
    ppm = params.ppm
    area = ppm * ppm  # px per mm²
    ink = ink_mask(fit(gray, w_mm, h_mm, ppm), ppm, params.blur_mm)
    ink = drop_small(ink, params.speck_mm2 * area)
    ink = fill_holes(ink, params.hole_mm2 * area)
    ink, eyes = dots(ink, params.speck_mm2 * area, params.dot_max_mm2 * area)
    if params.masses == "outline":
        ink = outline_masses(ink, params.mass_mm * ppm)
    sk = thin(ink)
    sk = prune(sk, params.spur_mm * ppm, params.dust_mm * ppm)
    sk = bridge_gaps(sk, params.gap_mm * ppm)
    if params.region_mm2 > 0:
        sk = merge_regions(sk, params.region_mm2 * area, params.narrow_mm * ppm)
        # a deleted line can leave the stub of a corner behind (as long as the merged strip was narrow)
        sk = prune(sk, max(params.spur_mm, params.narrow_mm) * ppm, params.dust_mm * ppm)
    canvas = _u8(redraw(sk, params.width_mm * ppm))
    for x, y in eyes:  # the face dots, all one size (`ink.Pen.solid` eyes are ~3 mm across)
        cv2.circle(canvas, (round(x), round(y)), round(params.dot_mm / 2 * ppm), 255, -1)
    out = fill_holes(canvas > 0, params.pinhole_mm2 * area)
    return Cleaned(out, sk, ppm, w_mm, h_mm)


def stroke_widths_mm(cleaned: Cleaned) -> NDArray[np.float32]:
    """The printed line width (mm) at every skeleton pixel: twice its distance to the paper."""
    d = _dist(cleaned.ink)
    return np.asarray(2 * d[cleaned.skeleton] / cleaned.ppm, dtype=np.float32)


# ---- vectors -----------------------------------------------------------------------------------------------


def contours(mask: Mask, params: Params = DEFAULT) -> list[NDArray[np.float64]]:
    """The mask's edges (outer edges and holes) as smoothed, simplified closed polygons in pixels."""
    found, _ = cv2.findContours(_u8(mask), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    k = params.smooth_px
    for cnt in found:
        pts = cnt[:, 0, :].astype(np.float64)
        if len(pts) < 8:
            continue
        if k > 0 and len(pts) > 4 * k:
            window = np.ones(2 * k + 1) / (2 * k + 1)
            pad = np.concatenate([pts[-k:], pts, pts[:k]])
            pts = np.stack([np.convolve(pad[:, i], window, mode="valid") for i in range(2)], axis=1)
        approx = cv2.approxPolyDP(pts.astype(np.float32), params.epsilon_mm * params.ppm, True)[:, 0, :]
        if len(approx) >= 3:
            polys.append(approx.astype(np.float64))
    return polys


def path_d(polys: list[NDArray[np.float64]], ppm: float) -> str:
    """Closed quadratic curves through the polygons' edge mid-points (smooth, no corners), in mm."""
    parts = []
    for poly in polys:
        pts = (poly + 0.5) / ppm
        mids = (pts + np.roll(pts, -1, axis=0)) / 2
        d = f"M{fmt(mids[-1][0])} {fmt(mids[-1][1])}"
        for (px, py), (mx, my) in zip(pts, mids, strict=True):
            d += f"Q{fmt(px)} {fmt(py)} {fmt(mx)} {fmt(my)}"
        parts.append(d + "Z")
    return "".join(parts)


def body(cleaned: Cleaned, params: Params = DEFAULT) -> str:
    d = path_d(contours(cleaned.ink, params), cleaned.ppm)
    return (
        f'<rect x="0" y="0" width="{fmt(cleaned.w_mm)}" height="{fmt(cleaned.h_mm)}" fill="{PAPER}"/>'
        f'<path fill="{INK}" fill-rule="evenodd" d="{d}"/>'
    )


def clean(png: Path, w_mm: float = BOX_W, h_mm: float = BOX_H, params: Params = DEFAULT) -> str:
    """The SVG body (mm units, no `<svg>` wrapper) of `png` cleaned into print line art w_mm × h_mm."""
    return body(clean_gray(load_gray(png), w_mm, h_mm, params), params)


def save(
    png: Path,
    book: str,
    art_id: str,
    w_mm: float = BOX_W,
    h_mm: float = BOX_H,
    params: Params = DEFAULT,
    *,
    out: Path | None = None,
) -> Path:
    """`png` cleaned and written as a full SVG to `content/coloring/art/<book>/<id>.svg` (or `out`)."""
    path = out if out is not None else ART / book / f"{art_id}.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg(w_mm, h_mm, clean(png, w_mm, h_mm, params)) + "\n", encoding="utf-8")
    return path
