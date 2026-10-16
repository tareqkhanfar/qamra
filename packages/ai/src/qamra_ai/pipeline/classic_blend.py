"""Putting the Classic hero edit back on the template page (2026-10-16 fix of the violet patches).

klein repaints the whole crop it is given, so pasting the crop back showed its rectangle: a colour wash,
added props, a recoloured outfit. Only the hero's head is taken from the edit now:

1. the edit is aligned to the template crop (a small shift or zoom of the model's output is undone);
2. its colours are matched to the template in a ring around the head (mean and spread in Lab), so a tint
   the model added disappears;
3. it is blended in through a soft mask around the head and hair only, so every other pixel (the clothes,
   the background, other children) stays the template's, and no edge can show.
"""

import cv2
import numpy as np
from PIL import Image

from qamra_ai.pipeline.classic_geometry import Rect

U8 = np.ndarray  # uint8 images and masks (OpenCV's types are loose; the names say what is meant)
F32 = np.ndarray  # float32 images and alphas

HEAD_FEATHER = 0.08  # the mask's soft edge, as a fraction of the head's shorter side
MASK_GROW = (0.06, 0.02, 0.06, 0.16)  # the hard mask around the head box: left, top, right, bottom (neck)
RING = (0.04, 0.3)  # the colour-matching ring: from just outside the mask to 30% of the head size
STD_RATIO = (0.75, 1.33)  # how far the colour spread may be stretched
MAX_SHIFT = (40.0, 30.0, 30.0)  # how far the Lab means may move (L, a, b on OpenCV's 0–255 scale)
ALIGN_PX = 384  # alignment runs on a copy this size
# klein often returns the crop zoomed in (up to ≈ 27% in the 2026-10-16 proof) or shifted: undone when the
# estimate is plausible (a zoom, a shift, almost no shear) and fits well; beyond these it is not trusted
MAX_ALIGN_SHIFT = 0.25
ALIGN_ZOOM = (0.75, 1.45)
MAX_SHEAR = 0.04
MIN_ALIGN_FIT = 0.6
HAIR_ZONE = (0.45, 0.1, 0.45, 0.9)  # where the hair may have changed around the head box (× head size)
CHANGE_DE = 14.0  # a Lab distance above this (after colour matching) counts as changed
HAIR_DE = 22.0  # this close to the hair's colour (before or after) counts as hair


def head_mask(size: tuple[int, int], head: Rect, grow: tuple[float, ...] = MASK_GROW) -> U8:
    """The hard mask (0/255) of the head and hair: the head box grown a little, with rounded corners."""
    w, h = size
    left, top, right, bottom = head
    hw, hh = right - left, bottom - top
    x0, y0 = max(0, round(left - hw * grow[0])), max(0, round(top - hh * grow[1]))
    x1, y1 = min(w, round(right + hw * grow[2])), min(h, round(bottom + hh * grow[3]))
    mask = np.zeros((h, w), np.uint8)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return mask
    r = max(1, round(min(x1 - x0, y1 - y0) * 0.35))
    cv2.rectangle(mask, (x0 + r, y0), (x1 - r, y1), 255, -1)
    cv2.rectangle(mask, (x0, y0 + r), (x1, y1 - r), 255, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(mask, (cx, cy), r, 255, -1)
    return mask


def soften(mask: U8, feather_px: float) -> F32:
    """0..1 alpha: the hard mask grown by half of `feather_px` and blurred, so what the mask covers is almost
    fully the edit (a half-blended old ponytail shows as a ghost) and the edge fades out beyond it."""
    grow = max(1, round(feather_px / 2))
    grown = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
    alpha = cv2.GaussianBlur(grown.astype(np.float32) / 255.0, (0, 0), max(1.0, feather_px / 2))
    return np.clip(alpha, 0.0, 1.0)


def inside(size: tuple[int, int], margin: int, open_sides: tuple[bool, bool, bool, bool]) -> U8:
    """255 except a `margin` band along the crop's sides that lie inside the page (`open_sides`: left, top,
    right, bottom lie on the page border, where nothing lies beyond and no band is needed)."""
    w, h = size
    out = np.zeros((h, w), np.uint8)
    left, top, right, bottom = (0 if side else margin for side in open_sides)
    out[top : max(top, h - bottom), left : max(left, w - right)] = 255
    return out


def align(edited: U8, original: U8, keep: U8) -> tuple[U8, U8]:
    """(`edited` warped onto `original`, where the warped edit has real pixels: 255).

    Estimated (affine) where both should be the same (`keep` > 0). The model often returns the crop zoomed
    in or shifted; pasted as it is, the new head would sit beside the template's neck and the old hair would
    show twice. A failed or implausible estimate leaves the edit as it is."""
    h, w = original.shape[:2]
    scale = min(1.0, ALIGN_PX / max(w, h))
    size = (max(8, round(w * scale)), max(8, round(h * scale)))
    a = cv2.resize(cv2.cvtColor(original, cv2.COLOR_RGB2GRAY), size, interpolation=cv2.INTER_AREA)
    b = cv2.resize(cv2.cvtColor(edited, cv2.COLOR_RGB2GRAY), size, interpolation=cv2.INTER_AREA)
    m = cv2.resize(keep, size, interpolation=cv2.INTER_NEAREST)
    whole = np.full((h, w), 255, np.uint8)
    start: np.ndarray = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-6)
    try:
        fit, found = cv2.findTransformECC(
            a.astype(np.float32), b.astype(np.float32), start, cv2.MOTION_AFFINE, criteria, m, 5
        )
    except cv2.error:
        return edited, whole
    warp = np.asarray(found, dtype=np.float32)
    lin = warp[:, :2]
    zoom = float(np.sqrt(abs(np.linalg.det(lin))))
    shear = float(max(abs(lin[0, 1]), abs(lin[1, 0]), abs(lin[0, 0] - lin[1, 1]) / 2))
    shift = max(abs(warp[0, 2]) / size[0], abs(warp[1, 2]) / size[1])
    plausible = ALIGN_ZOOM[0] <= zoom <= ALIGN_ZOOM[1] and shear <= MAX_SHEAR and shift <= MAX_ALIGN_SHIFT
    if fit < MIN_ALIGN_FIT or not plausible:
        return edited, whole
    if shift < 0.5 / max(size) and abs(zoom - 1) < 1e-3:
        return edited, whole  # already in place
    full = warp.copy()
    full[:, 2] /= scale
    flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
    moved = cv2.warpAffine(edited, full, (w, h), flags=flags, borderMode=cv2.BORDER_REPLICATE)
    valid = cv2.warpAffine(whole, full, (w, h), flags=flags, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return moved, valid


def match_colors(edited: U8, original: U8, ring: U8) -> U8:
    """The edit with its Lab mean and spread moved to the template's, measured in `ring` (> 0)."""
    sel = ring > 0
    if sel.sum() < 32:
        return edited
    le = cv2.cvtColor(edited, cv2.COLOR_RGB2LAB).astype(np.float32)
    lo = cv2.cvtColor(original, cv2.COLOR_RGB2LAB).astype(np.float32)
    out = np.empty_like(le)
    for c in range(3):
        e, o = le[..., c][sel], lo[..., c][sel]
        me, mo = float(e.mean()), float(o.mean())
        se, so = float(e.std()), float(o.std())
        ratio = float(np.clip(so / se, *STD_RATIO)) if se > 1e-3 else 1.0
        shift = float(np.clip(mo - me, -MAX_SHIFT[c], MAX_SHIFT[c]))
        out[..., c] = (le[..., c] - me) * ratio + me + shift
    out = np.clip(out, 0, 255).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_LAB2RGB)


def ring_around(mask: U8, head_side: float) -> U8:
    inner = max(1, round(head_side * RING[0]))
    outer = max(inner + 2, round(head_side * RING[1]))
    grow = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outer + 1, 2 * outer + 1)))
    near = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * inner + 1, 2 * inner + 1)))
    ring: U8 = ((grow > 0) & (near == 0)).astype(np.uint8) * 255
    return ring


def delta_e(lab: F32, color: F32) -> F32:
    """Per-pixel distance (ΔE 1976) of an OpenCV Lab image to one Lab colour."""
    d = lab - color
    d[..., 0] *= 100 / 255
    out: F32 = np.sqrt((d**2).sum(axis=2))
    return out


def hair_color(lab: F32, mask: U8) -> F32:
    """The hair's colour: the median of the darkest quarter of the head (hair is the head's largest dark
    area; the eyes are small)."""
    pixels = lab[mask > 0]
    if len(pixels) == 0:
        return np.zeros(3, np.float32)
    dark = pixels[pixels[:, 0] <= np.percentile(pixels[:, 0], 25)]
    out: F32 = np.median(dark, axis=0).astype(np.float32)
    return out


def changed_hair(edit: U8, original: U8, mask: U8, head: Rect, valid: U8) -> U8:
    """The head mask grown over what the edit changed next to it: hair that got longer or shorter (a
    ponytail gone, curls on the shoulders). Only changed areas touching the head count, inside a zone
    around the head box; elsewhere (clothes, background) the template wins."""
    h, w = mask.shape
    left, top, right, bottom = head
    hw, hh = right - left, bottom - top
    zone = np.zeros_like(mask)
    # The head itself, a little grown; then the two bands where hair falls: beside the face and down the
    # sides of the shoulders. Not beside the top of the head (a window, a cap's surroundings) and not under
    # the chin (the neck, the collar, the hands: the template's).
    zone[
        max(0, round(top - hh * HAIR_ZONE[1])) : round(bottom + hh * 0.1),
        max(0, round(left - hw * 0.1)) : round(right + hw * 0.1),
    ] = 255
    y0, y1 = round(top + hh * 0.3), min(h, round(bottom + hh * HAIR_ZONE[3]))
    zone[y0:y1, max(0, round(left - hw * HAIR_ZONE[0])) : round(left + hw * 0.25)] = 255
    zone[y0:y1, round(right - hw * 0.25) : min(w, round(right + hw * HAIR_ZONE[2]))] = 255
    sigma = max(1.0, min(hw, hh) / 120)
    le = cv2.GaussianBlur(cv2.cvtColor(edit, cv2.COLOR_RGB2LAB).astype(np.float32), (0, 0), sigma)
    lo = cv2.GaussianBlur(cv2.cvtColor(original, cv2.COLOR_RGB2LAB).astype(np.float32), (0, 0), sigma)
    d = le - lo
    d[..., 0] *= 100 / 255  # OpenCV's L is 0–255; ΔE wants 0–100
    # only hair counts: the old hair where it is gone (a ponytail) or the new hair where it was not (curls
    # on the shoulders). A companion's arm or a window the model redrew beside the head is not hair.
    hair_then, hair_now = hair_color(lo, mask), hair_color(le, mask)
    hairy = (delta_e(lo, hair_then) < HAIR_DE) | (delta_e(le, hair_now) < HAIR_DE)
    changed = (np.sqrt((d**2).sum(axis=2)) > CHANGE_DE) & hairy & (zone > 0) & (valid > 0)
    k = max(3, round(min(hw, hh) * 0.03)) | 1
    shape = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    grown = cv2.morphologyEx(changed.astype(np.uint8) * 255, cv2.MORPH_OPEN, shape)
    grown = cv2.morphologyEx(
        grown, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3 * k, 3 * k))
    )
    count, labels = cv2.connectedComponents(np.maximum(grown, mask))
    touching = set(np.unique(labels[mask > 0]).tolist()) - {0}
    if count <= 1 or not touching:
        return mask
    out: U8 = np.maximum(np.isin(labels, list(touching)).astype(np.uint8) * 255, mask)
    return out


def blend_head(
    page: Image.Image, edited: Image.Image, rect: Rect, head: Rect, feather: float = HEAD_FEATHER
) -> tuple[Image.Image, Image.Image]:
    """(the page with the edit's head blended in, the 0–255 alpha used inside `rect`).

    `rect` is the crop that was edited (page pixels); `head` the head box in page pixels. Outside the soft
    mask around the head every pixel stays the template's, exactly."""
    left, top, right, bottom = rect
    size = (right - left, bottom - top)
    original: U8 = np.asarray(page.crop(rect).convert("RGB"), dtype=np.uint8)
    edit: U8 = np.asarray(edited.convert("RGB").resize(size, Image.Resampling.LANCZOS), dtype=np.uint8)
    local = (head[0] - left, head[1] - top, head[2] - left, head[3] - top)
    mask = head_mask(size, local)
    side = float(min(local[2] - local[0], local[3] - local[1]))
    feather_px = max(2.0, side * feather)
    keep = cv2.erode(255 - mask, np.ones((3, 3), np.uint8))  # where the edit should equal the template
    edit, valid = align(edit, original, keep)
    edit = match_colors(edit, original, ring_around(mask, side) & valid)
    mask = changed_hair(edit, original, mask, local, valid)
    # the soft edge needs room: three feathers inside the crop and inside the edit's real pixels
    room = 3 * max(1, round(feather_px)) + 2
    open_sides = (left == 0, top == 0, right == page.width, bottom == page.height)
    mask &= inside(size, room, open_sides)
    mask &= cv2.erode(valid, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * room + 1, 2 * room + 1)))
    alpha = soften(mask, feather_px)
    mixed = original.astype(np.float32) * (1 - alpha[..., None]) + edit.astype(np.float32) * alpha[..., None]
    patch = Image.fromarray(np.clip(np.rint(mixed), 0, 255).astype(np.uint8))
    out = page.convert("RGB").copy()
    out.paste(patch, (left, top))
    return out, Image.fromarray((alpha * 255).astype(np.uint8))
