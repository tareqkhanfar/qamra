import re

import pytest

from qamra_ai.pipeline.theme import load_style, load_theme, render_template


def test_gender_variants() -> None:
    t = "{اسْتَيْقَظَ/اسْتَيْقَظَتْ} {name} و{companion} {معكَ/معكِ}"
    assert render_template(t, "m", "سليم", "بوبو") == "اسْتَيْقَظَ سليم وبوبو معكَ"
    assert render_template(t, "f", "سلمى", "بوبو") == "اسْتَيْقَظَتْ سلمى وبوبو معكِ"


@pytest.mark.parametrize("lang", ["ar", "en"])
@pytest.mark.parametrize("gender", ["m", "f"])
def test_first_day_renders_cleanly(lang: str, gender: str) -> None:
    theme = load_theme("first-day")
    assert len(theme.pages) == 12
    for page in theme.pages:
        text = theme.base_text(page, lang, gender, "X", "C")  # type: ignore[arg-type]
        assert not re.search(r"[{}]", text), f"page {page.index}: leftover template syntax: {text}"
        assert "X" in text


def test_theme_declares_companion_role_per_page() -> None:
    theme = load_theme("first-day")
    assert theme.companion_slot and theme.default_companion
    assert theme.cover.companion_action
    assert all(p.companion_action for p in theme.pages)


def test_unknown_style() -> None:
    with pytest.raises(KeyError):
        load_style("superhero-comic")
