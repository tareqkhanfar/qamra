"""«دوسية التأسيس» Volume 3 from its plan: vowels, syllables, words and sentences, teen numbers, adding and
subtracting, the vocabulary units, the certificate, and the volume as a PDF."""

import asyncio
import dataclasses
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader
from qamra_workbook.curriculum import load
from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import answer_key_html, book_html, build_pages, print_pdf
from qamra_workbook.render.foundation import volume_book
from qamra_workbook.render.pages.workbook_common import W, picture_id
from qamra_workbook.render.pages.workbook_math3 import (
    LRI,
    LRM,
    PDI,
    answer_box,
    group_pics,
    numeral_trace,
    sentence_row,
    teen_group,
)
from qamra_workbook.render.pages.workbook_pen3 import JOINS, join_path
from qamra_workbook.render.pages.workbook_reading3 import _syllables_of, sentence_picture
from qamra_workbook.render.pages.workbook_thinking3 import CAUSES, completions
from qamra_workbook.render.registry import REGISTRY, Assets, PageContext
from qamra_workbook.render.spec import BookSpec, Child, PageSpec
from qamra_workbook.render.workbook import printed_word_problems

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
PLAN = load(ROOT / "content/workbook/curriculum/kg2.yaml")
ASSETS = Assets(LibraryStore())
CHILD = Child("ليان", "f")


def volume(pages: range | None = None) -> BookSpec:
    return volume_book(PLAN, 3, CHILD, name_en="Layan", pages=pages)


def one(kind: str, section: str = "arabic", **params: object) -> PageSpec:
    lang = "en" if section == "english" else "ar"
    return PageSpec(
        "t-1", kind, 1, section, "عنوان", "تعليمات", lang, "Do it." if lang == "en" else "", params=params
    )


def built(page: PageSpec) -> tuple[str, list[str], list[str]]:
    b = dataclasses.replace(volume(range(0)), pages=(page,))
    out = REGISTRY[page.type].build(PageContext(page, b, ASSETS))
    return str(out.data.get("svg", "")), out.answer or [], out.problems


def test_every_page_of_volume_3_has_a_builder_and_passes_its_checks() -> None:
    book = volume()
    assert [p.number for p in book.pages] == list(range(1, 131))
    assert sorted({p.type for p in book.pages} - set(REGISTRY)) == []
    types = {p.number: p.type for p in book.pages}
    assert types[74] == "harakat" and types[87] == "syllables" and types[98] == "word-read"
    assert (
        types[9] == "teen-quantity-match" and types[41] == "picture-add" and types[70] == "picture-subtract"
    )
    assert (
        types[67] == "vocab-cards" and types[130] == "workbook-certificate" and types[13] == "letters-trace"
    )
    pages = build_pages(book, ASSETS)
    assert sum(1 for p in pages if p.built.answer) >= 70
    assert printed_word_problems(book) == []


def test_every_picture_word_of_volume_3_is_drawn() -> None:
    words = {w for p in PLAN.volumes[2].pages for w in p.params.get("words", []) if isinstance(w, str)}
    words |= {str(p.params["word"]) for p in PLAN.volumes[2].pages if "word" in p.params}
    reading = {
        w
        for p in PLAN.volumes[2].pages
        if p.type in ("word-read", "word-write")
        for w in p.params.get("words", [])
    }
    for w in words - reading:
        assert picture_id(w), w


def test_reading_pieces() -> None:
    assert _syllables_of("قَمَر") == ["قَ", "مَ", "ر"]
    assert sentence_picture("كَتَبَ باسِم") == "writing" and sentence_picture("I see a cat.") == "cat"
    svg, answer, problems = built(one("harakat", haraka="فتحة", letters=["ب", "ت", "د"]))
    assert problems == [] and "بَ" in svg and answer
    svg, answer, problems = built(one("word-read", words=["بَاب", "فِيل", "تُوت"]))
    assert problems == [] and len(answer) == 3 and svg.count('class="key-ring"') == 3
    _, _, problems = built(one("sentence-read", sentences=["كَتَبَ باسِم", "طارَ العُصفور"]))
    assert problems == ["no picture tells «طارَ العُصفور»"]


def test_teen_groups_and_sums_carry_their_counts() -> None:
    assert teen_group(13, 0, 0, 100, 40, "apple").count("data-count-item=") == 13
    assert teen_group(20, 0, 0, 100, 40, "star").count("data-ten=") == 2
    svg, answer, problems = built(one("picture-add", "math", max=5))
    assert problems == [] and len(answer) == 4
    for line in answer:
        a, b, total = re.findall(r"[٠-٩]+", line)
        assert int(a.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))) + int(
            b.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
        ) == int(total.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
    svg, answer, problems = built(one("picture-subtract", "math", max=10, mode="number-sentence"))
    assert problems == [] and svg.count("data-count=") == 4


def test_the_whole_volume_prints_without_overflow_and_passes_preflight(tmp_path: Path) -> None:
    book = volume()
    pages = build_pages(book, ASSETS)
    g = book.geometry
    pdf = asyncio.run(print_pdf(book_html(book, pages, ASSETS), tmp_path / "v.html", tmp_path / "v.pdf", g))
    assert len(PdfReader(pdf).pages) == 130
    key = asyncio.run(
        print_pdf(answer_key_html(book, pages, ASSETS), tmp_path / "k.html", tmp_path / "k.pdf", g)
    )
    for path in (pdf, key):  # the book and its answer key: bleed, boxes, fonts, DPI and the safe margin
        report = preflight(path, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
        assert report.passed and all(c.ok for c in report.checks), report.to_dict()


def context(page: PageSpec | None = None) -> PageContext:
    book = volume(range(0))
    return PageContext(page or one("sums", "math"), book, ASSETS)


def test_a_page_shows_its_answer_only_in_the_key() -> None:
    """Whatever is drawn in the answer colour is hidden (key-line, key-ring) unless it is part of the problem
    (the crossed-out pictures): a two-digit answer once showed its second digit to the child."""
    pages = build_pages(volume(), ASSETS)
    checked = 0
    for p in pages:
        svg = str(p.built.data.get("svg", ""))
        if not svg:
            continue
        root = ET.fromstring(svg)  # the page's drawing is well-formed (no doubled attributes)

        def shown(el: ET.Element, hidden: bool = False) -> int:
            hide = hidden or bool({"key-line", "key-ring", "cross"} & set(el.attrib.get("class", "").split()))
            red = "E0483A" in (el.attrib.get("fill", "") + el.attrib.get("stroke", "")).upper()
            return (0 if hide else int(red)) + sum(shown(c, hide) for c in el)

        assert shown(root) == 0, f"p{p.spec.number} ({p.spec.type}) shows its answer"
        checked += 1
    assert checked > 100
    boxed = answer_box(50, 20, 13, context(), 16, 18)
    assert boxed.count('class="key-line"') == 1 and boxed.count("<g") >= 3  # one hidden group, both digits


def test_number_sentences_read_left_to_right_and_the_key_keeps_them_so() -> None:
    tokens = [("num", 3), ("op", "+"), ("num", 2), ("eq", ""), ("box", 5)]
    row = sentence_row(context(), tokens, 10, 20, 12)
    plus = float(re.search(r'<text x="([\d.]+)"[^>]*>\+</text>', row).group(1))  # type: ignore[union-attr]
    equals = float(re.search(r'<text x="([\d.]+)"[^>]*>=</text>', row).group(1))  # type: ignore[union-attr]
    box = float(re.search(r'<rect x="([\d.]+)"', row).group(1))  # type: ignore[union-attr]
    assert 10 < plus < equals < box
    for p in build_pages(volume(), ASSETS):
        if p.spec.type not in ("picture-add", "picture-subtract") and p.spec.section != "math":
            continue
        for line in p.built.answer or []:
            if re.search(r"[+−] ", line):
                assert line.startswith(LRI) and line.endswith(PDI), line
                a, op, b, _, total = line.replace(LRM, "").strip(LRI + PDI).split()
                nums = [int(x.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))) for x in (a, b, total)]
                assert nums[2] == (nums[0] + nums[1] if op == "+" else nums[0] - nums[1]) <= 10, line


def test_teen_tracing_fits_its_row_and_the_sums_stay_within_ten() -> None:
    ctx = context()
    for n in range(11, 21):
        right = W - 82
        for k in range(2):
            _, left = numeral_trace(ctx, n, right, 0, 22, first=k == 0)
            right = left - 13
        assert right - 2 > 6, f"{n} runs out of its row"
    for p in build_pages(volume(), ASSETS):  # (a story's sum was once 10 + 1)
        if p.spec.type in ("picture-add", "picture-subtract"):
            for line in p.built.answer or []:
                *_, total = line.replace(LRM, "").strip(LRI + PDI).split()
                assert int(total.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))) <= 10


def test_join_strokes_run_from_the_right_across_the_whole_line() -> None:
    for kind in JOINS:
        stroke = Stroke(join_path(kind, 174, 14, 100, 14))
        assert abs(stroke.start[0] - 174) < 0.5 and abs(stroke.end[0] - 14) < 1.0, kind
        ys = [y for _, y in stroke.polyline]
        assert min(ys) >= 100 - 14 - 1 and max(ys) <= 100 + 9, kind  # between the top line and a bowl's depth
        assert stroke.length > 200, kind


def test_english_reading_pages_run_left_to_right_and_the_writing_pages_do_not_claim_dots_only() -> None:
    book = volume()
    by_number = {p.number: p for p in book.pages}
    assert by_number[114].lang == by_number[117].lang == "en"
    assert by_number[98].lang == by_number[115].lang == "ar"
    _, _, problems = built(one("sentence-read", "english", sentences=["I see a cat.", "I like apples."]))
    assert problems == []
    svg, _, problems = built(one("sentence-read", "english", sentences=["I see a cat."]))
    assert 'direction="rtl"' not in svg  # the full stop stays at the end of the English sentence
    types = {p.number: p.type for p in book.pages}
    assert [types[n] for n in (16, 32, 49, 65)] == [
        "letters-write-3"
    ] * 4  # not Volume 2's «differ only by dots»
    svg, _, problems = built(one("letters-write-3", letters=["ه", "و", "ي"], guided=1, independent=1))
    assert problems == [] and "الحرفان" not in svg


def test_cause_and_effect_uses_each_picture_once() -> None:
    pictures = [p for pair in CAUSES for p in pair]
    assert len(pictures) == len(set(pictures))


def test_every_counted_picture_shows_itself_and_seven_is_not_six() -> None:
    """Volume 2's layout puts the seventh picture on top of the sixth: a child would count six."""
    for count in range(1, 11):
        group = group_pics("apple", count, 0, 0, 60, 37)
        spots = [
            (float(x), float(y), float(w))
            for x, y, w in re.findall(r'<svg x="([\d.]+)" y="([\d.]+)" width="([\d.]+)"', group)
        ]
        assert len(spots) == count and f'data-count="{count}"' in group
        for i, (x1, y1, w1) in enumerate(spots):
            for x2, y2, _ in spots[i + 1 :]:
                assert max(abs(x1 - x2), abs(y1 - y2)) >= w1 * 0.9, f"{count}: two pictures overlap"


def test_the_picture_grid_has_one_way_to_finish() -> None:
    latin = [[(r + c) % 4 for c in range(4)] for r in range(4)]
    assert completions(latin, set(), 4) == 1
    assert completions(latin, {(0, 0), (0, 2), (2, 0), (2, 2)}, 4) == 2  # these four swap: two answers
    svg, answer, problems = built(one("picture-grid", "thinking", size=4))
    assert problems == [] and answer and svg.count("key-ring") == 8
