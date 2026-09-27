from pathlib import Path

import cv2
import numpy as np
import pytest
from qamra_ai.pipeline.drawing import clean_drawing


def _decode(png: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)


def test_five_fixtures_exist(drawing_paths: list[Path]) -> None:
    assert len(drawing_paths) == 5


@pytest.mark.parametrize("i", range(5))
def test_clean_drawing(drawing_paths: list[Path], i: int) -> None:
    result = clean_drawing(drawing_paths[i].read_bytes())
    img = _decode(result.png)
    assert result.paper_found
    h, w = img.shape[:2]
    assert 0.6 < w / h < 1.0  # portrait paper, table cropped away

    # paper border is flat and near-white (shadow + table removed)
    border = np.concatenate(
        [
            img[:20].reshape(-1, 3),
            img[-20:].reshape(-1, 3),
            img[:, :20].reshape(-1, 3),
            img[:, -20:].reshape(-1, 3),
        ]
    )
    assert np.median(border) > 235
    left, right = img[h // 2, : w // 8].mean(), img[h // 2, -w // 8 :].mean()
    assert abs(left - right) < 12  # the synthetic shadow darkened one side

    # the crayon fill in the middle keeps its color (not bleached to white)
    center = img[int(h * 0.45) : int(h * 0.55), int(w * 0.35) : int(w * 0.65)]
    sat = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)[..., 1]
    assert np.median(sat) > 60


def test_no_paper_still_cleans() -> None:
    img = np.full((600, 600, 3), 245, np.uint8)
    cv2.circle(img, (300, 300), 120, (200, 80, 160), -1)
    _, buf = cv2.imencode(".png", img)
    result = clean_drawing(buf.tobytes())
    assert not result.paper_found
    assert result.width == 600


def test_unreadable_drawing() -> None:
    with pytest.raises(ValueError):
        clean_drawing(b"nope")
