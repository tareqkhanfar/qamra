"""Compound and long names never refuse an order (the blocker of 2026-10-09: «رحلتي الأولى للتعلّم» stage 2
refused «عبد الرحمن», «أبو بكر» and «نور الهدى» because its name page's instruction then had 8 words).

- The word limits of every product count a name as one word, however many words the parent typed
  (`spec.instruction_words`): the limit keeps the book's own sentences short.
- The pages that print the child's name build and print without overflow, in both genders, for «عبد الرحمن»,
  «نور الهدى» and a 20-letter name: a box the full name does not fit at its smallest size shows the name's
  shorter forms (`names.shorter_names`, a compound never cut), and the family's game tables use the name the
  family calls the child by (`names.call_name`).
"""

import asyncio
import dataclasses
import datetime as dt
import json
from pathlib import Path

import pytest
from playwright.async_api import async_playwright
from qamra_workbook import islamic
from qamra_workbook.family import book_pages
from qamra_workbook.family import load as load_family
from qamra_workbook.islamic_sources import Resolver
from qamra_workbook.names import call_name, shorter_names
from qamra_workbook.render.engine import _FIT_JS, build_pages, names_of
from qamra_workbook.render.family import PLAN as FAMILY_PLAN
from qamra_workbook.render.family import SAMPLES as FAMILY_SAMPLES
from qamra_workbook.render.family import plan_pages
from qamra_workbook.render.family_order import family_spec
from qamra_workbook.render.islamic_volume import IslamicContext, check_volume, kit_for, volume_book
from qamra_workbook.render.journey_order import render_book, report, stage_specs
from qamra_workbook.render.samples import FamilySamples, assets_for, book_problems
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, Child, instruction_words
from qamra_workbook.render.workbook import volume_specs

ROOT = Path(__file__).resolve().parents[3]
SHEET = ROOT / "content/workbook/samples/sample-character.png"  # an AI-drawn sample sheet, not a real person
TWENTY = "عبدالرحمنمحمودالخطيب"  # 20 letters, one word (a full name typed without spaces)
LONGEST = "محمد عبد الرحمن أحمد محمود العلي الخطيب"  # 39 characters: a full name with the lineage
NAMES = ["عبد الرحمن", "نور الهدى", TWENTY]
CHILDREN = [pytest.param(Child(n, g, SHEET), id=f"{g}-{len(n)}") for n in NAMES for g in ("m", "f")]


# ---- the word limits ---------------------------------------------------------------------------------------


def test_a_name_is_one_word_in_the_word_limits() -> None:
    text = "هَذا {اسْمُكَ/اسْمُكِ} يا {child}! {تَتَبَّعْهُ/تَتَبَّعيهِ} حَرْفًا حَرْفًا"
    assert instruction_words(text, "m") == instruction_words(text, "f") == 7
    assert instruction_words("{تَعالَ/تَعالَي} مَعَ {member} إلى سوقِ {city}", "f") == 6
    assert instruction_words("Trace your name, {name_en}!", "m") == 4
    for name in (*NAMES, "أبو بكر", LONGEST):
        book = BookSpec("journey", "", Child(name, "m"), (), dt.date(2026, 10, 9))
        assert book.words("يا {child}، {تَتَبَّعِ/تَتَبَّعي} اسْمَكَ، ثُمَّ اكْتُبْهُ وَحْدَكَ") == 7
        assert len(book.personalize("يا {child}، تَتَبَّعْ").split()) == 1 + len(name.split()) + 1


@pytest.mark.parametrize("child", [*CHILDREN, Child("أبو بكر", "m"), Child(LONGEST, "f")])
def test_no_product_refuses_a_compound_or_long_name(child: Child) -> None:
    for stage in (1, 2, 3):  # stage 2's name page refused «عبد الرحمن» before
        interior, _ = stage_specs(child, stage, name_en="Abd Al-Rahman")
        assert book_problems(interior) == []
    for level in ("kg1", "kg2"):
        for volume in (1, 2, 3):
            volume_specs(child, level, volume, name_en="Abd Al-Rahman")  # raises PageProblems on a problem
    book = _family(child)
    assert book_problems(book) == []


def test_the_islamic_word_limits_count_the_name_as_one_word() -> None:
    """The volumes are checked once for both genders, the name counted as one word (≤ 7 in an instruction)."""
    from qamra_workbook.render.islamic_volume import text_problems

    seven = "{اسْتَمِعْ/اسْتَمِعي} يا {child} إلى الحِكايَةِ ثُمَّ {لَوِّنْ/لَوِّني}"
    assert text_problems("k", {"type": "coloring", "instruction": seven}) == []
    [problem] = text_problems("k", {"type": "coloring", "instruction": seven + " الصّورَةَ"})
    assert "8 words (max 7)" in str(problem)


# ---- the name's shorter forms ------------------------------------------------------------------------------


def test_a_long_name_has_shorter_forms_that_never_cut_a_compound() -> None:
    assert shorter_names(LONGEST) == ["محمد عبد الرحمن أحمد", "محمد عبد الرحمن", "محمد"]
    assert (
        shorter_names("عبد الرحمن") == [] and shorter_names("نور الهدى") == [] and shorter_names(TWENTY) == []
    )
    assert shorter_names("أبو بكر الصديق") == []  # «أبو» takes «بكر», «الصديق» joins them: one part
    assert call_name(LONGEST) == "محمد" and call_name("عبد الرحمن") == "عبد الرحمن"
    assert call_name("نور الهدى محمود") == "نور الهدى" and call_name("محمد أحمد عبد الله") == "محمد أحمد"
    assert call_name(TWENTY) == TWENTY  # one word: kept whole (it shrinks in its cell)
    book = BookSpec("journey", "", Child(f" {LONGEST} ", "m"), (), dt.date(2026, 10, 9))
    assert names_of(book) == [LONGEST, *shorter_names(LONGEST)]


# ---- the pages that print the name -------------------------------------------------------------------------


def _family(child: Child) -> BookSpec:
    samples = load_samples(FAMILY_SAMPLES)
    assert isinstance(samples, FamilySamples)
    plan = load_family(FAMILY_PLAN)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    return family_spec(tuple(specs), child, samples.family.spec(), day=dt.date(2026, 10, 9))


def _islamic(child: Child, tmp: Path) -> BookSpec:
    plan, resolver = islamic.load(), Resolver.load()
    content = check_volume(plan, "V1", resolver, build=False)
    context = IslamicContext(
        resolver, kit_for(child.character_sheet, tmp / "kit"), "preview", dt.date(2026, 10, 9)
    )
    return volume_book(plan, content, context, child)


def _named_pages(book: BookSpec, tmp: Path) -> BookSpec:
    """The book cut to the pages that print the child's name (as built for this child)."""
    first = book.child.name.split()[0]
    built = build_pages(book, assets_for(book, tmp))  # raises PageProblems when a page fails its checks
    named = {p.spec.id for p in built if first in str(p.built.data)}
    return dataclasses.replace(book, pages=tuple(p for p in book.pages if p.id in named))


def _print(book: BookSpec, tmp: Path) -> dict[str, object]:
    pdf = tmp / "names.pdf"
    asyncio.run(render_book(book, assets_for(book, tmp), pdf))  # raises PageProblems when a box overflows
    return report(pdf, book.geometry)


@pytest.mark.parametrize("child", CHILDREN)
def test_the_name_pages_print_for_compound_and_long_names(child: Child, tmp_path: Path) -> None:
    """Journey stages 2 and 3 (the name page, «ماذا تعلمت؟», the certificate), «دوسية التأسيس» KG1 V3 (the
    owner page, the name page, the certificate), «قلبي يعرف الله» V1 (the passport, the certificate)."""
    s2, _ = stage_specs(child, 2, name_en="Abd Al-Rahman")
    s3, _ = stage_specs(child, 3, name_en="Abd Al-Rahman")
    foundation, *_ = volume_specs(child, "kg1", 3, name_en="Abd Al-Rahman")
    for book in (s2, s3, foundation, _islamic(child, tmp_path)):
        book = _named_pages(book, tmp_path)
        assert len(book.pages) >= 2
        result = _print(book, tmp_path / book.pages[0].id)
        assert result["passed"], result


def test_the_longest_name_prints_on_every_family_page(tmp_path: Path) -> None:
    """The family book prints the child's name on about 36 pages, with family members typed at the API's
    longest (20 letters): a 39-letter name shows its shorter forms where the full one cannot fit, and the
    game tables call the child «محمد»."""
    child = Child(LONGEST, "m", SHEET)
    book = _family(child)
    assert book.family is not None
    members = tuple(
        dataclasses.replace(m, name="فاطمة الزهراء محمود") if m.is_adult else m for m in book.family.members
    )
    book = dataclasses.replace(book, family=dataclasses.replace(book.family, members=members))
    pages = _named_pages(book, tmp_path)
    built = build_pages(pages, assets_for(pages, tmp_path))
    games = [p.built.data["players"] for p in built if p.spec.type == "family-game-cards"]
    assert games and all(players[0] == {"name": "محمد", "child": True} for players in games)
    result = _print(pages, tmp_path)
    assert result["passed"], result


async def _fit(body: str, names: list[str]) -> tuple[list[str], list[str]]:
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


def test_a_box_shows_the_names_shorter_forms_and_the_books_own_text_stays_strict() -> None:
    style = "display:block;width:40mm;white-space:nowrap;overflow:hidden;font:12pt sans-serif"
    box = f'<b style="{style}" data-fit="9"'
    names = [LONGEST, *shorter_names(LONGEST)]
    out, texts = asyncio.run(
        _fit(
            f"{box}>شهادة {LONGEST}</b>{box}>{LONGEST}</b>{box}>ليان</b>"
            f"{box}>هذا نص طويل جدًا من نصوص الكتاب نفسه لا يتسع</b>{box} data-fit-wrap>{'كلمة ' * 12}</b>",
            names,
        )
    )
    assert texts[0] in (f"شهادة {n}" for n in names[1:]) and texts[1] in names[1:] and texts[2] == "ليان"
    assert out == ["p1: هذا نص طويل جدًا من نصوص الكتاب نفسه لا يتسع"]  # the book's own words: refused
