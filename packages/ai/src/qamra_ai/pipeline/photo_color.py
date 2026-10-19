"""The photo's light, made neutral before an image model sees it (owner's report of 2026-10-19).

A photo taken at night under yellow street light (or under a blue screen or LED) carries that light's colour,
and an edit model copies it: the watercolor portrait and sheet came out brownish-yellow, almost sepia. So the
reference we send (never the stored original) gets a gentle, clamped white balance and exposure correction
after the framing crop (`reference_photo`).

How it reads the light:
- the face is found (YuNet, as in the photo check) and left out of the estimate together with the hair and the
  neck: skin and hair are warm by nature, and a head-and-shoulders photo is mostly skin and hair;
- strongly coloured pixels (a red T-shirt, a green wall), near-black and clipped ones are left out too;
- what is left (background, grey or white clothes) gives the light's colour, "shades of grey" (a p-norm
  mean of linear RGB, between the grey-world average and the brightest patch).

How much it corrects:
- nothing inside a tolerance box around neutral (a warm room, a cool shade stay as they are); only the part of
  the cast past the box, and only `STRENGTH` of that; each channel's gain at most `MAX_GAIN` either way;
- the skin guard: the face's skin, once corrected, must stay inside a skin range (warm, never grey, green or
  blue); the correction is scaled back until it does. Skin is never pushed past where it started;
- exposure: a dark or blown face is brought toward a normal skin brightness (at most `MAX_LIFT` up or
  `MIN_LIFT` down), then a hazy photo gets a mild levels stretch (at most `MAX_STRETCH`);
- without a face, or with too little neutral area to read the light, the colour is left alone.

A photo that needs nothing comes back byte for byte as it was.
"""

import io
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps

from qamra_ai.pipeline.photo_check import detect_faces
from qamra_ai.pipeline.photo_crop import PhotoCrop, crop_photo

WORK_PX = 512  # the statistics are read on a copy at most this big
P_NORM = 4.0  # shades of grey: 1 = grey world, ∞ = the brightest patch
MAX_SAT = 0.55  # HSV saturation (sRGB) above which a pixel is a coloured object, not the light
DARK, CLIPPED = 0.06, 0.97  # sRGB max channel: too dark to read colour, or clipped
MIN_NEUTRAL = 0.06  # share of the picture that must be left to read the light from
# Tolerance around neutral, in ln(R/G) and ln(B/G) of the light: casts inside are kept (a warm room, shade)
A_RANGE = (-0.06, 0.10)
B_RANGE = (-0.15, 0.06)
STRENGTH = 0.8  # share of the cast past the tolerance that is taken out
MAX_GAIN = 1.5  # any channel's gain, either way
MIN_CHANGE = 0.02  # |ln gain| below this is no change
# Skin, in linear light: ln(R/G) and ln(B/G) of the cheeks after the correction must stay inside this range
SKIN_A = (math.log(1.12), math.log(3.0))
SKIN_B = (math.log(0.30), math.log(0.92))
# Exposure: the cheeks' sRGB luma is brought toward this range
SKIN_LUMA = (0.42, 0.80)
MAX_LIFT, MIN_LIFT = 1.6, 0.8  # linear exposure gain
MAX_STRETCH = 1.25  # levels stretch of a hazy photo
LEVELS = (0.005, 0.995)  # luma percentiles a stretch maps toward (0.02, 0.98)
MIN_SPAN = 0.25  # a narrower luma range is a plain picture (a wall), never stretched


@dataclass(frozen=True)
class ColorFix:
    """What `neutralize` did (all 1.0 / False: nothing)."""

    gains: tuple[float, float, float] = (1.0, 1.0, 1.0)  # linear R, G, B
    light: tuple[float, float] | None = None  # ln(R/G), ln(B/G) of the light read, when read
    skin: tuple[float, float] | None = None  # the same for the cheeks, before
    exposure: float = 1.0
    stretch: float = 1.0
    stretch_low: float = 0.0  # sRGB value the stretch maps to 0.02
    face: bool = False

    @property
    def changed(self) -> bool:
        return (
            any(abs(math.log(g)) >= MIN_CHANGE for g in self.gains)
            or abs(math.log(self.exposure)) >= MIN_CHANGE
            or self.stretch > 1.0 + MIN_CHANGE
        )


def to_linear(srgb: np.ndarray) -> np.ndarray:
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def to_srgb(lin: np.ndarray) -> np.ndarray:
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


def _luma(srgb: np.ndarray) -> np.ndarray:
    return np.asarray(srgb @ np.array([0.2126, 0.7152, 0.0722]), dtype=np.float64)


def _chroma(rgb: np.ndarray) -> tuple[float, float]:
    r, g, b = (max(float(c), 1e-6) for c in rgb)
    return math.log(r / g), math.log(b / g)


def _face(srgb: np.ndarray) -> tuple[int, int, int, int] | None:
    """The surest face's box (x, y, w, h) on the working copy, or None."""
    bgr = np.ascontiguousarray((srgb[:, :, ::-1] * 255).round().astype(np.uint8))
    faces = detect_faces(bgr)
    if not len(faces):
        return None
    x, y, w, h = (int(v) for v in max(faces, key=lambda f: f[-1])[:4])
    return (x, y, w, h) if w > 8 and h > 8 else None


def _cheeks(lin: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray | None:
    """Linear RGB of the cheeks and nose (below the eyes, above the mouth): the median, robust to a shadow."""
    x, y, w, h = box
    region = lin[y + int(0.48 * h) : y + int(0.70 * h), x + int(0.18 * w) : x + int(0.82 * w)].reshape(-1, 3)
    return np.median(region, axis=0) if len(region) >= 16 else None


def _head_mask(shape: tuple[int, int], box: tuple[int, int, int, int]) -> np.ndarray:
    """True on the head, hair and neck (left out of the light's estimate)."""
    x, y, w, h = box
    mask = np.zeros(shape, dtype=bool)
    top, bottom = max(0, int(y - 0.8 * h)), min(shape[0], int(y + 1.6 * h))
    left, right = max(0, int(x - 0.45 * w)), min(shape[1], int(x + 1.45 * w))
    mask[top:bottom, left:right] = True
    return mask


def read_light(srgb: np.ndarray, box: tuple[int, int, int, int] | None) -> tuple[float, float] | None:
    """ln(R/G), ln(B/G) of the light, from the neutral-ish pixels away from the head; None when too few."""
    hi, lo = srgb.max(axis=2), srgb.min(axis=2)
    sat = (hi - lo) / np.maximum(hi, 1e-6)
    usable = (sat <= MAX_SAT) & (hi >= DARK) & (hi <= CLIPPED)
    if box is not None:
        usable &= ~_head_mask(usable.shape, box)
    if usable.mean() < MIN_NEUTRAL:
        return None
    pixels = to_linear(srgb[usable])
    light = np.mean(pixels**P_NORM, axis=0) ** (1 / P_NORM)
    return _chroma(light)


def _past(value: float, bounds: tuple[float, float]) -> float:
    lo, hi = bounds
    return value - hi if value > hi else value - lo if value < lo else 0.0


def _clamp_gain(log_gain: float) -> float:
    limit = math.log(MAX_GAIN)
    return max(-limit, min(limit, log_gain))


def _inside(skin: tuple[float, float]) -> bool:
    a, b = skin
    return SKIN_A[0] <= a <= SKIN_A[1] and SKIN_B[0] <= b <= SKIN_B[1]


def white_balance(light: tuple[float, float], skin: tuple[float, float] | None) -> tuple[float, float, float]:
    """Linear (R, G, B) gains taking out the cast past the tolerance, scaled back so the skin stays skin."""
    a, b = light
    log_r = _clamp_gain(-STRENGTH * _past(a, A_RANGE))
    log_b = _clamp_gain(-STRENGTH * _past(b, B_RANGE))
    if skin is not None:
        for step in range(10, -1, -1):  # the largest share of the correction that keeps the skin in range
            t = step / 10
            moved = (skin[0] + t * log_r, skin[1] + t * log_b)
            # skin already outside the range (an odd light, make-up, a painted face) may not move further out
            if _inside(moved) or (not _inside(skin) and _distance(moved) <= _distance(skin)):
                break
        log_r, log_b = t * log_r, t * log_b
    gains = np.exp(np.array([log_r, 0.0, log_b]))
    gains /= float(gains @ np.array([0.2126, 0.7152, 0.0722]))  # keep the brightness of a grey
    return float(gains[0]), float(gains[1]), float(gains[2])


def _distance(skin: tuple[float, float]) -> float:
    return abs(_past(skin[0], SKIN_A)) + abs(_past(skin[1], SKIN_B))


def _exposure(cheeks_luma: float) -> float:
    lo, hi = SKIN_LUMA
    if lo <= cheeks_luma <= hi or cheeks_luma <= 0:
        return 1.0
    target = lo if cheeks_luma < lo else hi
    gain = (float(to_linear(np.array(target))) / float(to_linear(np.array(cheeks_luma)))) ** 0.75  # gently
    return float(max(MIN_LIFT, min(MAX_LIFT, gain)))


def _stretch(srgb: np.ndarray) -> tuple[float, float]:
    """(scale, low) of a mild levels stretch of a hazy photo (1.0, 0.0: none)."""
    lo, hi = np.quantile(_luma(srgb), LEVELS)
    span = float(hi - lo)
    if span < MIN_SPAN or span >= 0.96:  # a plain picture, or one that already spans the range
        return 1.0, 0.0
    scale = min(MAX_STRETCH, 0.96 / span)
    return (scale, float(lo) - 0.02 / scale) if scale > 1.0 + MIN_CHANGE else (1.0, 0.0)


def plan_fix(srgb: np.ndarray) -> ColorFix:
    """What to do with a picture (sRGB floats 0–1, H × W × 3); reads a copy at most `WORK_PX`."""
    h, w = srgb.shape[:2]
    scale = min(1.0, WORK_PX / max(h, w))
    small = np.asarray(srgb, dtype=np.float64)
    if scale < 1:
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        resized = cv2.resize(small.astype(np.float32), size, interpolation=cv2.INTER_AREA)
        small = np.asarray(resized, dtype=np.float64)
    box = _face(small)
    cheeks = _cheeks(to_linear(small), box) if box is not None else None
    skin = _chroma(cheeks) if cheeks is not None else None
    light = read_light(small, box) if box is not None else None
    gains = white_balance(light, skin) if light is not None else (1.0, 1.0, 1.0)
    exposure = 1.0
    if cheeks is not None:
        corrected = to_srgb(cheeks * np.array(gains))
        exposure = _exposure(float(_luma(corrected)))
    balanced = to_srgb(to_linear(small) * np.array(gains) * exposure)
    stretch, low = _stretch(balanced)
    return ColorFix(
        gains=gains,
        light=light,
        skin=skin,
        exposure=exposure,
        stretch=stretch,
        stretch_low=low,
        face=box is not None,
    )


def apply_fix(srgb: np.ndarray, fix: ColorFix) -> np.ndarray:
    out = to_srgb(to_linear(srgb) * np.array(fix.gains) * fix.exposure)
    if fix.stretch > 1.0:
        out = np.clip((out - fix.stretch_low) * fix.stretch, 0.0, 1.0)
    return out


def neutralize(data: bytes) -> tuple[bytes, ColorFix]:
    """A photo with its light made neutral and its exposure normal (as JPEG), and what was done. A photo that
    needs nothing, or can't be read, comes back as it was."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            img = ImageOps.exif_transpose(im).convert("RGB")
    except OSError:
        return data, ColorFix()
    srgb = np.asarray(img, dtype=np.float64) / 255.0
    fix = plan_fix(srgb)
    if not fix.changed:
        return data, fix
    out = apply_fix(srgb, fix)
    buf = io.BytesIO()
    Image.fromarray((out * 255).round().astype(np.uint8)).save(buf, format="JPEG", quality=92)
    return buf.getvalue(), fix


def reference_photo(data: bytes, crop: "PhotoCrop | Mapping[str, Any] | None") -> bytes:
    """The photo as an image model gets it: the parent's framing (`crop_photo`), its light made neutral."""
    return neutralize(crop_photo(data, crop))[0]
