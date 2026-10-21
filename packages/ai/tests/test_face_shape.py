"""The face's proportions measured on the photo, in words for the character prompts (2026-10-21)."""

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from tests_helpers import png

import qamra_ai.pipeline.face_shape as face_shape_module
from qamra_ai.pipeline.face_shape import FaceShape, face_shape, measure_face

FIXTURE = Path(__file__).parent / "fixtures" / "face-astronaut-public-domain.png"


def _encoded(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_a_face_looking_at_the_camera_is_measured() -> None:
    shape = measure_face(FIXTURE.read_bytes())
    assert shape is not None and 0.7 < shape.ratio < 0.9
    words = face_shape([png("white"), FIXTURE.read_bytes()])  # the first photo that can be measured
    assert words is not None and words.startswith("from the top of the forehead to the chin, the face is ")
    assert words.endswith("Keep exactly this shape.")


def test_no_face_is_not_measured() -> None:
    assert measure_face(png("white", (400, 400))) is None and face_shape([png("tan")]) is None
    assert measure_face(b"not an image") is None


def _row(*, eyes: tuple[float, float, float, float], nose_x: float, score: float = 0.95) -> np.ndarray:
    """A YuNet row: box 100 × 125 at (50, 40), the eyes, the nose, the mouth corners, the score."""
    rx, ry, lx, ly = eyes
    return np.array([[50, 40, 100, 125, rx, ry, lx, ly, nose_x, 110, 80, 130, 120, 130, score]], np.float32)


@pytest.mark.parametrize(
    ("row", "measured"),
    [
        (_row(eyes=(75, 80, 125, 80), nose_x=100), True),  # level, looking at the camera: 100 / 125
        (_row(eyes=(75, 80, 125, 95), nose_x=100), False),  # the eyes 17° off level: a tilted head
        (_row(eyes=(75, 80, 125, 80), nose_x=112), False),  # the nose off the middle: a turned head
        (_row(eyes=(75, 80, 125, 80), nose_x=100, score=0.8), False),  # an unsure detection
    ],
)
def test_only_a_face_looking_at_the_camera_is_measured(
    row: np.ndarray, measured: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(face_shape_module, "detect_faces", lambda img: row)
    shape = measure_face(_encoded(Image.new("RGB", (200, 200), "white")))
    assert (shape == FaceShape(0.8)) if measured else shape is None
    two = np.concatenate([row, row])
    monkeypatch.setattr(face_shape_module, "detect_faces", lambda img: two)
    assert measure_face(_encoded(Image.new("RGB", (200, 200), "white"))) is None  # two faces


@pytest.mark.parametrize(
    ("ratio", "band"),
    [
        (0.70, "long and narrow"),
        (0.79, "an oval, clearly longer than it is wide: about 4 wide to 5 long"),
        (0.86, "a little longer than it is wide"),
        (0.95, "about as wide as it is long"),
    ],
)
def test_the_ratio_in_words(ratio: float, band: str) -> None:
    words = FaceShape(ratio).words
    assert band in words and f"(width to length {ratio:.2f})" in words
