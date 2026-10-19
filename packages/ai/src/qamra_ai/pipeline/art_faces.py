"""Faces in a page illustration, so the story text never sits on one.

The same YuNet detector as the photo check (MIT, OpenCV zoo; detection only, no recognition), run with a
low threshold: on painted and 3D-styled characters it scores lower than on photos, and a missed face costs
more than a false one (a false one only makes the text a little smaller). Boxes are fractions of the image.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from qamra_ai.pipeline.photo_check import YUNET_MODEL

ART_FACE_SCORE = 0.3
MIN_FACE = 0.02  # ignore specks narrower than 2% of the picture
DETECT_PX = 640

Box = tuple[float, float, float, float]


def art_faces(image: Path) -> tuple[Box, ...]:
    """(x0, y0, x1, y1) of each face found, as fractions of the picture's width and height."""
    with Image.open(image) as src:
        im = src.convert("RGB")
        im.thumbnail((DETECT_PX, DETECT_PX))
    arr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    h, w = arr.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(YUNET_MODEL), "", (w, h), ART_FACE_SCORE, 0.3, 50)
    _, found = detector.detect(arr)
    boxes: list[Box] = []
    for row in found if found is not None else []:
        x, y, fw, fh = (float(v) for v in row[:4])
        if fw / w < MIN_FACE:
            continue
        boxes.append(
            (
                round(max(0.0, x / w), 4),
                round(max(0.0, y / h), 4),
                round(min(1.0, (x + fw) / w), 4),
                round(min(1.0, (y + fh) / h), 4),
            )
        )
    return tuple(boxes)
