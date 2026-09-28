"""Quantity first (Addendum 6 §4.7): groups of pictures matched to dot cards, before any numerals.

Checks: each group is drawn with exactly its count of pictures, each row's dot cards are all different,
and exactly one card has the group's amount.
"""

from __future__ import annotations

from dataclasses import dataclass

from qamra_workbook.puzzles.base import rng

# dice-style layouts in a unit square (the same arrangement for pictures and dots, so amounts compare)
LAYOUTS: dict[int, tuple[tuple[float, float], ...]] = {
    1: ((0.5, 0.5),),
    2: ((0.27, 0.5), (0.73, 0.5)),
    3: ((0.5, 0.26), (0.26, 0.72), (0.74, 0.72)),
    4: ((0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)),
    5: ((0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)),
}


def layout(count: int) -> tuple[tuple[float, float], ...]:
    try:
        return LAYOUTS[count]
    except KeyError:
        raise ValueError(f"quantity pages show 1–5 things, not {count}") from None


@dataclass(frozen=True)
class CountRow:
    picture: str
    count: int
    options: tuple[int, ...]  # amounts on the dot cards, in page order
    example: bool = False

    @property
    def answer(self) -> int:
        return self.options.index(self.count)

    def problems(self) -> list[str]:
        out = []
        if len(layout(self.count)) != self.count:
            out.append(f"the group of {self.count} is drawn with {len(layout(self.count))} pictures")
        if len(set(self.options)) != len(self.options):
            out.append(f"dot cards repeat an amount: {self.options}")
        if self.options.count(self.count) != 1:
            out.append(f"exactly one dot card must show {self.count}")
        if any(len(layout(n)) != n for n in self.options):
            out.append("a dot card is drawn with the wrong number of dots")
        return out


def generate_count_rows(
    seed: int | str, counts: list[int], options: list[int], picture: str, example: int | None = None
) -> list[CountRow]:
    """One row per count in a shuffled order (after the solved example row, when there is one); each row's
    dot cards are shuffled so the answer moves around."""
    r = rng(seed, "count")
    order = list(counts)
    while True:
        r.shuffle(order)
        if len(order) < 3 or order != sorted(order):  # avoid a staircase the child can guess
            break
    amounts = ([example] if example is not None else []) + order
    rows: list[CountRow] = []
    for i, n in enumerate(amounts):
        opts = list(options)
        while True:
            r.shuffle(opts)
            if not rows or opts.index(n) != rows[-1].answer:
                break
        rows.append(CountRow(picture, n, tuple(opts), example=example is not None and i == 0))
    return rows
