"""The AI line-art cleaner (`coloring.lineart`) on synthetic drawings: mixed line widths, specks, a mass."""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray
from qamra_workbook.coloring import lineart
from qamra_workbook.coloring.checks import line_problems
from qamra_workbook.coloring.ink import MAIN

W_MM, H_MM = 93.0, 116.0  # half the scene box: the same rules, a faster test
PX = 5.0  # the synthetic picture's pixels per mm (≈ a 1 MP model output at full size)


def synthetic() -> NDArray[np.uint8]:
    """Grey anti-aliased drawing: thin, medium and thick outlines, a solid blob, specks and a small gap."""
    w, h = round(W_MM * PX), round(H_MM * PX)
    img = np.full((h, w), 255, np.uint8)
    cv2.circle(img, (120, 140), 70, 0, 4, cv2.LINE_AA)  # a thin circle (0.8 mm)
    cv2.circle(img, (330, 150), 60, 40, 22, cv2.LINE_AA)  # a thick circle (4.4 mm), dark grey
    cv2.line(img, (40, 300), (420, 320), 0, 9, cv2.LINE_AA)  # a medium line (1.8 mm)
    cv2.rectangle(img, (60, 380), (220, 520), 0, 6, cv2.LINE_AA)  # a square with a gap on its right side
    cv2.rectangle(img, (214, 440), (230, 452), 255, -1)
    cv2.ellipse(img, (340, 450), (60, 45), 0, 0, 360, 0, -1)  # a solid black mass (hair)
    rng = np.random.default_rng(7)  # specks: 1–2 px dots all over
    for x, y in zip(rng.integers(0, w, 160).tolist(), rng.integers(0, h, 160).tolist(), strict=True):
        cv2.circle(img, (x, y), int(rng.integers(0, 2)), int(rng.integers(0, 120)), -1)
    return img


@pytest.fixture(scope="module")
def png(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("lineart") / "synthetic.png"
    cv2.imwrite(str(path), synthetic())
    return path


@pytest.fixture(scope="module")
def cleaned(png: Path) -> lineart.Cleaned:
    return lineart.clean_gray(lineart.load_gray(png), W_MM, H_MM)


def test_only_black_and_white(png: Path) -> None:
    body = lineart.clean(png, W_MM, H_MM)
    assert line_problems(body) == []
    assert set(re.findall(r'fill="([^"]+)"', body)) == {"#FFFFFF", "#000000"}
    assert body.count("<path") == 1 and 'fill-rule="evenodd"' in body
    assert "<svg" not in body


def test_widths_are_uniform(cleaned: lineart.Cleaned) -> None:
    widths = lineart.stroke_widths_mm(cleaned)
    assert len(widths) > 500
    # every line prints at the house width whatever its width in the picture (junctions are a bit wider)
    assert float(np.median(widths)) == pytest.approx(MAIN, abs=0.2)
    assert float(np.percentile(widths, 5)) >= MAIN - 0.3
    assert float(np.percentile(widths, 90)) <= MAIN + 0.5


def test_no_thin_grey_or_specks(cleaned: lineart.Cleaned) -> None:
    ppm = cleaned.ppm
    n, _, stats, _ = cv2.connectedComponentsWithStats(cleaned.ink.astype(np.uint8), connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA] / (ppm * ppm)
    assert areas.min() > 10, "a speck survived"  # mm²
    assert n - 1 <= 6  # the shapes only (2 circles, the line, the square, the mass outline)


def test_solid_mass_becomes_an_outline(cleaned: lineart.Cleaned) -> None:
    ppm = cleaned.ppm
    sx = W_MM / (W_MM * PX) * ppm  # the synthetic picture's px → cleaned px
    cx, cy = round(340 * sx), round(450 * sx)
    assert not cleaned.ink[cy, cx], "the mass is still solid black"
    assert cleaned.ink[cy, cx - round(60 * sx) : cx].any()  # its outline is there


def test_gap_is_closed(cleaned: lineart.Cleaned) -> None:
    sx = cleaned.ppm / PX
    inside = (round(140 * sx), round(450 * sx))  # (x, y) inside the square
    flood = (~cleaned.ink).astype(np.uint8)
    mask = np.zeros((flood.shape[0] + 2, flood.shape[1] + 2), np.uint8)
    cv2.floodFill(flood, mask, inside, 2)
    region = flood == 2
    assert not region[0, :].any() and not region[:, 0].any(), "the square leaks to the page edge"


def test_vectors_match_the_raster(cleaned: lineart.Cleaned) -> None:
    polys = lineart.contours(cleaned.ink)
    raster = np.zeros(cleaned.ink.shape, np.uint8)
    cv2.fillPoly(raster, [np.rint(p).astype(np.int32) for p in polys], 1)
    ink, drawn = cleaned.ink, raster.astype(bool)
    overlap = int((drawn & ink).sum()) / max(1, int((drawn | ink).sum()))
    assert overlap > 0.9
    # the vector outlines re-rasterised still print at the house width
    rasterised = lineart.Cleaned(
        raster.astype(bool), cleaned.skeleton & raster.astype(bool), cleaned.ppm, W_MM, H_MM
    )
    assert float(np.median(lineart.stroke_widths_mm(rasterised))) == pytest.approx(MAIN, abs=0.25)


def test_deterministic_and_saved(png: Path, tmp_path: Path) -> None:
    first = lineart.clean(png, W_MM, H_MM)
    assert lineart.clean(png, W_MM, H_MM) == first
    out = lineart.save(png, "test", "synthetic", W_MM, H_MM, out=tmp_path / "a.svg")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<svg") and f'width="{W_MM:g}mm"' in text and first in text


def test_thin_gives_one_pixel_lines() -> None:
    mask = np.zeros((60, 120), bool)
    mask[20:35, 10:110] = True
    sk = lineart.thin(mask)
    assert sk[:, 30:90].sum(axis=0).max() == 1  # one pixel across along the bar
    assert sk.sum() > 80


def _clean(img: NDArray[np.uint8], w_mm: float, h_mm: float) -> lineart.Cleaned:
    return lineart.clean_gray(img, w_mm, h_mm)


def test_busy_strips_merge_instead_of_turning_black() -> None:
    """Stairs drawn as thin lines 1.6 mm apart: too narrow to colour, so they merge (no black clump)."""
    img = np.full((300, 300), 255, np.uint8)  # 60 × 60 mm at 5 px/mm
    cv2.rectangle(img, (50, 50), (250, 250), 0, 3)
    for y in range(58, 250, 8):
        cv2.line(img, (50, y), (250, y), 0, 2)
    c = _clean(img, 60, 60)
    inside = c.ink[round(12 * c.ppm) : round(48 * c.ppm), round(12 * c.ppm) : round(48 * c.ppm)]
    assert inside.mean() < 0.35  # mostly white to colour, not a black block


def test_eyes_stay_as_dots() -> None:
    """A face: an outline, two small eye blobs (with a highlight) and a smile; the eyes come back as dots."""
    img = np.full((300, 300), 255, np.uint8)  # 60 × 60 mm at 5 px/mm
    cv2.circle(img, (150, 150), 100, 0, 5)
    for x in (115, 185):
        cv2.circle(img, (x, 130), 9, 0, -1)
        cv2.circle(img, (x + 3, 127), 3, 255, -1)  # the highlight: a hole the cleaning fills
    cv2.ellipse(img, (150, 185), (35, 20), 0, 20, 160, 0, 5)
    c = _clean(img, 60, 60)
    s = c.ppm / 5
    for x in (115, 185):
        assert c.ink[round(130 * s), round(x * s)], "an eye was lost"
    assert c.ink[round(205 * s), round(150 * s)], "the smile was lost"
