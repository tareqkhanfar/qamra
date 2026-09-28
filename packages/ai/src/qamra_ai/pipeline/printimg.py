"""Image files for print and proof: exact print-size crops, spread halves, small web/QA copies."""

import io

from PIL import Image


def _open_rgb(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert("RGB")


def _jpeg(img: Image.Image, quality: int, dpi: int | None = None) -> bytes:
    buf = io.BytesIO()
    kwargs: dict[str, object] = {"format": "JPEG", "quality": quality, "optimize": True}
    if dpi:
        kwargs["dpi"] = (dpi, dpi)
    img.save(buf, **kwargs)  # type: ignore[arg-type]
    return buf.getvalue()


def fit_exact(data: bytes, size: tuple[int, int], *, dpi: int = 300, quality: int = 92) -> bytes:
    """Center-crop to the target aspect, then Lanczos to exactly `size` (the print box incl. bleed)."""
    img = _open_rgb(data)
    w, h = img.size
    target_ratio = size[0] / size[1]
    if w / h > target_ratio:  # too wide: crop the sides
        new_w = round(h * target_ratio)
        img = img.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    else:  # too tall: crop top and bottom
        new_h = round(w / target_ratio)
        img = img.crop((0, (h - new_h) // 2, w, (h - new_h) // 2 + new_h))
    img = img.resize(size, Image.Resampling.LANCZOS)
    return _jpeg(img, quality, dpi)


def split_spread(data: bytes, page_w: int, *, dpi: int = 300, quality: int = 92) -> tuple[bytes, bytes]:
    """(left page, right page) of a print-size spread. Each keeps its bleed, so the fold area overlaps."""
    img = _open_rgb(data)
    w, _ = img.size
    left = img.crop((0, 0, page_w, img.size[1]))
    right = img.crop((w - page_w, 0, w, img.size[1]))
    return _jpeg(left, quality, dpi), _jpeg(right, quality, dpi)


def downscale(data: bytes, max_side: int, quality: int = 85) -> bytes:
    """JPEG copy no larger than `max_side` (QA input, thumbnails, web proof)."""
    img = _open_rgb(data)
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return _jpeg(img, quality)


def pixel_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as img:
        return img.size
