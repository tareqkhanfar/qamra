"""«أُلَوِّنُ فِلَسْطينَ»: the page list (content/coloring/palestine.yaml) and its 25 code-drawn scenes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from qamra_workbook.coloring.checks import line_problems
from qamra_workbook.coloring.scenes import SCENES, framed, get
from qamra_workbook.coloring.titles import title_of

BOOK = Path(__file__).resolve().parents[3] / "content/coloring/palestine.yaml"
TASHKEEL = re.compile("[ً-ْ]")
BARE = {"يافا"}  # every letter is long or followed by a long letter: nothing to mark


def _pages() -> list[dict[str, Any]]:
    data: dict[str, Any] = yaml.safe_load(BOOK.read_text(encoding="utf-8"))
    assert data["title_ar"] == "أُلَوِّنُ فِلَسْطينَ" and data["title_en"] == "I Color Palestine"
    pages: list[dict[str, Any]] = data["pages"]
    return pages


PAGES = _pages()
IDS = [str(p["id"]) for p in PAGES]


def test_the_book_has_25_unique_pages_each_with_a_drawn_scene() -> None:
    assert len(PAGES) == 25
    assert len(set(IDS)) == len(IDS)
    drawn = {s.id for s in SCENES.values() if s.book == "palestine"}
    assert drawn == set(IDS)  # every page has a scene and every scene is in the book
    for page in PAGES:
        assert get("palestine", page["id"]).source == "code"
    # the title page, 25 scenes, the free drawing page and «عن قمرة» fill the stapled book exactly
    assert 1 + len(PAGES) + 2 == title_of("palestine").pages


@pytest.mark.parametrize("page", PAGES, ids=IDS)
def test_captions_are_short_vowelized_titles(page: dict[str, Any]) -> None:
    ar, en = str(page["caption_ar"]), str(page["caption_en"])
    assert 2 <= len(ar.split()) <= 4, ar
    for word in ar.split():
        # «في» and «يافا» need no mark in the house style (no short vowel before a long letter)
        if len(word) > 2 and word not in BARE:
            assert TASHKEEL.search(word), word
    assert en and en[0].isupper() and not en.endswith(".")
    assert str(page["scene"]).strip()


@pytest.mark.parametrize("scene_id", IDS)
def test_each_scene_is_clean_line_art(scene_id: str) -> None:
    sc = get("palestine", scene_id)
    line = framed(sc, "line")
    assert line_problems(line) == []
    assert "<text" not in line  # no writing inside a drawing
    color = framed(sc, "color")
    assert line_problems(color)  # the colour version (cover, web) really is in colour
