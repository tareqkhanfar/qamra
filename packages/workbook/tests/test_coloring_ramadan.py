"""«أُلَوِّنُ رَمَضان»: the page list (content/coloring/ramadan.yaml) and its 21 code-drawn scenes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from qamra_workbook.coloring.checks import line_problems
from qamra_workbook.coloring.scenes import SCENES, framed, get

BOOK = Path(__file__).resolve().parents[3] / "content/coloring/ramadan.yaml"
TASHKEEL = re.compile("[ً-ْ]")


def _pages() -> list[dict[str, Any]]:
    data: dict[str, Any] = yaml.safe_load(BOOK.read_text(encoding="utf-8"))
    assert data["title_ar"] == "أُلَوِّنُ رَمَضانَ" and data["title_en"] == "I Color Ramadan"
    pages: list[dict[str, Any]] = data["pages"]
    return pages


PAGES = _pages()
IDS = [str(p["id"]) for p in PAGES]


def test_the_book_has_21_unique_pages_each_with_a_drawn_scene() -> None:
    assert len(PAGES) == 21
    assert len(set(IDS)) == len(IDS)
    drawn = {s.id for s in SCENES.values() if s.book == "ramadan"}
    assert drawn == set(IDS)  # every page has a scene and every scene is in the book
    for page in PAGES:
        assert get("ramadan", page["id"]).source == "code"


@pytest.mark.parametrize("page", PAGES, ids=IDS)
def test_captions_are_short_vowelized_titles(page: dict[str, Any]) -> None:
    ar, en = str(page["caption_ar"]), str(page["caption_en"])
    assert 2 <= len(ar.split()) <= 4, ar
    for word in ar.split():
        if len(word) > 2:  # «في» needs no mark in the house style (no short vowel before a long letter)
            assert TASHKEEL.search(word), word
    assert en and en[0].isupper() and not en.endswith(".")
    assert str(page["scene"]).strip()


@pytest.mark.parametrize("scene_id", IDS)
def test_each_scene_is_clean_line_art(scene_id: str) -> None:
    sc = get("ramadan", scene_id)
    line = framed(sc, "line")
    assert line_problems(line) == []
    assert "<text" not in line  # no writing inside a drawing
    color = framed(sc, "color")
    assert line_problems(color)  # the colour version (cover, web) really is in colour
