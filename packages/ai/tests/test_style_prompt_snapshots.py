"""Golden snapshots of every image prompt each art style assembles (`prompt_snapshot.py`).

«شبه حقيقي» v3 (2026-10-10) changes that style only: every other style must send byte-identical prompts (the
character sheet, every page and cover, the companion and family-member sheets, the Classic placeholder and
portrait, the class-book scenes and the page QA). The golden file was first taken before v3 (commit 0bd49a6);
its other-style entries are unchanged since, and the v2 guide kept in `prompts/style/history/` still
reproduces the prompts v2 sent, so a before/after comparison draws the real v2."""

import json
import subprocess  # nosec B404: git show of a fixed path

import pytest
from prompt_snapshot import GOLDEN, STYLES, snapshot, snapshot_styles

SEMI = "semi-realistic"
BEFORE_V3 = "0bd49a6"  # the commit that took the golden file before any v3 change
GOLDEN_DATA: dict[str, dict[str, str]] = json.loads(GOLDEN.read_text(encoding="utf-8"))
STYLES_NOW = snapshot_styles()


def _changed(key: str) -> list[str]:
    before, now = GOLDEN_DATA[key], snapshot(STYLES_NOW[key])
    return sorted(k for k in before.keys() | now.keys() if before.get(k) != now.get(k))


@pytest.mark.parametrize("key", [*STYLES, f"{SEMI}.v2"])
def test_every_style_sends_exactly_its_golden_prompts(key: str) -> None:
    assert _changed(key) == []


def test_only_semi_realistic_changed_since_before_v3() -> None:
    """The golden file as committed before v3: the other styles' entries are the same, and v2 from the
    history file is exactly what `semi-realistic` sent then."""
    try:
        old = subprocess.run(  # nosec B603 B607
            ["git", "show", f"{BEFORE_V3}:packages/ai/tests/fixtures/prompt_snapshots.json"],
            capture_output=True,
            check=True,
            text=True,
            cwd=GOLDEN.parent,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("no git history here (a source export)")
    before: dict[str, dict[str, str]] = json.loads(old)
    for slug in STYLES:
        if slug != SEMI:
            assert GOLDEN_DATA[slug] == before[slug], slug
    # class books name their style by slug, so an earlier guide version has no class-book prompts
    v2_then = {k: v for k, v in before[SEMI].items() if not k.startswith("class:")}
    assert GOLDEN_DATA[f"{SEMI}.v2"] == v2_then
    v3 = GOLDEN_DATA[SEMI]
    assert v3.keys() == before[SEMI].keys()
    assert not [k for k in v3 if v3[k] == before[SEMI][k]]  # every semi-realistic prompt group changed
