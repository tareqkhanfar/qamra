"""Classic hero edit geometry: box normalization, crop with margin, edit size, feathered paste, text boxes."""

import io

import pytest
from PIL import Image

from qamra_ai.cost import FAL_MEGAPIXEL
from qamra_ai.pipeline.classic_geometry import (
    EDIT_MAX_MP,
    EDIT_MIN_MP,
    HeroBox,
    crop_rect,
    edit_size,
    feather_mask,
    mirror,
    normalize_box,
    paste_back,
    preview_copy,
    seam_score,
    text_box,
)


def test_fractions_pass_through() -> None:
    assert normalize_box(0.2, 0.3, 0.4, 0.5) == HeroBox(0.2, 0.3, 0.4, 0.5)


def test_percent_and_pixel_answers_are_normalized() -> None:
    assert normalize_box(20, 30, 40, 50) == HeroBox(0.2, 0.3, 0.4, 0.5)  # percent
    box = normalize_box(256, 128, 512, 640, width=1024, height=1024)  # pixels of the image it saw
    assert box == HeroBox(0.25, 0.125, 0.5, 0.625)
    assert normalize_box(2000, 10, 900, 900, width=1024, height=1024) is None  # neither


def test_boxes_are_clipped_to_the_page_and_junk_is_rejected() -> None:
    assert normalize_box(-0.1, 0.5, 0.5, 0.7) == HeroBox(0.0, 0.5, 0.4, 0.5)
    assert normalize_box(0.5, 0.5, 0.01, 0.4) is None  # too thin to be a child
    assert normalize_box(0.5, 0.5, 0, 0.4) is None
    assert normalize_box("x", 0.5, 0.2, 0.4) is None
    assert normalize_box(0.1, None, 0.2, 0.4) is None
    assert normalize_box(float("nan"), 0.1, 0.2, 0.4) is None
    assert normalize_box(True, 0.1, 0.2, 0.4) is None


def test_box_round_trip_and_mirror() -> None:
    box = HeroBox(0.1, 0.2, 0.3, 0.4)
    assert HeroBox.from_dict(box.to_dict()) == box
    assert HeroBox.from_dict(None) is None and HeroBox.from_dict({"x": 1}) is None
    assert box.mirrored() == HeroBox(0.6, 0.2, 0.3, 0.4)
    assert box.mirrored().mirrored() == box
    assert box.rect(1000, 500) == (100, 100, 400, 300)


def test_crop_grows_by_the_margin_and_stays_on_the_page() -> None:
    assert crop_rect(HeroBox(0.4, 0.4, 0.2, 0.2), 1000, 1000, margin=0.25) == (350, 350, 650, 650)
    assert crop_rect(HeroBox(0.0, 0.8, 0.3, 0.2), 1000, 1000, margin=0.5) == (0, 700, 450, 1000)


@pytest.mark.parametrize("size", [(3000, 4000), (400, 600), (2551, 1524), (900, 900), (5031, 2551)])
def test_edit_size_keeps_the_shape_within_the_megapixel_budget(size: tuple[int, int]) -> None:
    w, h = edit_size(*size)
    mp = w * h / FAL_MEGAPIXEL
    assert w % 16 == 0 and h % 16 == 0
    assert mp <= EDIT_MAX_MP + 1e-9
    assert mp >= EDIT_MIN_MP * 0.9  # rounding down to multiples of 16 costs a little
    assert abs(w / h - size[0] / size[1]) < 0.05


def test_feather_mask_is_soft_inside_the_page_and_hard_at_the_trim() -> None:
    def at(mask: Image.Image, xy: tuple[int, int]) -> int:
        value = mask.getpixel(xy)
        assert isinstance(value, int)
        return value

    mask = feather_mask((200, 100), 20, (False, False, False, False))
    assert at(mask, (100, 50)) == 255 and at(mask, (0, 50)) < 40
    edge = feather_mask((200, 100), 20, (True, False, False, False))  # left edge on the page border
    assert at(edge, (0, 50)) == 255 and at(edge, (199, 50)) < 40


def _page(color: str = "#3050a0", size: tuple[int, int] = (600, 400)) -> Image.Image:
    return Image.new("RGB", size, color)


def test_paste_back_changes_only_the_rectangle() -> None:
    page = _page()
    edited = Image.new("RGB", (160, 160), "#e0a080")
    out = paste_back(page, edited, (200, 100, 400, 300))
    assert out.size == page.size
    assert out.getpixel((10, 10)) == page.getpixel((10, 10))  # outside: untouched
    assert out.getpixel((590, 390)) == page.getpixel((590, 390))
    center = out.getpixel((300, 200))
    assert isinstance(center, tuple) and center[0] > 150  # inside: the edit, tone-matched by at most 24


def test_tone_matching_hides_the_seam() -> None:
    """An edit whose colors drifted a little is shifted back at its border, so no step shows at the edge."""
    page = _page("#808080")
    drifted = Image.new("RGB", (200, 200), "#8c8c8c")
    out = paste_back(page, drifted, (200, 100, 400, 300))
    assert seam_score(out, (200, 100, 400, 300)) < 2.0


def test_mirror_and_preview_copy() -> None:
    img = Image.new("RGB", (200, 100), "white")
    img.paste(Image.new("RGB", (50, 100), "red"), (0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    flipped = Image.open(io.BytesIO(mirror(buf.getvalue())))
    red = flipped.getpixel((190, 50))
    assert isinstance(red, tuple) and red[0] > 200 and red[1] < 60  # the red band moved to the right
    small = Image.open(io.BytesIO(preview_copy(buf.getvalue(), max_side=100, label="PREVIEW")))
    assert max(small.size) == 100 and small.format == "JPEG"


def test_text_boxes_follow_the_layout() -> None:
    assert text_box("split", "none") is None
    top = text_box("full", "top")
    assert top is not None and top["area"] == "top" and top["y"] == 0.06
    side = text_box("full", "right")
    assert side is not None and side["area"] == "right" and side["x"] == 0.54
    spread = text_box("spread", "top-right")  # the page read first in Arabic: the right half
    assert spread is not None and spread["x"] >= 0.5 and spread["x"] + spread["w"] <= 1.0
    ltr = text_box("spread", "bottom-left")
    assert ltr is not None and ltr["x"] + ltr["w"] <= 0.5 and ltr["y"] == 0.52
