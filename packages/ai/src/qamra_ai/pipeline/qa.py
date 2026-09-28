"""Automatic page QA (Addendum 3 §2.3): Haiku vision scores → pass / redraw / flag for a human.

A page passes when its weighted score reaches the threshold (admin setting, default 0.75) and nothing
hard-fails. Hard fails: unsafe, text in the image, broken anatomy, the hero missing or duplicated, or
a clear likeness miss. Only failing pages are redrawn (max 2 automatic redraws), then flagged.
"""

from dataclasses import dataclass

from qamra_ai.pipeline.models import PageQA

WEIGHTS = {
    "likeness": 0.45,
    "outfit": 0.15,
    "text_space": 0.15,
    "count": 0.10,
    "companion": 0.10,
    "style": 0.05,
}
LIKENESS_FLAG = 7  # below this the review UI shows a "face" flag
LIKENESS_HARD_FAIL = 4  # "could be a sibling" or worse is never good enough


@dataclass(frozen=True)
class QAResult:
    score: float  # 0..1
    passed: bool
    flags: tuple[str, ...]  # machine flags for the review UI


def evaluate(qa: PageQA, *, expect_hero: bool, expect_companion: bool, threshold: float) -> QAResult:
    likeness = max(0, min(10, qa.likeness)) / 10
    parts = {
        "likeness": likeness if expect_hero else None,
        "outfit": float(qa.outfit_ok) if expect_hero else None,
        "text_space": float(qa.text_space_ok),
        "count": float(qa.people_count_ok),
        "companion": float(qa.companion_ok) if expect_companion else None,
        "style": float(qa.style_ok),
    }
    used = {k: v for k, v in parts.items() if v is not None}
    total_weight = sum(WEIGHTS[k] for k in used)
    score = round(sum(WEIGHTS[k] * v for k, v in used.items()) / total_weight, 3)

    flags: list[str] = []
    hard: list[str] = []
    if not qa.safe:
        hard.append("unsafe")
    if qa.text_in_image:
        hard.append("text_in_image")
    if not qa.anatomy_ok:
        hard.append("anatomy")
    expected_heroes = 1 if expect_hero else 0
    if qa.hero_count != expected_heroes:
        hard.append("hero_count")
    if expect_hero and qa.likeness < LIKENESS_HARD_FAIL:
        hard.append("face")
    elif expect_hero and qa.likeness < LIKENESS_FLAG:
        flags.append("face")
    if not qa.people_count_ok:
        flags.append("count")
    if expect_hero and not qa.outfit_ok:
        flags.append("outfit")
    if not qa.text_space_ok:
        flags.append("text_space")
    if expect_companion and not qa.companion_ok:
        flags.append("companion")
    if not qa.style_ok:
        flags.append("style")
    passed = not hard and score >= threshold
    return QAResult(score=score, passed=passed, flags=tuple(dict.fromkeys(hard + flags)))
