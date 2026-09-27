"""Child-drawing clean-up (Addendum 1 §1.2): crop to paper, fix perspective, remove shadows, boost contrast.

Pure OpenCV so it can also be ported to run on-device later (design: "clean-up runs on device").
"""

from dataclasses import dataclass

import cv2
import numpy as np

from qamra_ai.pipeline.photo_check import decode_image

WORK_MAX_SIDE = 1600
MIN_PAPER_AREA = 0.2  # paper must cover ≥ 20% of the photo to be trusted
FULL_FRAME_AREA = 0.97  # ≥ this → already a scan/tablet drawing, nothing to crop


@dataclass(frozen=True)
class CleanedDrawing:
    png: bytes
    paper_found: bool
    width: int
    height: int


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """→ top-left, top-right, bottom-right, bottom-left."""
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
        dtype=np.float32,
    )


def find_paper(img: np.ndarray) -> np.ndarray | None:
    """Largest bright 4-sided region → its 4 corners, or None."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    # paper is the bright region: Otsu threshold, then close gaps left by the drawing itself
    _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(biggest) / (img.shape[0] * img.shape[1])
    if not MIN_PAPER_AREA <= area < FULL_FRAME_AREA:
        return None
    hull = cv2.convexHull(biggest)
    peri = cv2.arcLength(hull, True)
    for eps in (0.02, 0.03, 0.05, 0.08):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4:
            return _order_corners(approx)
    return None


def warp_to_paper(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    tl, tr, br, bl = corners
    w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    m = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(img, m, (w, h))
    inset = max(2, int(min(w, h) * 0.015))  # trim paper edge / table sliver
    return warped[inset : h - inset, inset : w - inset]


def _design(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    return np.stack([np.ones_like(xs), xs, ys, xs * xs, xs * ys, ys * ys], axis=1)


def illumination(img: np.ndarray, fit_px: int = 256) -> np.ndarray | None:
    """Smooth quadratic lighting surface fitted to paper-like pixels (bright, unsaturated) only.

    A global low-order fit cannot "learn" a large crayon fill as background, unlike local
    blur/dilate estimates, so colored areas keep their color.
    """
    h, w = img.shape[:2]
    s = fit_px / max(h, w)
    small = cv2.resize(img, (max(8, int(w * s)), max(8, int(h * s))), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    sat, val = hsv[..., 1].astype(np.float64), hsv[..., 2].astype(np.float64)
    mask = (sat < 45) & (val > np.percentile(val, 25))
    ys, xs = np.nonzero(mask)
    if len(xs) < 50:
        return None
    sh, sw = small.shape[:2]
    xn, yn, v = xs / sw, ys / sh, val[ys, xs]
    keep = np.ones_like(v, dtype=bool)
    coef = np.zeros(6)
    for _ in range(4):  # drop pixels well below the surface (pencil lines, faint strokes)
        coef, *_ = np.linalg.lstsq(_design(xn[keep], yn[keep]), v[keep], rcond=None)
        resid = v - _design(xn, yn) @ coef
        keep = resid > -2.0 * max(1.0, float(resid[keep].std()))
    gx, gy = np.meshgrid(np.arange(sw) / sw, np.arange(sh) / sh)
    surface = (_design(gx.ravel(), gy.ravel()) @ coef).reshape(sh, sw)
    return cv2.resize(surface.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def remove_shadows(img: np.ndarray) -> np.ndarray:
    """Divide by the lighting surface → evenly lit paper; per-pixel gain keeps hue and saturation."""
    surface = illumination(img)
    if surface is None:
        return img
    gain = 250.0 / np.clip(surface, 40.0, 255.0)
    out: np.ndarray = np.clip(img.astype(np.float32) * gain[..., None], 0, 255).astype(np.uint8)
    return out


def boost(img: np.ndarray) -> np.ndarray:
    """Push near-white paper to white, deepen strokes, lift crayon saturation a little."""
    lut = np.clip((np.arange(256) - 20) * 255.0 / 215.0, 0, 255)
    lut[235:] = 255
    img = cv2.LUT(img, lut.astype(np.uint8))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 255)
    out: np.ndarray = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return out


def clean_drawing(data: bytes) -> CleanedDrawing:
    img = decode_image(data)
    if img is None:
        raise ValueError("unreadable drawing image")
    h, w = img.shape[:2]
    if max(h, w) > WORK_MAX_SIDE:
        s = WORK_MAX_SIDE / max(h, w)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)

    corners = find_paper(img)
    if corners is not None:
        img = warp_to_paper(img, corners)
    img = boost(remove_shadows(img))
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("could not encode cleaned drawing")
    return CleanedDrawing(buf.tobytes(), corners is not None, img.shape[1], img.shape[0])
