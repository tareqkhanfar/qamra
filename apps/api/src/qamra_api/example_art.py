"""Public example art (docs/decisions.md, "Public examples"): web-size copies of a sample book's pages,
watermarked «نموذج» ("SAMPLE" for English books).

- Never print resolution: at most `MAX_SIDE` pixels on the long side.
- Derived once and stored next to the book's own files, under the sample child's storage prefix, so deleting
  the sample child removes them too. The key carries a short hash of the source key and the page's last
  change: a redrawn page gets a fresh copy and a fresh URL (browsers may cache each URL for a day).
"""

import hashlib
import io
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFilter, ImageFont

Size = Literal["s", "m"]
MAX_SIDE: dict[str, int] = {"s": 560, "m": 1280}
QUALITY: dict[str, int] = {"s": 78, "m": 82}

# «نموذج», already shaped (Arabic presentation forms) and in visual order, drawn with Pillow's basic layout:
# identical with or without libraqm/FriBiDi (the slim API image may lack them, and an unshaped word would
# print as loose, reversed letters).
LABELS: dict[str, str] = {"ar": "ﺝﺫﻮﻤﻧ", "en": "SAMPLE"}
INK = (255, 253, 248)  # paper-raised
SHADE = (14, 21, 48)  # night-950


@lru_cache(maxsize=1)
def _font_file() -> Path:
    """IBM Plex Sans Arabic SemiBold from the PDF package (it carries the presentation forms)."""
    spec = find_spec("qamra_pdf")  # located, not imported: the PDF package pulls in Playwright
    if spec is None or spec.origin is None:
        raise RuntimeError("the qamra_pdf fonts are not installed")
    return Path(spec.origin).parent / "fonts" / "IBMPlexSansArabic-SemiBold.ttf"


def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_font_file()), px, layout_engine=ImageFont.Layout.BASIC)


def version(source_key: str, changed: str) -> str:
    """Short, stable id of one state of a page's art (never reveals the key itself)."""
    return hashlib.sha256(f"{source_key}|{changed}".encode()).hexdigest()[:12]


def derived_key(book_prefix: str, name: str, size: Size, ver: str) -> str:
    return f"{book_prefix}example/{name}-{size}-{ver}.jpg"


def _word(label: str, px: int, alpha: int) -> Image.Image:
    """The label on a transparent tile: light letters with a soft dark halo, readable on any art."""
    font = _font(px)
    left, top, right, bottom = (round(v) for v in font.getbbox(label))
    pad = px // 2
    tile = Image.new("RGBA", (right - left + 2 * pad, bottom - top + 2 * pad), (0, 0, 0, 0))
    halo = Image.new("RGBA", tile.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).text((pad - left, pad - top), label, font=font, fill=(*SHADE, alpha // 2))
    tile.alpha_composite(halo.filter(ImageFilter.GaussianBlur(max(2, px // 10))))
    ImageDraw.Draw(tile).text((pad - left, pad - top), label, font=font, fill=(*INK, alpha))
    return tile


def stamp(img: Image.Image, lang: str) -> Image.Image:
    """Diagonal «نموذج» marks across the picture (like the watermarked proof), plus a small corner tag."""
    label = LABELS.get(lang, LABELS["en"])
    w, h = img.size
    short = min(w, h)
    out = img.convert("RGBA")
    word = _word(label, max(16, round(short * 0.1)), 96).rotate(
        30, expand=True, resample=Image.Resampling.BICUBIC
    )
    # a loose lattice, offset every other row, so no crop removes every mark
    step_x, step_y = max(word.width, round(w * 0.6)), max(word.height, round(h * 0.42))
    for row, cy in enumerate(range(round(h * 0.2), h + step_y, step_y)):
        offset = (row % 2) * step_x // 2
        for cx in range(round(w * 0.25) - offset, w + step_x, step_x):
            out.alpha_composite(word, (cx - word.width // 2, cy - word.height // 2))
    tag = _word(label, max(12, round(short * 0.045)), 235)
    margin = max(6, round(short * 0.02))
    out.alpha_composite(tag, (margin, h - tag.height - margin))
    return out.convert("RGB")


def watermarked(data: bytes, size: Size, lang: str) -> bytes:
    """A web copy (JPEG, at most MAX_SIDE px, metadata dropped) with the sample marks."""
    with Image.open(io.BytesIO(data)) as original:
        img = original.convert("RGB")
    img.thumbnail((MAX_SIDE[size], MAX_SIDE[size]), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    stamp(img, lang).save(buf, format="JPEG", quality=QUALITY[size], optimize=True, progressive=True)
    return buf.getvalue()
