"""Finishing a free cover (Addendum 9 §2): the title on the art, the preview watermark burned in, and a
story-size copy (1080 × 1920) for sharing.

Arabic needs Pillow's complex text layout (libraqm, with FriBiDi). Without it the Arabic words would come out
unjoined and backwards, so the marks fall back to the Latin text instead and the title is left to the page.
"""

import io
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

import qamra_pdf

FONT_DIR = Path(qamra_pdf.__file__).parent / "fonts"
TITLE_FONT = FONT_DIR / "BalooBhaijaan2-ExtraBold.ttf"
BODY_FONT = FONT_DIR / "IBMPlexSansArabic-SemiBold.ttf"
COVER_PX = 1024
STORY = (1080, 1920)
CREAM, GOLD, NIGHT, INK = (251, 246, 236), (245, 196, 101), (22, 32, 74), (14, 21, 48)


@cache
def arabic_ok() -> bool:
    return bool(features.check("raqm"))


def _is_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in text)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    engine = ImageFont.Layout.RAQM if arabic_ok() else ImageFont.Layout.BASIC
    return ImageFont.truetype(str(path), size, layout_engine=engine)


def printable(text: str, fallback: str) -> str:
    """The text when this machine can shape it, else the Latin fallback."""
    return text if arabic_ok() or not _is_arabic(text) else fallback


def _line(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
    stroke: int = 0,
) -> None:
    if arabic_ok() and _is_arabic(text):
        draw.text(
            xy, text, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=INK,
            direction="rtl", language="ar",
        )  # fmt: skip
    else:
        draw.text(xy, text, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=INK)


def _fit(text: str, path: Path, size: int, width: int) -> ImageFont.FreeTypeFont:
    """The largest font up to `size` whose line fits `width`."""
    font = _font(path, size)
    while size > 12 and font.getlength(text) > width:
        size = int(size * 0.9)
        font = _font(path, size)
    return font


def titled(cover: bytes, name: str, subtitle: str, *, px: int = COVER_PX) -> Image.Image:
    """The cover art with the child's name and the story's subtitle in its calm top area, as on the book."""
    img = Image.open(io.BytesIO(cover)).convert("RGB").resize((px, px), Image.Resampling.LANCZOS)
    if (_is_arabic(name) or _is_arabic(subtitle)) and not arabic_ok():
        return img
    draw = ImageDraw.Draw(img)
    big = _fit(name, TITLE_FONT, px // 9, int(px * 0.8))
    _line(draw, (px / 2, px * 0.12), name, big, CREAM, stroke=max(2, px // 256))
    if subtitle:
        small = _fit(subtitle, TITLE_FONT, px // 16, int(px * 0.8))
        _line(draw, (px / 2, px * 0.215), subtitle, small, GOLD, stroke=max(2, px // 340))
    return img


def watermarked(img: Image.Image, text: str) -> Image.Image:
    """The preview mark, burned in: one wide diagonal line across the middle, as in the design."""
    w, h = img.size
    layer = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _fit(text, TITLE_FONT, w // 8, int(w * 1.1))
    _line(draw, (w, h), text, font, (*CREAM, 110))
    turned = layer.rotate(30, resample=Image.Resampling.BICUBIC).crop(
        (w // 2, h // 2, w // 2 + w, h // 2 + h)
    )
    return Image.alpha_composite(img.convert("RGBA"), turned).convert("RGB")


def story(cover: Image.Image, headline: str, footer: str) -> Image.Image:
    """A story-size copy: the cover as a small book on the night-blue brand background."""
    w, h = STORY
    canvas = Image.new("RGB", STORY, NIGHT)
    glow = Image.new("L", STORY, 0)
    ImageDraw.Draw(glow).ellipse((w * 0.1, h * 0.22, w * 0.9, h * 0.72), fill=90)
    canvas.paste(Image.new("RGB", STORY, (46, 58, 110)), (0, 0), glow.filter(ImageFilter.GaussianBlur(120)))
    side = int(w * 0.78)
    book = cover.resize((side, side), Image.Resampling.LANCZOS)
    x, y = (w - side) // 2, int(h * 0.24)
    shadow = Image.new("L", STORY, 0)
    ImageDraw.Draw(shadow).rectangle((x + 18, y + 30, x + side + 18, y + side + 30), fill=150)
    canvas.paste(Image.new("RGB", STORY, INK), (0, 0), shadow.filter(ImageFilter.GaussianBlur(28)))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, side - 1, side - 1), radius=22, fill=255)
    canvas.paste(book, (x, y), mask)
    ImageDraw.Draw(canvas).rectangle((x + side - 16, y + 6, x + side, y + side - 6), fill=INK)  # the spine
    draw = ImageDraw.Draw(canvas)
    _line(draw, (w / 2, h * 0.14), headline, _fit(headline, TITLE_FONT, 76, int(w * 0.86)), CREAM)
    _line(draw, (w / 2, h * 0.86), footer, _fit(footer, BODY_FONT, 46, int(w * 0.86)), GOLD)
    return canvas


def jpeg(img: Image.Image, quality: int = 88) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)  # no metadata
    return buf.getvalue()
