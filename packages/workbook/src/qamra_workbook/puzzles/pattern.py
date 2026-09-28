"""Pattern completion: a repeating unit shown at least twice, then empty slots to draw or sticker.

Checks: the shown items follow the unit, the unit uses exactly the promised number of different elements,
it is shown at least twice, the shortest rule that explains what is shown is the unit itself (so there is
only one right answer), and the answer continues it.
"""

from __future__ import annotations

from dataclasses import dataclass

from qamra_workbook.puzzles.base import rng

# element pairs: shapes first (the gentlest), then pictures
PAIRS = (
    ("shape:circle", "shape:triangle"),
    ("apple", "ball"),
    ("sun", "cloud"),
    ("shape:square", "shape:heart"),
    ("fish", "duck"),
    ("flower", "leaf"),
)


def minimal_period(seq: tuple[str, ...]) -> int:
    for p in range(1, len(seq) + 1):
        if all(seq[i] == seq[i % p] for i in range(len(seq))):
            return p
    return len(seq)


@dataclass(frozen=True)
class PatternRow:
    unit: tuple[str, ...]
    shown: tuple[str, ...]
    blanks: int = 1
    elements: int = 2
    example: bool = False

    @property
    def answer(self) -> tuple[str, ...]:
        n = len(self.shown)
        return tuple(self.unit[(n + k) % len(self.unit)] for k in range(self.blanks))

    def problems(self) -> list[str]:
        out = []
        size = len(self.unit)
        if len(set(self.unit)) != self.elements:
            out.append(f"the unit {self.unit} should use {self.elements} different elements")
        if self.shown != tuple(self.unit[i % size] for i in range(len(self.shown))):
            out.append("the shown items do not follow the unit")
        if len(self.shown) < 2 * size:
            out.append("the unit must be shown at least twice")
        if minimal_period(self.shown) != size:
            out.append(f"what is shown can be read as a different rule (period {minimal_period(self.shown)})")
        if self.blanks < 1:
            out.append("a pattern row needs an empty slot")
        return out


def pattern_row(unit: str, pair: tuple[str, str], shown: int, *, example: bool = False) -> PatternRow:
    """`unit` in letters (AB, ABB, AAB…) over the two elements of `pair`."""
    elements = tuple(pair[ord(ch) - ord("A")] for ch in unit)
    return PatternRow(elements, tuple(elements[i % len(elements)] for i in range(shown)), example=example)


def generate_pattern_rows(seed: int | str, units: list[str], shown: list[int]) -> list[PatternRow]:
    """One row per unit, each with its own element pair; the first row is the solved example."""
    r = rng(seed, "pattern")
    pairs = [PAIRS[0], *r.sample(PAIRS[1:], len(PAIRS) - 1)]  # the example always uses shapes
    return [
        pattern_row(unit, pairs[i % len(pairs)], n, example=i == 0)
        for i, (unit, n) in enumerate(zip(units, shown, strict=True))
    ]
