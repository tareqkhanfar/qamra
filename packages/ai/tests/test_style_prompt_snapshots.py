"""Golden snapshots of every image prompt each art style assembles (`prompt_snapshot.py`).

A change meant for some styles must leave the others byte-identical: the character portrait and sheet, every
page and cover, the companion and family-member sheets, the Classic placeholder and portrait, the class-book
scenes and the page QA. History of the golden file:
- 0bd49a6: taken before «شبه حقيقي» v3; 8317d79: only semi-realistic changed (v3), every other style
  byte-identical.
- portrait first (2026-10-10, the likeness work), rewritten on purpose:
  - semi-realistic: only the character sheet (v6) and the book pages carrying a portrait; its pages without
    one, QA, companion, family, Classic and class-book prompts are unchanged.
  - 3d, watercolor, cartoon: every group (house style v6 and their guides v3).
  - coloring, crayon, papercut: every group but the Classic portrait (house style v6).
  - new groups everywhere: the character portrait and the portrait-first sheet.
- 2026-10-16 (the Classic violet patches): only the Classic portrait, in every style
  (`classic_portrait.v2`: the style's medium line instead of its whole guide); the rest byte-identical.
- 2026-10-19 (the colour and likeness-notes work), rewritten on purpose:
  - every style: only the character portrait (v3) and sheet (v7) groups, plus new groups with likeness notes;
    pages, QA, companion, family, Classic and class-book prompts byte-identical;
  - watercolor: every group (guide v4: white paper, clean washes, no amber cast)."""

import json

import pytest
from prompt_snapshot import GOLDEN, STYLES, snapshot, snapshot_styles

GOLDEN_DATA: dict[str, dict[str, str]] = json.loads(GOLDEN.read_text(encoding="utf-8"))
STYLES_NOW = snapshot_styles()


def _changed(key: str) -> list[str]:
    before, now = GOLDEN_DATA[key], snapshot(STYLES_NOW[key])
    return sorted(k for k in before.keys() | now.keys() if before.get(k) != now.get(k))


@pytest.mark.parametrize("key", STYLES)
def test_every_style_sends_exactly_its_golden_prompts(key: str) -> None:
    assert _changed(key) == []


def test_the_golden_file_covers_every_style_and_the_portrait_first_prompts() -> None:
    assert set(GOLDEN_DATA) == set(STYLES)
    for groups in GOLDEN_DATA.values():
        assert {
            "character-portrait:boy",
            "character:boy:portrait-first",
            "character-portrait:boy:notes",
            "character:boy:portrait-first:notes",
        } <= groups.keys()
