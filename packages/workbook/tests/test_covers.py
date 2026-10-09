"""The activity series' covers (render/covers.py; the owner's request of 2026-10-09): a scene per part, the
child, the lettering and badges in code, the back with the part's real content and pages, the Islamic
volumes' perfect-bound wrap with its spine. Every cover passes the print preflight."""

import asyncio
import dataclasses
import datetime as dt
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from playwright.async_api import async_playwright
from qamra_workbook import islamic
from qamra_workbook.islamic_sources import Resolver
from qamra_workbook.render import covers
from qamra_workbook.render.engine import book_html, build_pages
from qamra_workbook.render.islamic_volume import (
    IslamicContext,
    check_volume,
    cover_book,
    kit_for,
    no_sacred_text,
    volume_book,
)
from qamra_workbook.render.journey_order import render_book, report, stage_specs
from qamra_workbook.render.samples import assets_for
from qamra_workbook.render.spec import BookSpec, Child, Geometry, PageSpec
from qamra_workbook.render.workbook import volume_specs

from qamra_pdf.render import set_boxes

ROOT = Path(__file__).resolve().parents[3]
SHEET = ROOT / "content/workbook/samples/sample-character.png"  # an AI-drawn sample sheet, not a real person
GIRL = Child("ليان", "f", SHEET)
BOY = Child("يوسف", "m", SHEET)
PARTS = [
    *(f"{level}-v{n}" for level in ("kg1", "kg2") for n in (1, 2, 3)),
    *(f"journey-{n}" for n in (1, 2, 3)),
    "family",
    *(f"islamic-{v}" for v in ("v1", "v2", "v3", "v4", "v5", "r")),
]


# ---- words and numbers -------------------------------------------------------------------------------------


def test_the_counted_noun_agrees_with_the_number() -> None:
    assert covers.counted(120, "صفحة", "صفحات") == "120 صفحة"
    assert covers.counted(8, "وحدة", "وحدات") == "8 وحدات"
    assert covers.counted(12, "مغامرة", "مغامرات") == "12 مغامرة"
    assert covers.counted(8, "وَحْدَة", "وَحَدَات", vowelized=True) == "8 وَحَدَاتٍ"
    assert covers.pages_phrase(118) == "118 صفحة ملوّنة"
    assert covers.pages_phrase(71, vowelized=True) == "71 صَفْحَةً مُلَوَّنَةً"
    assert covers.pages_phrase(7, vowelized=True) == "7 صَفَحَاتٍ مُلَوَّنَةٍ"


def test_titles_break_between_words_and_keep_the_name_whole() -> None:
    assert covers.title_lines("دوسية التأسيس") == ["دوسية التأسيس"]
    assert covers.title_lines("رحلتي الأولى للتعلّم") == ["رحلتي الأولى", "للتعلّم"]
    two = covers.title_lines("أَرْكَانُ الْإِسْلَامِ وَأَرْكَانُ الْإِيمَانِ", one_line_max=15)
    assert two == ["أَرْكَانُ الْإِسْلَامِ", "وَأَرْكَانُ الْإِيمَانِ"]  # the second line starts with «و»
    lines = covers.title_lines("مُغامَراتُ عبد الرحمن مَعَ عائِلَتي", "عبد الرحمن", 12)
    assert any("عبد الرحمن" in line for line in lines) and len(lines) == 2


def test_every_part_has_its_words_and_its_drawn_scene() -> None:
    for part in PARTS:
        series = "foundation" if part.startswith("kg") else part.split("-")[0]
        assert part in covers.series_copy(series)["parts"], part
        assert covers.scene_source(part) == covers.SCENES / f"{part}.jpg", part
        with Image.open(covers.SCENES / f"{part}.jpg") as img:
            assert img.width >= 1700 and abs(img.width / img.height - 0.75) < 0.01  # 3:4 at 2K
    for part, stem in covers.PLATES.items():  # the fallback a part shows without its scene
        assert (covers.ASSETS / f"{stem}.jpg").is_file(), part
    for series in ("foundation", "journey"):
        for part, words in covers.series_copy(series)["parts"].items():
            assert len(words["inside"]) == 6 and len(words["blocks"]) == 6, part


def test_a_scene_is_cropped_to_the_cover_at_300_dpi(tmp_path: Path) -> None:
    src = covers.SCENES / "kg1-v1.jpg"
    full = covers.plate(src, tmp_path, 216.0, 303.0)
    band = covers.plate(src, tmp_path, 216.0, 80.0, band=0.66)
    with Image.open(full) as a, Image.open(band) as b:
        assert a.size == (2551, 3579) and b.size == (2551, 945)


# ---- the perfect-bound wrap --------------------------------------------------------------------------------


def test_the_spine_grows_with_the_pages() -> None:
    assert covers.spine_mm(120) == 7.8 and covers.spine_mm(71) == 4.9
    g = Geometry(trim_w=210.0, trim_h=280.0)
    wrap = covers.wrap_geometry(g, 7.8)
    assert wrap.page_w == pytest.approx(3 + 210 + 7.8 + 210 + 3) and wrap.page_h == 286.0
    front, (x, width), back = covers.wrap_boxes(g, 7.8)
    assert (front.x, front.w, x, width, back.x) == (0.0, 213.0, 213.0, 7.8, pytest.approx(220.8))
    assert front.right == back.left == covers.SPINE_HINGE_MM  # no text in the glued hinge


# ---- the back's pages --------------------------------------------------------------------------------------


def _spec(n: int, kind: str) -> PageSpec:
    return PageSpec(id=f"p{n}", type=kind, number=n, section="intro", title="", instruction="")


def test_the_back_shows_preferred_pages_and_never_a_refused_one() -> None:
    kinds = ["owner-page", "name-trace", "toc", "maze", "letter-intro", "count-and-circle", "spot-difference"]
    book = BookSpec(
        "foundation", "دوسية", GIRL, tuple(_spec(i + 1, k) for i, k in enumerate(kinds)), dt.date.today()
    )
    assert covers.pick_pages(book, covers.THUMBS["foundation"]) == [4, 5, 6]
    assert 3 not in covers.pick_pages(book, (("maze",),), allow=lambda p: p.type != "maze")


def test_islamic_backs_only_show_pages_that_never_carry_sacred_text() -> None:
    @dataclasses.dataclass
    class Page:
        type: str
        sacred_text: str | None = None

    def spec(kind: str, **kw: str) -> PageSpec:
        page = Page(kind, **kw)
        return PageSpec(
            id=kind, type=kind, number=1, section="u-x", title="", instruction="", params={"page": page}
        )

    assert (
        no_sacred_text(spec("coloring")) and no_sacred_text(spec("passport")) and no_sacred_text(spec("maze"))
    )
    assert not no_sacred_text(spec("surah")) and not no_sacred_text(spec("dhikr"))
    assert not no_sacred_text(spec("story")) and no_sacred_text(spec("story", sacred_text="none"))


# ---- rendered covers pass the preflight --------------------------------------------------------------------


def _interior_pdf(book: BookSpec, out: Path) -> Path:
    """A stand-in interior (blank pages at the book's size) for the back's thumbnails: fast to make."""
    g = book.geometry
    pdf = out / "interior.pdf"
    size = (round(g.page_w / 25.4 * 72), round(g.page_h / 25.4 * 72))
    pages = [Image.new("RGB", size, c) for c in ("#F2B33D", "#2E9FD6", "#E4769D") * 3]
    pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=72)
    set_boxes(pdf, g.page_w, g.page_h, g.bleed)
    return pdf


def _render(cover: BookSpec, book: BookSpec, out: Path) -> dict[str, object]:
    pdf = out / "cover.pdf"
    asyncio.run(render_book(cover, assets_for(book, out), pdf))
    return report(pdf, cover.geometry)


def test_a_foundation_cover_passes_the_preflight(tmp_path: Path) -> None:
    book, cover, *_ = volume_specs(BOY, "kg2", 3, name_en="Yousef", pages=range(1, 10))
    cover = covers.with_thumbs(
        cover, book, _interior_pdf(book, tmp_path), tmp_path, covers.THUMBS["foundation"]
    )
    back = next(p for p in cover.pages if p.type == "workbook-cover-back")
    assert len(back.params["thumbs"]) == 3
    result = _render(cover, book, tmp_path)
    assert result["passed"] and all(c["ok"] for c in result["checks"]), result  # type: ignore[union-attr]
    assert result["min_dpi"] >= 299.5  # type: ignore[operator]


def test_a_journey_cover_with_a_long_name_passes_the_preflight(tmp_path: Path) -> None:
    child = Child("عبدالرحمن", "m", SHEET)
    book, cover = stage_specs(child, 1, numbers=list(range(1, 10)))
    result = _render(cover, book, tmp_path)  # without pages on its back: the list takes the room
    assert result["passed"] and all(c["ok"] for c in result["checks"]), result  # type: ignore[union-attr]


def test_an_islamic_volume_gets_one_wrap_with_its_spine(tmp_path: Path) -> None:
    plan, resolver = islamic.load(), Resolver.load()
    content = check_volume(plan, "R", resolver, build=False)
    context = IslamicContext(resolver, kit_for(SHEET, tmp_path / "assets"), "preview", dt.date(2026, 10, 9))
    book = volume_book(plan, content, context, GIRL)
    cover = cover_book(plan, "R", context, book, pages=len(content.slots))
    [wrap] = cover.pages
    assert wrap.type == "islamic-cover-wrap" and wrap.params["spine_mm"] == covers.spine_mm(
        len(content.slots)
    )
    assert cover.geometry.trim_w == pytest.approx(2 * book.geometry.trim_w + wrap.params["spine_mm"])
    [page] = build_pages(cover, assets_for(book, tmp_path))
    front, back = page.built.data["front"], page.built.data["back"]
    assert front["ribbon"]["text"] == "ليان" and front["subtitle"] == "رِحْلَةُ الْمُسْلِمَةِ الصَّغِيرَةِ"
    assert any(x["this"] for x in back["extra"]["books"]) and "راجعه" not in str(back)  # no reviewer claim
    result = _render(cover, book, tmp_path)
    assert result["passed"] and all(c["ok"] for c in result["checks"]), result  # type: ignore[union-attr]


# ---- the lettering: honorifics apart, small titles thin ----------------------------------------------------


def test_an_honorific_in_a_title_is_set_apart_from_the_lettering() -> None:
    """ﷺ in a display title (V4 «قصص الأنبياء وسيرة نبيّنا ﷺ»): its own run in Naskh, smaller, raised, one
    solid colour, and the copies that draw the outline, keyline, extrusion and shadow never draw it."""
    look = covers.LOOKS["islamic"]
    svg = str(covers.title_svg(["وَسِيرَةُ نَبِيِّنَا ﷺ"], look, width=170, height=40, uid="t"))
    base, _, layers = svg.partition("</defs>")
    hon = 'class="hon" font-family="Noto Naskh Arabic" font-weight="700" font-size="0.58em"'
    assert base.count(hon) == 1 and f'{hon} baseline-shift="0.3em" fill="none"> ﷺ</tspan>' in base
    assert layers.count(hon) == 1 and f'fill="{look.outline}"> ﷺ</tspan>' in layers  # solid, no gradient
    assert "url(#t-g" not in layers.split("ﷺ")[0].rsplit("<tspan", 1)[1]
    assert layers.count("ﷺ") == 1 and svg.count("ﷺ") == 3  # base, colour, aria-label: never a copy of its own
    plain = str(covers.title_svg(["أَعْرِفُ رَبِّي وَأُحِبُّهُ"], look, width=170, height=40, uid="t"))
    assert 'class="hon"' not in plain
    # the honorific's space goes with it, and the words keep their colours in order
    assert covers.title_lines("قَصَصُ الْأَنْبِيَاءِ وَسِيرَةُ نَبِيِّنَا ﷺ", one_line_max=15) == [
        "قَصَصُ الْأَنْبِيَاءِ",
        "وَسِيرَةُ نَبِيِّنَا ﷺ",
    ]


async def _fitted_titles(html: Path) -> list[dict[str, Any]]:
    """Every `svg.cvt` of a cover after the fit: its fitted size, the reach of its outline and keyline, how
    far its extrusion drops, and its honorific's size against the line's and its font."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(html.resolve().as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready.then(() => true)")
            assert await page.evaluate(covers.COVER_FIT_JS) == []
            found: list[dict[str, Any]] = await page.evaluate(
                """() => [...document.querySelectorAll('svg.cvt')].map(svg => {
                  const uses = [...svg.querySelectorAll('use')];
                  const at = (u, k) => parseFloat(u.getAttribute(k));
                  const hon = svg.querySelector(':scope > text tspan.hon');
                  const style = hon && getComputedStyle(hon);
                  return {
                    back: svg.querySelector('defs text').id.startsWith('cvb-'),
                    fs: parseFloat(svg.dataset.fs),
                    reach: Math.max(...uses.filter(u => !u.dataset.d)
                      .map(u => Math.hypot(at(u, 'x'), at(u, 'y')))),
                    drop: Math.max(...uses.filter(u => u.parentNode.getAttribute('class') !== 'cvt-soft')
                      .map(u => at(u, 'y'))),
                    hon: hon && {
                      ratio: parseFloat(style.fontSize)
                        / parseFloat(getComputedStyle(hon.closest('text')).fontSize),
                      font: style.fontFamily, fill: hon.getAttribute('fill'),
                      loaded: document.fonts.check('700 12px "Noto Naskh Arabic"', 'ﷺ'),
                    },
                  };
                })"""
            )
            return found
        finally:
            await browser.close()


def test_the_v4_wrap_sets_the_honorific_small_and_the_back_title_thin(tmp_path: Path) -> None:
    plan, resolver = islamic.load(), Resolver.load()
    content = check_volume(plan, "V4", resolver, build=False)
    context = IslamicContext(resolver, kit_for(SHEET, tmp_path / "assets"), "preview", dt.date(2026, 10, 9))
    book = volume_book(plan, content, context, BOY)
    cover = cover_book(plan, "V4", context, book, pages=len(content.slots))
    assets = assets_for(book, tmp_path)
    html = tmp_path / "cover.html"
    html.write_text(book_html(cover, build_pages(cover, assets), assets), encoding="utf-8")
    front, back = sorted(asyncio.run(_fitted_titles(html)), key=lambda t: t["back"])
    full = 1.5 + 0.75  # the keyline and the outline at full size
    # the front: a big title keeps the full sticker effect; ﷺ at 58 % in Naskh, solid
    assert front["fs"] >= covers.FULL_EFFECT_MM and front["reach"] == pytest.approx(full, abs=0.01)
    for title in (front, back):
        assert title["hon"]["ratio"] == pytest.approx(0.58, abs=0.01)
        assert "Noto Naskh Arabic" in title["hon"]["font"] and title["hon"]["loaded"]
        assert title["hon"]["fill"] == covers.LOOKS["islamic"].outline
    # the back: a small title gets a thin outline in proportion to its size and only a hint of extrusion
    assert back["fs"] < covers.SMALL_TITLE_MM
    assert back["reach"] == pytest.approx(full * back["fs"] / covers.FULL_EFFECT_MM, rel=0.08)
    depth = {k: t["drop"] - t["reach"] for k, t in (("front", front), ("back", back))}  # the extrusion
    assert back["reach"] < 0.5 * front["reach"] and depth["back"] < 0.25 * depth["front"]
    result = _render(cover, book, tmp_path)
    assert result["passed"] and all(c["ok"] for c in result["checks"]), result  # type: ignore[union-attr]
