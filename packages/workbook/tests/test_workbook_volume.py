"""«دوسية التأسيس» from its plan (Addendum 5): the page builders of Volume 1, and the volume as a PDF."""

import asyncio
import dataclasses
import re
from pathlib import Path

import pytest
from pypdf import PdfReader
from qamra_workbook.curriculum import REPLACED_WORDS, load, picture_words
from qamra_workbook.digits import DIGITS, digit_shapes
from qamra_workbook.latin import LATIN
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.foundation import volume_book
from qamra_workbook.render.pages.letters import tracing_row
from qamra_workbook.render.pages.workbook_common import arabic_shape, picture_id, shape_of
from qamra_workbook.render.registry import REGISTRY, Assets
from qamra_workbook.render.spec import BookSpec, Child, PageSpec
from qamra_workbook.render.workbook import printed_word_problems

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
PLAN = load(ROOT / "content/workbook/curriculum/kg2.yaml")
ASSETS = Assets(LibraryStore())
CHILD = Child("ليان", "f")


def volume(pages: range | None = None, **changes: object) -> BookSpec:
    book = volume_book(PLAN, 1, CHILD, name_en="Layan", pages=pages)
    return dataclasses.replace(book, **changes) if changes else book  # type: ignore[arg-type]


def one(kind: str, section: str = "arabic", **params: object) -> PageSpec:
    lang = "en" if section == "english" else "ar"
    return PageSpec(
        "t-1", kind, 1, section, "عنوان", "تعليمات", lang, "Do it." if lang == "en" else "", params=params
    )


def built(page: PageSpec) -> tuple[str, list[str], list[str]]:
    b = dataclasses.replace(volume(range(0)), pages=(page,))
    kind = REGISTRY[page.type]
    from qamra_workbook.render.registry import PageContext

    out = kind.build(PageContext(page, b, ASSETS))
    return str(out.data.get("svg", "")), out.answer or [], out.problems


def test_every_page_of_volume_1_has_a_builder_and_passes_its_checks() -> None:
    book = volume()
    assert [p.number for p in book.pages] == list(range(1, 129))
    missing = sorted({p.type for p in book.pages} - set(REGISTRY))
    assert missing == []
    pages = build_pages(book, ASSETS)  # raises when any page's checks fail
    assert sum(1 for p in pages if p.built.answer) >= 40
    assert printed_word_problems(book) == []


def test_every_picture_word_of_volume_1_is_drawn_and_the_replaced_words_are_gone() -> None:
    words = {w for p in PLAN.volumes[0].pages for w in p.params.get("words", []) if isinstance(w, str)}
    words |= {str(p.params["word"]) for p in PLAN.volumes[0].pages if "word" in p.params}
    assert {picture_id(w) for w in words}  # every word resolves to a library picture (KeyError otherwise)
    assert not set(REPLACED_WORDS) & {w for w in picture_words(PLAN)}
    for word in ("ذيل", "طاولة"):
        assert word not in REPLACED_WORDS


def test_letters_digits_and_the_alif_with_hamza() -> None:
    assert len(LATIN) == 52 and all(len(x.strokes) >= 1 for x in LATIN.values())
    assert {c for c in "٠١٢٣٤٥٦٧٨٩0123456789"} <= set(DIGITS)
    assert [d.char for d in digit_shapes(10)] == ["١", "٠"] and [
        d.char for d in digit_shapes(10, "latin")
    ] == ["1", "0"]
    alif = arabic_shape("أ")
    assert (
        len(alif.strokes) == 2 and min(y for _, y in alif.strokes[1].polyline) < alif.guides.top
    )  # hamza above


def test_arabic_writing_rows_keep_room_for_tails_and_run_right_to_left() -> None:
    ba, a = shape_of("ب"), shape_of("A")
    height = lambda row: float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', str(row)).group(1))  # noqa: E731
    tail = 24 * (158 - 97) / 122  # the band from the base line down to the tail line
    assert height(tracing_row(ba, width=176, cap=24, number=str)) == pytest.approx(5 + 24 + tail + 4)
    assert height(tracing_row(a, width=176, cap=33, number=str)) == pytest.approx(
        33 + 12
    )  # English unchanged
    first_ba = re.search(
        r'<circle cx="([\d.]+)"', str(tracing_row(ba, width=176, cap=24, count=1, number=str))
    )
    assert first_ba and float(first_ba.group(1)) > 88  # the first letter sits on the right


def test_counting_pages_show_their_quantities() -> None:
    svg, answer, problems = built(one("count-and-circle", "math", numbers=[3, 4, 5]))
    counts = [int(n) for n in re.findall(r'data-count="(\d+)"', svg)]
    assert problems == [] and len(counts) == 4 and set(counts) <= {3, 4, 5}
    assert svg.count("data-count-item=") == sum(counts)  # each group is drawn with exactly its count
    assert answer and "٣" in answer[0] + "٤٥"


def test_find_letter_repeats_each_target_and_letter_intro_checks_its_words() -> None:
    svg, answer, problems = built(one("find-letter", letters=["ت", "ث"], distractors=["ب", "ن"]))
    assert problems == [] and svg.count('data-glyph="ت"') >= 4 and svg.count('data-glyph="ث"') >= 4
    assert any("ت:" in line for line in answer)
    _, _, problems = built(one("letter-intro", letter="ب", words=["بطة", "أسد"]))
    assert problems == ["«أسد» does not start with ب"]


def test_the_pen_check_has_the_checklist_and_two_tracing_tasks() -> None:
    svg, _, problems = built(
        one("assessment", "pen", checklist=["grip", "pressure", "direction"], tracing=["zigzag", "circle"])
    )
    assert problems == [] and "مسكة القلم" in svg and "الاتجاه" in svg and "الضغط" in svg
    _, _, problems = built(one("assessment", "pen", checklist=["grip"], tracing=["zigzag"]))
    assert problems


def test_numbers_follow_the_book_numerals() -> None:
    hindi = volume(range(36, 37))
    latin = dataclasses.replace(hindi, numerals="latin")
    assert build_pages(hindi, ASSETS)[0].title.endswith("١")
    assert build_pages(latin, ASSETS)[0].title.endswith("1")


def test_openers_take_their_title_from_the_plan() -> None:
    opener = next(p for p in volume(range(8, 9)).pages)
    assert opener.title == "أنا وعالم الأرقام"


def test_the_whole_volume_prints_without_overflow_and_passes_preflight(tmp_path: Path) -> None:
    """The acceptance render (about a minute): 128 A4 pages, nothing overflows (the engine refuses to print
    otherwise), fonts embedded, bleed and safe area respected."""
    book = volume()
    pages = build_pages(book, ASSETS)
    pdf = asyncio.run(
        print_pdf(book_html(book, pages, ASSETS), tmp_path / "v.html", tmp_path / "v.pdf", book.geometry)
    )
    assert len(PdfReader(pdf).pages) == 128
    g = book.geometry
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
    assert report.passed and all(c.ok for c in report.checks), report.to_dict()
