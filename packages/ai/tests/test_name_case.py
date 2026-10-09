"""«يا أبا بكر», never «يا أبو بكر»: the story themes, the Classic texts, the AI-written text and the prompts.

A theme text fills the child's name through `qamra_pdf.arabic_names`: the accusative after «يا» and at
`{name:acc}`, as typed elsewhere. The Classic vowelization never sees the marks (its cache key stays), and
the model's text gets its vocatives fixed on the child's own name.
"""

import pytest

from qamra_ai import prompts
from qamra_ai.pipeline.classic import classic_story
from qamra_ai.pipeline.models import Child, StoryOut, StoryPageOut
from qamra_ai.pipeline.story import fix_name_case
from qamra_ai.pipeline.theme import Theme, fill_title, load_theme, render_template
from qamra_ai.pipeline.translate import translation_source
from qamra_ai.pipeline.vowelize import VowelizedTexts, fill, source_hash, sources
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


@pytest.mark.parametrize("slug", ["first-day", "graduation", "new-sibling"])
@pytest.mark.parametrize("gender", ["m", "f"])
def test_the_case_marks_never_change_the_vowelized_source(slug: str, gender: str) -> None:
    """A mark is not part of what the model vowelizes, so the cached texts stay valid (no new paid call)."""
    theme = load_theme(slug)
    marked = sources(theme, gender)  # type: ignore[arg-type]
    assert ":acc" not in marked.model_dump_json()
    assert source_hash(marked) == source_hash(sources(_unmarked(theme), gender))  # type: ignore[arg-type]
    assert ":acc" not in str(translation_source(theme))  # English names do not change


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
    version = 2 if name == "story_adapt" else 1
    extra = {"theme_bible": ""} if name == "story_adapt" else {}
    brand = {"brand_name_en": "Qamra", "brand_name_ar": "قمرة"}
    text = prompts.render(name, version=version, lang="ar", **brand, **extra)
    assert "«أبا» after «يا»" in text and "Never write «يا أبو»" in text
    assert "أبا" not in prompts.render(name, version=version, lang="en", **brand, **extra)
