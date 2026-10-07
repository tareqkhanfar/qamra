"""Odd one out: rows of pictures where exactly one differs.

Rules (the owner's review of 7 October 2026: «based on what is it different?»):
- `same`: one picture repeated, one different picture. The difference is seen, nothing to know.
- `category`: three (or four) pictures of one named group and one from outside it. The group is printed with
  the row (`hint`, a chip such as «فَواكِهُ») and the review panels ask its question (`question`, such as
  «أَيُّها لَيْسَ فاكِهَةً؟»), so the child is never left guessing the rule.

A category row has one and only one defensible answer: the group's members are hand-picked (`Group.members`),
the odd picture comes from the group's own list of things that are clearly outside it (`Group.outside`: no
teddy among the animals, no kite among the things that fly), and the members of a row have different main
colours, so no colour (the yellow banana) singles out a second picture. Check: `OddRow.problems`.
"""

from __future__ import annotations

import random
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


@dataclass(frozen=True)
class Group:
    hint: str  # the chip printed with the row, vowelized
    question: str  # the review panel's question, vowelized
    members: tuple[str, ...]
    outside: tuple[str, ...]  # clearly not in the group, for a 4–6-year-old


GROUPS: dict[str, Group] = {
    "fruit": Group(
        "فَواكِهُ",
        "أَيُّها لَيْسَ فاكِهَةً؟",
        ("apple", "banana", "grapes", "orange", "pear", "strawberry"),
        ("car", "shoe", "hat", "chair", "umbrella", "key"),
    ),
    "animal": Group(
        "حَيَواناتٌ",
        "أَيُّها لَيْسَ حَيَوانًا؟",
        ("cat", "cow", "elephant", "giraffe", "horse", "lion"),
        ("car", "chair", "umbrella", "cup", "book", "clock"),
    ),
    "clothes": Group(
        "مَلابِسُ",
        "أَيُّها لا نَلْبَسُهُ؟",
        ("dress", "jacket", "boots", "coat", "sock", "hat"),
        ("apple", "car", "cup", "cat", "book", "clock"),
    ),
    "ride": Group(
        "وَسائِلُ نَقْلٍ",
        "أَيُّها لَيْسَ وَسيلَةَ نَقْلٍ؟",
        ("car", "bus", "plane", "van", "ship"),
        ("apple", "cup", "flower", "book", "clock", "key"),
    ),
    "fly": Group(
        "أَشْياءُ تَطيرُ",
        "أَيُّها لا يَطيرُ؟",
        ("bird", "butterfly", "bee", "parrot"),
        ("cat", "cow", "fish", "elephant", "chair"),
    ),
    "food": Group(
        "طَعامٌ",
        "أَيُّها لَيْسَ طَعامًا؟",
        ("bread", "carrot", "cheese", "apple", "egg", "grapes"),
        ("shoe", "car", "book", "key", "chair", "hat"),
    ),
}
# KG1 (ages 4–5): the groups a young child names without thinking twice; KG2 adds what flies and food
BASIC_GROUPS = ("fruit", "animal", "clothes", "ride")

# (no plane among what flies: next to an animal it would be a second answer, «not an animal»)
# the main colour each group member reads as at a glance: a row's members never share one, so colour alone
# never splits a row three against one
MAIN_COLOR = {
    "apple": "red",
    "banana": "yellow",
    "grapes": "purple",
    "orange": "orange",
    "pear": "green",
    "strawberry": "red",
    "cat": "orange",
    "cow": "white",
    "elephant": "grey",
    "giraffe": "yellow",
    "horse": "brown",
    "lion": "orange",
    "dress": "pink",
    "jacket": "green",
    "boots": "yellow",
    "coat": "red",
    "sock": "blue",
    "hat": "blue",
    "car": "red",
    "bus": "yellow",
    "plane": "white",
    "van": "teal",
    "ship": "blue",
    "bird": "blue",
    "butterfly": "purple",
    "bee": "yellow",
    "parrot": "red",
    "bread": "brown",
    "carrot": "orange",
    "cheese": "yellow",
    "egg": "white",
}


@dataclass(frozen=True)
class OddRow:
    items: tuple[str, ...]
    odd: int
    rule: Rule
    example: bool = False
    group: str = ""  # a category row's group (a key of GROUPS)

    def key(self, item: str) -> str:
        if self.rule == "same":
            return item
        return "in" if item in GROUPS[self.group].members else "out"

    def problems(self) -> list[str]:
        out = []
        if not 4 <= len(self.items) <= 5:
            out.append(f"a row has 4–5 pictures, not {len(self.items)}")
        if self.rule == "category":
            if self.group not in GROUPS:
                return [*out, f"a category row needs a named group, not {self.group!r}"]
            group = GROUPS[self.group]
            if self.items[self.odd] not in group.outside:
                out.append(f"{self.items[self.odd]} is not clearly outside «{self.hint}»")
            others = [i for k, i in enumerate(self.items) if k != self.odd]
            colors = [MAIN_COLOR.get(i, i) for i in others]
            if len(set(colors)) != len(colors):
                out.append(f"two pictures of «{self.hint}» share a colour ({colors})")
        keys = Counter(self.key(i) for i in self.items)
        singles = [k for k, n in keys.items() if n == 1]
        if len(keys) != 2 or len(singles) != 1:
            out.append(f"exactly one picture must differ ({dict(keys)})")
        elif self.key(self.items[self.odd]) != singles[0]:
            out.append("the answer key points at the wrong picture")
        return out

    @property
    def hint(self) -> str:
        """The group's chip (empty on a `same` row: the difference is seen)."""
        return GROUPS[self.group].hint if self.rule == "category" else ""

    @property
    def question(self) -> str:
        return GROUPS[self.group].question if self.rule == "category" else ""

    @property
    def answer(self) -> str:
        word = strip_tashkeel(picture(self.items[self.odd]).word_ar)
        return f"{word} (المجموعة: {strip_tashkeel(self.hint)})" if self.hint else word


def _pick_members(r: random.Random, group: Group, count: int, used: set[str]) -> list[str]:
    """`count` members of different main colours, not shown elsewhere on the page when the group allows."""
    for pool in ([m for m in group.members if m not in used], list(group.members)):
        by_color: dict[str, list[str]] = {}
        for m in pool:
            by_color.setdefault(MAIN_COLOR[m], []).append(m)
        if len(by_color) >= count:
            return [r.choice(by_color[c]) for c in r.sample(sorted(by_color), count)]
    raise ValueError(f"«{group.hint}» has no {count} pictures of different colours")


def generate_odd_rows(
    seed: int | str, rules: list[Rule], sizes: list[int], groups: tuple[str, ...] | None = None
) -> list[OddRow]:
    """One row per rule; the first row is the solved example. Category rows on a page use different groups
    that share no picture, and a row avoids the pictures the rows above it show."""
    r = rng(seed, "odd")
    pairs = list(SAME_POOL)
    r.shuffle(pairs)
    choices = list(groups or GROUPS)
    used: set[str] = set()
    rows = []
    for i, (rule, size) in enumerate(zip(rules, sizes, strict=True)):
        name = ""
        if rule == "same":
            majority, odd_pic = pairs[i % len(pairs)]
            items = [majority] * (size - 1)
        else:
            name = r.choice(choices)
            group = GROUPS[name]
            # groups that share a picture (fruit and food) never meet on a page
            rest = [g for g in choices if g != name and not set(GROUPS[g].members) & set(group.members)]
            choices = rest or choices
            items = _pick_members(r, group, size - 1, used)
            odd_pic = r.choice([p for p in group.outside if p not in used] or list(group.outside))
        position = r.randrange(1 if i == 0 else 0, size)  # the example never starts with its answer
        items.insert(position, odd_pic)
        used.update(items)
        rows.append(OddRow(tuple(items), position, rule, example=i == 0, group=name))
    return rows
