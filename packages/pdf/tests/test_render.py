import asyncio
from pathlib import Path

import pdfplumber
import pytest
from PIL import Image, ImageDraw
from pypdf import PdfReader

from qamra_pdf import (
    BookSpec,
    Brand,
    CoverSpec,
    KeepsakeSpec,
    PageSpec,
    Panel,
    ParentsSpec,
    TitleSpec,
    panel_for,
    preflight,
    render_book,
    render_html,
)
from qamra_pdf.render import RenderedBook

VOWELIZED = "فِي صَبَاحٍ مُشْرِقٍ، اسْتَيْقَظَتْ سَلْمَى بَاكِرًا وَقَلْبُهَا يَرْقُصُ فَرَحًا."
BRAND = Brand("قمرة", "Qamra", "qamra.app", "حكاية طفلك… تحت ضوء القمر", "Your child's story, by moonlight.")
PAGE_PX = 2551  # 216 mm at 300 DPI


def _img(path: Path, color: str, size: tuple[int, int] = (PAGE_PX, PAGE_PX)) -> Path:
    Image.new("RGB", size, color).save(path, quality=90)
    return path


def _spec(
    tmp: Path, *, text: str = VOWELIZED, watermark: bool = False, image_px: int = PAGE_PX, age: int = 5
) -> BookSpec:
    story = _img(tmp / "story.jpg", "#22306A", (image_px, image_px))
    split = _img(tmp / "split.jpg", "#7FA38A", (PAGE_PX, 1524))
    left = _img(tmp / "spread-left.jpg", "#E9826B")
    right = _img(tmp / "spread-right.jpg", "#F2B33D")
    pages = [
        PageSpec(1, "title", "left"),
        PageSpec(2, "story", "right", "full", story, text, Panel("top")),
        PageSpec(3, "story", "left", "split", split, text),
        PageSpec(4, "story", "right", "spread", right, text, Panel("bottom")),
        PageSpec(5, "story", "left", "spread", left, None, None, is_last_story=True),
        PageSpec(6, "companion", "right"),
        PageSpec(7, "parents", "left"),
        PageSpec(8, "activity", "right"),
    ]
    return BookSpec(
        lang="ar",
        title="سَلْمَى فِي أَوَّلِ يَوْمٍ بِالرَّوْضَةِ",
        child_name="سَلْمَى",
        child_age=age,
        gender="f",
        brand=BRAND,
        title_page=TitleSpec(
            "سَلْمَى",
            "فِي أَوَّلِ يَوْمٍ بِالرَّوْضَةِ",
            "حكاية لسلمى",
            "إلى سلمى… نحبّكِ",
            _img(tmp / "portrait.jpg", "#FCEFD2", (700, 700)),
        ),
        cover=CoverSpec(
            _img(tmp / "cover.jpg", "#F2B33D"),
            "سَلْمَى",
            "فِي أَوَّلِ يَوْمٍ",
            "حكاية جميلة.",
            qr_url="https://qamra.app/v/abc",
        ),
        pages=pages,
        parents=ParentsSpec("درسٌ جميل.", ["سؤال أول؟", "سؤال ثانٍ؟"]),
        keepsake=KeepsakeSpec(
            _img(tmp / "d.jpg", "white", (800, 800)),
            _img(tmp / "c.jpg", "#A99BD6", (800, 800)),
            "سَلْمَى",
            "بوبو",
            "28 / 09 / 2026",
        ),
        watermark=watermark,
    )


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> tuple[BookSpec, RenderedBook]:
    tmp = tmp_path_factory.mktemp("book")
    spec = _spec(tmp)
    return spec, asyncio.run(render_book(spec, tmp / "out"))


def test_interior_pages_have_exact_size_and_boxes(rendered: tuple[BookSpec, RenderedBook]) -> None:
    _, book = rendered
    assert book.interior_pdf is not None
    reader = PdfReader(book.interior_pdf)
    assert len(reader.pages) == 8
    for page in reader.pages:
        assert float(page.mediabox.width) / 72 * 25.4 == pytest.approx(216, abs=0.01)
        assert float(page.trimbox.left) / 72 * 25.4 == pytest.approx(3, abs=0.01)
        assert float(page.trimbox.width) / 72 * 25.4 == pytest.approx(210, abs=0.01)


def test_cover_is_one_rtl_wrap_with_spine(rendered: tuple[BookSpec, RenderedBook]) -> None:
    spec, book = rendered
    assert book.cover_pdf is not None
    reader = PdfReader(book.cover_pdf)
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.width) / 72 * 25.4 == pytest.approx(2 * 210 + 8 + 6, abs=0.01)
    html = render_html("cover.html.j2", spec)
    assert html.index('class="left-panel"') < html.index('class="front"')  # front panel on the left for RTL
    with pdfplumber.open(book.cover_pdf) as pdf:
        words = pdf.pages[0].extract_text() or ""
    assert "qamra.app" in words


def test_fonts_embedded_and_not_type3(rendered: tuple[BookSpec, RenderedBook]) -> None:
    _, book = rendered
    assert book.interior_pdf is not None
    report = preflight(book.interior_pdf, width_mm=216, height_mm=216, bleed_mm=3, safe_mm=10, signature=4)
    fonts = next(c for c in report.checks if c.name == "fonts_embedded")
    assert fonts.ok, fonts.detail


def test_print_files_pass_preflight(rendered: tuple[BookSpec, RenderedBook]) -> None:
    spec, book = rendered
    assert book.interior_pdf is not None and book.cover_pdf is not None
    interior = preflight(book.interior_pdf, width_mm=216, height_mm=216, bleed_mm=3, safe_mm=10, signature=4)
    assert interior.passed, interior.to_dict()
    assert interior.min_dpi is not None and interior.min_dpi >= 299.5
    cover = preflight(book.cover_pdf, width_mm=spec.wrap_width_mm, height_mm=216, bleed_mm=3, safe_mm=10)
    assert cover.passed, cover.to_dict()


def test_folios_use_arabic_indic_digits(rendered: tuple[BookSpec, RenderedBook]) -> None:
    _, book = rendered
    assert book.interior_pdf is not None
    with pdfplumber.open(book.interior_pdf) as pdf:
        text = pdf.pages[1].extract_text() or ""
    assert "٢" in text and "2" not in text


def test_web_proof_is_small(rendered: tuple[BookSpec, RenderedBook]) -> None:
    _, book = rendered
    assert book.proof_pdf is not None and book.interior_pdf is not None
    assert len(PdfReader(book.proof_pdf).pages) == 8 + 2  # front + interior + back
    assert book.proof_pdf.stat().st_size < book.interior_pdf.stat().st_size


def test_low_resolution_images_fail_preflight(tmp_path: Path) -> None:
    spec = _spec(tmp_path, image_px=1200)
    book = asyncio.run(render_book(spec, tmp_path / "out", proof=False))
    assert book.interior_pdf is not None
    report = preflight(book.interior_pdf, width_mm=216, height_mm=216, bleed_mm=3, safe_mm=10, signature=4)
    dpi = next(c for c in report.checks if c.name == "image_dpi")
    assert not report.passed and not dpi.ok and "p2" in dpi.detail


@pytest.mark.parametrize("age", [5, 6])  # 20 pt and 16 pt (21.333… CSS px must not read as shrunk)
def test_text_that_fits_is_not_reported(tmp_path: Path, age: int) -> None:
    spec = _spec(tmp_path, age=age)
    book = asyncio.run(render_book(spec, tmp_path / "out", proof=False))
    assert book.fit == []


def test_long_text_shrinks_to_the_age_minimum(tmp_path: Path) -> None:
    spec = _spec(tmp_path, text=" ".join([VOWELIZED] * 7))
    book = asyncio.run(render_book(spec, tmp_path / "out", proof=False))
    fits = {f.page: f for f in book.fit}
    assert 2 in fits and fits[2].pt >= spec.min_text_pt
    assert fits[2].overflow or fits[2].pt < spec.text_pt


def test_busy_art_gets_an_opaque_panel(tmp_path: Path) -> None:
    calm = _img(tmp_path / "calm.jpg", "#CFE0EE", (600, 600))
    busy_path = tmp_path / "busy.jpg"
    busy = Image.new("RGB", (600, 600), "white")
    draw = ImageDraw.Draw(busy)
    for x in range(0, 600, 12):
        for y in range(0, 600, 12):
            if (x + y) // 12 % 2:
                draw.rectangle((x, y, x + 11, y + 11), fill="#16204A")
    busy.save(busy_path)
    calm_panel, busy_panel = panel_for(calm, "top"), panel_for(busy_path, "top")
    assert not calm_panel.busy and calm_panel.opacity == pytest.approx(0.88)
    assert busy_panel.busy and busy_panel.opacity > 0.9
    assert calm_panel.contrast is not None and calm_panel.contrast >= 7


def test_watermark_on_previews(tmp_path: Path) -> None:
    html = render_html("interior.html.j2", _spec(tmp_path, watermark=True))
    assert "مُعايَنَة · قمرة" in html
