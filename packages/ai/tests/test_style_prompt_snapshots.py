"""Golden snapshots of every image prompt each art style assembles (`prompt_snapshot.py`).

A change meant for one style (e.g. «شبه حقيقي») must leave every other style's prompts byte-identical: the
character sheet, every page and cover, the companion and family-member sheets, the Classic placeholder and
portrait, the class-book scenes and the page QA."""

import json

import pytest
from prompt_snapshot import GOLDEN, STYLES, snapshot

from qamra_ai.pipeline.theme import load_style

GOLDEN_DATA: dict[str, dict[str, str]] = json.loads(GOLDEN.read_text(encoding="utf-8"))


def _changed(slug: str, now: dict[str, str]) -> list[str]:
    before = GOLDEN_DATA[slug]
    return sorted(k for k in before.keys() | now.keys() if before.get(k) != now.get(k))


@pytest.mark.parametrize("slug", STYLES)
def test_every_style_sends_exactly_the_prompts_it_sent_before(slug: str) -> None:
    assert _changed(slug, snapshot(load_style(slug))) == []
