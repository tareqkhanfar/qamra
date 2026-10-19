"""The story lettering (Playpen Sans Arabic on a painted watercolor wash): fonts, contrast, faces, glyphs."""

import asyncio
import io
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw
from playwright.async_api import async_playwright
from pypdf import PdfReader

from qamra_pdf import (
    BookSpec,
    Brand,
    CoverSpec,
    PageSpec,
    Panel,
    TitleSpec,
    paper_panel,
    preflight,
    readable,
    render_book,
    render_html,
)
from qamra_pdf.checks import CREAM, contrast, palette_for, panel_for
from qamra_pdf.ornaments import MOTIFS, flourish, motif, motif_for
from qamra_pdf.page_scripts import FIT_JS
from qamra_pdf.render import FONTS_DIR

REPO = Path(__file__).resolve().parents[3]
PAGE_PX = 2551  # 216 mm at 300 DPI
BRAND = Brand("قمرة", "Qamra", "qamra.app", "", "")
# A line break between «أَوَّلَ» and «لُقْمَةٍ» once drew «…يَدَاكِ يَا اكِ يَا» (Chromium reused glyphs across
# the break with Playpen's "calt" on): the words of a real example page.
LUNCH = (
    "الْغَدَاءُ تَحْتَ الشَّجَرَةِ: خُبْزُ طَابُونٍ، وَزَيْتٌ وَزَعْتَرٌ، وَشَايٌ عَلَى النَّارِ. قَدَّمَتْ زِينَةُ "
    "أَوَّلَ لُقْمَةٍ لِسِيدِي، فَقَالَ: «سَلِمَتْ يَدَاكِ يَا زِينَةُ!»"
)
SHORT = "جَاءَ مَوْسِمُ الزَّيْتُونِ! حَمَلَتْ زِينَةُ سَلَّةً صَغِيرَةً."


def _img(path: Path, color: str, size: tuple[int, int] = (PAGE_PX, PAGE_PX)) -> Path:
    Image.new("RGB", size, color).save(path, quality=90)
    return path


def _book(tmp: Path, pages: list[PageSpec], lang: str = "ar", name: str = "زِينَةُ") -> BookSpec:
    cover = _img(tmp / "cover.jpg", "#7FA38A")
    return BookSpec(
        lang=lang,  # type: ignore[arg-type]
        title="زِينَةُ فِي مَوْسِمِ الزَّيْتُونِ",
        child_name=name,
        child_age=5,
        gender="f",
        brand=BRAND,
        title_page=TitleSpec("زِينَةُ", "فِي مَوْسِمِ الزَّيْتُونِ", "حكاية", "إلى زينة"),
        cover=CoverSpec(front_image=cover, name="زِينَةُ", subtitle="فِي مَوْسِمِ الزَّيْتُونِ", blurb="…"),
        pages=pages,
        motif="olive",
    )


# ---- fonts: licensed, static, embedded


def test_story_fonts_are_static_and_licensed() -> None:
    for weight in ("SemiBold", "ExtraBold"):
        font = TTFont(FONTS_DIR / f"PlaypenSansArabic-{weight}.ttf")
        assert "fvar" not in font, "variable fonts embed as Type 3"
        cmap = font.getBestCmap()
        assert all(ord(c) in cmap for c in "زيتونَُِّْـًٌٍabcXYZ"), "Arabic, tashkeel and Latin"
    licence = (FONTS_DIR / "OFL-PlaypenSansArabic.txt").read_text()
    assert "SIL Open Font License" in licence and "Playpen Sans Project Authors" in licence
    assert "Playpen Sans Arabic" in (REPO / "docs/licenses.md").read_text()


def test_story_fonts_embed_as_truetype_and_pass_preflight(tmp_path: Path) -> None:
    art = _img(tmp_path / "art.jpg", "#CFE0EE")
    pages = [
        PageSpec(1, "title", "left"),
        PageSpec(2, "story", "right", "full-bleed-cloud", art, SHORT, panel_for(art, "top")),
        PageSpec(3, "story", "left", "vignette-text", art, SHORT, paper_panel(art, "top")),
        PageSpec(4, "story", "right", "dialogue", art, "قَالَتْ زِينَةُ: «أَنَا جَاهِزَةٌ!»", Panel("bottom")),
        PageSpec(5, "parents", "left"),
    ]
    book = asyncio.run(render_book(_book(tmp_path, pages), tmp_path / "out", proof=False))
    assert book.interior_pdf is not None
    fonts: dict[str, str] = {}
    for page in PdfReader(book.interior_pdf).pages:
        for ref in (page["/Resources"].get("/Font") or {}).values():  # type: ignore[union-attr]
            font = ref.get_object()
            fonts[str(font.get("/BaseFont"))] = str(font.get("/Subtype"))
    assert any("PlaypenSansArabic-SemiBold" in f for f in fonts), fonts
    assert any("PlaypenSansArabic-ExtraBold" in f for f in fonts), fonts  # the child's name
    assert set(fonts.values()) == {"/Type0"}, fonts
    report = preflight(book.interior_pdf, width_mm=216, height_mm=216, bleed_mm=3, safe_mm=10)
    assert report.passed, report.to_dict()
    html = (tmp_path / "out" / "interior.html").read_text()
    assert 'data-shape="wash"' in html and "motif-olive" in html and 'class="flourish"' in html


def test_english_books_keep_the_same_storybook_hand(tmp_path: Path) -> None:
    art = _img(tmp_path / "art.jpg", "#CFE0EE")
    text = "Zaina carried a small basket, and Grandpa called: “Come on, Zaina!”"
    pages = [PageSpec(1, "story", "left", "full-bleed-cloud", art, text, panel_for(art, "top"))]
    html = render_html("interior.html.j2", _book(tmp_path, pages, "en", "Zaina"))
    assert '[dir="ltr"] .story-text { font-family: var(--story-face); }' in html
    assert '<span class="hero-name">Zaina</span>' in html


# ---- colors from the picture: readable everywhere


@pytest.mark.parametrize(
    "color", ["#F4EBD8", "#CFE0EE", "#6E8F3A", "#B3262F", "#22306A", "#0E1530", "#808080"]
)
def test_ink_and_name_reach_contrast_on_the_painted_wash(tmp_path: Path, color: str) -> None:
    art = _img(tmp_path / "art.jpg", color, (600, 600))
    for area in ("top", "bottom", "left"):
        panel = panel_for(art, area)  # type: ignore[arg-type]

        def rgb(c: str) -> tuple[int, int, int]:
            return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16))

        assert contrast(rgb(panel.ink), rgb(panel.backdrop)) >= 7, (color, area, panel)
        for accent in ("#A8560A", "#C2306F", "#2B4BA8", "#3F7F1F", "#A8232D", "#FFD75E"):
            assert contrast(rgb(readable(accent, panel.backdrop)), rgb(panel.backdrop)) >= 4.5


def test_busy_art_is_measured_where_the_wash_is_thinnest(tmp_path: Path) -> None:
    busy = Image.new("RGB", (600, 600), "white")
    draw = ImageDraw.Draw(busy)
    for x in range(0, 600, 12):
        for y in range(0, 600, 12):
            if (x + y) // 12 % 2:
                draw.rectangle((x, y, x + 11, y + 11), fill="#16204A")
    busy.save(tmp_path / "busy.jpg")
    wash, _ink, _deep, backdrop, c = palette_for(tmp_path / "busy.jpg", "top", 0.96)
    assert c >= 7 and backdrop != wash  # the art shows through the thinnest wash, and still reads
    assert contrast(CREAM, CREAM) == 1  # sanity of the helper


def test_every_theme_has_a_motif_and_it_draws() -> None:
    assert motif_for("olive-season", "nature-fresh") == "olive"
    assert motif_for("star-keeper", "night-glow") == "star"
    assert motif_for("unknown", "candy-bright") == "heart"
    assert motif_for("olive-season", "nature-fresh", "flower") == "flower"  # the theme's own choice wins
    for kind in MOTIFS:
        assert "<svg" in motif(kind) and "<svg" in flourish(kind, "#8A6A2E")


# ---- faces: the words never sit on one


def _face_book(
    tmp: Path, faces: tuple[tuple[float, float, float, float], ...], text: str = LUNCH
) -> BookSpec:
    art = _img(tmp / "art.jpg", "#CFE0EE")
    pages = [PageSpec(1, "story", "left", "full-bleed-cloud", art, text, panel_for(art, "top"), faces=faces)]
    return _book(tmp, pages)


def test_text_moves_off_a_face(tmp_path: Path) -> None:
    head = ((0.62, 0.22, 0.78, 0.38),)  # a head under the right half of the top text area
    book = asyncio.run(
        render_book(_face_book(tmp_path, head), tmp_path / "out", proof=False, print_files=True)
    )
    (box,) = book.boxes
    assert not box.on_face and not box.overflow, box
    assert box.moved or box.pt < 26, box  # it slid or shrank off the face


def test_text_that_cannot_leave_the_faces_is_flagged(tmp_path: Path) -> None:
    crowd = tuple(
        (x / 10, y / 10, x / 10 + 0.08, y / 10 + 0.08) for x in range(0, 10, 2) for y in range(0, 10, 2)
    )
    book = asyncio.run(render_book(_face_book(tmp_path, crowd), tmp_path / "out", proof=False))
    (box,) = book.boxes
    assert box.on_face and box.pt >= 24  # never below the age minimum; the page goes to review


# ---- glyphs: a line break never changes the letters


_LINES_JS = """
(el) => {
  // the first character of every visual line after the first (base letters only; marks have no own box)
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const starts = []; let lastTop = null;
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    for (let i = 0; i < node.data.length; i++) {
      if (/[\\u064b-\\u0652\\u0670\\s]/.test(node.data[i])) continue;
      const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + 1);
      const top = r.getBoundingClientRect().top;
      if (lastTop !== null && top > lastTop + 8) {
        let j = i; while (j > 0 && !/\\s/.test(node.data[j - 1])) j--;  // the start of that word
        starts.push([node, j]);
      }
      lastTop = top;
    }
  }
  // force the same breaks with <br>: each line is then shaped on its own, from scratch (the paragraph keeps
  // its width: the box is max-content)
  el.style.width = el.getBoundingClientRect().width + 'px';
  for (const [node, j] of starts.reverse()) {
    const rest = node.splitText(j);
    rest.parentNode.insertBefore(document.createElement('br'), rest);
  }
  return starts.length;
}
"""


async def _break_diffs(html: Path, override: str = "") -> list[float]:
    """For a sweep of box widths: the share of pixels that differ between the paragraph as wrapped and the
    same lines forced with <br>."""
    out: list[float] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        for width in range(118, 168, 3):
            await page.goto(html.as_uri())
            await page.add_style_tag(
                content=f".cloud-box {{ max-width: {width}mm !important; max-height: none !important; }}"
                + override
            )
            await page.evaluate("document.fonts.ready.then(() => true)")
            await page.evaluate(FIT_JS, 24)
            text = page.locator(".cloud-box .story-text")
            before = Image.open(io.BytesIO(await text.screenshot())).convert("RGB")
            lines = await text.evaluate(_LINES_JS)
            after = Image.open(io.BytesIO(await text.screenshot())).convert("RGB")
            if lines == 0 or before.size != after.size:
                out.append(1.0 if before.size != after.size else 0.0)
                continue
            diff = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v > 60 else 0)
            out.append(diff.histogram()[255] / (diff.size[0] * diff.size[1]))
        await browser.close()
    return out


def test_line_breaks_never_change_the_letters(tmp_path: Path) -> None:
    art = _img(tmp_path / "art.jpg", "#CFE0EE", (600, 600))
    pages = [PageSpec(1, "story", "left", "full-bleed-cloud", art, LUNCH, Panel("top"))]
    html = tmp_path / "book.html"
    html.write_text(render_html("interior.html.j2", _book(tmp_path, pages)), encoding="utf-8")
    ours = asyncio.run(_break_diffs(html))
    assert max(ours) < 0.002, ours
    # the check sees the bug: with the font's contextual alternates on, some width draws wrong letters
    with_calt = asyncio.run(_break_diffs(html, ".story-text { font-feature-settings: normal !important; }"))
    assert max(with_calt) > 0.01, with_calt
