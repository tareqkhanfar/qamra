"""The parent's framing of the child's photo: the cut-out the image model gets, and the check on it."""

import io

import pytest
from PIL import Image

from qamra_ai.pipeline.photo_check import check_photo
from qamra_ai.pipeline.photo_crop import (
    FRAME_ASPECT,
    MIN_CROP_SIDE_PX,
    PhotoCrop,
    auto_frame,
    check_framed,
    crop_photo,
    frame_photo,
)

FAR_AT = (1348, 100)  # where the 512 px fixture sits on a 2048 × 1536 photo: a child far from the camera


def _jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _far(face_png: bytes) -> bytes:
    canvas = Image.new("RGB", (2048, 1536), (150, 160, 170))
    canvas.paste(Image.open(io.BytesIO(face_png)).convert("RGB"), FAR_AT)
    return _jpeg(canvas)


def _around_face(width: int = 540) -> PhotoCrop:
    """The parent's framing of the far photo: the fixture's face in the frame, 540 × 513 px."""
    return PhotoCrop(x=FAR_AT[0] / 2048, y=FAR_AT[1] / 1536, w=width / 2048, h=width / FRAME_ASPECT / 1536)


def _halves() -> bytes:
    """200 × 100: red on the left, blue on the right."""
    img = Image.new("RGB", (200, 100), (220, 0, 0))
    img.paste((0, 0, 220), (100, 0, 200, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _open(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def _is_red(px: tuple[int, ...]) -> bool:
    return px[0] > 150 and px[2] < 80


def _is_blue(px: tuple[int, ...]) -> bool:
    return px[2] > 150 and px[0] < 80


def test_the_cut_out_is_the_framed_part_of_the_original() -> None:
    right = _open(crop_photo(_halves(), PhotoCrop(x=0.5, y=0, w=0.5, h=1)))
    assert right.size == (100, 100) and _is_blue(right.getpixel((50, 50)))  # type: ignore[arg-type]


@pytest.mark.parametrize(("rotate", "top_red"), [(90, True), (270, False)])
def test_the_cut_out_is_turned_clockwise(rotate: int, top_red: bool) -> None:
    turned = _open(crop_photo(_halves(), PhotoCrop(x=0, y=0, w=1, h=1, rotate=rotate)))
    assert turned.size == (100, 200)  # the photo's left side goes up when turned clockwise
    top, bottom = turned.getpixel((50, 20)), turned.getpixel((50, 180))
    assert _is_red(top) == top_red and _is_blue(bottom) == top_red  # type: ignore[arg-type]


def test_a_photo_without_framing_is_used_whole() -> None:
    data = _halves()
    assert crop_photo(data, None) is data
    assert crop_photo(data, {"x": "junk"}) is data  # a stored framing that doesn't hold: the whole photo


def test_the_stored_framing_is_read_back() -> None:
    crop = PhotoCrop(x=0.1, y=0.2, w=0.3, h=0.4, rotate=90)
    assert PhotoCrop.parse(crop.as_dict()) == crop
    assert PhotoCrop.parse(None) is None
    assert PhotoCrop.parse({"x": 0.9, "y": 0, "w": 0.5, "h": 0.5}) is None  # leaves the photo
    assert PhotoCrop.parse({"x": 0, "y": 0, "w": 1, "h": 1, "rotate": 45}) is None


def test_a_framing_must_have_the_frames_shape() -> None:
    assert _around_face().problem(2048, 1536) is None
    assert PhotoCrop(x=0, y=0, w=0.5, h=0.2).problem(2048, 1536) == "aspect"  # a strip, not the frame
    assert PhotoCrop(x=0.8, y=0, w=0.3, h=0.3).problem(2048, 1536) == "outside"
    assert PhotoCrop(x=0, y=0, w=0.01, h=0.01).problem(2048, 1536) == "range"
    # turned a quarter: the frame's shape is the cut-out's once turned (here 513 × 540 of the original)
    turned = PhotoCrop(x=0.5, y=0, w=513 / 2048, h=540 / 1536, rotate=90)
    assert turned.size(2048, 1536) == (540, 513) and turned.problem(2048, 1536) is None
    assert PhotoCrop(x=0.5, y=0, w=513 / 2048, h=540 / 1536).problem(2048, 1536) == "aspect"


def test_a_far_away_face_passes_once_the_parent_zooms_in(face_png: bytes) -> None:
    far = _far(face_png)
    assert [i.code for i in check_photo(far).issues] == ["face_small"]  # the whole photo: too far
    framed = check_framed(far, _around_face())
    assert framed.ok, framed
    assert framed.metrics["width"] == 540 and framed.metrics["face_ratio"] > 0.12


def test_zooming_in_past_the_photos_sharpness_is_refused_kindly(face_png: bytes) -> None:
    tiny = _around_face(width=300)  # 300 × 285 px of the original: under MIN_CROP_SIDE_PX
    check = check_framed(_far(face_png), tiny)
    assert [i.code for i in check.issues] == ["crop_small"]
    assert "صغّروها" in check.issues[0].message_ar and "Zoom out" in check.issues[0].message_en


def test_a_framing_without_the_face_fails_the_check(face_png: bytes) -> None:
    empty = PhotoCrop(x=0, y=0.5, w=600 / 2048, h=600 / FRAME_ASPECT / 1536)
    check, _ = frame_photo(_far(face_png), empty)
    assert [i.code for i in check.issues] == ["no_face"]


def test_two_children_framed_to_one(face_png: bytes) -> None:
    face = _open(face_png).resize((1024, 1024))
    two = Image.new("RGB", (2048, 1024))
    two.paste(face, (0, 0))
    two.paste(face, (1024, 0))
    data = _jpeg(two)
    whole, kept = frame_photo(data)
    assert [i.code for i in whole.issues] == ["many_faces"] and kept is None  # no guess at which child
    left = PhotoCrop(x=0.05, y=0, w=1000 / 2048, h=1000 / FRAME_ASPECT / 1024)
    check, kept = frame_photo(data, left)
    assert check.ok and kept == left


def test_a_face_cut_by_the_frame_is_refused(face_png: bytes) -> None:
    """The detector still finds a face cut by the frame's top edge (it clips its box there): refused, so the
    parent moves the photo; a little lower, with the whole face in, it passes."""
    face = _open(face_png).resize((1024, 1024))
    data = _jpeg(face)
    h = 0.66 / FRAME_ASPECT  # 674 × 640 px: a frame on the photo's left part, face 124–350 px down

    def at(y: float) -> list[str]:
        return [i.code for i in check_framed(data, PhotoCrop(x=0, y=y, w=0.66, h=h)).issues]

    assert at(0.05) == []
    cut = check_framed(data, PhotoCrop(x=0, y=0.1875, w=0.66, h=h))
    assert [i.code for i in cut.issues][:1] == ["face_cut"] and not cut.ok
    assert "كاملًا" in cut.issues[0].message_ar and "whole face" in cut.issues[0].message_en


def test_an_upload_without_framing_is_framed_around_the_face(face_png: bytes) -> None:
    far = _far(face_png)
    check, kept = frame_photo(far)
    assert check.ok and kept is not None  # the far face is fine, framed
    face = check_photo(far).face_box
    assert face is not None
    left, top, right, bottom = kept.box(2048, 1536)
    assert min(right - left, bottom - top) >= MIN_CROP_SIDE_PX
    assert left <= face[0] and right >= face[0] + face[2] and top <= face[1] and bottom >= face[1] + face[3]


def test_auto_framing_puts_the_face_in_the_oval_and_stays_inside_the_photo() -> None:
    crop = auto_frame(2000, 1600, (900, 700, 200, 240))  # face box height 240: a 571 px frame
    width, height = crop.size(2000, 1600)
    assert abs(width / height - FRAME_ASPECT) < 0.01
    cx = (crop.x + crop.w / 2) * 2000
    assert abs(cx - 1000) < 2  # the face's centre on the oval's
    edge = auto_frame(1000, 800, (0, 0, 300, 360))  # a face in the corner, and bigger than the frame allows
    assert edge.x == 0 and edge.y == 0 and edge.problem(1000, 800) is None
    assert edge.w <= 1 and edge.h <= 1


def test_a_photo_that_passes_whole_keeps_its_framing(face_png: bytes) -> None:
    check, kept = frame_photo(face_png)
    assert check.ok and kept is not None and kept.problem(512, 512) is None
