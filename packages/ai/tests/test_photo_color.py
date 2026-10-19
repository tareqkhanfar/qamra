"""The photo's light made neutral before an image model sees it (owner's report of 2026-10-19: a night photo
under yellow street light gave a sepia watercolor). Synthetic casts on the public-domain face fixture."""

import io
import math

import numpy as np
import pytest
from PIL import Image

from qamra_ai.pipeline.photo_color import (
    MAX_GAIN,
    MAX_LIFT,
    SKIN_A,
    SKIN_B,
    ColorFix,
    neutralize,
    plan_fix,
    reference_photo,
    to_linear,
    to_srgb,
    white_balance,
)
from qamra_ai.pipeline.photo_crop import PhotoCrop, crop_photo


def _srgb(data: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.float64) / 255.0


def _png(srgb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray((np.clip(srgb, 0, 1) * 255).round().astype(np.uint8)).save(buf, format="PNG")
    return buf.getvalue()


def _cast(srgb: np.ndarray, light: tuple[float, float, float]) -> np.ndarray:
    """The same scene under a coloured light (linear RGB multiplied by the light)."""
    return to_srgb(to_linear(srgb) * np.array(light))


def _off(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def test_a_daylight_photo_comes_back_byte_for_byte(face_png: bytes) -> None:
    out, fix = neutralize(face_png)
    assert out is face_png and not fix.changed
    assert fix.face and fix.light is not None and fix.skin is not None


@pytest.mark.parametrize(
    ("name", "light", "kept"),
    [
        ("sodium street light", (1.0, 0.78, 0.42), 0.6),
        ("tungsten bulb", (1.0, 0.85, 0.6), 0.6),
        ("blue screen", (0.6, 0.82, 1.0), 0.75),  # gentler: a cool shade inside the tolerance stays
    ],
)
def test_a_cast_is_taken_out_and_the_skin_comes_back_toward_its_own(
    face_png: bytes, name: str, light: tuple[float, float, float], kept: float
) -> None:
    daylight = plan_fix(_srgb(face_png)).skin
    cast = _cast(_srgb(face_png), light)
    out, fix = neutralize(_png(cast))
    assert fix.changed, name
    assert fix.skin is not None and daylight is not None
    after = plan_fix(_srgb(out)).skin
    assert after is not None
    # clearly closer to the skin in daylight, and the correction goes the right way
    assert _off(after, daylight) < kept * _off(fix.skin, daylight), name
    r, _, b = fix.gains
    warm = light[0] > light[2]
    assert (r < 1 < b) if warm else (r > 1 > b), name


def test_gains_are_clamped_even_under_an_extreme_light(face_png: bytes) -> None:
    fix = plan_fix(_cast(_srgb(face_png), (1.0, 0.45, 0.08)))
    g = np.array(fix.gains)
    ratios = g / g[1]  # relative to green: what each correction did to the channel
    assert all(1 / MAX_GAIN - 1e-6 <= r <= MAX_GAIN + 1e-6 for r in ratios)


def test_a_mild_warm_room_is_left_as_it_is(face_png: bytes) -> None:
    fix = plan_fix(_cast(_srgb(face_png), (1.0, 0.97, 0.92)))
    assert all(abs(math.log(g)) < 0.03 for g in fix.gains)


def test_the_skin_guard_never_greys_pale_skin() -> None:
    pale = (math.log(1.18), math.log(0.8))  # fair skin, barely warmer than grey
    gains = white_balance((0.6, -0.9), pale)  # a beige wall read as a strong yellow light
    after = (pale[0] + math.log(gains[0] / gains[1]), pale[1] + math.log(gains[2] / gains[1]))
    assert SKIN_A[0] - 1e-9 <= after[0] and after[1] <= SKIN_B[1] + 1e-9
    full = white_balance((0.6, -0.9), None)  # no face: the whole correction
    assert full[0] / full[1] < gains[0] / gains[1]


def test_skin_already_out_of_range_is_never_pushed_further_out() -> None:
    grey = (math.log(1.02), math.log(0.97))  # a face lit by a blue screen read as almost grey
    gains = white_balance((0.5, -0.7), grey)  # a correction that would cool it further
    assert gains[0] / gains[1] >= 1 - 1e-9 or gains[2] / gains[1] <= 1 + 1e-9


def test_without_a_face_the_colours_are_left_alone() -> None:
    flat = np.full((600, 600, 3), 0.5) * np.array([1.0, 0.85, 0.5])  # a yellow-lit grey wall, no one there
    data = _png(flat)
    out, fix = neutralize(data)
    assert out is data and not fix.face and fix.gains == (1.0, 1.0, 1.0)


def test_a_dark_face_is_lifted_gently(face_png: bytes) -> None:
    dark = to_srgb(to_linear(_srgb(face_png)) * 0.2)
    fix = plan_fix(dark)
    assert 1.0 < fix.exposure <= MAX_LIFT


def test_the_reference_is_the_framing_then_the_colour_step(face_png: bytes) -> None:
    cast = _png(_cast(_srgb(face_png), (1.0, 0.78, 0.42)))
    crop = PhotoCrop(x=0.0, y=0.0, w=1.0, h=1.0)
    assert reference_photo(cast, crop) == neutralize(crop_photo(cast, crop))[0]
    assert reference_photo(cast, None) == neutralize(cast)[0]
    assert reference_photo(face_png, None) is face_png


def test_an_unreadable_photo_comes_back_as_it_was() -> None:
    assert neutralize(b"not an image") == (b"not an image", ColorFix())
