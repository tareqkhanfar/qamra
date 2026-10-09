import asyncio
import dataclasses
import unicodedata
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


def test_cover_title_lettering_ribbon_and_series_pill(tmp_path: Path) -> None:
    spec = dataclasses.replace(_spec(tmp_path), series="magic")
    html = render_html("cover.html.j2", spec)
    assert 'class="title-art"' in html and "سلمى" in html
    assert "بُطُولَةُ الْبَطَلَةِ الرَّائِعَةِ" in html  # gender-aware ribbon
    boy = render_html("cover.html.j2", dataclasses.replace(spec, gender="m"))
    assert "بُطُولَةُ الْبَطَلِ الرَّائِعِ" in boy
    assert 'class="series-pill"' in html and ">سحري<" in html and 'class="spine"' in html
    assert ">كلاسيك<" in render_html("cover.html.j2", dataclasses.replace(spec, series="classic"))
    assert 'class="sp-line"' not in render_html("cover.html.j2", dataclasses.replace(spec, series=None))
    # two-tone lettering: the child's name in its own gradient, the letters extruded (3D side)
    assert '<tspan class="nm"' in html and "--nf:url(#ct-name)" in html and 'data-depth="1.3"' in html
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


def test_poster_titles_lead_with_the_name() -> None:
    from qamra_pdf.lettering import display_text, poster_layout

    assert poster_layout("يوم تخرّج ليان", "ليان") == (["يوم تخرّج ليان"], None)  # short: one line
    assert poster_layout("آدم في أوّل يوم بالروضة", "آدم") == (["آدم", "في أوّل يوم بالروضة"], 0)
    assert poster_layout("حكاية عبد الرحمن الخاصة والجميلة جدا", "عبد الرحمن") == (
        ["حكاية", "عبد الرحمن", "الخاصة والجميلة جدا"],
        1,
    )
    assert poster_layout("Layla's First Day at Kindergarten", "Layla")[0][0] == "Layla's"
    # cover lettering keeps the shadda, drops the short vowels and the sun letter's shadda after al-
    assert display_text("آدَمُ فِي أَوَّلِ يَوْمٍ بِالرَّوْضَةِ") == "آدم في أوّل يوم بالروضة"
    assert display_text("يَوْمُ تَخَرُّجِ هٰذا") == "يوم تخرّج هذا"  # no stray dagger alif
    assert [display_text(w) for w in ("اللّٰهِ", "لِلرَّوْضَةِ", "الَّذي", "وَالشَّمْسِ", "الأَوَّلُ")] == [
        "الله",
        "للروضة",
        "الذي",
        "والشمس",
        "الأوّل",
    ]


def test_honorifics_are_their_own_runs_with_the_space_before_them() -> None:
    from qamra_pdf.lettering import HONORIFIC_FONT, honorific_runs, with_honorifics

    assert honorific_runs("وسيرة نبينا ﷺ") == [("وسيرة نبينا", False), (" ﷺ", True)]
    assert honorific_runs("الله ﷻ ونبيه ﷺ.") == [
        ("الله", False),
        (" ﷻ", True),
        (" ونبيه", False),
        (" ﷺ", True),
        (".", False),
    ]
    assert honorific_runs("يوم تخرّج سلمى") == [("يوم تخرّج سلمى", False)]
    assert honorific_runs("عيسى \ufd47") == [("عيسى", False), (" \ufd47", True)]  # «عليه السلام» as one sign
    marked = str(with_honorifics("سيرة <نبينا> ﷺ", "none"))
    assert (
        "&lt;نبينا&gt;" in marked
        and f'font-family="{HONORIFIC_FONT}"' in marked
        and 'fill="none"> ﷺ' in marked
    )


async def _story_title(html: Path, pdf: Path) -> dict[str, Any]:
    from playwright.async_api import async_playwright

    from qamra_pdf.lettering import TITLE_FIT_JS

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(html.as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready.then(() => true)")
            await page.evaluate(TITLE_FIT_JS)
            found: dict[str, Any] = await page.evaluate(
                """() => {
                  const hon = document.querySelector('svg.title-art defs tspan.hon');
                  const style = getComputedStyle(hon);
                  const line = getComputedStyle(hon.closest('text'));
                  return {ratio: parseFloat(style.fontSize) / parseFloat(line.fontSize),
                          fill: style.fill, font: style.fontFamily, text: hon.textContent};
                }"""
            )
            await page.pdf(path=str(pdf), print_background=True, prefer_css_page_size=True)
            return found
        finally:
            await browser.close()


def test_an_honorific_in_a_story_title_is_set_apart(tmp_path: Path) -> None:
    """A title with ﷺ: the sign is painted once, by the face layer, in one solid colour, at 58 % of its line
    in Noto Naskh (embedded, never a Type 3 fallback); the glow, shadow, outline, extrusion and rim layers
    leave it out. The back's title and the spine set it apart the same way (`span.hon`)."""
    from qamra_pdf.lettering import title_svg

    svg = str(
        title_svg("سلمى تحب نبيها ﷺ", "gold-magic", width_mm=194, height_mm=60, keep="سلمى", poster=True)
    )
    assert ".hon{fill:var(--hf,none)}" in svg and 'style="--hf:#FFF4DA;--nf:url(#t-name)"' in svg
    assert svg.count('class="hon"') == 1 and svg.count("ﷺ") == 2  # the line's text and the aria-label
    light = str(
        title_svg("سلمى تحب نبيها ﷺ", "gold-magic", width_mm=194, height_mm=60, keep="سلمى", glow=0.35)
    )
    assert "--hf:#3A1D08" in light  # on light art: the outline's dark colour, so it reads without an outline
    base = _spec(tmp_path)
    spec = dataclasses.replace(base, cover=dataclasses.replace(base.cover, subtitle="تُحِبُّ نَبِيَّهَا ﷺ"))
    html = tmp_path / "cover.html"
    html.write_text(render_html("cover.html.j2", spec), encoding="utf-8")
    pdf = tmp_path / "cover.pdf"
    hon = asyncio.run(_story_title(html, pdf))
    assert hon["text"] == " ﷺ" and hon["ratio"] == pytest.approx(0.58, abs=0.01)
    assert hon["fill"] == "none" and "Noto Naskh Arabic" in hon["font"]  # outside every layer of copies
    fonts = _fonts(pdf)
    assert any("NotoNaskhArabic-Bold" in name for name in fonts), fonts
    assert all(kind == "/Type0" for kind in fonts.values()), fonts
    back = html.read_text(encoding="utf-8").split('<div class="hook">', 1)[1].split("</div>", 1)[0]
    assert back.endswith('<span class="hon"> ﷺ</span>') and '<span class="nm">سلمى</span>' in back


def test_page_counts_agree_with_the_number() -> None:
    from qamra_pdf.strings import page_count

    assert [page_count(n, "ar") for n in (2, 3, 10, 11, 24, 100)] == [
        "صَفْحَتانِ",
        "٣ صَفَحاتٍ",
        "١٠ صَفَحاتٍ",
        "١١ صَفْحَةً",
        "٢٤ صَفْحَةً",
        "١٠٠ صَفْحَةٍ",
    ]
    assert page_count(24, "en") == "24 pages" and page_count(1, "en") == "1 page"


def _art(path: Path, sky: str, ground: str, scene_from: float) -> Path:
    """A calm sky over a busy striped scene starting at `scene_from` (share of the height)."""
    im = Image.new("RGB", (PAGE_PX // 4, PAGE_PX // 4), sky)
    draw = ImageDraw.Draw(im)
    top = int(im.height * scene_from)
    for x in range(0, im.width, 8):
        draw.rectangle((x, top, x + 3, im.height), fill=ground)
    im.save(path)
    return path


def test_the_cover_reads_its_art(tmp_path: Path) -> None:
    from qamra_pdf.cover import read_art

    night = read_art(_art(tmp_path / "night.jpg", "#101A40", "#C9A14A", 0.5))
    day = read_art(_art(tmp_path / "day.jpg", "#F4EBD6", "#3E7A4A", 0.3))
    assert night.mode == "dark" and day.mode == "light"
    # where the busy scene begins (108 mm and 65 mm of the 216 mm page), within the smoothing window
    assert abs(night.calm_mm - 108) <= 10 and abs(day.calm_mm - 65) <= 10
    for reading in (night, day):  # print-safe tones: a dark deep, a pale light
        deep = int(reading.deep[1:3], 16) + int(reading.deep[3:5], 16) + int(reading.deep[5:7], 16)
        light = int(reading.light[1:3], 16) + int(reading.light[3:5], 16) + int(reading.light[5:7], 16)
        assert deep < 3 * 80 and light > 3 * 220


def _sheet(path: Path) -> Path:
    """A three-view character sheet: three standing figures on plain cream paper."""
    im = Image.new("RGB", (1500, 1000), "#F3E9D6")
    draw = ImageDraw.Draw(im)
    for cx in (250, 750, 1250):
        draw.ellipse((cx - 70, 80, cx + 70, 230), fill="#C98B5E", outline="#3A2414", width=6)  # head
        draw.rectangle((cx - 110, 230, cx + 110, 640), fill="#2F4A8A", outline="#16204A", width=6)  # body
        draw.rectangle((cx - 90, 640, cx + 90, 930), fill="#22306A", outline="#16204A", width=6)  # legs
    im.save(path)
    return path


def test_back_cover_facts_pages_and_the_child(tmp_path: Path) -> None:
    base = _library_spec(tmp_path)
    spec = dataclasses.replace(
        base,
        age_range=(3, 7),
        series="classic",
        cover=dataclasses.replace(base.cover, hero=_sheet(tmp_path / "sheet.png")),
    )
    book = asyncio.run(render_book(spec, tmp_path / "out", proof=False))
    assert book.cover_pdf is not None
    html = (tmp_path / "out" / "cover.html").read_text(encoding="utf-8")
    assert "لِلأَعْمارِ ٣–٧" in html  # the theme's ages, in Arabic-Indic digits
    assert f">{len(spec.pages)} صَفْحَةً<".translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")) in html
    assert "الحِكايَةُ مُشَكَّلَةٌ بِالكامِل" in html  # the story text is fully vowelized
    assert "نُسْخَةٌ خاصَّةٌ بِـ" in html and 'class="hero-fig"' in html  # the waving child, cut out
    assert html.count('class="thumb t') == 2  # pages from the book, each picture once (this one has two)
    assert '<div class="barcode-zone" data-reserved="barcode"></div>' in html  # kept free
    report = preflight(book.cover_pdf, width_mm=spec.wrap_width_mm, height_mm=216, bleed_mm=3, safe_mm=10)
    assert report.passed and report.min_dpi is not None and report.min_dpi >= 299.5, report.to_dict()
    with pdfplumber.open(book.cover_pdf) as pdf:
        text = unicodedata.normalize("NFKC", pdf.pages[0].extract_text() or "")
    assert "qamra.app" in text


def test_one_unvowelized_page_drops_the_vowelized_claim() -> None:
    from qamra_pdf.cover import is_vowelized

    pages = [VOWELIZED] * 6
    assert is_vowelized(pages) and is_vowelized([*pages, "!"])  # a page without words is not counted
    assert not is_vowelized([*pages, "استيقظت سلمى باكرا وقلبها يرقص فرحا"])  # retyped by a parent


def test_back_cover_thumbnails_spread_through_the_story() -> None:
    from qamra_pdf.cover import pick_thumbs, story_thumbs

    pics = [Path(f"p{i:02d}.jpg") for i in range(2, 22)]
    picked = pick_thumbs(pics)
    assert len(picked) == 3 and pics[0] not in picked and pics[-1] not in picked
    assert picked == sorted(picked) and len(set(picked)) == 3
    pages = [PageSpec(2, "story", "right", "spread-panorama", Path("wide.jpg"), "x")] + [
        PageSpec(n, "story", side_of(n), "full-bleed-cloud", Path(f"q{n}.jpg"), "x") for n in range(3, 9)
    ]
    assert Path("wide.jpg") not in story_thumbs(pages)  # half of a panorama would cut the scene


def test_back_cover_falls_back_to_the_portrait_and_drops_unvowelized_claims(tmp_path: Path) -> None:
    base = _spec(tmp_path, text="نص قصير بلا تشكيل في هذه الصفحة من الحكاية الجميلة جدا")
    plain = dataclasses.replace(base, cover=dataclasses.replace(base.cover, hero=base.title_page.portrait))
    html = render_html("cover.html.j2", plain)
    assert 'class="moon-portrait on-back"' in html and 'class="hero-fig"' not in html  # not a sheet
    assert "مُشَكَّلَةٌ" not in html and "لِلأَعْمارِ" not in html  # no vowels, no theme ages: no claims


def test_spine_names_the_child_in_gold(tmp_path: Path) -> None:
    html = render_html("cover.html.j2", _spec(tmp_path))
    spine = html[html.index('class="spine-text"') :]
    assert '<span class="nm">سلمى</span>' in spine[:400]


def test_english_cover_mirrors_the_wrap(tmp_path: Path) -> None:
    base = _spec(tmp_path)
    spec = dataclasses.replace(
        base,
        lang="en",
        title="Salma's First Day",
        child_name="Salma",
        cover=dataclasses.replace(base.cover, name="Salma's First Day", subtitle="", blurb="A lovely story."),
        series="magic",
    )
    html = render_html("cover.html.j2", spec)
    assert html.index('class="left-panel"') < html.index('class="back ')  # back on the left for LTR
    assert "Starring the amazing heroine" in html and "A special edition for" in html and ">Magic<" in html


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
