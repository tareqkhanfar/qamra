"""«دوسية التأسيس» KG1 from its plan: every page of the three volumes builds through `foundation_kg1`, the KG1
page types keep their rules (tracing over writing, listening vowels, picture sums), the KG1 words are
drawn, and each volume prints as a PDF that passes preflight."""

import asyncio
import dataclasses
import re
from collections import Counter
from itertools import pairwise
from pathlib import Path

import pytest
from pypdf import PdfReader
from qamra_workbook.curriculum import REPLACED_WORDS, load, picture_words
from qamra_workbook.pictures import PICTURES, LibraryStore
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.engine import answer_key_html, book_html, build_pages, print_pdf
from qamra_workbook.render.foundation import volume_book
from qamra_workbook.render.foundation_kg1 import (
    ENGLISH_PICTURES_KG1,
    LETTER_PICTURES_KG1,
    LOOKALIKE_KG1,
    engine_type_kg1,
    texts_kg1,
)
from qamra_workbook.render.pages import workbook_kg1  # noqa: F401  (registers the builders)
from qamra_workbook.render.pages.workbook_common import picture_id, shape_of
from qamra_workbook.render.pages.workbook_kg1_arabic import (
    NOT_A_FIRST_SOUND,
    WORD_ROOM,
    body_ratio,
    first_sound_pictures,
    model_word,
)
from qamra_workbook.render.pages.workbook_kg1_math import counted
from qamra_workbook.render.pages.workbook_kg1_pen import row_strokes
from qamra_workbook.render.pages.workbook_kg1_review import pictures_for
from qamra_workbook.render.pages.workbook_position import word_shapes
from qamra_workbook.render.registry import REGISTRY, Assets, PageContext
from qamra_workbook.render.spec import BookSpec, Child, PageSpec
from qamra_workbook.render.workbook import printed_word_problems

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
PLAN = load(ROOT / "content/workbook/curriculum/kg1.yaml")
ASSETS = Assets(LibraryStore())
CHILD = Child("ليان", "f")
PAGES = {1: 120, 2: 116, 3: 114}


def volume(number: int = 1, pages: range | None = None) -> BookSpec:
    return volume_book(PLAN, number, CHILD, name_en="Layan", pages=pages)


def one(kind: str, section: str = "arabic", **params: object) -> PageSpec:
    lang = "en" if section == "english" else "ar"
    return PageSpec(
        "t-1", kind, 1, section, "عنوان", "تعليمات", lang, "Do it." if lang == "en" else "", params=params
    )


def built(page: PageSpec) -> tuple[str, list[str], list[str]]:
    b = dataclasses.replace(volume(1, range(0)), pages=(page,))
    out = REGISTRY[page.type].build(PageContext(page, b, ASSETS))
    return str(out.data.get("svg", "")), out.answer or [], out.problems


@pytest.mark.parametrize("number", [1, 2, 3])
def test_every_page_of_the_volume_has_a_builder_and_passes_its_checks(number: int) -> None:
    book = volume(number)
    assert [p.number for p in book.pages] == list(range(1, PAGES[number] + 1))
    assert sorted({p.type for p in book.pages} - set(REGISTRY)) == []
    pages = build_pages(book, ASSETS)  # raises when any page's checks fail
    assert sum(1 for p in pages if p.built.answer) >= 35
    assert printed_word_problems(book) == []
    assert all(len(p.instruction.split()) <= 7 for p in pages)
    # the answer key never prints a replaced word either (decision 7), nor «None» or an empty line
    for p in pages:
        words = strip_tashkeel(" ".join(p.built.answer or [])).replace("،", " ").replace(":", " ").split()
        for i, word in enumerate(words):
            new = REPLACED_WORDS.get(word)
            assert not new or " ".join(words[i : i + len(new.split())]) == new, (p.spec.id, word)
        assert all(line.strip() and "None" not in line for line in p.built.answer or [])


def test_the_plan_routes_to_the_kg1_pages_and_the_kg2_ones_it_reuses() -> None:
    types = {p.number: p.type for p in volume(1).pages}
    assert types[5] == "kg1-pen-lines" and types[74] == "shapes" and types[55] == "spiral-lines"
    assert (
        types[18] == "kg1-letter-trace"
        and types[21] == "kg1-letter-write"
        and types[54] == "kg1-letters-write"
    )
    assert types[40] == "kg1-en-letter" and types[116] == "kg1-assessment" and types[86] == "kg1-hidden-stars"
    types3 = {p.number: p.type for p in volume(3).pages}
    assert types3[90] == "kg1-harakat" and types3[98] == "kg1-harakat" and types3[103] == "kg1-word-write"
    assert (
        types3[15] == "number-train"
        and types3[32] == "kg1-picture-add"
        and types3[114] == "workbook-certificate"
    )
    assert (
        types3[12] == "kg1-vocab-unit" and types3[85] == "kg1-vocab-review" and types3[59] == "cut-and-paste"
    )
    assert (
        types[15] == "kg1-classify" and types[49] == "kg1-find-letter-en" and types[60] == "kg1-number-write"
    )
    assert types[89] == "kg1-match-letter-picture" and types[99] == "kg1-number-write"
    assert (
        types3[8] == "kg1-count-and-circle"
        and types3[76] == "kg1-memory"
        and types3[78] == "kg1-match-letter-picture"
    )
    page = next(p for p in PLAN.volumes[0].pages if p.n == 31)  # find-letter gets its look-alikes
    assert engine_type_kg1(page) == "kg1-find-letter" and types[31] == "kg1-find-letter"
    assert types[61] == "kg1-color-by-letter" and types3[81] == "kg1-color-by-letter"
    assert texts_kg1("arabic", "harakat", {"haraka": "damma"}, "")[0] == "أسمع الضمة"


def test_every_picture_word_of_kg1_is_drawn_and_the_replaced_words_are_gone() -> None:
    words = {
        w for v in PLAN.volumes for p in v.pages for w in p.params.get("words", []) if isinstance(w, str)
    }
    words |= {str(p.params["word"]) for v in PLAN.volumes for p in v.pages if "word" in p.params}
    vocab = {
        "one",
        "two",
        "three",
        "four",
        "five",
        "red",
        "blue",
        "yellow",
        "green",
        "circle",
        "square",
        "star",
    }
    assert {picture_id(w) for w in words - vocab}  # every word resolves to a library picture
    assert {"whale", "beehive", "gazelle", "hoopoe", "pyramid", "pumpkin", "zebra", "mother"} <= set(PICTURES)
    assert not set(REPLACED_WORDS) & set(picture_words(PLAN))
    assert set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي") <= {c for c in LOOKALIKE_KG1} | {"ا"}


def test_kg1_traces_big_and_writes_alone_only_one_short_row() -> None:
    svg, _, problems = built(one("kg1-letter-trace", letter="أ", sizes=["xl", "l"]))
    assert problems == [] and svg.count('class="trace-row"') == 2  # the big track, then two dotted rows
    svg, _, problems = built(one("kg1-letter-write", letter="أ", guided=3, independent=1))
    assert problems == [] and svg.count('class="trace-row"') == 4
    svg, _, problems = built(one("kg1-letters-write", letters=["ت", "ث"], guided=2, independent=1))
    assert problems == [] and svg.count('class="trace-row"') == 6
    _, _, problems = built(one("kg1-word-write", words=["أسد", "قمر"], mode="independent"))
    assert problems == ["KG1 traces words on dots only (decision 2)"]


def test_vowels_are_heard_and_words_are_recognized_not_read() -> None:
    svg, answer, problems = built(one("kg1-harakat", haraka="kasra", letters=["ب", "د", "ر"], mode="listen"))
    assert problems == [] and len(answer) == 3 and svg.count('class="key-ring"') == 3
    _, _, problems = built(one("kg1-harakat", haraka="fatha", letters=["ب"], mode="write"))
    assert problems
    svg, answer, problems = built(one("kg1-word-read", words=["فيل", "كرة", "نحلة"], mode="first-letter"))
    assert problems == [] and [a.split()[-1] for a in answer] == ["ف", "ك", "ن"]


def test_picture_sums_stay_within_five_and_show_their_counts() -> None:
    svg, answer, problems = built(one("kg1-picture-add", "math", max=5))
    counts = [int(n) for n in re.findall(r'data-count="(\d+)"', svg)]
    assert problems == [] and len(answer) == 3 and counts and max(counts) <= 5
    svg, answer, problems = built(one("kg1-picture-subtract", "math", max=4, mode="story"))
    crossed = [int(n) for n in re.findall(r'data-crossed="(\d+)"', svg)]
    assert problems == [] and all(c >= 1 for c in crossed) and "بقي" in svg


def test_pen_rows_run_from_the_start_side_and_the_pen_check_takes_kg1_strokes() -> None:
    (stroke,) = row_strokes("teeth", 150, 30, 50, 8)
    assert stroke.start[0] == 150 and stroke.end[0] == 30
    assert len(row_strokes("arc", 150, 30, 50, 8)) == 3
    svg, _, problems = built(
        one("kg1-assessment", "pen", checklist=["grip", "pressure", "direction"], tracing=["loop", "teeth"])
    )
    assert problems == [] and "مسكة القلم" in svg and "أسنان السين" in svg
    _, _, problems = built(one("kg1-assessment", "pen", checklist=["grip"], tracing=["wave"]))
    assert problems


def test_english_traces_only_in_volume_1_and_allows_box_for_x() -> None:
    page = one("kg1-en-letter", "english", letter="X", word="box", volume=3, color_in=True)
    b = dataclasses.replace(volume(1, range(0)), pages=(page,))
    out = REGISTRY[page.type].build(PageContext(page, b, ASSETS))
    assert out.problems == []
    page = one("kg1-en-letter", "english", letter="A", word="apple", volume=1)
    out = REGISTRY[page.type].build(PageContext(page, b, ASSETS))
    assert len(out.data["rows"]) == 3 and all("trace-row" in str(r) for r in out.data["rows"])


def boxes(svg: str, pattern: str) -> list[tuple[float, float, float, float]]:
    return [tuple(float(v) for v in m) for m in re.findall(pattern, svg)]  # type: ignore[misc]


def test_number_pages_write_each_number_and_never_show_none() -> None:
    svg, _, problems = built(one("kg1-number-write", "math", numbers=[4, 5, 0], guided=2, independent=1))
    assert problems == [] and svg.count('class="trace-row"') == 4  # a row for each number, then one alone
    assert "أكتب وحدي: ٤ ٥ ٠" in svg
    svg, _, problems = built(one("kg1-number-write", "math", numbers=[9, 10], guided=2, independent=1))
    assert (
        problems == [] and svg.count('class="trace-row"') == 3
    )  # two numbers: a full row and a row to go on
    title = texts_kg1("math", "number-write", {"numbers": [1, 2, 3]}, "")
    assert title and title[0] == "أكتب الأعداد 1 و2 و3"
    assert all("None" not in p.title + p.instruction for n in (1, 2, 3) for p in volume(n).pages)


def test_texts_name_the_shapes_the_place_words_and_the_number_train_of_the_page() -> None:
    assert texts_kg1("math", "shapes", {"shapes": ["circle", "square"]}, "")[0] == "الدائرة والمربع"
    assert texts_kg1("math", "shapes", {"shapes": ["triangle", "rectangle"]}, "")[0] == "المثلث والمستطيل"
    assert texts_kg1("pen", "pen-lines", {"line": "shape", "shapes": ["square", "triangle"]}, "")[0] == (
        "المربع والمثلث"
    )
    assert (
        texts_kg1("math", "position-words", {"concept": "inside-outside"}, "")[0] == "داخل الصندوق أم خارجه؟"
    )
    assert texts_kg1("math", "pattern-complete", {"kind": "numbers"}, "")[0] == "قطار الأعداد"


def test_picture_sums_keep_their_groups_clear_of_the_numerals_and_agree_with_their_nouns() -> None:
    for top in (3, 4, 5):
        svg, _, problems = built(one("kg1-picture-add", "math", max=top))
        items = boxes(
            svg, r'<svg x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="[\d.]+" [^>]*class="pic item'
        )
        rings = boxes(svg, r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="#FFFDF6"')
        assert problems == [] and items and rings
        for x, y, w in items:
            assert x >= 0 and x + w <= 186  # inside the work area
            for cx, cy, r in rings:  # clear of the three numerals of its row
                assert x + w <= cx - r or x >= cx + r or y + w <= cy - r or y >= cy + r
    ctx = PageContext(one("kg1-picture-add", "math"), volume(1, range(0)), ASSETS)
    assert counted(ctx, 1, "bird", subject=True) == "عصفور واحد" and counted(ctx, 1, "bird") == "عصفور"
    assert counted(ctx, 2, "bird") == "عصفوران" and counted(ctx, 3, "bird") == "٣ عصافير"
    assert counted(ctx, 1, "apple", subject=True) == "تفاحة واحدة"
    assert counted(ctx, 2, "apple", subject=True) == "تفاحتان"
    assert counted(ctx, 2, "apple", accusative=True) == "تفاحتين"
    svg, _, problems = built(one("kg1-picture-add", "math", max=5, mode="story"))
    assert problems == [] and "١ عصافير" not in svg and "١ تفاحات" not in svg


def test_counting_to_ten_offers_three_numerals_a_row() -> None:
    svg, answer, problems = built(one("kg1-count-and-circle", "math", numbers=[6, 7, 8, 9, 10]))
    cards = re.findall(r'<rect x="[\d.]+" y="([\d.]+)" width="22" height="24"', svg)
    assert problems == [] and len(cards) == 12 and svg.count('class="key-ring"') == 4
    assert sorted(Counter(cards).values()) == [3, 3, 3, 3]  # three numerals in each of the 4 rows
    assert len(answer[0].split("،")) == 4


def test_the_english_find_page_fills_the_page_with_four_rows() -> None:
    svg, answer, problems = built(one("kg1-find-letter-en", "english", letters=["A", "B"]))
    assert problems == [] and [a.split(":")[0] for a in answer] == ["A a", "B b", "A a", "B b"]
    assert all(int(a.split(":")[1]) >= 2 for a in answer) and svg.count('class="key-ring"') >= 8


def test_three_letters_and_six_words_fit_without_overlapping_cards() -> None:
    page = next(p for p in PLAN.volumes[0].pages if p.n == 89)
    words = [str(w) for w in page.params["words"]]
    svg, answer, problems = built(one("kg1-match-letter-picture", letters=["ج", "ح", "خ"], words=words))
    cards = sorted(boxes(svg, r'<rect x="[\d.]+" y="([\d.]+)" width="40" height="([\d.]+)"'))
    assert problems == [] and len(cards) == 6 and len(answer) == 3
    assert all(y + h <= y2 for (y, h), (y2, _) in pairwise(cards))


def test_the_dot_to_dot_pages_draw_big_numbered_dots_and_show_the_picture_they_make() -> None:
    for to, level, name in ((5, 1, "بيت"), (10, 1, "نجمة"), (10, 2, "سمكة")):
        svg, answer, problems = built(one("kg1-dot-to-dot", "pen", to=to, level=level))
        assert problems == [] and name in answer[0] and svg.count('class="wb-num"') == to
        assert svg.count("<circle") >= to  # the dots, and the first one green


def test_a_memory_page_hides_one_of_five_pictures() -> None:
    svg, answer, problems = built(one("kg1-memory", "thinking", items=5))
    assert problems == [] and "الصورة التي اختفت" in answer[0] and "؟" in svg and svg.count("key-ring") == 1


def test_classifying_by_color_has_three_baskets_and_the_sea_has_no_turtle() -> None:
    svg, answer, problems = built(
        one("kg1-classify", "thinking", by="color", colors=["أحمر", "أصفر", "أزرق"])
    )
    assert problems == [] and len(answer) == 3 and svg.count('class="key-line"') == 6  # a line per picture
    _, lines, _ = built(one("kg1-classify", "thinking", by="habitat", categories=["البر", "البحر"]))
    assert "سلحفاة" not in " ".join(lines)


def test_hearing_a_word_leaves_the_word_its_corner_and_a_short_letter_gets_a_bigger_row() -> None:
    for word in ("أسد", "قمر", "موز", "نحلة", "خروف"):
        _, width = model_word(word_shapes(word), 30, 22, {})
        assert width <= WORD_ROOM + 0.01
    assert body_ratio(shape_of("ه")) < 0.6
    assert body_ratio(shape_of("ب")) >= 0.6
    svg, _, problems = built(one("kg1-letter-trace", letter="ه", sizes=["l", "m"]))
    assert problems == [] and svg.count('class="trace-row"') == 2
    _, _, problems = built(one("kg1-word-write", words=["أسد", "قمر"], mode="dotted"))
    assert problems == []


def test_the_color_by_code_heart_keeps_whole_cells_and_its_legend_inside_the_page() -> None:
    _, answer, problems = built(
        one("kg1-color-by-code", "mixed", letters=["أ", "ب", "ت"], numbers=[1, 2, 3], mode="color-by-code")
    )
    assert problems == [] and len(answer[0].split("،")) == 6  # every code of the legend has a cell


def test_the_english_review_never_draws_a_crayon_outside_its_card() -> None:
    svg, _, problems = built(
        one("kg1-vocab-review", "english", units=["Numbers", "Colors", "Shapes", "Family"])
    )
    assert problems == []
    for tx, scale in re.findall(r"translate\(([\d.]+) [\d.]+\) scale\(([\d.]+)\)", svg):
        assert float(tx) + 34 * float(scale) <= 186  # a crayon's right end stays on the page


@pytest.mark.parametrize("number", [1, 2, 3])
def test_the_whole_volume_and_its_answer_key_print_and_pass_preflight(tmp_path: Path, number: int) -> None:
    """The acceptance render (about a minute a volume): nothing overflows (the engine refuses to print
    otherwise), fonts embedded, images at 300 DPI, bleed and safe area respected, in the volume and in its
    answer key."""
    book = volume(number)
    pages = build_pages(book, ASSETS)
    g = book.geometry
    pdf = asyncio.run(print_pdf(book_html(book, pages, ASSETS), tmp_path / "v.html", tmp_path / "v.pdf", g))
    assert len(PdfReader(pdf).pages) == PAGES[number]
    key = asyncio.run(
        print_pdf(answer_key_html(book, pages, ASSETS), tmp_path / "k.html", tmp_path / "k.pdf", g)
    )
    for name, file in (("volume", pdf), ("key", key)):
        report = preflight(file, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
        assert report.passed and all(c.ok for c in report.checks), (name, report.to_dict())


def test_a_picture_for_a_letter_is_never_a_number_a_color_or_a_shape() -> None:
    import random

    r = random.Random(3)
    for letter in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي":
        pool = first_sound_pictures(letter)
        assert pool and all(PICTURES[p].category not in NOT_A_FIRST_SOUND for p in pool), letter
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":  # the English reviews too: «eight» is not a picture for E
        assert all(PICTURES[p].category not in NOT_A_FIRST_SOUND for p in pictures_for(letter, r, 3))
    assert "ten" not in first_sound_pictures("ع")
    assert "plane" not in first_sound_pictures("ط")  # a plain «طائرة» never appears (decision 7)
    for letter in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي":
        for pid in first_sound_pictures(letter):
            assert strip_tashkeel(PICTURES[pid].word_ar) not in REPLACED_WORDS, (letter, pid)


def test_the_arabic_find_page_keeps_its_cards_inside_the_page_and_circles_one_letter_a_row() -> None:
    svg, answer, problems = built(
        one(
            "kg1-find-letter",
            letters=["ب", "ت", "ث"],
            distractors=list("نمهو"),
        )
    )
    assert problems == [] and len(answer) == 6  # three counts, three pictures
    for x, w in boxes(svg, r'<rect x="([\d.-]+)" y="[\d.]+" width="([\d.]+)" height="[\d.]+" rx="4"'):
        assert x >= 0 and x + w <= 186  # the letter boxes stay on the page
    assert svg.count('class="key-ring"') >= 9 + 3  # every target bubble and one letter of each picture row


def test_the_colored_picture_pages_use_whole_cells_and_every_letter_shows_up() -> None:
    _, answer, problems = built(one("kg1-color-by-letter", "arabic", letters=["ف", "ق", "ك", "ل"]))
    assert problems == [] and len(answer[0].split("،")) == 4
    _, answer, problems = built(one("kg1-color-by-letter", "arabic", letters=["م", "ن", "ه", "و", "ي"]))
    assert problems == [] and len(answer[0].split("،")) == 5
    counts = [
        int(n)
        for n in re.findall(
            r"\((\d+|[٠-٩]+)\)", answer[0].translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
        )
    ]
    assert min(counts) >= 2 and max(counts) - min(counts) <= 2  # about as many cells for each letter


def test_the_review_pictures_are_the_words_the_plan_taught_for_each_letter() -> None:
    """The find pages and the reviews ask about the pictures of the letter's own pages first: the tables of
    `foundation_kg1` stay equal to the plan, so a child is only asked about words they have met."""
    arabic = {
        str(p.params["letter"]): tuple(picture_id(str(w)) for w in p.params["words"])
        for v in PLAN.volumes
        for p in v.pages
        if p.type == "letter-intro"
    }
    english = {
        str(p.params["letter"]): picture_id(str(p.params["word"]))
        for v in PLAN.volumes
        for p in v.pages
        if p.type == "en-letter"
    }
    assert arabic == LETTER_PICTURES_KG1 and english == ENGLISH_PICTURES_KG1
    assert set(first_sound_pictures("ق")) == {"moon", "pencil"}


def test_inside_outside_puts_the_ball_in_the_first_box_and_one_picture_in_each() -> None:
    svg, answer, problems = built(one("kg1-inside-outside", "math", concept="inside-outside"))
    assert problems == [] and len(answer) == 3 and "كُرَة" in answer[0]
    assert svg.count('class="key-ring"') == 3


def test_a_review_of_two_letters_still_offers_three_pictures_a_row() -> None:
    for letters, section in ((["أ", "ب"], "arabic"), (["A", "B"], "english")):
        svg, answer, problems = built(one("kg1-unit-review", section, letters=letters))
        assert problems == [] and svg.count('viewBox="0 0 100 100"') == 6  # two rows of three pictures
        assert any(line.startswith(f"{letters[0]}:") for line in answer)


def test_the_hidden_stars_page_hides_five_stars_among_other_small_things() -> None:
    svg, answer, problems = built(one("kg1-hidden-stars", "thinking", count=5))
    assert problems == [] and svg.count('class="key-ring"') == 5 and "٥ نجوم" in answer[0]
    assert {p.number: p.type for p in volume(2).pages}[82] == "hidden-pictures"  # «٥ أشياء مختبئة»: as in KG2


def test_the_story_pages_follow_the_plan_s_steps_and_print_no_tanween_labels() -> None:
    page = next(p for p in PLAN.volumes[1].pages if p.n == 59)
    assert page.params["steps"] == 3 and engine_type_kg1(page) == "kg1-story-sequence"
    svg, answer, problems = built(one("kg1-story-sequence", "thinking", task="sequence", steps=3))
    assert problems == [] and svg.count('class="key-ring"') == 3  # three frames, three cut-out pictures
    assert "بَذْرَة ← نَبْتَة ← زَهْرَة" in answer[0] and "ًا" not in svg  # no «أولًا» labels: numbers only
    svg, answer, problems = built(one("kg1-story-sequence", "thinking", task="sequence", steps=4))
    assert problems == [] and svg.count('class="key-ring"') == 4
    _, _, problems = built(one("kg1-story-sequence", "thinking", task="sequence", steps=5))
    assert problems
