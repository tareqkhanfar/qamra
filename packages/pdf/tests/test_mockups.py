"""Product mockups (Addendum 11 §2.7): sizes, spine side per language, texture extraction, photo mode."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from qamra_pdf.mockups import (
    HARDCOVER_PX,
    SPREAD_PX,
    BookArt,
    cover_art,
    facing,
    find_blank_quad,
    mockups_from_pdfs,
    photo_mockup,
    pick_spread,
    render_mockups,
    spine_side,
    spread_from_pages,
)
from qamra_pdf.spec import PageSpec

GREEN, MAGENTA, GOLD = (110, 190, 120), (255, 0, 255), (230, 180, 40)
DPI = 40  # small test PDFs: 210 mm ≈ 331 px


def _mm(mm: float) -> int:
    return round(mm / 25.4 * DPI)


def _wrap_pdf(path: Path, front: tuple[int, int, int], back: tuple[int, int, int], lang: str) -> Path:
    """A flat cover wrap without bleed: Arabic [front | spine | back], English [back | spine | front]."""
    trim, spine = _mm(210), _mm(8)
    im = Image.new("RGB", (2 * trim + spine, trim), back)
    x_front = 0 if lang == "ar" else trim + spine
    im.paste(Image.new("RGB", (trim, trim), front), (x_front, 0))
    im.paste(Image.new("RGB", (spine, trim), MAGENTA), (trim, 0))
    im.save(path, resolution=DPI)
    return path


def _interior_pdf(path: Path, n: int = 12) -> Path:
    """Square pages; pages 4–5 carry one picture across the gutter (a panorama), the rest are plain."""
    side = _mm(210)
    pages = []
    for i in range(1, n + 1):
        im = Image.new("RGB", (side, side), (245, 240, 230))
        if i in (4, 5):
            ImageDraw.Draw(im).rectangle((0, side // 3, side, side), fill=(40, 60, 140))
            ImageDraw.Draw(im).ellipse((side // 4, side // 2, side // 2, side - 20), fill=(240, 120, 60))
        pages.append(im)
    pages[0].save(path, save_all=True, append_images=pages[1:], resolution=DPI)
    return path


def test_spine_side_and_facing_pages_follow_the_language() -> None:
    assert spine_side("ar") == "right" and spine_side("en") == "left"
    assert facing(4, "ar") == (5, 4)  # Arabic: the even page is the right-hand page
    assert facing(4, "en") == (4, 5)


def test_spread_prefers_a_panorama_then_the_middle_pair() -> None:
    def story(n: int, layout: str = "full-bleed-cloud") -> PageSpec:
        return PageSpec(number=n, kind="story", side="left", layout=layout, image=Path(f"p{n}.jpg"))

    pages = [PageSpec(number=1, kind="title", side="left")] + [story(n) for n in range(2, 12)]
    assert spread_from_pages(pages, "ar") == (7, 6)
    pages[7] = story(8, "spread-panorama")
    pages[8] = story(9, "spread-panorama")
    assert spread_from_pages(pages, "ar") == (9, 8) and spread_from_pages(pages, "en") == (8, 9)
    assert spread_from_pages(pages[:2], "ar") is None


@pytest.mark.parametrize("lang", ["ar", "en"])
def test_cover_art_cuts_the_front_and_spine_from_the_wrap(tmp_path: Path, lang: str) -> None:
    wrap = cover_art(_wrap_pdf(tmp_path / "cover.pdf", GREEN, GOLD, lang), lang, px=300)  # type: ignore[arg-type]
    assert wrap.front.size == (300, 300)
    assert np.allclose(np.asarray(wrap.front).reshape(-1, 3).mean(axis=0), GREEN, atol=6)
    assert wrap.spine is not None and np.allclose(np.asarray(wrap.spine).mean(axis=(0, 1)), MAGENTA, atol=30)
    assert wrap.back is not None and np.allclose(np.asarray(wrap.back).mean(axis=(0, 1)), GOLD, atol=6)
    assert 7 < wrap.spine_mm < 9


def test_pick_spread_finds_the_panorama(tmp_path: Path) -> None:
    pdf = _interior_pdf(tmp_path / "interior.pdf")
    assert pick_spread(pdf, "ar") == (5, 4)


def _magenta_x(im: Image.Image) -> float:
    """Mean x (0–1) of the spine's pixels in a render."""
    px = np.asarray(im, dtype=np.int16)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    _, xs = np.nonzero((r > 90) & (b > 90) & (g < 70) & (np.abs(r - b) < 40))
    assert len(xs) > 200, "the spine is not visible"
    return float(xs.mean()) / im.width


async def test_mockups_render_at_size_with_the_spine_on_the_binding_side(tmp_path: Path) -> None:
    cover = _wrap_pdf(tmp_path / "cover.pdf", GREEN, GOLD, "ar")
    interior = _interior_pdf(tmp_path / "interior.pdf")
    ar = await mockups_from_pdfs(cover, interior, "ar", tmp_path / "ar", photos=None)
    assert ar.modes == {"hardcover": "css", "spread": "css"} and ar.spread is not None
    with Image.open(ar.hardcover) as hard, Image.open(ar.spread) as spread:
        assert hard.size == HARDCOVER_PX and spread.size == SPREAD_PX
        assert _magenta_x(hard) > 0.6  # Arabic: bound on the right

    art = BookArt(
        front=Image.new("RGB", (600, 600), GREEN), lang="en", spine=Image.new("RGB", (24, 600), MAGENTA)
    )
    en = await render_mockups(art, tmp_path / "en", photos=None)
    assert en.spread is None and en.modes == {"hardcover": "css"}
    with Image.open(en.hardcover) as hard:
        assert hard.size == HARDCOVER_PX and _magenta_x(hard) < 0.4  # English: bound on the left


async def test_a_broken_print_file_raises_for_the_caller_to_handle(tmp_path: Path) -> None:
    bad = tmp_path / "cover.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(Exception):  # noqa: B017 (pdfium's own error type)
        await mockups_from_pdfs(bad, bad, "ar", tmp_path / "out", photos=None)


def _product_photo(quad: list[tuple[int, int]] | None) -> Image.Image:
    """A fake product photo: cream linen with noise, and (optionally) a blank white cover under soft light."""
    rng = np.random.default_rng(3)
    base = np.full((900, 900, 3), (232, 222, 204), dtype=np.float32)
    base += rng.normal(0, 4, base.shape)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    if quad is not None:
        ImageDraw.Draw(im).polygon(quad, fill=(250, 250, 248))
        light = np.linspace(1.0, 0.94, 900, dtype=np.float32)[None, :, None]  # light from the left
        im = Image.fromarray(np.clip(np.asarray(im, dtype=np.float32) * light, 0, 255).astype(np.uint8))
    return im


async def test_photo_mode_finds_the_blank_cover_and_falls_back_when_unsure(tmp_path: Path) -> None:
    quad = [(220, 160), (700, 220), (650, 720), (170, 660)]
    found = find_blank_quad(_product_photo(quad))
    assert found is not None
    assert all(abs(fx - x) < 8 and abs(fy - y) < 8 for (fx, fy), (x, y) in zip(found, quad, strict=True))
    assert find_blank_quad(_product_photo(None)) is None
    assert (
        find_blank_quad(_product_photo([(100, 400), (800, 420), (800, 470), (100, 450)])) is None
    )  # a strip

    photo = tmp_path / "B1-mockup-hardcover-angle.jpg"
    _product_photo(quad).save(photo, quality=95)
    out = photo_mockup(photo, Image.new("RGB", (500, 500), (200, 30, 60)), HARDCOVER_PX, tmp_path / "h.png")
    assert out is not None
    with Image.open(out) as im:
        assert im.size == HARDCOVER_PX
        r, g, _ = im.getpixel((800, 800))  # type: ignore[misc]
        assert r > 150 and g < 60  # the art sits where the blank cover was
    made = await render_mockups(
        BookArt(front=Image.new("RGB", (500, 500), "red"), lang="en"), tmp_path / "m", photos=tmp_path
    )
    assert made.modes == {"hardcover": "photo"}  # mirrored for an English book; no spread without pages
    blank = tmp_path / "blank.jpg"
    _product_photo(None).save(blank)
    assert photo_mockup(blank, Image.new("RGB", (500, 500)), HARDCOVER_PX, tmp_path / "x.png") is None
