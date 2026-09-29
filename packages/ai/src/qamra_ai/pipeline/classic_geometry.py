"""Geometry of the Classic hero edit (Addendum 4 §1A): crop the hero box with a margin, size the crop for the
edit model, and paste the edited crop back with a feathered edge.

Boxes are normalized (x, y, w, h) fractions of the page image, top-left origin, so one hero box serves the
print file, the preview and a mirrored (English) page alike. Rectangles are pixel (left, top, right, bottom).
"""

import io
import math
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat

from qamra_ai.cost import FAL_MEGAPIXEL

Rect = tuple[int, int, int, int]

MIN_SIDE = 0.04  # a box smaller than 4% of the page on a side is not a hero
EDIT_MAX_MP = 0.6  # the edit is billed per megapixel: 0.6 MP keeps a page near $0.015 (plan §3)
EDIT_MIN_MP = 0.35  # small crops are enlarged so the model has enough face to work with
EDIT_MULTIPLE = 16  # FLUX.2 sizes are multiples of 16
MARGIN = 0.15  # context around the hero box, per side, as a fraction of the box
FEATHER = 0.06  # feather width as a fraction of the crop's shorter side
MAX_TONE_SHIFT = 24  # the most the edit's colors are moved (per channel, 0–255) to match the page


@dataclass(frozen=True)
class HeroBox:
    x: float
    y: float
    w: float
    h: float

    def to_dict(self) -> dict[str, float]:
        return {"x": round(self.x, 4), "y": round(self.y, 4), "w": round(self.w, 4), "h": round(self.h, 4)}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HeroBox | None":
        if not data:
            return None
        return normalize_box(data.get("x"), data.get("y"), data.get("w"), data.get("h"))

    def mirrored(self) -> "HeroBox":
        """The same box on the horizontally flipped page (English books use mirrored templates)."""
        return HeroBox(round(1 - self.x - self.w, 6), self.y, self.w, self.h)

    def rect(self, width: int, height: int) -> Rect:
        return (
            round(self.x * width),
            round(self.y * height),
            round((self.x + self.w) * width),
            round((self.y + self.h) * height),
        )


FULL_PAGE = HeroBox(0.0, 0.0, 1.0, 1.0)


def _num(v: object) -> float | None:
    if isinstance(v, bool) or not isinstance(v, int | float | str):
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return f if math.isfinite(f) else None


def normalize_box(
    x: object, y: object, w: object, h: object, *, width: int | None = None, height: int | None = None
) -> HeroBox | None:
    """A clean (x, y, w, h) in 0..1, or None when the answer is unusable.

    Vision models sometimes answer in percent or in pixels instead of fractions. Values above 1 that fit in
    0..100 are percent (a hero is never under 100 px on a page); larger ones are pixels when the image size
    is known and they fit it. The box is then clipped to the page, and a box smaller than `MIN_SIDE` on a
    side (or empty) is rejected.
    """
    vals = [_num(v) for v in (x, y, w, h)]
    if any(v is None for v in vals):
        return None
    fx, fy, fw, fh = (float(v) for v in vals if v is not None)
    if max(fx, fy, fw, fh) > 1.0 + 1e-6:
        if fx + fw <= 100.5 and fy + fh <= 100.5:
            fx, fy, fw, fh = fx / 100, fy / 100, fw / 100, fh / 100
        elif width and height and fx + fw <= width * 1.02 and fy + fh <= height * 1.02:
            fx, fw, fy, fh = fx / width, fw / width, fy / height, fh / height
        else:
            return None
    if fw <= 0 or fh <= 0:
        return None
    x0, y0 = max(0.0, fx), max(0.0, fy)
    x1, y1 = min(1.0, fx + fw), min(1.0, fy + fh)
    if x1 - x0 < MIN_SIDE or y1 - y0 < MIN_SIDE:
        return None
    return HeroBox(round(x0, 6), round(y0, 6), round(x1 - x0, 6), round(y1 - y0, 6))


def crop_rect(box: HeroBox, width: int, height: int, margin: float = MARGIN) -> Rect:
    """The hero box grown by `margin` of its size on every side, clipped to the page."""
    left, top, right, bottom = box.rect(width, height)
    mx = round((right - left) * margin)
    my = round((bottom - top) * margin)
    return (max(0, left - mx), max(0, top - my), min(width, right + mx), min(height, bottom + my))


def edit_size(
    width: int, height: int, *, max_mp: float = EDIT_MAX_MP, min_mp: float = EDIT_MIN_MP
) -> tuple[int, int]:
    """Output size for the edit: the crop's shape, between `min_mp` and `max_mp`, multiples of 16."""
    mp = width * height / FAL_MEGAPIXEL
    target = min(max_mp, max(min_mp, mp))
    scale = math.sqrt(target / mp)
    w = max(EDIT_MULTIPLE, int(width * scale) // EDIT_MULTIPLE * EDIT_MULTIPLE)
    h = max(EDIT_MULTIPLE, int(height * scale) // EDIT_MULTIPLE * EDIT_MULTIPLE)
    return w, h


def open_rgb(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert("RGB")


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def to_jpeg(img: Image.Image, *, quality: int = 92, dpi: int | None = 300) -> bytes:
    buf = io.BytesIO()
    kwargs: dict[str, Any] = {"format": "JPEG", "quality": quality}
    if dpi:
        kwargs["dpi"] = (dpi, dpi)
    img.convert("RGB").save(buf, **kwargs)
    return buf.getvalue()


def feather_mask(
    size: tuple[int, int], feather: int, open_sides: tuple[bool, bool, bool, bool]
) -> Image.Image:
    """White inside, fading to black over `feather` px at the crop's edges.

    `open_sides` (left, top, right, bottom) marks edges that lie on the page border: nothing lies beyond
    them, so they stay hard (a fade there would let the old placeholder show through at the trim).
    """
    w, h = size
    feather = max(1, min(feather, w // 4, h // 4))
    mask = Image.new("L", size, 0)
    left, top, right, bottom = open_sides
    inset = (
        -feather * 2 if left else feather,
        -feather * 2 if top else feather,
        w + feather * 2 if right else w - feather,
        h + feather * 2 if bottom else h - feather,
    )
    ImageDraw.Draw(mask).rectangle(inset, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather / 2))


def match_border(edited: Image.Image, original: Image.Image, band: float = 0.08) -> Image.Image:
    """Shift the edited crop's colors so its outer band matches the original's (hides tone drift at seams)."""
    w, h = edited.size
    b = max(2, round(min(w, h) * band))
    ring = Image.new("L", (w, h), 255)
    ImageDraw.Draw(ring).rectangle((b, b, w - b, h - b), fill=0)
    src = ImageStat.Stat(original, ring).mean
    dst = ImageStat.Stat(edited, ring).mean
    # a small, even drift only: a big difference means the border itself changed, which is the QA's call
    shift = [
        max(-MAX_TONE_SHIFT, min(MAX_TONE_SHIFT, round(s - d))) for s, d in zip(src[:3], dst[:3], strict=True)
    ]
    if all(abs(v) <= 1 for v in shift):
        return edited
    bands = [
        ch.point(lambda v, s=s: max(0, min(255, v + s))) for ch, s in zip(edited.split(), shift, strict=True)
    ]
    return Image.merge("RGB", bands)


def paste_back(
    page: Image.Image, edited: Image.Image, rect: Rect, feather_frac: float = FEATHER
) -> Image.Image:
    """The page with the edited crop resized into `rect` and blended in with a feathered edge."""
    left, top, right, bottom = rect
    size = (right - left, bottom - top)
    original = page.crop(rect)
    patch = match_border(edited.convert("RGB").resize(size, Image.Resampling.LANCZOS), original)
    open_sides = (left == 0, top == 0, right == page.width, bottom == page.height)
    mask = feather_mask(size, round(min(size) * feather_frac), open_sides)
    out = page.copy()
    out.paste(patch, (left, top), mask)
    return out


def seam_score(page: Image.Image, rect: Rect) -> float:
    """Mean color jump across the pasted rectangle's inner edges (0 = invisible). A cheap local seam check."""
    left, top, right, bottom = rect
    gray = page.convert("L")
    jumps: list[float] = []
    for x in (left, right):
        if 2 <= x <= page.width - 2:
            a = gray.crop((x - 2, top, x - 1, bottom))
            c = gray.crop((x + 1, top, x + 2, bottom))
            jumps.append(ImageStat.Stat(ImageChops.difference(a, c)).mean[0])
    for y in (top, bottom):
        if 2 <= y <= page.height - 2:
            a = gray.crop((left, y - 2, right, y - 1))
            c = gray.crop((left, y + 1, right, y + 2))
            jumps.append(ImageStat.Stat(ImageChops.difference(a, c)).mean[0])
    return round(sum(jumps) / len(jumps), 2) if jumps else 0.0


def mirror(data: bytes) -> bytes:
    """A horizontally flipped copy (print JPEG): an English book reads left to right, so its text panels and
    the art's calm areas swap sides."""
    return to_jpeg(open_rgb(data).transpose(Image.Transpose.FLIP_LEFT_RIGHT), quality=95)


# The text panel on a page, matching qamra_pdf.checks.AREAS (fractions of one page).
TEXT_AREAS: dict[str, tuple[float, float, float, float]] = {
    "top": (0.06, 0.06, 0.94, 0.40),
    "bottom": (0.06, 0.52, 0.94, 0.86),
    "left": (0.06, 0.06, 0.46, 0.86),
    "right": (0.54, 0.06, 0.94, 0.86),
}


def text_box(layout: str, text_area: str) -> dict[str, Any] | None:
    """Where the text panel sits on the template image, as a normalized box with its area name.

    Split pages set their text below the picture (no box). A spread's panel sits on the page read first:
    its half of the double-width image.
    """
    if layout == "split" or text_area == "none":
        return None
    vertical = "bottom" if text_area.startswith("bottom") else "top"
    if layout == "spread":
        x0, y0, x1, y1 = TEXT_AREAS[vertical]
        offset = 0.5 if text_area.endswith("right") else 0.0
        x0, x1 = offset + x0 / 2, offset + x1 / 2
        area = text_area
    else:
        area = text_area if text_area in ("left", "right") else vertical
        x0, y0, x1, y1 = TEXT_AREAS[area]
    return {"x": x0, "y": y0, "w": round(x1 - x0, 4), "h": round(y1 - y0, 4), "area": area}


def preview_copy(data: bytes, *, max_side: int = 720, label: str = "PREVIEW") -> bytes:
    """A small watermarked JPEG for the parent's preview: never print quality, marked diagonally."""
    img = open_rgb(data)
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    w, h = img.size
    layer = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = ImageFont.load_default(size=max(14, w // 18))
    step_y = max(60, h // 3)
    for row, y in enumerate(range(0, h * 2, step_y)):
        draw.text(((row % 2) * w // 3, y), f"{label}          " * 4, fill=(255, 255, 255, 80), font=font)
    layer = layer.rotate(30, resample=Image.Resampling.BICUBIC).crop((w // 2, h // 2, w // 2 + w, h // 2 + h))
    out = Image.alpha_composite(img.convert("RGBA"), layer)
    return to_jpeg(out.convert("RGB"), quality=82, dpi=None)
