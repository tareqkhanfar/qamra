"""Odd one out: rows of pictures where exactly one differs.

Rules: `same` (one picture repeated, one different picture) and `category` (pictures of one category,
one from another). Check: exactly one item breaks the row's rule, and it is the one in the answer key.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.puzzles.base import rng

Rule = Literal["same", "category"]

# pairs that are easy to tell apart at a glance (different category, shape and main color)
SAME_POOL = (
    ("apple", "car"),
    ("duck", "ball"),
    ("star", "fish"),
    ("flower", "cup"),
    ("cat", "umbrella"),
    ("sun", "leaf"),
    ("heart", "boat"),
)
CATEGORY_POOL = {
    "fruit": ("apple", "banana", "strawberry"),
    "animal": ("cat", "dog", "cow", "sheep", "lion", "rabbit", "duck"),
    "vehicle": ("car", "boat"),
}


@dataclass(frozen=True)
class OddRow:
    items: tuple[str, ...]
    odd: int
    rule: Rule
    example: bool = False

    def key(self, item: str) -> str:
        return item if self.rule == "same" else picture(item).category

    def problems(self) -> list[str]:
        keys = Counter(self.key(i) for i in self.items)
        singles = [k for k, n in keys.items() if n == 1]
        out = []
        if not 4 <= len(self.items) <= 5:
            out.append(f"a row has 4–5 pictures, not {len(self.items)}")
        if len(keys) != 2 or len(singles) != 1:
            out.append(f"exactly one picture must differ ({dict(keys)})")
        elif self.key(self.items[self.odd]) != singles[0]:
            out.append("the answer key points at the wrong picture")
        return out

    @property
    def answer(self) -> str:
        return strip_tashkeel(picture(self.items[self.odd]).word_ar)


def generate_odd_rows(seed: int | str, rules: list[Rule], sizes: list[int]) -> list[OddRow]:
    """One row per rule; the first row is the solved example."""
    r = rng(seed, "odd")
    pairs = list(SAME_POOL)
    r.shuffle(pairs)
    rows = []
    for i, (rule, size) in enumerate(zip(rules, sizes, strict=True)):
        if rule == "same":
            majority, odd_pic = pairs[i % len(pairs)]
            items = [majority] * (size - 1)
        else:
            groups = list(CATEGORY_POOL)
            major = r.choice([g for g in groups if len(CATEGORY_POOL[g]) >= size - 1])
            items = r.sample(list(CATEGORY_POOL[major]), size - 1)
            odd_pic = r.choice([p for g in groups if g != major for p in CATEGORY_POOL[g]])
        position = r.randrange(1 if i == 0 else 0, size)  # the example never starts with its answer
        items.insert(position, odd_pic)
        rows.append(OddRow(tuple(items), position, rule, example=i == 0))
    return rows
