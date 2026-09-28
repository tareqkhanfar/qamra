import cv2
import numpy as np
from tests_helpers import encode

from qamra_ai.pipeline.photo_check import check_photo

# The fixture is 512 px (the minimum). Upscale so resizing tests stay above MIN_SIDE_PX.


def _big(face_png: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(face_png, np.uint8), cv2.IMREAD_COLOR)
    return cv2.resize(img, (1024, 1024))


def test_good_photo_passes(face_png: bytes) -> None:
    result = check_photo(face_png)
    assert result.ok, result
    assert result.face_box is not None


def test_unreadable() -> None:
    assert [i.code for i in check_photo(b"not an image").issues] == ["unreadable"]


def test_too_small(face_png: bytes) -> None:
    small = cv2.resize(_big(face_png), (300, 300))
    assert [i.code for i in check_photo(encode(small)).issues] == ["too_small"]


def test_no_face() -> None:
    blank = np.full((800, 800, 3), 200, np.uint8)
    assert [i.code for i in check_photo(encode(blank)).issues] == ["no_face"]


def test_two_faces(face_png: bytes) -> None:
    img = _big(face_png)
    two = np.hstack([img, img])
    assert [i.code for i in check_photo(encode(two)).issues] == ["many_faces"]


def test_dark(face_png: bytes) -> None:
    dark = (_big(face_png) * 0.25).astype(np.uint8)
    codes = [i.code for i in check_photo(encode(dark)).issues]
    assert "dark" in codes or codes == ["no_face"]


def test_blurry(face_png: bytes) -> None:
    blurry = cv2.GaussianBlur(_big(face_png), (0, 0), 9)
    codes = [i.code for i in check_photo(encode(blurry)).issues]
    assert "blurry" in codes or codes == ["no_face"]


def test_messages_are_bilingual() -> None:
    issue = check_photo(b"x").issues[0]
    assert issue.message_ar and issue.message_en
