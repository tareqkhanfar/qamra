"""Bring generated images to print resolution. Phase 0 uses Lanczos; a real upscaler is decided in Phase 2."""

import io

from PIL import Image


def print_px(trim_mm: float, bleed_mm: float, dpi: int) -> int:
    return round((trim_mm + 2 * bleed_mm) / 25.4 * dpi)


def to_print_jpeg(data: bytes, px: int, dpi: int = 300, quality: int = 90) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    img = img.resize((px, px), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, dpi=(dpi, dpi), optimize=True)
    return buf.getvalue()


def to_jpeg(data: bytes, max_side: int = 1600, quality: int = 88) -> bytes:
    """For non-bleed assets (drawings, sheets) placed inside a page."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()
