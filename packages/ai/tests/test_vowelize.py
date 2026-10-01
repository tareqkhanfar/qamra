"""Classic texts vowelized once: sources per gender, the word-for-word check, the cache key, text refresh."""

from typing import Any

import pytest

from qamra_ai.config import Settings
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.classic import classic_story
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_theme
from qamra_ai.pipeline.vowelize import (
    VowelizedTexts,
    checked,
    same_words,
    source_hash,
    sources,
    vowelize,
    with_current_texts,
)


def test_sources_choose_the_gender_and_keep_the_placeholders() -> None:
    theme = load_theme("graduation")
    girl, boy = sources(theme, "f"), sources(theme, "m")
    assert "اسْتَيْقَظَتْ {name}" in girl.pages[0].text and "اسْتَيْقَظَ {name}" in boy.pages[0].text
    assert "{companion}" in girl.pages[0].text and "/" not in girl.pages[0].text
    assert girl.title == "يوم تخرّج {name}" and "نحبُّكِ" in girl.dedication and len(girl.questions) == 2
    assert source_hash(girl) != source_hash(boy) and source_hash(girl) == source_hash(sources(theme, "f"))


def test_only_diacritics_may_change() -> None:
    assert same_words("ذهبَ {name} إلى الروضة.", "ذَهَبَ {name} إِلَى الرَّوْضَةِ.")
    assert not same_words("ذهبَ {name} إلى الروضة.", "ذهبَ {name} إلى المدرسة.")  # a word changed
    assert not same_words("ذهبَ {name} إلى الروضة.", "ذهبَ ليان إلى الروضة.")  # the placeholder filled
    assert not same_words("قال {companion}.", "قال {name}.")


def test_a_changed_page_keeps_its_source() -> None:
    source = sources(load_theme("graduation"), "f")
    answer = source.model_copy(deep=True)
    answer.title = "يَوْمُ تَخَرُّجِ {name}"
    answer.pages[1].text = "نصّ آخر تمامًا"  # the model rewrote a page: never accepted
    result = checked(source, answer)
    assert result.texts.title == "يَوْمُ تَخَرُّجِ {name}"
    assert result.texts.pages[1].text == source.pages[1].text and result.kept == ["page:2"]


async def test_vowelize_with_the_fake_model() -> None:
    settings = Settings(_env_file=None, image_provider="fake", text_provider="fake")  # type: ignore[call-arg]
    rt = Runtime(settings=settings, text=default_fake_text_provider(), image=FakeImageProvider())
    result = await vowelize(rt, load_theme("graduation"), "f", step="vowelize:f")
    assert result.kept == [] and result.texts == sources(load_theme("graduation"), "f")
    assert rt.text.calls[0]["step"] == "vowelize:f"  # type: ignore[attr-defined]


def test_a_book_fills_the_name_into_the_vowelized_words() -> None:
    theme = load_theme("graduation")
    texts = sources(theme, "f")
    texts.pages[0].text = "اِسْتَيْقَظَتْ {name} بَاكِرًا مَعَ {companion}."
    story = classic_story(
        theme, Child(name="ليان", gender="f", age=5), "ar", "قَمّور", VowelizedTexts(**texts.model_dump())
    )
    assert story.pages[0].text == "اِسْتَيْقَظَتْ ليان بَاكِرًا مَعَ قَمّور."
    assert story.title == "يوم تخرّج ليان" and len(story.pages) == len(theme.pages)
    english = classic_story(theme, Child(name="Layan", gender="f", age=5), "en", "Qamour", texts)
    assert english.pages[0].text == theme.base_text(
        theme.pages[0], "en", "f", "Layan", "Qamour"
    )  # as written


@pytest.mark.parametrize("change_pages", [False, True])
def test_theme_text_edits_reach_the_template(change_pages: bool) -> None:
    pinned: dict[str, Any] = {
        "title_ar": "قديم",
        "pages": [
            {"index": 1, "text_ar": "قديم", "scene": "a"},
            {"index": 2, "text_ar": "قديم", "scene": "b"},
        ],
    }
    current: dict[str, Any] = {
        "title_ar": "جديد",
        "pages": [
            {"index": 1, "text_ar": "جديد", "scene": "z"},
            {"index": 2, "text_ar": "جديد", "scene": "z"},
        ],
    }
    if change_pages:
        current["pages"] = current["pages"][:1]  # the story itself changed: the template must be redrawn
    out = with_current_texts(pinned, current)
    if change_pages:
        assert out == pinned
    else:
        assert out["title_ar"] == "جديد" and [p["text_ar"] for p in out["pages"]] == ["جديد", "جديد"]
        assert [p["scene"] for p in out["pages"]] == ["a", "b"]  # the art's scenes stay
