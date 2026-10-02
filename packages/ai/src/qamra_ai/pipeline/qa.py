"""Automatic page QA (Addendum 3 §2.3, Addendum 11 §4.5): Haiku vision scores → pass / redraw / flag.

A page passes when its weighted score reaches the threshold (admin setting, default 0.75), nothing
hard-fails and no consistency lock is broken. Only failing pages are redrawn (max 2 automatic redraws,
each told what the last review found), then the best attempt is kept and flagged for a human.

- Hard fails: unsafe, text in the image, broken anatomy, the hero missing or duplicated, a clear
  likeness miss.
- Lock misses (the book's style bible): the hero's outfit is not its scene group's, the hijab is not the
  book's one head covering, the companion does not match its sheet, the hero is cut by the print edge.
  They are redrawn like hard fails but rank above them when the best attempt is chosen.
- Soft flags lower the score only: weak likeness, the people count, a busy text area, someone else cut
  by the edge, the art style.
"""

from dataclasses import dataclass

from qamra_ai.pipeline.models import PageQA

WEIGHTS = {
    "likeness": 0.40,
    "outfit": 0.13,
    "hijab": 0.05,
    "text_space": 0.12,
    "count": 0.08,
    "companion": 0.10,
    "framing": 0.07,
    "style": 0.05,
}
LIKENESS_FLAG = 7  # below this the review UI shows a "face" flag
LIKENESS_HARD_FAIL = 4  # "could be a sibling" or worse is never good enough
HARD_FLAGS = ("unsafe", "text_in_image", "anatomy", "hero_count", "face")
LOCK_FLAGS = ("outfit", "hijab", "companion", "crop")


@dataclass(frozen=True)
class QAResult:
    score: float  # 0..1
    passed: bool
    flags: tuple[str, ...]  # machine flags for the review UI

    @property
    def hard(self) -> int:
        return sum(f in self.flags for f in HARD_FLAGS)

    @property
    def lock_misses(self) -> int:
        return sum(f in self.flags for f in LOCK_FLAGS)


def _is_hero(entry: str) -> bool:
    return entry.strip().lower().removeprefix("the ").startswith("hero")


def evaluate(qa: PageQA, *, expect_hero: bool, expect_companion: bool, threshold: float) -> QAResult:
    likeness = max(0, min(10, qa.likeness)) / 10
    cropped = [c for c in qa.cropped if c.strip()]
    hero_cropped = expect_hero and any(_is_hero(c) for c in cropped)
    others_cropped = any(not _is_hero(c) for c in cropped)
    parts = {
        "likeness": likeness if expect_hero else None,
        "outfit": float(qa.outfit_ok) if expect_hero else None,
        "hijab": float(qa.hijab_ok) if expect_hero else None,
        "text_space": float(qa.text_space_ok),
        "count": float(qa.people_count_ok),
        "companion": float(qa.companion_ok) if expect_companion else None,
        "framing": 0.0 if hero_cropped or others_cropped else 1.0,
        "style": float(qa.style_ok),
    }
    used = {k: v for k, v in parts.items() if v is not None}
    total_weight = sum(WEIGHTS[k] for k in used)
    score = round(sum(WEIGHTS[k] * v for k, v in used.items()) / total_weight, 3)

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

    locks: list[str] = []
    if expect_hero and not qa.outfit_ok:
        locks.append("outfit")
    if expect_hero and not qa.hijab_ok:
        locks.append("hijab")
    if expect_companion and not qa.companion_ok:
        locks.append("companion")
    if hero_cropped:
        locks.append("crop")

    soft: list[str] = []
    if expect_hero and LIKENESS_HARD_FAIL <= qa.likeness < LIKENESS_FLAG:
        soft.append("face")
    if not qa.people_count_ok:
        soft.append("count")
    if not qa.text_space_ok:
        soft.append("text_space")
    if others_cropped:
        soft.append("crop_other")
    if not qa.style_ok:
        soft.append("style")
    passed = not hard and not locks and score >= threshold
    return QAResult(score=score, passed=passed, flags=tuple(dict.fromkeys(hard + locks + soft)))
