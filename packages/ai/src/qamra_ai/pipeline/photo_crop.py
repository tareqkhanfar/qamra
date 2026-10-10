"""The parent's framing of the child's photo (the create flow's photo step, owner's request of 2026-10-10).

The web shows the photo in a 358 × 340 frame with a face-guide oval; the parent drags, zooms and turns it
until the face sits in the oval. The API keeps that framing as numbers on the photo (`ChildPhoto.crop`), never
as a second, re-encoded copy: `x, y, w, h` are fractions (0–1) of the stored original (upright, at most
2048 px), and `rotate` turns the cut-out clockwise in 90° steps. The image model gets the whole frame (head
and shoulders), not only the oval. A photo without a framing (older uploads, the admin's test books) is used
whole.

The photo check runs on the cut-out, so a far-away face is fine once the parent zooms in, as long as the
cut-out keeps `MIN_CROP_SIDE_PX`. A photo uploaded without a framing is framed around the face found.
"""

import io
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps

from qamra_ai.pipeline.photo_check import MIN_SIDE_PX, PhotoCheck, PhotoIssue, check_photo

FRAME_W, FRAME_H = 358, 340  # the photo frame (apps/web/src/lib/photoCrop.ts `FRAME`)
FRAME_ASPECT = FRAME_W / FRAME_H
ASPECT_TOLERANCE = 0.02  # rounding (the web frames with the same aspect, never a measured one)
MIN_CROP_SIDE_PX = 400  # the cut-out's short side (a whole photo needs 512: there the face may be small)
MIN_FRACTION = 0.05
# Framing an upload the parent didn't frame: the face box (YuNet: brows to chin) takes this share of the
# frame's height, centred here, so the head fills the oval (cx 179, cy 140, ry 104 of the 358 × 340 frame).
FACE_HEIGHT = 0.42
FACE_CENTER = (0.5, 0.45)
# The face box must stay this far inside the cut-out: the detector clips a face cut by the frame's edge to
# that edge (it still finds the eyes), and a half face draws badly.
EDGE_MARGIN = 0.03
ROTATIONS = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180, 270: Image.Transpose.ROTATE_90}
FRAMEABLE = {"face_small"}  # whole-photo issues that framing around the face may fix


@dataclass(frozen=True)
class PhotoCrop:
    x: float
    y: float
    w: float
    h: float
    rotate: int = 0

    @classmethod
    def parse(cls, value: Mapping[str, Any] | None) -> "PhotoCrop | None":
        """The stored framing, or None: none was saved, or it doesn't hold (then the whole photo is used)."""
        if not value:
            return None
        try:
            crop = cls(
                x=float(value["x"]),
                y=float(value["y"]),
                w=float(value["w"]),
                h=float(value["h"]),
                rotate=int(value.get("rotate", 0)),
            )
        except (KeyError, TypeError, ValueError):
            return None
        return crop if crop.out_of_range() is None else None

    def as_dict(self) -> dict[str, float | int]:
        return {
            "x": round(self.x, 6),
            "y": round(self.y, 6),
            "w": round(self.w, 6),
            "h": round(self.h, 6),
            "rotate": self.rotate,
        }

    def out_of_range(self) -> str | None:
        """What is wrong with the numbers themselves (any photo size), or None."""
        if self.rotate not in (0, 90, 180, 270):
            return "rotate"
        if not (
            0 <= self.x <= 1
            and 0 <= self.y <= 1
            and MIN_FRACTION <= self.w <= 1
            and MIN_FRACTION <= self.h <= 1
        ):
            return "range"
        if self.x + self.w > 1.001 or self.y + self.h > 1.001:
            return "outside"
        return None

    def problem(self, width: int, height: int) -> str | None:
        """What makes this framing impossible on a `width` × `height` photo (the frame's shape), or None."""
        if (wrong := self.out_of_range()) is not None:
            return wrong
        cw, ch = self.size(width, height)
        if not ch or abs(cw / ch / FRAME_ASPECT - 1) > ASPECT_TOLERANCE:
            return "aspect"
        return None

    def box(self, width: int, height: int) -> tuple[int, int, int, int]:
        """(left, top, right, bottom) in pixels of the original, inside it."""
        left, top = round(self.x * width), round(self.y * height)
        right = min(width, round((self.x + self.w) * width))
        bottom = min(height, round((self.y + self.h) * height))
        return left, top, max(left + 1, right), max(top + 1, bottom)

    def size(self, width: int, height: int) -> tuple[int, int]:
        """The cut-out's (width, height) in pixels, once turned."""
        left, top, right, bottom = self.box(width, height)
        w, h = right - left, bottom - top
        return (h, w) if self.rotate in (90, 270) else (w, h)

    @property
    def zoomed(self) -> bool:
        """The parent zoomed in: the frame no longer spans the photo's full width or height."""
        return self.w < 0.999 and self.h < 0.999


def image_size(data: bytes) -> tuple[int, int]:
    """(width, height) of an upright photo; ValueError when it can't be read."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            return ImageOps.exif_transpose(im).size
    except OSError as e:  # PIL.UnidentifiedImageError is an OSError
        raise ValueError("unreadable photo") from e


def crop_photo(data: bytes, crop: "PhotoCrop | Mapping[str, Any] | None") -> bytes:
    """The photo as the image model gets it: the parent's framing, turned upright (as JPEG); without a
    framing, the whole photo as stored."""
    framing = crop if isinstance(crop, PhotoCrop) or crop is None else PhotoCrop.parse(crop)
    if framing is None:
        return data
    with Image.open(io.BytesIO(data)) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    img = img.crop(framing.box(*img.size))
    if framing.rotate in ROTATIONS:
        img = img.transpose(ROTATIONS[framing.rotate])
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def auto_frame(width: int, height: int, face_box: tuple[int, int, int, int]) -> PhotoCrop:
    """A head-and-shoulders framing around the face found, as the parent would set it: the face in the oval,
    never smaller than `MIN_CROP_SIDE_PX` and never past the photo's edges."""
    fx, fy, fw, fh = face_box
    ch = max(fh / FACE_HEIGHT, MIN_CROP_SIDE_PX)  # the frame is wider than tall: its height is the short side
    cw = ch * FRAME_ASPECT
    fit = min(1.0, width / cw, height / ch)  # zoomed out at most to the whole photo (the frame stays covered)
    cw, ch = cw * fit, ch * fit
    left = min(max(0.0, fx + fw / 2 - FACE_CENTER[0] * cw), width - cw)
    top = min(max(0.0, fy + fh / 2 - FACE_CENTER[1] * ch), height - ch)
    return PhotoCrop(x=left / width, y=top / height, w=cw / width, h=ch / height)


def check_framed(data: bytes, crop: PhotoCrop) -> PhotoCheck:
    """The photo check on what the image model will get: the parent's framing of the photo."""
    width, height = image_size(data)
    cw, ch = crop.size(width, height)
    if min(cw, ch) < MIN_CROP_SIDE_PX:
        code = "crop_small" if crop.zoomed else "too_small"
        return PhotoCheck(ok=False, issues=[PhotoIssue(code)], metrics={"width": cw, "height": ch})
    check = check_photo(crop_photo(data, crop), min_side=MIN_CROP_SIDE_PX)
    if check.face_box is not None and _at_edge(check.face_box, cw, ch):
        check.issues.insert(0, PhotoIssue("face_cut"))  # moving the photo is the first thing to fix
        check.ok = False
    return check


def _at_edge(box: tuple[int, int, int, int], width: int, height: int) -> bool:
    x, y, w, h = box
    mx, my = EDGE_MARGIN * width, EDGE_MARGIN * height
    return x < mx or y < my or x + w > width - mx or y + h > height - my


def frame_photo(data: bytes, crop: PhotoCrop | None = None) -> tuple[PhotoCheck, PhotoCrop | None]:
    """The check an upload passes, and the framing kept with it.

    With the parent's framing: the photo (512 px at least, as always), then the cut-out are checked. Without
    one: the whole photo is checked, then framed around the face it shows; a face found but too far away is
    fine when the framed cut-out passes. When framing doesn't hold, a photo that passed whole is kept whole.
    """
    if crop is not None:
        try:
            width, height = image_size(data)
        except ValueError:
            return PhotoCheck(ok=False, issues=[PhotoIssue("unreadable")]), None
        if min(width, height) < MIN_SIDE_PX:
            return PhotoCheck(ok=False, issues=[PhotoIssue("too_small")]), None
        return check_framed(data, crop), crop
    whole = check_photo(data)
    if whole.face_box is None or not {i.code for i in whole.issues} <= FRAMEABLE:
        return whole, None
    width, height = image_size(data)
    framing = auto_frame(width, height, whole.face_box)
    framed = check_framed(data, framing)
    if framed.ok:
        return framed, framing
    return whole, None
