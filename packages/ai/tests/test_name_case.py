"""«يا أبا بكر», «إلى أبي بكر», never «يا أبو بكر»: the story themes, the Classic texts, the AI-written text
and the prompts.

A theme text fills the child's name through `qamra_pdf.arabic_names`: the accusative after «يا» and at
`{name:acc}`, the genitive at `{name:gen}`, as typed elsewhere. The Classic vowelization never sees the marks
(its cache key stays), and the model's text gets its vocatives and genitives fixed on the child's own name.
A tashkeel fix in a theme text is made in the cached vowelization too, which is re-keyed: no new paid call.
"""

import pytest

from qamra_ai import prompts
from qamra_ai.pipeline.classic import classic_story
from qamra_ai.pipeline.models import Child, StoryOut, StoryPageOut
from qamra_ai.pipeline.story import fix_name_case
from qamra_ai.pipeline.theme import Theme, fill_title, load_theme, render_template
from qamra_ai.pipeline.translate import translation_source
from qamra_ai.pipeline.vowelize import (
    CORRECTIONS,
    DEDICATION_AR,
    VowelizedTexts,
    corrected_cache,
    corrected_definition,
    fill,
    same_words,
    source_hash,
    sources,
)
from qamra_pdf.arabic_names import unmark

ABU_BAKR = Child(name="أبو بكر", gender="m", age=5)
SALMA = Child(name="سلمى", gender="f", age=5)


def _page(theme: Theme, needle: str) -> int:
    return next(i for i, p in enumerate(theme.pages) if needle in p.text_ar)


def _unmarked(theme: Theme) -> Theme:
    pages = [p.model_copy(update={"text_ar": unmark(p.text_ar, ("name", "companion"))}) for p in theme.pages]
    return theme.model_copy(update={"pages": pages})


@pytest.mark.parametrize(
    ("slug", "needle", "boy", "girl"),
    [
        ("new-sibling", "وَضَمَّتْ", "وَضَمَّتْ أبا بكر طَوِيلًا", "وَضَمَّتْ سلمى طَوِيلًا"),
        ("first-day", "اسْتَقْبَلَتِ", "اسْتَقْبَلَتِ الْمُعَلِّمَةُ أبا بكر", "اسْتَقْبَلَتِ الْمُعَلِّمَةُ سلمى"),
        ("first-day", "اسْتَقْبَلَتِ", "«أَهْلًا بِكَ يَا أبا بكر،", "«أَهْلًا بِكِ يَا سلمى،"),
        ("graduation", "نَادَتِ", "نَادَتِ الْمُعَلِّمَةُ: «أبا بكر!» فَمَشَى أبو بكر", "«سلمى!» فَمَشَتْ سلمى"),
    ],
)
def test_the_theme_texts_put_the_name_in_its_case(slug: str, needle: str, boy: str, girl: str) -> None:
    theme = load_theme(slug)
    page = theme.pages[_page(theme, needle)]
    assert boy in theme.base_text(page, "ar", "m", ABU_BAKR.name, "قمّور")
    assert girl in theme.base_text(page, "ar", "f", SALMA.name, "قمّور")
    assert "أبو بكر" not in theme.base_text(page, "ar", "m", ABU_BAKR.name, "قمّور").split("فَمَشَى")[0]


def test_a_subject_and_a_title_keep_the_name_as_typed() -> None:
    theme = load_theme("new-sibling")
    first = theme.base_text(theme.pages[0], "ar", "m", ABU_BAKR.name, "قمّور")
    assert "فَرِحَ أبو بكر" in first and "أبا" not in first
    assert theme.title("ar", "m", ABU_BAKR.name) == "أبو بكر وضيفنا الصغير"
    assert fill_title(theme.title_ar, ABU_BAKR.name, None) == "أبو بكر وضيفنا الصغير"
    assert render_template("يا {companion}، {name:acc}", "m", "سلمى", "أبو شنب") == "يا أبا شنب، سلمى"


@pytest.mark.parametrize("slug", ["first-day", "graduation", "new-sibling", "custom"])
@pytest.mark.parametrize("gender", ["m", "f"])
def test_the_case_marks_never_change_the_vowelized_source(slug: str, gender: str) -> None:
    """A mark is not part of what the model vowelizes, so the cached texts stay valid (no new paid call)."""
    theme = load_theme(slug)
    marked = sources(theme, gender)  # type: ignore[arg-type]
    assert ":acc" not in marked.model_dump_json() and ":gen" not in marked.model_dump_json()
    assert source_hash(marked) == source_hash(sources(_unmarked(theme), gender))  # type: ignore[arg-type]
    assert ":acc" not in str(translation_source(theme))  # English names do not change
    assert ":gen" not in str(translation_source(theme))


@pytest.mark.parametrize(("slug", "needle"), [("new-sibling", "وَضَمَّتْ"), ("first-day", "اسْتَقْبَلَتِ")])
def test_a_classic_book_fills_the_vowelized_text_in_the_templates_case(slug: str, needle: str) -> None:
    theme = load_theme(slug)
    texts = VowelizedTexts(**sources(theme, "m").model_dump())  # the cached words: no marks in them
    index = theme.pages[_page(theme, needle)].index
    story = classic_story(theme, ABU_BAKR, "ar", "قمّور", texts)
    text = next(p.text for p in story.pages if p.index == index)
    assert text == theme.base_text(theme.pages[_page(theme, needle)], "ar", "m", ABU_BAKR.name, "قمّور")
    assert "أبا بكر" in text and "يا أبو" not in text and "يَا أبو" not in text
    girl = classic_story(theme, SALMA, "ar", "قمّور", VowelizedTexts(**sources(theme, "f").model_dump()))
    assert "أبا" not in " ".join(p.text for p in girl.pages)
    assert fill("يَا {name}", "أبو بكر", "") == "يَا أبا بكر"  # no template needed after «يا»


def test_the_models_vocatives_are_fixed_on_the_childs_name() -> None:
    story = StoryOut(
        title="أَبُو بَكْرٍ فِي الرَّوْضَةِ",
        dedication="إِلَى أَبِي بَكْرٍ، نَجْمِنَا",
        pages=[
            StoryPageOut(index=1, text="قَالَتِ الْمُعَلِّمَةُ: «أَهْلًا يَا أَبُو بَكْرٍ!»"),
            StoryPageOut(index=2, text="رَكَضَ أَبُو بَكْرٍ. يا أبو علي!"),
        ],
        parents_lesson="",
        parents_questions=["اسألوا: يا أبو بكر، ماذا تعلّمت؟", "ماذا رسم أبو بكر؟"],
        blurb="حكاية أبو بكر",
    )
    fixed = fix_name_case(story, "أبو بكر")
    assert fixed.pages[0].text == "قَالَتِ الْمُعَلِّمَةُ: «أَهْلًا يَا أَبَا بَكْرٍ!»"
    assert fixed.pages[1].text == story.pages[1].text  # a subject, and another name: untouched
    assert fixed.parents_questions == ["اسألوا: يا أبا بكر، ماذا تعلّمت؟", "ماذا رسم أبو بكر؟"]
    assert (fixed.title, fixed.dedication, fixed.blurb) == (story.title, story.dedication, story.blurb)
    assert fix_name_case(story, "سلمى") is story  # nothing to fix for a name without «أبو»


@pytest.mark.parametrize("name", ["story_adapt", "story_custom"])
def test_the_story_prompts_ask_for_the_five_nouns(name: str) -> None:
    version = 3 if name == "story_adapt" else 2  # the versions that ship (story.py, custom_story.py)
    extra = {"theme_bible": ""} if name == "story_adapt" else {}
    brand = {"brand_name_en": "Qamra", "brand_name_ar": "قمرة"}
    text = prompts.render(name, version=version, lang="ar", **brand, **extra)
    assert "«أبا» after «يا»" in text and "Never write «يا أبو»" in text
    assert "أبا" not in prompts.render(name, version=version, lang="en", **brand, **extra)


# ---- the genitive ----------------------------------------------------------------------------------------

ABU_SHANAB = "أبو شنب"  # a companion named by the child


@pytest.mark.parametrize(
    ("slug", "needle", "boy", "girl"),
    [
        ("new-sibling", "نَظَرَ الضَّيْفُ", "إِلَى أبي بكر…", "إِلَى سلمى…"),
        ("first-day", "غَدًا نَعُودُ", "هَمَسَ أبو بكر لِأبي شنب:", "هَمَسَتْ سلمى لِأبي شنب:"),
        ("graduation", "الصَّفُّ الْأَوَّلُ", "هَمَسَ أبو بكر لِأبي شنب:", "هَمَسَتْ سلمى لِأبي شنب:"),
        ("graduation", "وَعَلَى أَنْفِ", "وَعَلَى أَنْفِ أبي شنب نُقْطَةُ", "وَعَلَى أَنْفِ أبي شنب نُقْطَةُ"),
    ],
)
def test_the_theme_texts_put_a_genitive_name_in_its_case(slug: str, needle: str, boy: str, girl: str) -> None:
    theme = load_theme(slug)
    page = theme.pages[_page(theme, needle)]
    assert boy in theme.base_text(page, "ar", "m", ABU_BAKR.name, ABU_SHANAB)
    assert girl in theme.base_text(page, "ar", "f", SALMA.name, ABU_SHANAB)
    plain = theme.base_text(page, "ar", "f", SALMA.name, "قمّور")  # no «أبو»: as before the marks
    assert plain == render_template(unmark(page.text_ar, ("name", "companion")), "f", SALMA.name, "قمّور")


def test_titles_and_blurbs_take_the_genitive() -> None:
    graduation, custom = load_theme("graduation"), load_theme("custom")
    assert graduation.title("ar", "m", ABU_BAKR.name) == "يوم تخرّج أبي بكر"
    assert fill_title(graduation.title_ar, ABU_BAKR.name, None) == "يوم تخرّج أبي بكر"
    assert graduation.title("ar", "f", SALMA.name) == "يوم تخرّج سلمى"
    assert fill_title(custom.title_ar, "ذو الفقار", "m") == "حكاية ذي الفقار الخاصة"
    blurb = render_template(custom.blurb_ar or "", "m", ABU_BAKR.name, "")
    assert blurb.startswith("حكايةٌ كُتبت لأبي بكر وحدَه")  # «لـ» + an alif: the لا ligature
    assert render_template(custom.blurb_ar or "", "f", SALMA.name, "").startswith("حكايةٌ كُتبت لـسلمى وحدَها")
    for slug, words in [("first-day", "حكاية أبي بكر في أوّل يوم"), ("new-sibling", "حكاية أبي بكر الأخِ")]:
        theme = load_theme(slug)
        assert words in render_template(theme.blurb_ar or "", "m", ABU_BAKR.name, "")


@pytest.mark.parametrize("slug", ["first-day", "graduation", "new-sibling"])
def test_a_classic_book_from_the_cache_prints_every_case(slug: str) -> None:
    """The cached words have no marks; the fill gives the dedication, title, pages and parents' page their
    case from the theme's templates, exactly as the uncached book prints them."""
    theme = load_theme(slug)
    texts = VowelizedTexts(**sources(theme, "m").model_dump())
    cached = classic_story(theme, ABU_BAKR, "ar", ABU_SHANAB, texts)
    direct = classic_story(theme, ABU_BAKR, "ar", ABU_SHANAB)
    assert cached.model_dump() == direct.model_dump()
    assert cached.dedication.startswith("إلى أبي بكر، نجمِنا الصغير")
    every = " ".join([cached.title, cached.blurb, cached.parents_lesson, *[p.text for p in cached.pages]])
    for wrong in ("يا أبو", "يَا أبو", "إِلَى أبو", "لِـأبو", "لِـأبي", "لِأبو", "أَنْفِ أبو", "تخرّج أبو"):
        assert wrong not in every
    girl = classic_story(theme, SALMA, "ar", "قمّور", VowelizedTexts(**sources(theme, "f").model_dump()))
    assert girl.dedication.startswith("إلى سلمى،")
    assert "أبي" not in " ".join(p.text for p in girl.pages) and "أبا" not in girl.title


def test_the_dedication_template_keeps_its_cache_key() -> None:
    assert "{name:gen}" in DEDICATION_AR
    assert sources(load_theme("first-day"), "m").dedication.startswith("إلى {name}،")


def test_the_models_genitives_are_fixed_on_the_childs_name() -> None:
    story = StoryOut(
        title="هَدِيَّةٌ لِأَبُو بَكْرٍ",
        dedication="إِلَى أَبُو بَكْرٍ، نَجْمِنَا",
        pages=[
            StoryPageOut(index=1, text="ذَهَبَتْ مَامَا مَعَ أَبُو بَكْرٍ إِلَى الرَّوْضَةِ."),
            StoryPageOut(index=2, text="رَكَضَ أَبُو بَكْرٍ. مع أبو علي! لـأبو بكر"),
        ],
        parents_lesson="اقرؤوا لأبو بكر كل مساء.",
        parents_questions=["ماذا قالت المعلمة عن أبو بكر؟"],
        blurb="حكاية أبو بكر",
    )
    fixed = fix_name_case(story, "أبو بكر")
    assert fixed.title == "هَدِيَّةٌ لِأَبِي بَكْرٍ"
    assert fixed.dedication == "إِلَى أَبِي بَكْرٍ، نَجْمِنَا"
    assert fixed.pages[0].text == "ذَهَبَتْ مَامَا مَعَ أَبِي بَكْرٍ إِلَى الرَّوْضَةِ."
    assert fixed.pages[1].text == "رَكَضَ أَبُو بَكْرٍ. مع أبو علي! لأبي بكر"  # the subject, another name
    assert fixed.parents_lesson == "اقرؤوا لأبي بكر كل مساء."
    assert fixed.parents_questions == ["ماذا قالت المعلمة عن أبي بكر؟"]
    assert fixed.blurb == "حكاية أبو بكر"  # an iḍāfa is the model's (the prompt asks for it)
    assert fix_name_case(story, "سلمى") is story


@pytest.mark.parametrize("name", ["story_adapt", "story_custom"])
def test_the_story_prompts_ask_for_the_genitive(name: str) -> None:
    version = 3 if name == "story_adapt" else 2  # the versions that ship (story.py, custom_story.py)
    extra = {"theme_bible": ""} if name == "story_adapt" else {}
    brand = {"brand_name_en": "Qamra", "brand_name_ar": "قمرة"}
    text = prompts.render(name, version=version, lang="ar", **brand, **extra)
    assert "«أبي» in the genitive" in text and "لِأَبِي بَكْرٍ" in text and "«لأبو»" in text


# ---- tashkeel fixes keep the vowelization cache -----------------------------------------------------------

SLIPS = {  # the theme text before the fix of 2026-10-09 → after
    "graduation": ("{وَرَفَعَ/وَرَفَعَتْ} الشَّهَادَةَ", "{وَرَفَعَ/وَرَفَعَتِ} الشَّهَادَةَ"),
    "new-sibling": ("{وَأَرَى/وَأَرَتْ} الضَّيْفَ", "{وَأَرَى/وَأَرَتِ} الضَّيْفَ"),
}


def _before_fix(slug: str) -> dict[str, object]:
    """The theme's definition as a template pinned it before the fix (the file's words with the slip)."""
    theme = load_theme(slug).model_dump(mode="json")
    before, after = SLIPS[slug]
    for page in theme["pages"]:
        page["text_ar"] = page["text_ar"].replace(after, before)
    return theme


@pytest.mark.parametrize("slug", sorted(SLIPS))
def test_the_theme_files_carry_the_fix(slug: str) -> None:
    theme = load_theme(slug).model_dump(mode="json")
    before, after = SLIPS[slug]
    texts = [p["text_ar"] for p in theme["pages"]]
    assert any(after in t for t in texts) and not any(before in t for t in texts)
    assert corrected_definition(theme) == theme  # nothing left to correct
    assert {c.theme for c in CORRECTIONS} == set(SLIPS)


@pytest.mark.parametrize("slug", sorted(SLIPS))
@pytest.mark.parametrize("gender", ["m", "f"])
def test_a_cached_vowelization_is_corrected_and_still_matches(slug: str, gender: str) -> None:
    """A template pinned the old words and vowelized them (the model kept or dropped marks as it liked): the
    deploy fix gives it the corrected words and a cache keyed to them, so the book prints the fix and the
    worker finds the cache fresh (`ensure_texts` makes no call)."""
    old = _before_fix(slug)
    old_source = sources(Theme.model_validate(old), gender)  # type: ignore[arg-type]
    model = old_source.model_copy(deep=True)  # the cached answer: the model's vowelization of the old words
    cache = {"hash": source_hash(old_source), "gender": gender, "texts": model.model_dump(), "kept": []}

    done = corrected_cache(old, cache, gender)  # type: ignore[arg-type]
    assert done is not None
    definition, fixed = done
    current = load_theme(slug)
    assert definition == current.model_dump(mode="json")  # the pinned words are the file's words now
    assert fixed["hash"] == source_hash(sources(current, gender))  # type: ignore[arg-type]
    assert fixed["hash"] == source_hash(sources(Theme.model_validate(definition), gender))  # type: ignore[arg-type]
    printed = " ".join(p["text"] for p in fixed["texts"]["pages"])
    word = {"graduation": "وَرَفَعَتِ الشَّهَادَةَ", "new-sibling": "وَأَرَتِ الضَّيْفَ"}[slug]
    assert (word in printed) == (gender == "f")
    assert "تْ الشَّهَادَةَ" not in printed and "تْ الضَّيْفَ" not in printed
    assert fixed["corrected"][-1]["fixes"] and fixed["gender"] == gender  # a note; the rest of the cache kept
    assert corrected_cache(definition, fixed, gender) is None  # idempotent: the next deploy changes nothing
    new_source = sources(current, gender)  # type: ignore[arg-type]
    for src, new in zip(new_source.pages, VowelizedTexts.model_validate(fixed["texts"]).pages, strict=True):
        assert same_words(src.text, new.text)


def test_the_fix_reaches_a_cache_the_model_vowelized_differently() -> None:
    """The model may have written «وَرَفَعَتْ» or «وَرَفَعَت» (or already «وَرَفَعَتِ»): each becomes «وَرَفَعَتِ»."""
    old = _before_fix("graduation")
    old_source = sources(Theme.model_validate(old), "f")
    for written in ("وَرَفَعَتْ الشَّهَادَةَ", "وَرَفَعَت الشَّهادَةَ", "وَرَفَعَتِ الشَّهَادَةَ"):
        model = old_source.model_copy(deep=True)
        for page in model.pages:
            page.text = page.text.replace("وَرَفَعَتْ الشَّهَادَةَ", written)
        cache = {"hash": source_hash(old_source), "texts": model.model_dump()}
        done = corrected_cache(old, cache, "f")
        assert done is not None
        printed = " ".join(p["text"] for p in done[1]["texts"]["pages"])
        assert "وَرَفَعَتِ الشَّه" in printed and "وَرَفَعَتْ" not in printed


def test_a_stale_or_missing_cache_is_never_made_fresh() -> None:
    old = _before_fix("graduation")
    stale = {"hash": "0000", "texts": {}}
    assert corrected_cache(old, stale, "f") == (load_theme("graduation").model_dump(mode="json"), stale)
    assert corrected_cache(old, {}, "f") == (load_theme("graduation").model_dump(mode="json"), {})
    other = load_theme("first-day").model_dump(mode="json")
    assert corrected_cache(other, {"hash": "x"}, "m") is None  # no fix for this theme


def test_the_story_prompt_shows_the_model_no_case_marks() -> None:
    from qamra_ai.pipeline.story import theme_bible

    for slug in ("graduation", "custom", "first-day", "new-sibling"):
        bible = theme_bible(load_theme(slug), "ar")
        assert ":gen" not in bible and ":acc" not in bible
    assert "Title template: يوم تخرّج {name}" in theme_bible(load_theme("graduation"), "ar")
