"""The child's name on the activity books (order flows §d chunk 9): the Arabic name page never crashes on a
name (ؤ ئ ء آ ة ى, compound names, Latin letters, very long names), the books print the parent's English
spelling instead of a guess, and the family book's city has a fallback."""

import asyncio
import dataclasses
import datetime as dt
from pathlib import Path

import pytest
from qamra_workbook.family import load as load_family
from qamra_workbook.journey_book import english_name, stage_names, with_name_en
from qamra_workbook.letters.model import Letter
from qamra_workbook.names import (
    MIN_CAP_MM,
    TRACEABLE_AR,
    can_trace,
    check_name,
    clean_arabic,
    clean_latin_name,
    latin_words,
    name_parts,
)
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import build_pages
from qamra_workbook.render.journey_order import stage_specs
from qamra_workbook.render.pages.letters import letter_extent
from qamra_workbook.render.pages.workbook_front import (
    name_scale,
    seated,
    spell,
    spell_name,
    traced_latin,
    traced_name,
)
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import (
    CITY_FALLBACK_PLAIN,
    CITY_FALLBACK_VOWELIZED,
    BookSpec,
    Child,
    Family,
    Member,
    PageSpec,
)
from qamra_workbook.render.workbook import VariantNotBuilt, cover_specs, plan_of, render_order, volume_specs

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
TWENTY = "عبدالرحمنمحمودالخطيب"  # 20 letters, one word (a full name typed without spaces)


def name_page(name: str, script: str = "ar", name_en: str = "") -> BookSpec:
    params = {"script": script, **({"name_en": name_en} if name_en else {})}
    page = PageSpec("t-name", "name-trace", 2, "intro", "اسْمي", "تَتَبَّعِ اسْمَكَ", params=params)
    return BookSpec("foundation", "دوسية", Child(name, "f"), (page,), date=dt.date.today())


# ---- Arabic: which names trace ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["رؤى", "لؤي", "آية", "هيئة", "عائشة", "شاطئ", "مأمون", "إسراء", "نور الهدى", "عبد الرحمن", TWENTY],
)
def test_names_with_hamza_seats_compounds_and_long_names_trace(name: str) -> None:
    assert can_trace(name)
    letters = spell_name(name)
    assert letters and all(isinstance(x, Letter) for x in letters)
    assert len(TWENTY) == 20


def test_the_hamza_seats_are_drawn_over_their_letter_without_dots() -> None:
    for char, forms in (("ؤ", ("isolated", "final")), ("ئ", ("initial", "medial", "isolated", "final"))):
        for form in forms:
            shape = seated(char, form)
            body, mark = shape.strokes[0], shape.strokes[-1]
            assert shape.char == char and shape.form == form and shape.dots == ()
            assert max(y for _, y in mark.polyline) < max(y for _, y in body.polyline)  # the hamza sits above
            x0, _, x1, _ = letter_extent(shape)
            assert x0 >= 0 and x1 <= shape.width + 1  # inside the letter's box
    # رؤى: ر ؤ ى never join the next letter; لؤي: ل joins ؤ, which never joins ي
    assert [(x.char, x.form) for x in spell_name("رؤى")] == [
        ("ر", "isolated"),
        ("ؤ", "isolated"),
        ("ى", "isolated"),
    ]
    louay = [(x.char, x.form) for x in spell_name("لؤي")]
    assert louay == [("ل", "initial"), ("ؤ", "final"), ("ي", "isolated")]
    assert [x.form for x in spell_name("عائشة")] == ["initial", "final", "initial", "medial", "final"]
    aya = [(x.char, x.form) for x in spell_name("آية")]
    assert aya == [("آ", "isolated"), ("ي", "initial"), ("ة", "final")]


def test_content_words_stay_strict_and_now_have_the_hamza_seats() -> None:
    """`spell` writes the book's own words: a letter the hand lacks is a content mistake and raises."""
    assert [x.char for x in spell("مُؤْمِن")] == ["م", "ؤ", "م", "ن"] and len(spell("بِئْر")) == 3
    with pytest.raises(KeyError):
        spell("Sara")


def test_latin_letters_digits_and_symbols_are_not_traced_and_never_raise() -> None:
    assert not can_trace("Sara") and spell_name("Sara") == []
    assert check_name("Sara").unsupported == ("S", "a", "r")
    assert not can_trace("سارة Sara") and [x.char for x in spell_name("سارة Sara")] == ["س", "ا", "ر", "ة"]
    for odd in ("", "   ", "123", "🙂", "ليان2", "Adam", "<b>"):
        assert not can_trace(odd)
        spell_name(odd)  # never raises
        traced_name(odd)
    assert set("ؤئءآةىأإ") <= TRACEABLE_AR


def test_names_are_cleaned_before_the_check() -> None:
    assert clean_arabic("  مُحَمَّد  ") == "محمد"  # tashkeel
    assert clean_arabic("ليـــان") == "ليان"  # tatweel
    assert clean_arabic("علی") == "علي" and clean_arabic("کرم") == "كرم"  # Persian keyboard letters
    assert clean_arabic("ﻻنا") == "لانا"  # presentation forms
    assert clean_arabic("نور-الهدى") == "نور الهدى"
    assert can_trace("مُحَمَّد") and can_trace("علی")


def test_a_long_name_traces_its_first_parts_and_keeps_compounds_whole() -> None:
    assert name_parts(("محمد", "عبد", "الرحمن", "أحمد")) == ["محمد", "عبد الرحمن", "أحمد"]
    assert name_parts(("نور", "الهدى")) == ["نور الهدى"] and name_parts(("أبو", "بكر")) == ["أبو بكر"]
    assert traced_name("ليان") == "ليان" and traced_name("نور الهدى") == "نور الهدى"
    assert traced_name("محمد عبد الرحمن أحمد العلي الخطيب") == "محمد عبد الرحمن"
    for name in ("عبد الرحمن محمد أحمد العلي", "محمد عبد الرحمن", "محمد أحمد عبد الرحمن الخطيب"):
        assert not traced_name(name).endswith("عبد")  # never «عبد» without its other half
    for name in ("نور الهدى", "محمد عبد الرحمن أحمد العلي الخطيب"):
        assert name_scale(spell_name(traced_name(name)), 176.0, 22.0) >= MIN_CAP_MM
    assert 0 < name_scale(spell_name(TWENTY), 176.0, 22.0) < MIN_CAP_MM  # one long word: shrunk to fit, whole


@pytest.mark.parametrize(
    "name", ["رؤى", "لؤي", "آية", "هيئة", "نور الهدى", TWENTY, "Sara", "سارة Sara", "🙂"]
)
def test_the_name_page_builds_for_every_name(name: str) -> None:
    page = build_pages(name_page(name), ASSETS)[0]  # raises when the page's checks fail
    assert len(page.built.data["rows"]) == 3 and page.built.data["model"]
    if can_trace(name) or spell_name(name):
        assert "<path" in str(page.built.data["rows"][0])  # dotted letters to trace
    else:  # the name as printed, over empty lines
        assert "wb-name-typed" in str(page.built.data["model"]) and name in str(page.built.data["model"])


# ---- English: the parent's spelling ---------------------------------------------------------------------


def test_the_english_spelling_is_checked_and_tidied() -> None:
    assert clean_latin_name(" Sara ") == "Sara" and clean_latin_name("Zé") == "Ze"
    assert clean_latin_name("Nour  Al-Huda") == "Nour Al-Huda" and clean_latin_name("O’Neil") == "O'Neil"
    for bad in ("", "سارة", "R2D2", "-Sara", "a" * 41, "Sara!", None):
        assert clean_latin_name(bad) is None
    assert latin_words("Nour Al-Huda") == ["Nour", "Al", "Huda"] and latin_words("Zé") == ["Ze"]
    assert traced_latin("Abdulrahman Mohammad Ali Alkhatib") == "Abdulrahman"
    assert traced_latin("Nour Al-Huda") == "Nour Al Huda"


def test_the_english_name_page_traces_the_parents_spelling() -> None:
    page = build_pages(name_page("ضحى", "en", "Duha"), ASSETS)[0]
    assert page.built.data["name"] == "Duha" and not page.built.problems
    long = build_pages(name_page("ضحى", "en", "Nour Al-Huda"), ASSETS)[0]
    assert long.built.data["name"] == "Nour Al Huda"


def test_the_books_print_the_parents_english_name_and_only_guess_as_a_last_resort() -> None:
    duha = Child("ضحى", "f")
    assert english_name(duha, "Duha") == ("Duha", False)
    assert english_name(duha, "") == ("Daha", True)  # the transliteration, flagged by the order job
    assert english_name(duha, "دحى")[1] is True  # Arabic letters are not an English spelling
    assert english_name(Child("Sara", "f"), "") == ("Sara", False)  # already in English letters
    assert (
        stage_names(1) == (False, False) and stage_names(2) == (True, True) and stage_names(3) == (True, True)
    )
    interior, _ = stage_specs(duha, 2, name_en="Duha")
    english = [p for p in interior.pages if p.type == "name-trace" and p.params.get("script") == "en"]
    assert english and all(p.params["name_en"] == "Duha" for p in english)
    cheer = [p for p in interior.pages if "{name_en}" in str(p.params.get("cheer", ""))]
    assert cheer and interior.personalize(str(cheer[0].params["cheer"]), cheer[0]) == "Well done, Duha!"
    guessed = with_name_en(list(interior.pages), duha, "")
    assert {p.params["name_en"] for p in guessed if p.params.get("script") == "en"} == {"Duha"}  # kept


def test_the_workbook_volume_prints_the_english_name_and_says_when_it_is_a_guess() -> None:
    roua = Child("رؤى", "f")
    book, cover, latin, guessed = volume_specs(roua, "kg2", 1, name_en="Roua", pages=range(1, 5))
    english = next(p for p in book.pages if p.type == "name-trace" and p.params.get("script") == "en")
    assert english.params["name_en"] == "Roua" and latin == "Roua" and not guessed
    assert volume_specs(roua, "kg2", 1, pages=range(1, 5))[3] is True  # no spelling given: a guess
    assert volume_specs(roua, "kg2", 1, pages=range(5, 9))[3] is False  # no English name page: no guess
    assert [p.type for p in cover.pages] == ["workbook-cover-front", "workbook-cover-back"]


# ---- the family book's city -------------------------------------------------------------------------------


def test_an_empty_city_never_prints_souq_with_nothing_after_it() -> None:
    family = Family("الخطيب", (Member("ماما", "سعاد"),))
    plan = load_family(ROOT / "content/family-book/plan.yaml")
    market = next(s for s in plan.sections if s.id == "market")
    hook = family.personalize(market.hook)
    assert hook.startswith(f"سوقُ {CITY_FALLBACK_VOWELIZED} ") and "سوقُ  " not in hook
    assert family.personalize("قبل الذهاب إلى سوق {city}.") == f"قبل الذهاب إلى سوق {CITY_FALLBACK_PLAIN}."
    # a parent's plain line with tanween is still plain («طريقًا آمنًا»)
    park = "اختاروا حديقة أو طريقًا آمنًا في {city}، وابقوا معًا."
    assert family.personalize(park) == f"اختاروا حديقة أو طريقًا آمنًا في {CITY_FALLBACK_PLAIN}، وابقوا معًا."
    assert family.personalize("في {city}") == "في مدينتكم"
    given = dataclasses.replace(family, city="نابلس")
    assert given.personalize(market.hook).startswith("سوقُ نابلس ")
    assert given.personalize("في {city}") == "في نابلس"
    texts = [
        line
        for a in plan.activities
        for p in a.pages
        for line in [p.title, p.instruction, *p.parent]
        if "{city}" in line
    ]
    assert texts and all("{city}" not in family.personalize(t) for t in texts)


def test_the_market_sign_names_the_city_or_the_fallback() -> None:
    page = PageSpec("f-34", "shopping-list", 34, "market", "قائِمَةُ مُشْتَرَياتي", "ماذا نَحْتاجُ؟")
    for city, shown in (("", CITY_FALLBACK_VOWELIZED), ("رام الله", "رام الله")):
        book = BookSpec(
            "family",
            "مغامراتي",
            Child("ليان", "f"),
            (page,),
            date=dt.date.today(),
            family=Family("الخطيب", (Member("ماما"),), city),
        )
        assert build_pages(book, ASSETS)[0].built.data["city"] == shown


# ---- «دوسية التأسيس» per order --------------------------------------------------------------------------


def test_the_cover_comes_from_the_plan() -> None:
    front, back = cover_specs(plan_of("kg1"), 2, "qamra.app")
    assert front.params["code"] == "KG1" and front.params["volume"] == "الجُزْءُ الثّاني"
    assert front.params["level"] == "المستوى الأول" and front.params["ages"] == "4–5"
    assert front.params["subjects"] == ["pen", "arabic", "math", "english", "thinking"]
    assert back.type == "workbook-cover-back" and back.params["domain"] == "qamra.app"
    assert front.params["part"] == "kg1-v2" and front.params["pages"] == 116  # the cover's scene and badges
    child = Child("لؤي", "m")
    pages = build_pages(BookSpec("foundation", "دوسية", child, (front, back), dt.date.today()), ASSETS)
    cover, back_cover = pages[0].built.data["cv"], pages[1].built.data["cv"]
    assert pages[0].built.data["kicker"] == "دوسية لؤي" and cover["ribbon"]["text"] == "دوسية لؤي"
    pills = [p["text"] for p in cover["pills"]]
    assert pills == ["KG1 · المستوى الأول", "الجزء الثاني"]  # plain, like the level
    assert [b["text"] for b in cover["badges"]][::2] == ["١١٦ صفحة ملوّنة", "باسم لؤي وشخصيته"]
    assert len(back_cover["inside"]) == 6 and back_cover["made_for"] == "صُنعت خصيصًا لـلؤي"
    with pytest.raises(ValueError):
        plan_of("kg3")


def test_the_black_and_white_interior_is_refused_before_anything_is_drawn(tmp_path: Path) -> None:
    with pytest.raises(VariantNotBuilt):
        asyncio.run(render_order(Child("ليان", "f"), "kg2", 1, tmp_path, interior="bw"))
    assert not any(tmp_path.iterdir())
