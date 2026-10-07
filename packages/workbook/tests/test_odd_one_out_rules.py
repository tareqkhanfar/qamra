"""Odd one out says its rule (the owner's review of 7 October 2026: «based on what is it different?»): every
row in «دوسية التأسيس», on the exercise pages and in the review and assessment panels, is either seen (three
alike and one not) or names its group (a chip on the row, a question under the panel), and in a named group
the odd picture is the only one outside it. KG1's first volume only shows differences that are seen."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from qamra_workbook import puzzles
from qamra_workbook.curriculum import load
from qamra_workbook.pictures import PICTURES, LibraryStore
from qamra_workbook.puzzles.odd import BASIC_GROUPS, GROUPS, MAIN_COLOR, OddRow, Rule, generate_odd_rows
from qamra_workbook.render.engine import build_pages
from qamra_workbook.render.foundation import volume_book
from qamra_workbook.render.pages import thinking, workbook_kg1  # noqa: F401  (registers the builders)
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import Child

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
VOLUMES = [(level, n) for level in ("kg1", "kg2") for n in (1, 2, 3)]


def assert_clear(row: OddRow) -> None:
    others = [item for k, item in enumerate(row.items) if k != row.odd]
    odd = row.items[row.odd]
    assert row.problems() == [], row
    if row.rule == "same":
        assert len(set(others)) == 1 and odd not in others and not row.hint, row
    else:
        group = GROUPS[row.group]
        assert row.hint and row.question, row
        assert all(item in group.members for item in others), row
        assert odd not in group.members and odd in group.outside, row


def test_every_group_is_drawn_and_has_room_for_its_rows() -> None:
    for name, group in GROUPS.items():
        assert set(group.members) | set(group.outside) <= set(PICTURES), name
        assert not set(group.members) & set(group.outside), name
        assert len({MAIN_COLOR[m] for m in group.members}) >= 4, name  # a row of five still has a colour each
        assert "ْ" in group.hint or "ُ" in group.hint or "َ" in group.hint, name  # vowelized
    assert set(BASIC_GROUPS) <= set(GROUPS)


@pytest.mark.parametrize("seed", range(60))
def test_generated_rows_are_seen_or_name_their_group(seed: int) -> None:
    rows = generate_odd_rows(seed, ["same", "same", "category", "category"], [4, 4, 4, 5])
    for row in rows:
        assert_clear(row)
    named = [row.group for row in rows if row.rule == "category"]
    assert len(set(named)) == len(named)  # one group per row on a page
    shown = [item for row in rows for item in set(row.items)]
    assert len(shown) == len(set(shown))  # no picture in two rows of a page
    basic = generate_odd_rows(seed, ["same", "category", "category"], [4, 4, 4], BASIC_GROUPS)
    assert all(row.group in BASIC_GROUPS for row in basic if row.rule == "category")


def recorded(level: str, number: int, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, OddRow]]:
    """Every odd-one-out row a volume draws, with its page id."""
    seen: list[tuple[str, OddRow]] = []
    page_id = [""]

    def spy(
        seed: int | str, rules: list[Rule], sizes: list[int], groups: tuple[str, ...] | None = None
    ) -> list[OddRow]:
        rows = generate_odd_rows(seed, rules, sizes, groups)
        seen.extend((page_id[0], row) for row in rows)
        return rows

    monkeypatch.setattr(puzzles, "generate_odd_rows", spy)
    monkeypatch.setattr(thinking, "generate_odd_rows", spy)
    plan = load(ROOT / f"content/workbook/curriculum/{level}.yaml")
    child = Child("ليان", "f")
    for page in volume_book(plan, number, child, name_en="Layan").pages:
        page_id[0] = page.id
        one = range(page.number, page.number + 1)
        build_pages(volume_book(plan, number, child, name_en="Layan", pages=one), ASSETS)
    return iter(seen)


@pytest.mark.parametrize(("level", "number"), VOLUMES)
def test_every_odd_one_out_row_in_the_workbooks_is_seen_or_names_its_group(
    level: str, number: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = list(recorded(level, number, monkeypatch))
    assert rows, f"{level} v{number} has no odd-one-out rows"
    for page, row in rows:
        try:
            assert_clear(row)
        except AssertionError as e:
            raise AssertionError(f"{page}: {e}") from e
        if row.rule == "category" and level == "kg1":
            assert row.group in BASIC_GROUPS, page
    if (level, number) == ("kg1", 1):  # KG1's first volume: differences that are seen
        assert all(row.rule == "same" for _, row in rows)
