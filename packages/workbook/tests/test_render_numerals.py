"""Numerals on the page (decision 2026-09-28 §4): Hindi numerals (١٢٣) by default on Arabic and math pages,
Latin numerals (123) when the parent asks, and always 123 on English pages. One function writes every digit
(`format_number`, through `BookSpec.num`)."""

import dataclasses
import datetime as dt
import re
from pathlib import Path
from typing import Any

import pytest
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import RenderedPage, book_html, build_pages
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import SPEC, Samples, book_from, book_problems, load
from qamra_workbook.render.spec import BookSpec, Child, Lang, Numerals, PageSpec, format_number, minutes_ar

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
CARD = re.compile(r'data-numeral="(\d)">([^<]*)<')
DOT_LABEL = re.compile(r'class="dot-label">([^<]+)<')
HINDI, LATIN = "٠١٢٣٤٥٦٧٨٩", "0123456789"
STYLES: tuple[Numerals, ...] = ("hindi", "latin")


def page(n: int, kind: str, section: str, lang: Lang = "ar", **params: Any) -> PageSpec:
    return PageSpec(
        id=f"test-p{n}",
        type=kind,
        number=n,
        section=section,
        title="الأرقام من 1 إلى 5",
        instruction="{عُدّ/عُدّي} {وضع/وضعي} دائرة حول الرقم",
        lang=lang,
        instruction_en="Trace the 2 letters." if lang == "en" else "",
        stage=1,
        skill="يطابق 3 تفاحات بالرقم ٣",
        audio=lang == "en",
        params=params,
    )


def book(numerals: Numerals, *pages: PageSpec) -> BookSpec:
    child = Child("ليان", "f")
    return BookSpec("journey", "رحلتي الأولى للتعلّم", child, pages, dt.date(2026, 9, 28), numerals=numerals)


def quantity(numerals: Numerals) -> RenderedPage:
    """The stage 1 numerals page: count the apples, circle the numeral (one of three, from 1–5)."""
    spec = page(
        104,
        "quantity-first",
        "math",
        seed=71,
        picture="apple",
        answer_with="numerals",
        example=3,
        counts=[2, 5, 4],
        options=[1, 2, 3, 4, 5],
        cards=3,
    )
    (rendered,) = build_pages(book(numerals, spec), ASSETS)
    return rendered


def test_one_function_writes_every_digit() -> None:
    assert format_number(1234) == "١٢٣٤"
    assert format_number(1234, "latin") == "1234"
    assert format_number("٣–5 تفاحات", "hindi") == "٣–٥ تفاحات"  # whichever way the text was written
    assert format_number("٣–5 تفاحات", "latin") == "3–5 تفاحات"
    assert minutes_ar(10) == "١٠ دقائق"
    assert minutes_ar(15, "latin") == "15 دقيقة"


def test_the_book_chooses_hindi_or_latin() -> None:
    assert BookSpec("journey", "", Child("ليان", "f"), (), dt.date(2026, 9, 28)).numerals == "hindi"
    hindi, latin = book("hindi"), book("latin")
    assert (hindi.num(27), latin.num(27)) == ("٢٧", "27")
    assert (hindi.folio(104), latin.folio(104)) == ("١٠٤", "104")
    assert (hindi.date_ar(), latin.date_ar()) == ("٢٨ أيلول ٢٠٢٦", "28 أيلول 2026")


@pytest.mark.parametrize(("numerals", "digits"), [("hindi", HINDI), ("latin", LATIN)])
def test_a_math_page_prints_the_books_numerals(numerals: Numerals, digits: str) -> None:
    rendered = quantity(numerals)
    rows = rendered.built.data["rows"]
    for row in rows:
        cards = [(int(n), text) for card in row["cards"] for n, text in CARD.findall(str(card))]
        assert len(cards) == 3 and all(text == digits[n] for n, text in cards)
        assert [n for n, _ in cards].count(row["count"]) == 1  # one card is the answer
        assert str(row["group"]).count("data-count-item") == row["count"]
    assert rendered.title == f"الأرقام من {digits[1]} إلى {digits[5]}"
    assert rendered.skill == f"يطابق {digits[3]} تفاحات بالرقم {digits[3]}"
    assert rendered.folio == "".join(digits[int(d)] for d in "104")
    answers = "".join(rendered.built.answer or [])
    other = LATIN if digits == HINDI else HINDI
    assert any(d in answers for d in digits) and not any(d in answers for d in other)
    html = book_html(book(numerals), [rendered], ASSETS)
    assert f"المحطة {digits[1]}" in html  # the section chip


def test_english_pages_always_print_123() -> None:
    en = page(80, "en-letter", "english", lang="en", letter="A", word="apple")
    for numerals in STYLES:
        (rendered,) = build_pages(book(numerals, en), ASSETS)
        assert rendered.numerals == "latin"
        labels = DOT_LABEL.findall(str(rendered.built.data["model"]))
        labels += [x for row in rendered.built.data["rows"] for x in DOT_LABEL.findall(str(row))]
        assert labels and all(x in LATIN for label in labels for x in label)
        assert rendered.title == "الأرقام من 1 إلى 5" and rendered.instruction_en == "Trace the 2 letters."
    # the page number stays in the book's style, so the book numbers its pages one way
    (hindi,) = build_pages(book("hindi", en), ASSETS)
    assert hindi.folio == "٨٠"


def test_arabic_letter_pages_follow_the_book() -> None:
    ba = page(32, "finger-trace", "arabic", letter="ب", word="duck")
    for numerals, digits in zip(STYLES, (HINDI, LATIN), strict=True):
        (rendered,) = build_pages(book(numerals, ba), ASSETS)
        labels = DOT_LABEL.findall(str(rendered.built.data["letter"]))
        assert labels == [digits[1], digits[2]]  # the stroke, then the dot


def test_the_samples_show_the_option() -> None:
    samples = load(ROOT / SPEC)
    assert isinstance(samples, Samples)
    assert samples.numerals == "hindi" and samples.latin_preview == ["math"]
    b = book_from(samples)
    math = [p for p in b.pages if p.section == "math"]
    assert [(p.type, p.params.get("answer_with")) for p in math] == [("quantity-first", "numerals")]


def test_the_replaced_words_stay_out_of_the_samples() -> None:
    text = (ROOT / SPEC).read_text(encoding="utf-8")
    assert "ظبي" not in text and "ذئب" not in text
    b = book_from(load(ROOT / SPEC))
    ok = page(50, "finger-trace", "arabic", letter="ذ", word="duck")
    retired = dataclasses.replace(ok, title="حرف الذال: ذ — ذِئْب")
    found = book_problems(BookSpec(b.product, b.title_ar, b.child, (retired,), b.date))
    assert found == ["test-p50: «ذئب» was replaced by «ذَيل» (decision 2026-09-28)"]
