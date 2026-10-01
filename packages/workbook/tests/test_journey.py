from pathlib import Path
from typing import Any

import pytest
from qamra_workbook.journey import (
    SMALL_SECTION,
    Journey,
    JourneyPage,
    Section,
    Stage,
    check_letter_pace,
    check_letters,
    check_memory_pairs,
    check_numbers,
    check_sections,
    check_stage_one_numerals,
    check_stage_pages,
    check_stage_scope,
    check_variety,
    check_words,
    load,
    problems,
    retired_words,
)

PLAN = Path(__file__).resolve().parents[3] / "content" / "journey" / "plan.yaml"
SECTIONS = [Section(id="think", title_ar="أدرّب عقلي", icon="🧠", journey_step="أفكر")]
MAP = [
    Section(id=x, title_ar=x, icon="•", journey_step=x) for x in ("think", "eye-hand", "listening", "finale")
]


def page(
    n: int, kind: str, section: str = "think", instruction: str = "لوّن الدوائر", **params: Any
) -> JourneyPage:
    return JourneyPage(
        n=n,
        section=section,
        type=kind,
        title="مهمة",
        instruction=instruction,
        skill="x",
        difficulty=1,
        params=params,
    )


def shared(n: int, kind: str, section: str, pair: list[str]) -> JourneyPage:
    """An opener or «ماذا تعلمت؟» shared by two sections."""
    return page(n, kind, section).model_copy(update={"merged": pair})


def stage(pages: list[JourneyPage], number: int = 1) -> Stage:
    return Stage(stage=number, age="3–4", title_ar="المحطة", objectives={}, pages=pages)


def journey(*stages: Stage, letters: tuple[str, ...] = ("ب", "ت", "ث", "ن")) -> Journey:
    return Journey(
        title_ar="رحلتي",
        title_en="Journey",
        idea="",
        skill_order="",
        difficulty_notes="",
        writing_notes="",
        letter_order=list(letters),
        sections=MAP,
        samples=[],
        stages=list(stages),
    )


def taught(first: int, *letters: str) -> list[JourneyPage]:
    """Each letter's finger-trace page, then its letter-trace page, from page `first` on (stage 2)."""
    out = []
    for i, letter in enumerate(letters):
        out.append(page(first + 2 * i, "finger-trace", "think", letter=letter))
        out.append(page(first + 2 * i + 1, "letter-trace", "think", letter=letter))
    return out


def test_instructions_stay_short() -> None:
    long = page(1, "odd-one-out", instruction="ابحث عن الصورة المختلفة بين كل هذه الصور الجميلة هنا")
    assert any("instruction has 10 words" in p for p in check_stage_pages(stage([long])))


def test_sections_open_on_the_map_and_close_with_a_review() -> None:
    pages = [
        page(1, "journey-map", "intro"),
        page(2, "section-opener"),
        page(3, "odd-one-out"),
        page(4, "mini-certificate"),
    ]
    assert check_sections(stage(pages), SECTIONS) == []
    pages[1] = page(2, "odd-one-out")
    assert any("starts with a section-opener" in p for p in check_sections(stage(pages), SECTIONS))


def test_the_same_format_is_not_repeated() -> None:
    pages = [page(i, "maze") for i in range(1, 4)]
    assert check_variety(stage(pages)) == ["S1 p3: more than 2 maze pages in a row"]


def test_memory_pages_are_the_two_sides_of_one_sheet() -> None:
    assert check_memory_pairs(stage([page(1, "memory-look"), page(2, "memory-recall")])) == []
    wrong = stage([page(1, "odd-one-out"), page(2, "memory-look"), page(3, "memory-recall")])
    assert any("odd page" in p for p in check_memory_pairs(wrong))


def test_stage_one_has_no_letters_and_small_quantities() -> None:
    pages = [page(1, "letter-intro", letter="ب"), page(2, "quantity-first", numbers=[7])]
    found = check_stage_scope(stage(pages))
    assert any("no letters in stage 1" in p for p in found)
    assert any("quantities 1–5" in p for p in found)


def test_every_stage_visits_every_section() -> None:
    pages = [
        page(1, "journey-map", "intro"),
        page(2, "section-opener"),
        page(3, "odd-one-out"),
        page(4, "mini-certificate"),
    ]
    found = check_sections(stage(pages), MAP)
    assert any("every stage visits every section" in p and "'eye-hand', 'listening'" in p for p in found)


def small_pair(think_pages: int = 1) -> list[JourneyPage]:
    """think and eye-hand share their opener and «ماذا تعلمت؟»; listening and finale have their own."""
    think = [page(3 + i, "odd-one-out") for i in range(think_pages)]
    k = 3 + think_pages
    return [
        page(1, "journey-map", "intro"),
        shared(2, "section-opener", "think", ["think", "eye-hand"]),
        *think,
        page(k, "maze", "eye-hand"),
        shared(k + 1, "what-i-learned", "eye-hand", ["think", "eye-hand"]),
        page(k + 2, "section-opener", "listening"),
        page(k + 3, "loud-soft", "listening"),
        page(k + 4, "what-i-learned", "listening"),
        page(k + 5, "section-opener", "finale"),
        page(k + 6, "mini-certificate", "finale"),
    ]


def test_two_small_sections_share_an_opener_and_a_review() -> None:
    assert check_sections(stage(small_pair()), MAP) == []
    big = check_sections(stage(small_pair(SMALL_SECTION + 1)), MAP)
    assert any(f"only small sections (≤ {SMALL_SECTION} pages" in p and "think has 6" in p for p in big)


def test_a_shared_page_sits_where_it_opens_or_closes_both_sections() -> None:
    pages = small_pair()
    wil = pages[4]
    pages[4] = page(wil.n, "what-i-learned", "eye-hand")  # eye-hand closes alone: think is left open
    assert any("section think must end with what-i-learned" in p for p in check_sections(stage(pages), MAP))
    pages = small_pair()
    pages[2] = shared(3, "odd-one-out", "think", ["think", "eye-hand"])  # not an opener or a review
    found = check_sections(stage(pages), MAP)
    assert any("only a section's opener or closing «ماذا تعلمت؟» is shared" in p for p in found)
    pages = small_pair()
    pages[1] = shared(2, "section-opener", "think", ["think", "listening"])  # not neighbours
    found = check_sections(stage(pages), MAP)
    assert any("merged: ['think', 'listening']" in p for p in found)
    assert any("section eye-hand starts with a section-opener" in p for p in found)


def test_one_new_letter_per_page() -> None:
    together = [
        page(1, "finger-trace", letter="ب"),
        page(2, "finger-trace", letter="ت"),
        page(3, "letter-trace", letters=["ب", "ت"]),
    ]
    found = check_letter_pace(journey(stage(together, 2)))
    assert found == ["S2 p3: 2 new letters (ب ت); one new letter per page"]
    one_by_one = [*taught(1, "ب", "ت"), page(5, "find-letter", letters=["ب", "ت"])]
    assert check_letter_pace(journey(stage(one_by_one, 2))) == []


def test_a_letter_never_shows_before_its_first_page() -> None:
    early = [page(1, "find-letter", letter="ب"), *taught(2, "ب")]
    found = check_letter_pace(journey(stage(early, 2)))
    assert found == ["S2 p1: shows ب before the page that introduces it"]
    sound_first = [page(1, "first-sound", letter="ب", words=["بطة"]), *taught(2, "ب")]  # the sound only
    assert check_letter_pace(journey(stage(sound_first, 2))) == []


def test_four_letters_on_a_page_only_to_review() -> None:
    four = ["ب", "ت", "ث", "ن"]
    practice = [*taught(1, *four), page(9, "find-letter", letters=four)]
    found = check_letter_pace(journey(stage(practice, 2)))
    assert found == [
        "S2 p9: 4 letters on a find-letter page; only review pages "
        "(unit-review, what-i-learned, assessment) combine 4 letters or more"
    ]
    review = [*taught(1, *four), page(9, "unit-review", letters=four)]
    assert check_letter_pace(journey(stage(review, 2))) == []
    three = [*taught(1, *four), page(9, "find-letter", letters=four[:3])]
    assert check_letter_pace(journey(stage(three, 2))) == []


def test_each_letter_goes_through_its_three_pages() -> None:
    complete = [*taught(1, "ب"), page(3, "find-letter", letters=["ب"])]
    assert check_letters(journey(stage(complete, 2), letters=("ب",))) == [
        "finger-trace pages must introduce all 28 letters once, in letter_order; found ب",
        "en-letter pages must cover A–Z once, in order; found ",
    ]
    no_pen = [page(1, "finger-trace", letter="ب"), page(2, "find-letter", letters=["ب"])]
    found = check_letters(journey(stage(no_pen, 2), letters=("ب",)))
    assert "S2 letter ب: missing letter-trace after its finger-trace page" in found
    no_find = [*taught(1, "ب"), page(3, "unit-review", letters=["ب"])]
    found = check_letters(journey(stage(no_find, 2), letters=("ب",)))
    assert "S2 letter ب: missing find-letter after its finger-trace page" in found


def test_the_letters_split_fourteen_and_fourteen() -> None:
    order = list("أبتثجحخدذرزسشصضطظعغفقكلمنهوي")
    ok = [
        stage([page(i + 1, "finger-trace", letter=x) for i, x in enumerate(order[:14])], 2),
        stage([page(i + 1, "finger-trace", letter=x) for i, x in enumerate(order[14:])], 3),
    ]
    split = [f for f in check_letters(journey(*ok, letters=tuple(order))) if "per stage" in f]
    assert split == []
    late = [
        stage([page(i + 1, "finger-trace", letter=x) for i, x in enumerate(order[:13])], 2),
        stage([page(i + 1, "finger-trace", letter=x) for i, x in enumerate(order[13:])], 3),
    ]
    split = [f for f in check_letters(journey(*late, letters=tuple(order))) if "per stage" in f]
    first, second = "".join(order[:13]).replace("أ", "ا"), "".join(order[13:])  # alif is written ا
    assert split == [
        f"S2 introduces letters 1–14 of letter_order (14 per stage); found {first}",
        f"S3 introduces letters 15–28 of letter_order (14 per stage); found {second}",
    ]


def test_stage_one_recognizes_numerals_one_to_five_and_never_writes_them() -> None:
    one_to_five = [1, 2, 3, 4, 5]
    ok = [
        page(1, "quantity-first", "math", numbers=one_to_five, answer_with="dots"),
        page(2, "number-intro", "math", numbers=one_to_five),
        page(3, "quantity-first", "math", numbers=one_to_five, answer_with="numerals"),
    ]
    assert check_stage_one_numerals(stage(ok)) == []
    traced = check_stage_one_numerals(stage([*ok, page(4, "number-trace", "math", numbers=[1, 2])]))
    assert traced == ["S1: stage 1 recognizes numerals but never writes them (pages [4])"]
    on_a_line = [*ok, page(4, "write-progression", "math", level=2, target=[1, 2])]
    assert any("never writes" in p for p in check_stage_one_numerals(stage(on_a_line)))
    unseen = check_stage_one_numerals(stage([ok[0], ok[2]]))
    assert unseen == ["S1: stage 1 meets the numerals 1–5 on number-intro pages; missing [1, 2, 3, 4, 5]"]
    unmatched = check_stage_one_numerals(stage(ok[:2]))
    assert any("matches every numeral 1–5 to its quantity" in p for p in unmatched)
    six = check_stage_scope(stage([*ok, page(4, "number-quantity-match", "math", numbers=[6])]))
    assert any("quantities 1–5" in p for p in six)


def test_numerals_come_after_their_quantities() -> None:
    first = [
        page(1, "number-intro", "math", numbers=[1, 2]),
        page(2, "quantity-first", "math", numbers=[1, 2], answer_with="dots"),
    ]
    found = check_numbers(journey(stage(first)))
    assert "number 1: the numeral comes before its quantity page" in found
    matched_only = [page(1, "quantity-first", "math", numbers=[3], answer_with="numerals")]
    found = check_numbers(journey(stage(matched_only)))
    assert "number 3: needs a quantity-first page" in found  # answering with numerals is not a quantity page


def test_the_replaced_words_never_appear() -> None:
    assert retired_words({"words": ["ذرة", "ذَيل", "ظِلّ", "لسان", "ضرس"]}) == []
    assert retired_words({"words": ["ظَبْي"], "title": "ذِئْب"}) == ["ذئب", "ظبي"]
    words = [page(1, "finger-trace", "think", letter="ذ", words=["ذرة", "ذئب"])]
    assert check_words(journey(stage(words, 2))) == ["S2 p1: «ذئب» was replaced by «ذَيْل»"]
    notes = journey(stage([page(1, "odd-one-out")], 2)).model_copy(update={"idea": "ظبي في الغابة"})
    assert check_words(notes) == ["the plan's notes still use «ظبي»; it was replaced by «ظِلّ»"]


@pytest.mark.skipif(not PLAN.exists(), reason="the journey plan is not written yet")
def test_journey_plan_keeps_every_rule() -> None:
    assert problems(load(PLAN)) == []
