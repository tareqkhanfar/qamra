"""«دوسية التأسيس» Volume 2 from its plan: the new page types (letter position, place words, numbers to ten,
the twin-letter writing page, the Volume 2 pen and thinking pages), its pictures, and the volume as a PDF."""

import asyncio
import dataclasses
import re
from pathlib import Path

import pytest
from pypdf import PdfReader
from qamra_workbook.curriculum import load
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.foundation import volume_book
from qamra_workbook.render.pages import (  # noqa: F401  (registers the builders)
    workbook_position,
    workbook_review2,
)
from qamra_workbook.render.pages.workbook_common import picture_id
from qamra_workbook.render.pages.workbook_math2 import layout10
from qamra_workbook.render.pages.workbook_pen2 import spiral
from qamra_workbook.render.pages.workbook_position import position_of, word_shapes
from qamra_workbook.render.registry import REGISTRY, Assets, PageContext
from qamra_workbook.render.spec import BookSpec, Child, PageSpec
from qamra_workbook.render.workbook import printed_word_problems

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
PLAN = load(ROOT / "content/workbook/curriculum/kg2.yaml")
ASSETS = Assets(LibraryStore())
CHILD = Child("ليان", "f")


def volume(pages: range | None = None) -> BookSpec:
    return volume_book(PLAN, 2, CHILD, name_en="Layan", pages=pages)


def one(kind: str, section: str = "arabic", **params: object) -> PageSpec:
    lang = "en" if section == "english" else "ar"
    return PageSpec(
        "t-1", kind, 1, section, "عنوان", "تعليمات", lang, "Do it." if lang == "en" else "", params=params
    )


def built(page: PageSpec) -> tuple[str, list[str], list[str]]:
    b = dataclasses.replace(volume(range(0)), pages=(page,))
    out = REGISTRY[page.type].build(PageContext(page, b, ASSETS))
    return str(out.data.get("svg", "")), out.answer or [], out.problems


def test_every_page_of_volume_2_has_a_builder_and_passes_its_checks() -> None:
    book = volume()
    assert [p.number for p in book.pages] == list(range(1, 125))
    assert sorted({p.type for p in book.pages} - set(REGISTRY)) == []
    types = {p.number: p.type for p in book.pages}
    assert types[7] == "letter-position" and types[56] == "place-words" and types[30] == "letters-write"
    assert types[9] == "number-intro-ten" and types[92] == "number-trace-ten" and types[108] == "number-train"
    assert types[5] == "spiral-lines" and types[49] == "letter-dot-to-dot" and types[61] == "pattern-abc"
    assert types[53] == "shapes-four"
    pages = build_pages(book, ASSETS)
    assert sum(1 for p in pages if p.built.answer) >= 50
    assert printed_word_problems(book) == []


def test_every_picture_word_of_volume_2_is_drawn() -> None:
    words = {w for p in PLAN.volumes[1].pages for w in p.params.get("words", []) if isinstance(w, str)}
    words |= {str(p.params["word"]) for p in PLAN.volumes[1].pages if "word" in p.params}
    assert len({picture_id(w) for w in words}) >= 60


def test_letter_positions_are_read_from_the_written_word() -> None:
    assert position_of(word_shapes("بطة"), "ب") == 0
    assert position_of(word_shapes("حبل"), "ب") == 1
    assert position_of(word_shapes("عنب"), "ب") == 2
    assert position_of(word_shapes("باب"), "أ") == 1  # the alif inside باب counts as أ
    svg, answer, problems = built(
        one("letter-position", letters=["ج", "ح", "خ"], words=["جمل", "نحلة", "درج", "نخلة"])
    )
    assert problems == [] and answer and svg.count('class="key-ring"') == 4  # one ring per word
    _, _, problems = built(one("letter-position", letters=["ب"], words=["جمل"]))
    assert problems == ["«جمل» holds none of ['ب']"]


def test_numbers_to_ten_count_their_things_and_ten_is_two_digits() -> None:
    assert len(layout10(10)) == 10 and len(layout10(7)) == 7
    with pytest.raises(ValueError):
        layout10(11)
    svg, answer, problems = built(one("count-and-circle-ten", "math", numbers=[9, 10]))
    counts = [int(n) for n in re.findall(r'data-count="(\d+)"', svg)]
    assert problems == [] and len(counts) == 4 and set(counts) <= {9, 10}
    assert svg.count("data-count-item=") == sum(counts)
    svg, _, problems = built(one("number-trace-ten", "math", number=10))
    assert problems == [] and 'data-count="10"' in svg and svg.count("<circle") > 40  # two dotted digits
    svg, answer, problems = built(one("number-train", "math", numbers=list(range(1, 11))))
    assert problems == [] and len(answer) == 4


def test_place_words_and_the_twin_writing_page() -> None:
    svg, answer, problems = built(one("place-words", "math", concept=["above-below", "inside-outside"]))
    assert problems == [] and any("فوق" in a for a in answer) and any("داخل" in a for a in answer)
    _, _, problems = built(one("place-words", "math", concept="upside-down"))
    assert problems
    svg, _, problems = built(one("letters-write", letters=["ر", "ز"], guided=1, independent=1))
    assert problems == [] and svg.count('class="trace-row"') == 4  # a guided and an alone row per letter


def test_spirals_start_outside_and_the_pen_check_takes_the_new_skills() -> None:
    s = spiral(50, 50, 20)
    assert 70 < s.start[0] < 72 and abs(s.end[0] - 50) < 2
    svg, _, problems = built(
        one(
            "assessment",
            "pen",
            checklist=["grip", "pressure", "direction"],
            tracing=["spiral", "between-lines"],
        )
    )
    assert problems == [] and "حلزون" in svg and "بين السطرين" in svg


def test_the_whole_volume_prints_without_overflow_and_passes_preflight(tmp_path: Path) -> None:
    book = volume()
    pages = build_pages(book, ASSETS)
    pdf = asyncio.run(
        print_pdf(book_html(book, pages, ASSETS), tmp_path / "v.html", tmp_path / "v.pdf", book.geometry)
    )
    assert len(PdfReader(pdf).pages) == 124
    g = book.geometry
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
    assert report.passed and all(c.ok for c in report.checks), report.to_dict()
