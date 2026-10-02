import asyncio
import dataclasses
from pathlib import Path
from typing import Any, Literal

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
from qamra_pdf.lettering import TITLE_STYLES
from qamra_pdf.page_layouts import LAYOUTS
from qamra_pdf.render import RenderedBook
from qamra_pdf.spec import STORY_PT

VOWELIZED = "فِي صَبَاحٍ مُشْرِقٍ، اسْتَيْقَظَتْ سَلْمَى بَاكِرًا وَقَلْبُهَا يَرْقُصُ فَرَحًا."
BRAND = Brand("قمرة", "Qamra", "qamra.app", "حكاية طفلك… تحت ضوء القمر", "Your child's story, by moonlight.")
PAGE_PX = 2551  # 216 mm at 300 DPI


def _img(path: Path, color: str, size: tuple[int, int] = (PAGE_PX, PAGE_PX), noise: bool = False) -> Path:
    im = Image.new("RGB", size, color)
    if noise:  # photo-like detail, so image bytes dominate the file size as in a real book
        grain = Image.effect_noise((size[0] // 8, size[1] // 8), 60).resize(size).convert("RGB")
        im = Image.blend(im, grain, 0.35)
    im.save(path, quality=90)
    return path


def _spec(
    tmp: Path,
    *,
    text: str = VOWELIZED,
    watermark: bool = False,
    image_px: int = PAGE_PX,
    age: int = 5,
    noise: bool = False,
) -> BookSpec:
    story = _img(tmp / "story.jpg", "#22306A", (image_px, image_px), noise)
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
    spec = _spec(tmp, noise=True)
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
    assert html.index('class="left-panel"') < html.index('class="front ')  # front panel on the left for RTL
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


@pytest.mark.parametrize("age", [5, 6])  # 26 pt and 21 pt (21 pt = 28 CSS px must not read as shrunk)
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


# ---- Addendum 11: cover lettering, back cover, layout library, typography


def _fonts(pdf: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for page in PdfReader(pdf).pages:
        resources: Any = page["/Resources"]
        for ref in (resources.get("/Font") or {}).values():
            font = ref.get_object()
            out[str(font.get("/BaseFont", "?"))] = str(font.get("/Subtype"))
    return out


def test_display_fonts_embed_as_truetype_never_type3(rendered: tuple[BookSpec, RenderedBook]) -> None:
    _, book = rendered
    assert book.interior_pdf is not None and book.cover_pdf is not None
    cover, interior = _fonts(book.cover_pdf), _fonts(book.interior_pdf)
    assert all(kind == "/Type0" for kind in {**cover, **interior}.values()), {**cover, **interior}
    assert any("Lalezar" in name for name in cover)  # the outlined title is filled copies, not a stroke
    assert any("ArefRuqaa" in name for name in interior)  # the handwritten dedication
    assert any("NotoNaskhArabic-SemiBold" in name for name in interior)  # the child's name in the story


def test_cover_title_lettering_ribbon_and_moon(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    html = render_html("cover.html.j2", spec)
    assert 'class="title-art"' in html and "سَلْمَى" in html
    assert "بُطُولَةُ الْبَطَلَةِ الرَّائِعَةِ" in html  # gender-aware ribbon
    boy = render_html("cover.html.j2", dataclasses.replace(spec, gender="m"))
    assert "بُطُولَةُ الْبَطَلِ الرَّائِعِ" in boy
    assert 'class="front-moon"' in html and 'class="spine"' in html
    for style in TITLE_STYLES:
        assert f"style-{style}" in render_html("cover.html.j2", dataclasses.replace(spec, title_style=style))


def test_back_cover_qr_only_with_family_voice(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    with_voice = render_html("cover.html.j2", spec)
    assert 'class="qr-card"' in with_voice and "امْسَحوا الرَّمْزَ" in with_voice
    quiet = render_html(
        "cover.html.j2", dataclasses.replace(spec, cover=dataclasses.replace(spec.cover, qr_url=None))
    )
    assert 'class="qr-card"' not in quiet and '<svg viewBox="0 0 2' not in quiet
    assert "قَريبًا" not in quiet and "قريبا" not in quiet  # no «قريباً» placeholder
    assert "qamra.app" in quiet and 'class="blurb"' in quiet


def test_spine_text_only_when_wide_enough(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    assert 'class="spine-text"' in render_html("cover.html.j2", dataclasses.replace(spec, spine_mm=7.8))
    assert 'class="spine-text"' not in render_html("cover.html.j2", dataclasses.replace(spec, spine_mm=5.0))


def _library_spec(tmp: Path, text: str = VOWELIZED) -> BookSpec:
    """One story page per layout of the library, in both text areas."""
    story = _img(tmp / "story.jpg", "#CFE0EE")
    split = _img(tmp / "split.jpg", "#7FA38A", (PAGE_PX, 1524))
    half = _img(tmp / "half.jpg", "#F2B33D")
    spoken = "هَمَسَتْ سَلْمَى: «أَنَا جَاهِزَةٌ!»"
    pages: list[PageSpec] = [PageSpec(1, "title", "left")]
    n = 2
    for layout in LAYOUTS:
        for area in ("top", "bottom"):
            image = split if layout == "split-frame" else half if layout == "spread-panorama" else story
            words = "سَلْمَى تَطِيرُ!" if layout == "big-moment" else spoken if layout == "dialogue" else text
            pages.append(PageSpec(n, "story", side_of(n), layout, image, words, Panel(area)))
            n += 1
    pages += [PageSpec(n, "story", side_of(n), "full-bleed-cloud", story, text, Panel("left"))]
    pages += [PageSpec(n + 1, "story", side_of(n + 1), "dialogue", story, spoken, Panel("right"))]
    pages += [PageSpec(n + 2, "parents", side_of(n + 2)), PageSpec(n + 3, "memories", side_of(n + 3))]
    return dataclasses.replace(_spec(tmp), pages=pages, keepsake=None)


def side_of(n: int) -> Literal["left", "right"]:
    return "left" if n % 2 else "right"


def test_every_layout_renders_without_overflow_or_empty_boxes(tmp_path: Path) -> None:
    spec = _library_spec(tmp_path)
    html = render_html("interior.html.j2", spec)
    for layout in LAYOUTS:
        assert f'data-layout="{layout}"' in html
    book = asyncio.run(render_book(spec, tmp_path / "out", proof=False))
    assert book.interior_pdf is not None
    assert book.overflowing_pages == []
    texts = [p for p in spec.pages if p.kind == "story" and p.text]
    assert {b.page for b in book.boxes} == {p.number for p in texts}  # every text sits in a fitted box
    assert all(b.fill >= 0.6 for b in book.boxes), [
        (b.page, b.fill) for b in book.boxes
    ]  # never mostly empty
    report = preflight(book.interior_pdf, width_mm=216, height_mm=216, bleed_mm=3, safe_mm=10)
    assert report.passed, report.to_dict()


def test_old_full_height_side_panel_would_count_as_empty() -> None:
    """The fill measure catches the proof's problem: a full-height panel holding three short lines."""
    from qamra_pdf.render import _FIT_JS

    html = (
        '<div data-panel="3" style="position:absolute;top:0;height:190mm;width:84mm">'
        '<p class="story-text" style="font-size:20pt">ثَلاثَةُ أَسْطُرٍ قَصيرَةٍ فَقَط</p></div>'
    )

    async def fill() -> float:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            out = await page.evaluate(_FIT_JS, 18)
            await browser.close()
        return float(out[0]["fill"])

    assert asyncio.run(fill()) < 0.3


def test_child_name_is_highlighted_in_story_text(tmp_path: Path) -> None:
    from qamra_pdf.render import hero_text

    marked = str(hero_text("اسْتَيْقَظَتْ سَلْمَى بَاكِرًا، وَقَالَتْ لِـسلمى: «سلمى!» وسلماها", "سلمى"))
    assert marked.count('class="hero-name"') == 3  # with or without tashkeel, never half a joined word
    assert "وسلماها" in marked and str(hero_text("Salma smiled.", "Salma", "en")).count("hero-name") == 1
    html = render_html("interior.html.j2", _spec(tmp_path))
    assert '<span class="hero-name">سَلْمَى</span>' in html


def test_story_text_sizes_follow_the_age() -> None:
    assert STORY_PT["young"] == (26.0, 24.0) and STORY_PT["older"] == (21.0, 20.0)


def test_title_lines_never_break_a_word_or_the_name() -> None:
    from qamra_pdf.lettering import split_lines

    for title, name in (
        ("يوم تخرّج سلمى", "سلمى"),
        ("حكاية عبد الرحمن الخاصة", "عبد الرحمن"),
        ("سلمى في رحلة إلى القمر", "سلمى"),
        ("آدم في أوّل يوم بالروضة وأصدقاء جدد كثيرون جدًا", "آدم"),
    ):
        lines = split_lines(title, keep=name)
        assert 1 <= len(lines) <= 3 and " ".join(lines).split() == title.split()
        assert any(name in line for line in lines)  # the name is never split over two lines


def test_cover_thumbnails_at_phone_size(tmp_path: Path) -> None:
    from qamra_pdf.thumbs import cover_thumbs

    out = asyncio.run(cover_thumbs(_spec(tmp_path), tmp_path / "thumbs.png"))
    with Image.open(out) as im:
        assert im.height >= 300 and im.width >= len(TITLE_STYLES) * 300


def test_decor_images_are_used_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from qamra_pdf import assets

    frame = Image.new("RGB", (600, 600), "white")
    ImageDraw.Draw(frame).ellipse((60, 60, 540, 540), outline="#E9A92B", width=40)
    frame.save(tmp_path / "E3-moon-portrait-frame.png")
    monkeypatch.setenv("QAMRA_DECOR_DIR", str(tmp_path))
    found = assets.prepare_decor(tmp_path / "decor")
    assert "moon_frame" in found
    with Image.open(found["moon_frame"]) as im:
        corner: Any = im.getpixel((5, 5))
        assert im.mode == "RGBA" and corner[3] == 0  # the white background is keyed out
    spec = _spec(tmp_path)
    html = render_html("interior.html.j2", spec, assets=assets.Assets(decor=found))
    assert 'class="mp-frame-img"' in html
    assert 'class="mp-frame-img"' not in render_html("interior.html.j2", spec)  # SVG fallback otherwise
