"""«دَفْتَري» (My Sketchbook): the page list (content/coloring/sketchbook.yaml) and its code-drawn art."""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from qamra_workbook.coloring.checks import line_problems
from qamra_workbook.coloring.sketch import ART, DATE_LINES, art_svg

BOOK = Path(__file__).resolve().parents[3] / "content/coloring/sketchbook.yaml"
VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")
NAME_SLOT = re.compile(r"\{child(?::acc|:gen)?\}")
TASHKEEL = re.compile("[ً-ْٰ]")
ARABIC_WORD = re.compile("[ء-يً-ْٰ]+")
UNMARKED_OK = {"ماذا", "إلى", "هذا"}  # words whose usual spelling carries no mark
KINDS = {"blank", "prompt", "finish", "date", "favourite"}


def _book() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(BOOK.read_text(encoding="utf-8"))
    return data


PAGES: list[dict[str, Any]] = _book()["pages"]


def _resolve(text: str, gender: str) -> str:
    return VARIANT.sub(lambda m: m.group(1 if gender == "m" else 2), text)


def test_book_titles() -> None:
    book = _book()
    assert book["title_ar"] == "دَفْتَري"
    assert book["title_en"] == "My Sketchbook"


def test_46_pages_with_unique_ids_and_known_kinds() -> None:
    assert len(PAGES) == 46  # + the title page and «عن قمرة» = 48
    ids = [page["id"] for page in PAGES]
    assert len(set(ids)) == len(ids)
    assert {page["kind"] for page in PAGES} <= KINDS


def test_the_mix_of_pages() -> None:
    kinds = [page["kind"] for page in PAGES]
    assert kinds[0] == "date"  # early in the book
    assert kinds.count("date") == 1
    assert kinds.count("favourite") == 1 and kinds.index("favourite") >= len(kinds) - 4
    assert 12 <= kinds.count("blank") <= 16
    assert 5 <= kinds.count("finish") <= 6
    assert kinds.count("prompt") >= 22
    run = 0
    for kind in kinds:
        run = run + 1 if kind == "blank" else 0
        assert run <= 2, "never more than two blank pages in a row"


def test_the_four_seasons_are_separate_prompts() -> None:
    ids = {page["id"] for page in PAGES}
    assert {"winter-rain", "spring-flowers", "summer-sea", "autumn-olives"} <= ids


def test_neighbouring_blank_pages_use_different_frames() -> None:
    for a, b in itertools.pairwise(PAGES):
        if a["kind"] == b["kind"] == "blank":
            assert a["art"] != b["art"]


def test_every_page_has_its_art() -> None:
    for page in PAGES:
        assert page["art"] in ART, page["id"]


@pytest.mark.parametrize("art_id", sorted(ART))
def test_every_art_is_clean_line_art_of_the_right_size(art_id: str) -> None:
    markup = art_svg(art_id, "line")
    assert line_problems(markup) == []
    assert 'width="186mm"' in markup and 'height="238mm"' in markup
    assert art_svg(art_id, "color").startswith("<svg")


def test_prompts_in_both_languages() -> None:
    for page in PAGES:
        if page["kind"] == "blank":
            assert page["prompt_ar"] == "" and page["prompt_en"] == "", page["id"]
        else:
            assert page["prompt_ar"].strip() and page["prompt_en"].strip(), page["id"]


def test_gender_variants_are_well_formed() -> None:
    for page in PAGES:
        text = page["prompt_ar"]
        assert text.count("{") == text.count("}"), page["id"]
        for gender in ("m", "f"):
            resolved = NAME_SLOT.sub("", _resolve(text, gender))
            assert "{" not in resolved and "}" not in resolved and "/" not in resolved, (page["id"], gender)
        for masc, fem in VARIANT.findall(text):
            assert masc.strip() and fem.strip() and masc != fem, page["id"]
        if VARIANT.search(text):
            assert _resolve(text, "m") != _resolve(text, "f")


def test_prompts_are_short_and_vowelized() -> None:
    for page in PAGES:
        for gender in ("m", "f"):
            text = NAME_SLOT.sub("سلمى", _resolve(page["prompt_ar"], gender))
            assert len(text.split()) <= 7, page["id"]
            for word in ARABIC_WORD.findall(text):
                bare = TASHKEEL.sub("", word)
                if len(bare) >= 3 and bare not in UNMARKED_OK and bare != "سلمى":
                    assert TASHKEEL.search(word), f"{page['id']}: «{word}» has no tashkeel"


def test_the_name_appears_sparingly() -> None:
    named = [page["id"] for page in PAGES if NAME_SLOT.search(page["prompt_ar"])]
    assert named == ["my-sketchbook"]
    date = PAGES[0]
    assert "{child}" in date["prompt_en"]


def test_the_date_page_labels_its_writing_lines() -> None:
    date = PAGES[0]
    assert len(date["lines_ar"]) == len(date["lines_en"]) == len(DATE_LINES)
    for x0, x1, y in DATE_LINES:
        assert 0 < x0 < x1 < 186 and 0 < y < 238
