import io

import cv2
import numpy as np
from PIL import Image


def encode(img: np.ndarray, ext: str = ".png") -> bytes:
    ok, buf = cv2.imencode(ext, img)
    assert ok
    return bytes(buf.tobytes())


def png(color: str = "white", size: tuple[int, int] = (64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()
