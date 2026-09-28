"""The rules that encode Tareq's decisions of 28 September 2026 (docs/workbook/decisions-2026-09-28.md)."""

from pathlib import Path
from typing import Any

import pytest
from qamra_workbook.curriculum import (
    ARABIC_LETTERS,
    EDUCATOR_SIGN_OFF_AR,
    PAGE_TYPE_AR,
    PAGE_TYPES,
    VOLUME_3_MUST_HAVE,
    Curriculum,
    Page,
    Unit,
    Volume,
    check_al,
    check_arabic_letters,
    check_independent_writing,
    check_notes,
    check_number_range,
    check_numbers,
    check_pen_assessment,
    check_review_rhythm,
    check_review_weeks,
    check_scope,
    check_vowels,
    check_weeks,
    check_words,
    load,
    render_educator,
    render_markdown,
)

ROOT = Path(__file__).resolve().parents[3]
CURRICULUM = ROOT / "content" / "workbook" / "curriculum"
DOCS = ROOT / "docs" / "workbook"
MARKS = ["grip", "pressure", "direction"]


def pg(
    n: int,
    kind: str,
    subject: str = "arabic",
    week: int = 1,
    unit: str = "u",
    skill: str = "مهارة",
    **params: Any,
) -> Page:
    return Page(
        n=n, week=week, subject=subject, unit=unit, type=kind, skill=skill, difficulty=1, params=params
    )  # type: ignore[arg-type]


def vol(pages: list[Page], number: int = 1, weeks: int = 1, review_weeks: list[int] | None = None) -> Volume:
    units = [Unit(id=p.unit, subject=p.subject, title_ar="وحدة") for p in {p.unit: p for p in pages}.values()]
    return Volume(
        volume=number,
        term=number,
        weeks=weeks,
        title_ar="جزء",
        objectives={},
        units=units,
        pages=pages,
        review_weeks=review_weeks or [],
    )


def plan(level: str, *volumes: Volume, **fields: Any) -> Curriculum:
    base: dict[str, Any] = {
        "level": level,
        "age": "4–5",
        "title_ar": "دوسية",
        "title_en": "Workbook",
        "letter_order": list(ARABIC_LETTERS),
        "progression_notes": "",
        "interleaving_notes": "",
        "alignment_notes": "",
        "volumes": list(volumes),
    }
    return Curriculum.model_validate(base | fields)


def test_the_letter_order_is_alphabetical() -> None:
    shuffled = ["ب", "أ", *ARABIC_LETTERS[2:]]
    found = check_arabic_letters(plan("kg1", letter_order=shuffled))
    assert "letter_order must be the 28 letters in alphabetical order, أ ب ت ث … (decision 1)" in found
    assert not any("alphabetical" in p for p in check_arabic_letters(plan("kg1")))


def test_kg1_writes_alone_only_the_listed_simple_letters() -> None:
    pages = [
        pg(1, "letter-write", letters=["ب"], guided=2, independent=1),
        pg(2, "letter-write", letters=["ج"], guided=2, independent=1),
        pg(3, "word-write", words=["أسد"], mode="independent"),
        pg(4, "word-write", words=["قمر"], mode="dotted"),
    ]
    found = check_independent_writing(plan("kg1", vol(pages), independent_writing=["ب", "د"]))
    assert found == [
        "V1 p2: letter-write for ج; kg1 only traces them",
        "V1 p3: word-write asks for writing alone; kg1 writes alone only listed letters",
        "letter د is in independent_writing but no letter-write page has an independent row",
    ]
    assert check_independent_writing(plan("kg2", vol(pages))) == []  # KG2 writes every letter alone


def test_a_traced_letter_needs_no_write_page_but_a_written_one_does() -> None:
    steps = [
        pg(1, "letter-intro", letter="ج"),
        pg(2, "letter-trace", letter="ج"),
        pg(3, "find-letter", letters=["ج"]),
        pg(4, "match-letter-picture", letters=["ج"]),
    ]
    assert not any(
        "letter ج" in p for p in check_arabic_letters(plan("kg1", vol(steps), independent_writing=["ب"]))
    )
    assert "V1 letter ج: missing letter-write" in check_arabic_letters(plan("kg2", vol(steps)))


def test_a_review_week_introduces_nothing_reviews_the_new_letters_and_is_light() -> None:
    intros = [pg(n, "letter-intro", week=1, letter=x) for n, x in enumerate("أبتث", start=1)]
    practice = [pg(n, "maze", "pen", week=1, unit="p") for n in range(5, 9)]
    later = [pg(n, "maze", "pen", week=3, unit="p") for n in range(30, 36)]
    good = [pg(10, "coloring", week=2), pg(11, "unit-review", week=2, letters=["أ", "ب", "ت", "ث"])]
    assert check_review_weeks(vol(intros + practice + good + later, weeks=3, review_weeks=[2])) == []
    heavy = [pg(n, "maze", "pen", week=2, unit="p") for n in range(12, 18)]
    bad = [
        pg(10, "letter-intro", week=2, letter="ج"),
        pg(11, "unit-review", week=2, letters=["أ", "ب"]),
        *heavy,
    ]
    found = check_review_weeks(vol(intros + practice + bad + later, weeks=3, review_weeks=[2]))
    assert "V1 p10: letter-intro in review week 2; nothing new here" in found
    assert "V1: review week 2 does not review ت، ث" in found
    assert any(p.startswith("V1: review week 2 has 8 pages; a light week has fewer than") for p in found)
    assert check_review_weeks(vol(intros, weeks=3, review_weeks=[3])) == [
        "V1: review week 3 must be a week of the volume before its last week"
    ]


def test_kg1_has_a_review_week_after_every_four_to_five_letters() -> None:
    six = [pg(n, "letter-intro", week=n, letter=x) for n, x in enumerate("أبتثجح", start=1)]
    assert check_review_rhythm(plan("kg1", vol(six, weeks=6))) == [
        "V1 week 6: 6 new letters since the last review week (at most 5)"
    ]
    early = vol([*six[:3], pg(4, "unit-review", week=4, letters=list("أبت"))], weeks=4, review_weeks=[4])
    assert check_review_rhythm(plan("kg1", early)) == [
        "V1: review week 4 comes after 3 new letters; KG1 reviews every 4–5"
    ]
    on_time = vol([*six[:4], pg(5, "unit-review", week=5, letters=list("أبتث"))], weeks=5, review_weeks=[5])
    assert check_review_rhythm(plan("kg1", on_time)) == []


def test_kg2_term_two_has_eleven_weeks_and_its_extra_week_is_a_review() -> None:
    v2 = vol([pg(1, "maze", "pen", week=1, unit="p")], 2, weeks=10)
    assert "V2: 10 weeks; term 2 has 11 (decision 8)" in check_weeks(v2)
    assert check_review_rhythm(plan("kg2", v2)) == [
        "V2: term 2 counts 11 weeks and the extra week is a review week; list it in review_weeks"
    ]


def test_kg1_only_listens_to_three_vowels_at_the_end_of_volume_3() -> None:
    listen = [
        pg(1, "letter-intro", week=1, letter="ي"),
        *[
            pg(n, "harakat", week=8 + n, haraka=h, letters=["ب"], mode="listen")
            for n, h in ((2, "fatha"), (3, "damma"))
        ],
        pg(4, "harakat", week=11, haraka="kasra", letters=["ب"], mode="listen"),
    ]
    assert check_vowels(plan("kg1", vol([]), vol([], 2), vol(listen, 3, weeks=11))) == []
    early = [
        pg(1, "harakat", week=2, haraka="fatha", letters=["ب"], mode="listen"),
        pg(2, "letter-intro", letter="ي"),
    ]
    assert "V3 p1: KG1 meets the vowels only in V3's last 3 weeks, after the letters" in check_vowels(
        plan("kg1", vol(early, 3, weeks=11))
    )
    sukun = [
        pg(1, "harakat", week=10, skill="أتعرّف على السكون: بْ", haraka="sukun", letters=["ب"], mode="listen")
    ]
    found = check_vowels(plan("kg1", vol(sukun, 3, weeks=11)))
    assert "harakat pages must teach fatha, damma, kasra; found sukun" in found
    assert "V3 p1: sukun is not taught in kg1" in found
    assert "V3 p1: a shadda or sukun or tanween mark; kg1 does not use it" in found
    assert "V3 p1: the skill names السكون" in found
    build = [pg(1, "syllables", week=10, letters=["م"], harakat=["fatha"], mode="build")]
    assert (
        "V3 p1: KG1 vowel pages are sound recognition only (params.mode: listen), no writing"
        in check_vowels(plan("kg1", vol(build, 3, weeks=11)))
    )


def test_kg2_reads_no_tanween_and_no_shadda() -> None:
    pages = [
        pg(1, "harakat", week=7, haraka="تنوين", letters=["ب"]),
        pg(2, "word-read", week=9, words=["غَسَّالَة", "كِتَابٌ"]),
        pg(3, "letter-intro", skill="أتعرّف على حرف الغين مع الغسّالة", letter="غ", words=["غسالة"]),
    ]
    found = check_vowels(plan("kg2", vol(pages, 3, weeks=11)))
    assert "V3 p1: tanween is not taught in kg2" in found
    assert "V3 p2: a shadda or tanween mark; kg2 does not use it" in found
    assert not any(p.startswith("V3 p3") for p in found)  # instruction text may spell أتعرّف and الغسّالة


def test_al_is_read_only_at_the_end_of_kg2_with_a_few_familiar_moon_letter_words() -> None:
    pictures = vol(
        [pg(1, "letter-intro", letter="ق", words=["قمر", "قلم"]), pg(2, "find-letter", words=["باب"])]
    )
    ok = vol([pg(1, "word-read", week=10, words=["الْقَمَر", "الْبَاب"])], 3, weeks=11)
    assert check_al(plan("kg2", pictures, ok)) == []
    early = vol([pg(1, "word-read", week=5, words=["الْقَمَر"])], 3, weeks=11)
    assert check_al(plan("kg2", pictures, early)) == [
        "V3 p1: «القمر»; «ال» is read only in KG2 Volume 3's last 3 weeks"
    ]
    odd = vol(
        [pg(1, "word-read", week=10, words=["الشمس"]), pg(2, "word-read", week=11, words=["الفيل"])],
        3,
        weeks=11,
    )
    assert check_al(plan("kg2", pictures, odd)) == [
        "V3 p1: «الشمس»; «ال» comes only before moon letters, so no sun/moon lesson is needed",
        "V3 p2: «الفيل» is not familiar; «فيل» should appear earlier as a picture word",
    ]
    lesson = vol(
        [pg(1, "word-read", week=10, skill="أميّز اللام الشمسية من القمرية", words=["الْقَمَر"])], 3, weeks=11
    )
    assert check_al(plan("kg2", pictures, lesson)) == ["V3 p1: no sun/moon letter lesson (decision 6)"]
    assert any("«ال» is read only in KG2" in p for p in check_al(plan("kg1", pictures, ok)))
    assert check_al(plan("kg2", pictures)) == [
        "KG2 reads a few familiar «ال» words in Volume 3's last 3 weeks (decision 6)"
    ]


def test_counting_starts_at_one_and_zero_comes_after_five() -> None:
    old = [pg(n, "number-intro", "math", unit="m", number=x) for n, x in enumerate(range(0, 6), start=1)]
    found = check_numbers(plan("kg2", vol(old)))
    assert (
        "V1: number-intro pages must introduce (1, 2, 3, 4, 5, 0) in this order; found (0, 1, 2, 3, 4, 5)"
        in found
    )
    assert "V1 p1: zero before 5; it comes after 5, as «nothing» (decision 5)" in found


def test_numbers_stay_under_the_cap_with_tens_and_ones_in_pictures() -> None:
    v2 = vol([pg(1, "count-and-circle", "math", unit="m", numbers=[9, 12])], 2)
    v3 = vol(
        [
            pg(1, "number-trace", "math", unit="m", numbers=[18, 19]),
            pg(2, "dot-to-dot", "pen", unit="p", to=25),
            pg(3, "number-quantity-match", "math", unit="m", numbers=[16, 20], tens_ones="pictures"),
        ],
        3,
    )
    found = check_number_range(plan("kg2", v2, v3))
    assert "V2 p1: 12; numbers above 10 wait for Volume 3" in found
    assert "V3 p1: numbers above 10 show tens and ones in pictures only (tens_ones: pictures)" in found
    assert "V3 p2: 25 is above the kg2 cap of 20" in found
    assert not any(p.startswith("V3 p3") for p in found)
    kg1 = plan("kg1", vol([pg(1, "dot-to-dot", "pen", unit="p", to=12)], 3))
    assert check_number_range(kg1) == ["V3 p1: 12 is above the kg1 cap of 10"]


def test_replaced_picture_words_never_come_back() -> None:
    pages = [
        pg(1, "letter-intro", letter="ظ", words=["ظرف", "ظبي"]),
        pg(
            2,
            "letter-intro",
            skill="أتعرّف على الطاء مع الطائرة الورقية والطاولة",
            words=["طائرة ورقية", "طاولة"],
        ),
        pg(3, "match-letter-picture", skill="أصل الذال بالذئب والطائرة", words=["ذيل", "لقلق"]),
    ]
    assert check_words(plan("kg2", vol(pages))) == [
        "V1 p1: «ظبي» was replaced by «ظل» (decision 7)",
        "V1 p3: «ذئب» was replaced by «ذيل» (decision 7)",
        "V1 p3: «طائرة» was replaced by «طائرة ورقية» (decision 7)",
        "V1 p3: «لقلق» was replaced by «لعبة» (decision 7)",
    ]


def test_each_volume_closes_with_a_pen_skills_check() -> None:
    body = [pg(1, "pen-lines", "pen", unit="p"), pg(2, "maze", "pen", week=2, unit="p")]
    check = pg(3, "assessment", "pen", week=2, unit="t", checklist=MARKS, tracing=["wave", "circle"])
    last = pg(4, "assessment", "arabic", week=2, unit="a")
    assert check_pen_assessment(vol([*body, check, last], weeks=2)) == []
    assert check_pen_assessment(vol(body, weeks=2)) == [
        "V1: needs one pen-skills assessment at the end (decision 9); found 0"
    ]
    early = pg(2, "assessment", "pen", unit="t", checklist=["grip"], tracing=["wave"])
    assert check_pen_assessment(
        vol([body[0], early, body[1].model_copy(update={"n": 3}), last], weeks=2)
    ) == [
        "V1 p2: the pen checklist must cover grip, pressure, direction; no pressure, direction",
        "V1 p2: the pen-skills assessment has two tracing tasks (params.tracing)",
        "V1 p2: the pen-skills assessment belongs with the final assessments of the last week",
    ]


def test_kg1_has_no_sentences_and_no_syllable_pages_to_require() -> None:
    v1 = vol([pg(1, "pen-lines", "pen", unit="p")])
    v3 = vol(
        [pg(n, kind, subject="arabic") for n, kind in enumerate(VOLUME_3_MUST_HAVE["kg1"], start=1)]
        + [pg(20, "certificate", "mixed", unit="c")],
        3,
    )
    assert check_scope(plan("kg1", v1, vol([pg(1, "sentence-read", sentences=["أنا أقرأ"])], 2), v3)) == [
        "V2: KG1 has no sentences (decision 4)"
    ]
    assert check_scope(plan("kg2", v1, vol([], 2), v3)) == [
        "V3: syllables pages are missing",
        "V3: sentence-read pages are missing",
    ]


def test_every_note_goes_to_the_educator_in_arabic() -> None:
    c = plan("kg1", progression_notes="Easy to hard.", alignment_notes="General.", alignment_notes_ar="عامة.")
    assert check_notes(c) == [
        "progression_notes_ar is missing; the educator's version is in Arabic (decision 10)"
    ]
    assert set(PAGE_TYPE_AR) == set(PAGE_TYPES)


@pytest.mark.parametrize("level", ["kg1", "kg2"])
def test_the_educator_version_is_arabic_with_the_changes_and_the_sign_off(level: str) -> None:
    c = load(CURRICULUM / f"{level}.yaml")
    text = render_educator(c, f"content/workbook/curriculum/{level}.yaml")
    assert EDUCATOR_SIGN_OFF_AR in text
    assert c.changes_ar and all(change in text for change in c.changes_ar)
    assert text.index(c.changes_ar[-1]) < text.index("## التدرّج")
    assert c.progression_notes_ar.strip() in text
    assert c.progression_notes.strip() not in text  # the English notes stay in the repository


@pytest.mark.parametrize("level", ["kg1", "kg2"])
def test_the_rendered_plans_match_the_yaml(level: str) -> None:
    c, source = load(CURRICULUM / f"{level}.yaml"), f"content/workbook/curriculum/{level}.yaml"
    hint = f"run: uv run python -m qamra_workbook.plan render {level}"
    assert (DOCS / f"plan-{level}.md").read_text(encoding="utf-8") == render_markdown(c, source), hint
    assert (DOCS / f"educator-{level}.md").read_text(encoding="utf-8") == render_educator(c, source), hint
