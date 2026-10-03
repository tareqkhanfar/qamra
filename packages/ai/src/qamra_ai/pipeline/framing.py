"""A drawn page is one continuous picture, edge to edge (Addendum 11 §3).

Image models sometimes answer "keep the top calm for the text" by stacking a separate pale band above the
scene behind a white dividing line, or keep a white paper margin around a watercolor. Both are found here
from the pixels, without a model call, and the page is redrawn like any review miss.
"""

import io

import numpy as np
from PIL import Image

LIGHT = 225.0  # a near-white line or band (0–255 luminance)
FLAT = 1.5  # its spread across the whole width: a pasted fill; a painted sky or wall is never this even
PAPER = 6.0  # white paper with grain around such a fill: a fade to the edge, judged with the edge


def _runs(flat: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) of every run of two or more flat lines."""
    runs, y, n = [], 0, len(flat)
    while y < n:
        if flat[y]:
            end = y
            while end < n and flat[end]:
                end += 1
            if end - y >= 2:
                runs.append((y, end))
            y = end
        else:
            y += 1
    return runs


def framing_problem(data: bytes, *, light_edges_ok: bool = False) -> str | None:
    """'split' for a flat light line or band inside the picture (two images stacked), 'border' for one
    along an edge (a margin or a pasted band), else None. `light_edges_ok`: watercolor fades to the paper."""
    img = Image.open(io.BytesIO(data)).convert("L")
    img.thumbnail((512, 512))
    a = np.asarray(img, dtype=np.float32)
    problem = None
    for lines in (a, a.T):  # rows, then columns
        n = len(lines)
        mean, spread = lines.mean(axis=1), lines.std(axis=1)
        flat = (mean > LIGHT) & (spread < FLAT)
        paper = (mean > LIGHT) & (spread < PAPER)  # white with grain: a fade to the paper, not a picture
        near = max(2, round(n * 0.03))
        for start, end in _runs(flat):
            while start > 0 and paper[start - 1]:
                start -= 1
            while end < n and paper[end]:
                end += 1
            if start > near and end < n - near:
                return "split"
            if not light_edges_ok:
                problem = "border"
    return problem
