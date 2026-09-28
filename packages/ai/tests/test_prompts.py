import pytest
from jinja2 import UndefinedError

from qamra_ai import prompts


def test_missing_variable_fails_loudly() -> None:
    with pytest.raises(UndefinedError):
        prompts.render("character_sheet", n_photos=1)


def test_no_glued_lines() -> None:
    text = prompts.render(
        "story_adapt_user",
        child={"name": "س", "gender": "f", "age": 5, "interests": []},
        companion={"name": "ب", "type_label": "x", "traits": None},
        theme_title="T",
        pages_json="[]",
    )
    assert "\nTheme: T\n" in text


def test_vowelization_rule_by_age() -> None:
    base = dict(
        brand_name_en="Qamra",
        brand_name_ar="قمرة",
        n_pages=12,
        lang="ar",
        gender="m",
        max_chars=180,
        companion=None,
    )
    assert "FULL تشكيل" in prompts.render("story_adapt", age=5, vowelize=True, **base)
    assert "FULL تشكيل" not in prompts.render("story_adapt", age=9, vowelize=False, **base)
    assert "masculine" in prompts.render("story_adapt", age=5, vowelize=True, **base)
