"""«دوسية أبي بكر», «باسم أبي بكر», «صُنِعَ لِأبي بكر» (the genitive, 2026-10-09): on the covers of the four
activity series, the owner pages, the certificates and the sticker sheets, a name that starts with «أبو» takes
«أبي» after a preposition and as the second term of an iḍāfa (`{child:gen}` in a text, `genitive()` where the
name is set apart under its label), and «لـ» joins it as Arabic writes it («لِأبي بكر», never «لِـأبي بكر»).
A name that stands alone (the ribbon of the Islamic cover, a certificate's name line, «صاحب هذا الكتاب») or is
a subject prints as typed, and a name without «أبو» («سلمى», «محمد») prints exactly as before the marks
(`qamra_pdf.arabic_names`)."""

import asyncio
import dataclasses
import datetime as dt
import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.async_api import async_playwright
from qamra_workbook import islamic
from qamra_workbook.family import book_pages
from qamra_workbook.family import load as load_family
from qamra_workbook.islamic_sources import Resolver
from qamra_workbook.names import shorter_names
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render import covers, spec
from qamra_workbook.render.engine import _FIT_JS, RenderedPage, build_pages, case_names, names_of
from qamra_workbook.render.family import PLAN as FAMILY_PLAN
from qamra_workbook.render.family import cover_specs as family_covers
from qamra_workbook.render.family import plan_pages
from qamra_workbook.render.family_order import family_spec
from qamra_workbook.render.islamic_content import IslamicContext
from qamra_workbook.render.islamic_volume import VolumeContent, check_volume, cover_book, kit_for, volume_book
from qamra_workbook.render.journey_order import render_book, report, stage_specs
from qamra_workbook.render.pages import (
    islamic_keepsake,
    journey_frame,
    reward_stickers,
    workbook_front,
)
from qamra_workbook.render.registry import Assets, PageContext
from qamra_workbook.render.samples import assets_for
from qamra_workbook.render.spec import BookSpec, Child, Family, Member, PageSpec
from qamra_workbook.render.stickers import sheet_book
from qamra_workbook.render.workbook import volume_specs

from qamra_pdf import arabic_names

ROOT = Path(__file__).resolve().parents[3]
SHEET = ROOT / "content/workbook/samples/sample-character.png"  # an AI-drawn sample sheet, not a real person
DAY = dt.date(2026, 10, 9)
ABU = Child("أبو بكر", "m", SHEET)
FAMILY = Family("الكيلاني", (Member("ستّي", scarf=True), Member("بابا", "سامي")), "الخليل")
_M = "[ً-ْٰ]*"
TATWEEL_ALIF = re.compile(f"ل{_M}ـ[اأإآٱ]")  # «لِـأبي»: the «ـ» must go before an alif (the لا ligature)
# «أبو بكر» right after a word that takes the genitive: a missed mark
MISSED = re.compile(f"(?:باسم|اسم|دوسية|رحلة|مَتْجَرُ|مُلْصَق{_M}ا{_M}ت{_M}|إِلَى|خصيصًا)\\s+أبو بكر|ل{_M}ـ?أبو")


@pytest.fixture(scope="module")
def assets(tmp_path_factory: pytest.TempPathFactory) -> Assets:
    """The sample sheet's cut-outs, shared by every child here (they all use the same sheet)."""
    return assets_for(BookSpec("foundation", "", ABU, (), DAY), tmp_path_factory.mktemp("assets"))


Islamic = tuple[islamic.Plan, VolumeContent, IslamicContext]


@pytest.fixture(scope="module")
def islamic_v1(tmp_path_factory: pytest.TempPathFactory) -> Islamic:
    plan, resolver = islamic.load(), Resolver.load()
    content = check_volume(plan, "V1", resolver, build=False)
    kit = kit_for(SHEET, tmp_path_factory.mktemp("kit"))
    return plan, content, IslamicContext(resolver, kit, "preview", DAY)


def _only(book: BookSpec, *types: str) -> BookSpec:
    return dataclasses.replace(book, pages=tuple(p for p in book.pages if p.type in types))


def _products(child: Child, assets: Assets, isl: Islamic) -> dict[str, list[RenderedPage]]:
    """Every page this change touches, per product: the covers, the owner pages, the certificates, the sticker
    sheets and the family book's shop sign."""
    out: dict[str, list[RenderedPage]] = {}
    book, cover, *_ = volume_specs(child, "kg1", 3, name_en="Name", day=DAY)
    out["foundation"] = build_pages(cover, assets) + build_pages(
        _only(book, "owner-page", "workbook-certificate"), assets
    )
    for stage in (1, 2):
        interior, jcover = stage_specs(child, stage, day=DAY, name_en="Name")
        named = _only(interior, "journey-owner", "certificate")
        out[f"journey-{stage}"] = [
            *build_pages(jcover, assets),
            *build_pages(named, assets),
            *build_pages(sheet_book(interior), assets),
        ]
    plan, content, context = isl
    volume = volume_book(plan, content, context, child)
    out["islamic"] = [
        *build_pages(cover_book(plan, "V1", context, volume, pages=len(content.slots)), assets),
        *build_pages(_only(volume, "islamic-front-title", "muslim-passport", "muslim-certificate"), assets),
        *build_pages(sheet_book(volume), assets),
    ]
    fplan = load_family(ROOT / FAMILY_PLAN)
    specs, _ = plan_pages(fplan, list(range(1, len(book_pages(fplan)) + 1)), {})
    shop = tuple(p for p in specs if p.type == "price-tags" and p.params.get("mode") == "blank")
    out["family"] = build_pages(family_spec((*family_covers(fplan), *shop), child, FAMILY, day=DAY), assets)
    return out


def _page(pages: list[RenderedPage], kind: str) -> RenderedPage:
    return next(p for p in pages if p.spec.type == kind)


def _texts(cv: dict[str, object]) -> list[str]:
    """The words of a cover's data: the ribbon, the badges, the blurb, «يأتي مع الكتاب» and «صُنع لـ…»."""
    ribbon = cv.get("ribbon")
    out = [str(ribbon["text"])] if isinstance(ribbon, dict) else []
    for key in ("badges", "comes"):
        out += [str(b["text"]) for b in cv.get(key, []) or []]  # type: ignore[attr-defined]
    out += [str(x) for x in cv.get("blurb", []) or []]  # type: ignore[attr-defined]
    return [*out, str(cv.get("made_for", ""))]


def _printed(pages: list[RenderedPage]) -> str:
    return "\n".join(" ".join([p.title, p.instruction, str(p.built.data)]) for p in pages)


@pytest.fixture(scope="module")
def aba_bakr(assets: Assets, islamic_v1: Islamic) -> dict[str, list[RenderedPage]]:
    return _products(ABU, assets, islamic_v1)


# ---- «أبو بكر» ---------------------------------------------------------------------------------------------


def test_the_foundation_cover_names_aba_bakr_in_the_genitive(aba_bakr: dict[str, list[RenderedPage]]) -> None:
    pages = aba_bakr["foundation"]
    front, back = _page(pages, "workbook-cover-front"), _page(pages, "workbook-cover-back")
    assert front.built.data["cv"]["ribbon"]["text"] == "دوسية أبي بكر" == front.built.data["kicker"]
    assert "باسم أبي بكر وشخصيته" in _texts(front.built.data["cv"])
    words = _texts(back.built.data["cv"])
    assert "صفحة «هذا الكتاب لأبي بكر»" in words  # «لـ» + «أبي»: the لا ligature, no «ـ»
    assert "اسم أبي بكر للتتبّع بالعربية والإنجليزية" in words
    assert "منهج متكامل للروضة في ثلاثة أجزاء، باسم أبي بكر وشخصيته." in words
    assert words[-1] == "صُنعت خصيصًا لأبي بكر" and back.built.data["kicker"] == "دوسية أبي بكر"
    assert any("يُكمل أبو بكر الحروف" in w for w in words)  # the subject of the blurb: as typed


def test_the_journey_covers_name_aba_bakr_in_the_genitive(aba_bakr: dict[str, list[RenderedPage]]) -> None:
    for stage in (1, 2):
        pages = aba_bakr[f"journey-{stage}"]
        front = _texts(_page(pages, "journey-cover-front").built.data["cv"])
        back = _texts(_page(pages, "journey-cover-back").built.data["cv"])
        assert front[0] == "رحلة أبي بكر" and "باسم أبي بكر وشخصيته" in front
        assert back[-1] == "صُنع هذا الكتاب خصيصًا لأبي بكر"
        assert ("شهادة باسم أبي بكر" if stage == 1 else "اسم أبي بكر للتتبّع، وشهادة باسمه") in back


def test_the_islamic_cover_makes_the_book_for_aba_bakr(aba_bakr: dict[str, list[RenderedPage]]) -> None:
    wrap = _page(aba_bakr["islamic"], "islamic-cover-wrap").built.data
    front, back = _texts(wrap["front"]), _texts(wrap["back"])
    assert front[0] == "أبو بكر"  # the ribbon: the name alone, as typed
    assert "صُنِعَ لِأبي بكر" in front
    assert back[-1] == "صُنِعَ هَذَا الْكِتَابُ خِصِّيصًا لِأبي بكر"


def test_the_family_cover_makes_the_book_for_aba_bakr_and_his_family(
    aba_bakr: dict[str, list[RenderedPage]],
) -> None:
    pages = aba_bakr["family"]
    front = _texts(_page(pages, "cover-front").built.data["cv"])
    back = _texts(_page(pages, "cover-back").built.data["cv"])
    assert front[0] == "عائِلَةُ الكيلاني"  # the family's name: a surname, never inflected
    assert "باسم أبي بكر وعائلته" in front
    assert back[-1] == "صُنع خصيصًا لأبي بكر وعائلة الكيلاني"
    assert _page(pages, "price-tags").built.data["sign"] == "مَتْجَرُ أبي بكر"


def test_owner_pages_certificates_and_sticker_sheets(aba_bakr: dict[str, list[RenderedPage]]) -> None:
    foundation, journey, isl = aba_bakr["foundation"], aba_bakr["journey-2"], aba_bakr["islamic"]
    # «هذا الكتاب لـ» and the name under it
    owner = _page(foundation, "owner-page")
    assert owner.built.data["name"] == "أبي بكر" and owner.title == "هذا الكِتابُ لِأبي بكر"
    assert _page(journey, "journey-owner").built.data["name"] == "أبي بكر"
    # «تُمْنَحُ هَذِهِ الشَّهَادَةُ إِلَى» and the name
    certificate = _page(isl, "muslim-certificate").built.data
    assert certificate["labels"]["give"].endswith("إِلَى") and certificate["name"] == "أبي بكر"
    # the name alone on its line: as typed
    assert _page(foundation, "workbook-certificate").built.data["name"] == "أبو بكر"
    assert _page(journey, "certificate").built.data["name"] == "أبو بكر"
    assert _page(isl, "islamic-front-title").built.data["name"] == "أبو بكر"  # «صَاحِبُ هَذَا الْكِتَابِ»
    assert _page(isl, "muslim-passport").built.data["name"] == "أبو بكر"  # «اسْمِي»
    # «مُلْصَقاتُ» owns the name
    for pages in (journey, isl):
        sheet = _page(pages, "reward-stickers").built.data
        assert sheet["owner_label"].startswith("مُلْصَق") and sheet["owner"] == "أبي بكر"


def test_no_genitive_slot_is_missed_and_no_lam_keeps_its_tatweel_before_an_alif(
    aba_bakr: dict[str, list[RenderedPage]],
) -> None:
    for product, pages in aba_bakr.items():
        words = "\n".join(
            "\n".join(_texts(cv))
            for p in pages
            for cv in (p.built.data.get("cv"), p.built.data.get("front"), p.built.data.get("back"))
            if isinstance(cv, dict)
        )
        named = [str(p.built.data.get(k, "")) for p in pages for k in ("name", "owner", "sign", "kicker")]
        text = "\n".join([words, *named, *(p.title for p in pages)])
        assert not TATWEEL_ALIF.search(text), (product, TATWEEL_ALIF.findall(text))
        assert not MISSED.search(text), (product, MISSED.findall(text))
        assert "أبي بكر" in text, product


# ---- the «لـ» join agrees with the covers' own rule --------------------------------------------------------


def _ctx(name: str) -> PageContext:
    book = BookSpec("foundation", "", Child(name, "m"), (), DAY)
    return PageContext(PageSpec("t", "workbook-cover-back", 1, "front", "", ""), book, Assets(LibraryStore()))


_TASHKEEL = re.compile("[ً-ْٰ]")


def test_lam_joins_a_genitive_name_as_the_covers_join_an_unmarked_one() -> None:
    """`covers.fill` turns «لِـال…» into «لل…» for unmarked text; a `{child:gen}` slot is joined when it is
    filled («لِلمعتصم», «لِأحمد»): the same letters, the kasra kept where the template has it."""
    for template in ("صُنعت خصيصًا لـ{child}", "صُنِعَ لِـ{child}", "صُنِعَ هَذَا الْكِتَابُ خِصِّيصًا لِـ{child}"):
        marked = template.replace("{child}", "{child:gen}")
        joined = covers.fill(_ctx("المعتصم"), marked)
        assert "لمعتصم" in joined and "ـ" not in joined and "لال" not in joined
        assert _TASHKEEL.sub("", joined) == _TASHKEEL.sub("", covers.fill(_ctx("المعتصم"), template))
    assert covers.fill(_ctx("المعتصم"), "صُنِعَ لِـ{child:gen}") == "صُنِعَ لِلمعتصم"
    assert covers.fill(_ctx("أحمد"), "صُنِعَ لِـ{child:gen}") == "صُنِعَ لِأحمد"
    assert covers.fill(_ctx("أبو بكر"), "صُنعت خصيصًا لـ{child:gen}") == "صُنعت خصيصًا لأبي بكر"
    assert covers.fill(_ctx("سلمى"), "صُنِعَ لِـ{child:gen}") == "صُنِعَ لِـسلمى"  # «ـ» before any other letter


def test_a_title_keeps_the_name_whole_in_its_case() -> None:
    title = "مُغامَراتُ أبي بكر مَعَ عائِلَتِهِ"
    assert covers.printed_name(title, "أبو بكر") == "أبي بكر"
    assert covers.printed_name("دوسية التأسيس", "أبو بكر") == "أبو بكر"
    lines = covers.title_lines(title, covers.printed_name(title, "أبو بكر"), 10)
    assert len(lines) == 2 and any("أبي بكر" in line for line in lines)  # never «…أبي» / «بكر…»


# ---- a name without «أبو»: exactly as before the marks -----------------------------------------------------


@pytest.fixture
def unmarked(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The texts as they were before the genitive marks: `{child:gen}` filled as `{child}`, and the names set
    apart under a label printed as typed."""
    fill = arabic_names.fill_name

    def plain(text: str, slot: str, name: str) -> str:
        return fill(text.replace("{" + slot + ":gen}", "{" + slot + "}"), slot, name)

    monkeypatch.setattr(spec, "fill_name", plain)
    for module in (workbook_front, journey_frame, islamic_keepsake, reward_stickers):
        monkeypatch.setattr(module, "genitive", lambda name: name)
    yield


def _snapshot(products: dict[str, list[RenderedPage]]) -> list[tuple[str, str, str, str]]:
    return [
        (p.spec.id, p.title, p.instruction, str(p.built.data)) for pages in products.values() for p in pages
    ]


@pytest.mark.parametrize("child", [Child("سلمى", "f", SHEET), Child("محمد", "m", SHEET)], ids=["f", "m"])
def test_a_name_without_abu_prints_exactly_as_before(
    child: Child, assets: Assets, islamic_v1: Islamic, request: pytest.FixtureRequest
) -> None:
    now = _products(child, assets, islamic_v1)
    text = _printed([p for pages in now.values() for p in pages])
    assert f"دوسية {child.name}" in text and f"باسم {child.name}" in text and f"لِـ{child.name}" in text
    request.getfixturevalue("unmarked")
    before = _products(child, assets, islamic_v1)
    assert _snapshot(now) == _snapshot(before)


# ---- a long «أبو» name never refuses an order (render.engine._FIT_JS) --------------------------------------

LONG_ABU = "أبو بكر محمد عبد الرحمن أحمد الخطيب"
LONGEST = "محمد عبد الرحمن أحمد محمود العلي الخطيب"  # test_long_names: a full name with the lineage


def _book(name: str) -> BookSpec:
    return BookSpec("journey", "", Child(name, "m"), (), DAY)


def test_the_name_is_shortened_in_every_case_it_prints_in() -> None:
    typed = [LONG_ABU, *shorter_names(LONG_ABU)]
    assert typed[-1] == "أبو بكر" and len(typed) > 2  # «أبو» keeps «بكر»
    lists = case_names(_book(LONG_ABU))
    assert lists == [
        typed,
        [n.replace("أبو", "أبا", 1) for n in typed],
        [n.replace("أبو", "أبي", 1) for n in typed],
    ]
    for name in ("سلمى", LONGEST, "عبد الرحمن"):  # one list: the typed name and its shorter forms, as before
        assert case_names(_book(name)) == [names_of(_book(name))]
    assert case_names(_book("")) == []


async def _fit(body: str, names: object) -> tuple[list[str], list[str]]:
    """`_FIT_JS` on a page of boxes: what it reports, and each box's text afterwards."""
    html = f"<html><body data-names='{json.dumps(names)}'><div data-page=\"p1\">{body}</div></body></html>"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(html)
            out: list[str] = await page.evaluate(_FIT_JS)
            texts: list[str] = await page.evaluate(
                "() => [...document.querySelectorAll('[data-fit]')].map(el => el.textContent)"
            )
            return out, texts
        finally:
            await browser.close()


_BOX = (
    '<b style="display:block;width:40mm;white-space:nowrap;overflow:hidden;font:12pt sans-serif" data-fit="9"'
)


def test_a_tight_box_shortens_the_name_in_its_case_and_a_typed_name_as_before() -> None:
    lists = case_names(_book(LONG_ABU))
    acc, gen = lists[1], lists[2]
    out, texts = asyncio.run(
        _fit(
            f"{_BOX}>مُلْصَقاتُ {gen[0]}</b>{_BOX}>يا {acc[0]}!</b>{_BOX}>{LONG_ABU}</b>"
            f"{_BOX}>يا {acc[0]} وَلِ{gen[0]}</b>",
            lists,
        )
    )
    assert out == []  # nothing refused
    assert texts[0] in (f"مُلْصَقاتُ {n}" for n in gen[1:]) and texts[1] in (f"يا {n}!" for n in acc[1:])
    assert texts[2] in lists[0][1:]
    assert "أبا بكر" in texts[3] and "أبي بكر" in texts[3] and LONG_ABU.split()[-1] not in texts[3]
    # a name without «أبو»: the nested list behaves exactly as the flat one did
    long_text = "هذا نص طويل جدًا من نصوص الكتاب نفسه لا يتسع"  # the book's own words: refused
    boxes = f"{_BOX}>شهادة {LONGEST}</b>{_BOX}>{LONGEST}</b>{_BOX}>سلمى</b>{_BOX}>{long_text}</b>"
    flat = asyncio.run(_fit(boxes, names_of(_book(LONGEST))))
    assert asyncio.run(_fit(boxes, case_names(_book(LONGEST)))) == flat
    assert flat[0] == [f"p1: {long_text}"] and flat[1][2] == "سلمى"


def test_the_sticker_sheets_print_a_long_abu_name(tmp_path: Path, islamic_v1: Islamic) -> None:
    """«مُلْصَقاتُ أبي بكر محمد عبد الرحمن أحمد الخطيب» on the journey and Islamic sheets (a tight box): the
    name's shorter forms in the genitive, never a refused order."""
    child = Child(LONG_ABU, "m", SHEET)
    interior, _ = stage_specs(child, 2, day=DAY, name_en="Abu Bakr")
    plan, content, context = islamic_v1
    volume = volume_book(plan, content, context, child)
    for book in (sheet_book(interior), sheet_book(volume)):
        [page] = build_pages(book, assets_for(book, tmp_path))
        assert page.built.data["owner"] == LONG_ABU.replace("أبو", "أبي", 1)
        pdf = tmp_path / f"{book.pages[0].id}.pdf"
        asyncio.run(render_book(book, assets_for(book, tmp_path), pdf))  # raises PageProblems on an overflow
        assert report(pdf, book.geometry)["passed"]
