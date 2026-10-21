"""The face's proportions, measured on the photo, in words for the character prompts (2026-10-21).

The owner's report: in the cartoon and 3D styles the child's face came out rounder, wider and younger than
his child's, though the hair, eyes and smile were close. A stylized image model simplifies a face toward
its idea of a cartoon child: round, wide, short in the chin. Words like "oval" alone did not hold it, so the
photo's own proportion goes into the prompt as a measured fact (`likeness.v4`, "Measured on the photo: …").

What is measured: the width of the face against its length, from the face box of the YuNet detector the photo
check already runs (MIT, OpenCV zoo; detection only, no recognition, nothing leaves the server). The box spans
the cheeks and runs from the top of the forehead to the chin. On the owner's test photo of a 5-year-old it
reads 0.79; the cartoon and 3D portraits drawn from it read 0.82–0.95.

The measure is only trusted on a face that looks at the camera: one face, a confident detection, the eyes
level (roll ≤ 8°) and the nose between them (a turned head looks narrower). YuNet's eye points follow a
tilted head only loosely, so the roll guard catches a clear tilt, not a slight one; the bands are coarse
(4:5, 6:7…) for that reason. Otherwise None, and the prompt
goes without the line.
"""

import math
from dataclasses import dataclass

import cv2

from qamra_ai.pipeline.photo_check import decode_image, detect_faces

MIN_SCORE = 0.85
MAX_ROLL_DEG = 8.0
MAX_YAW = 0.15  # the nose's offset from the eyes' midpoint, in eye distances
DETECT_PX = 1024
# width/length → words, the first bound the ratio is under; the last band has no upper bound
BANDS: tuple[tuple[float, str], ...] = (
    (0.74, "long and narrow, clearly longer than it is wide: about 3 wide to 4 long"),
    (0.82, "an oval, clearly longer than it is wide: about 4 wide to 5 long"),
    (0.90, "a little longer than it is wide: about 6 wide to 7 long"),
    (math.inf, "about as wide as it is long"),
)


@dataclass(frozen=True)
class FaceShape:
    ratio: float  # face width / face length (top of the forehead to the chin)

    @property
    def words(self) -> str:
        band = next(text for bound, text in BANDS if self.ratio < bound)
        return (
            f"from the top of the forehead to the chin, the face is {band} "
            f"(width to length {self.ratio:.2f}). Keep exactly this shape."
        )


def measure_face(photo: bytes) -> FaceShape | None:
    """The face's width-to-length ratio on a photo of one child looking at the camera, else None."""
    img = decode_image(photo)
    if img is None:
        return None
    h, w = img.shape[:2]
    scale = DETECT_PX / max(h, w)
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    faces = detect_faces(img)
    if len(faces) != 1:
        return None
    row = faces[0]
    fw, fh, score = float(row[2]), float(row[3]), float(row[-1])
    (rx, ry), (lx, ly), (nx, _) = (row[4], row[5]), (row[6], row[7]), (row[8], row[9])
    eyes = math.hypot(lx - rx, ly - ry)
    if score < MIN_SCORE or fh <= 0 or eyes <= 0:
        return None
    roll = abs(math.degrees(math.atan2(ly - ry, lx - rx)))
    yaw = abs(nx - (rx + lx) / 2) / eyes
    if roll > MAX_ROLL_DEG or yaw > MAX_YAW:
        return None
    return FaceShape(round(fw / fh, 2))


def face_shape(photos: list[bytes]) -> str | None:
    """The prompts' measured line from the first photo that can be measured (as framed), or None."""
    for photo in photos:
        shape = measure_face(photo)
        if shape is not None:
            return shape.words
    return None
