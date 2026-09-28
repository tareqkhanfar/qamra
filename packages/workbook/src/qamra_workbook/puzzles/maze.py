"""Grid mazes: a seeded depth-first carve gives a perfect maze (one path between any two cells).

Checks: every passage joins grid neighbours, the maze is a spanning tree (all cells reachable, no loops),
the exit is reachable from the entrance (BFS), and the solution is long enough to be a real path.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from qamra_workbook.puzzles.base import rng

Cell = tuple[int, int]  # (column, row); column 0 is the left side, row 0 the top
Side = Literal["top", "bottom", "left", "right"]
Segment = tuple[tuple[float, float], tuple[float, float]]


def _edge(a: Cell, b: Cell) -> frozenset[Cell]:
    return frozenset((a, b))


@dataclass(frozen=True)
class Maze:
    cols: int
    rows: int
    passages: frozenset[frozenset[Cell]]
    start: Cell
    end: Cell
    start_side: Side
    end_side: Side

    def cells(self) -> list[Cell]:
        return [(c, r) for r in range(self.rows) for c in range(self.cols)]

    def open_neighbours(self, cell: Cell) -> list[Cell]:
        c, r = cell
        near = [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
        return [n for n in near if _edge(cell, n) in self.passages]

    def solve(self) -> list[Cell] | None:
        """Shortest path from the entrance cell to the exit cell (BFS)."""
        came: dict[Cell, Cell | None] = {self.start: None}
        queue = deque([self.start])
        while queue:
            cell = queue.popleft()
            if cell == self.end:
                path: list[Cell] = []
                step: Cell | None = cell
                while step is not None:
                    path.append(step)
                    step = came[step]
                return path[::-1]
            for n in self.open_neighbours(cell):
                if n not in came:
                    came[n] = cell
                    queue.append(n)
        return None

    def reachable(self) -> set[Cell]:
        seen, stack = {self.start}, [self.start]
        while stack:
            for n in self.open_neighbours(stack.pop()):
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        return seen

    def problems(self) -> list[str]:
        out = []
        cells = set(self.cells())
        for edge in self.passages:
            a, b = tuple(edge)
            if a not in cells or b not in cells or abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
                out.append(f"passage {sorted(edge)} does not join two neighbouring cells")
        if len(self.reachable()) != len(cells):
            out.append("some cells cannot be reached")
        if len(self.passages) != len(cells) - 1:
            out.append("the maze has loops or gaps (not a spanning tree)")
        for cell, side in ((self.start, self.start_side), (self.end, self.end_side)):
            if not _on_side(cell, side, self.cols, self.rows):
                out.append(f"opening {cell} is not on the {side} side")
        path = self.solve()
        if path is None:
            out.append("no path from the entrance to the exit")
        elif len(path) < self.cols + self.rows - 1:
            out.append(f"the path is too short ({len(path)} cells)")
        return out

    def walls(self) -> list[Segment]:
        """Wall segments in cell units, merged into straight runs, with the two openings left out."""
        horizontal: list[tuple[int, int]] = []  # (row line, column) unit walls
        vertical: list[tuple[int, int]] = []  # (column line, row)
        for c in range(self.cols):
            for r in range(self.rows + 1):
                above, below = (c, r - 1), (c, r)
                if 0 < r < self.rows and _edge(above, below) in self.passages:
                    continue
                if (r == 0 and self._opening(below, "top")) or (
                    r == self.rows and self._opening(above, "bottom")
                ):
                    continue
                horizontal.append((r, c))
        for r in range(self.rows):
            for c in range(self.cols + 1):
                left, right = (c - 1, r), (c, r)
                if 0 < c < self.cols and _edge(left, right) in self.passages:
                    continue
                if (c == 0 and self._opening(right, "left")) or (
                    c == self.cols and self._opening(left, "right")
                ):
                    continue
                vertical.append((c, r))
        return _runs(horizontal, horizontal=True) + _runs(vertical, horizontal=False)

    def _opening(self, cell: Cell, side: Side) -> bool:
        return (cell == self.start and side == self.start_side) or (
            cell == self.end and side == self.end_side
        )


def _on_side(cell: Cell, side: Side, cols: int, rows: int) -> bool:
    c, r = cell
    return {"top": r == 0, "bottom": r == rows - 1, "left": c == 0, "right": c == cols - 1}[side]


def _runs(units: list[tuple[int, int]], *, horizontal: bool) -> list[Segment]:
    out: list[Segment] = []
    for line_no in sorted({u[0] for u in units}):
        steps = sorted(u[1] for u in units if u[0] == line_no)
        begin = prev = steps[0]
        for s in [*steps[1:], None]:
            if s is not None and s == prev + 1:
                prev = s
                continue
            a, b = float(begin), float(prev + 1)
            line = float(line_no)
            out.append(((a, line), (b, line)) if horizontal else ((line, a), (line, b)))
            if s is not None:
                begin = prev = s
    return out


def generate_maze(
    cols: int,
    rows: int,
    seed: int | str,
    *,
    start: Cell | None = None,
    end: Cell | None = None,
    start_side: Side = "right",
    end_side: Side = "left",
) -> Maze:
    """A perfect maze. By default it runs right to left (the Arabic reading direction): in at the top
    right, out at the bottom left."""
    start = start if start is not None else (cols - 1, 0)
    end = end if end is not None else (0, rows - 1)
    r = rng(seed, "maze")
    passages: set[frozenset[Cell]] = set()
    seen = {start}
    stack = [start]
    while stack:
        c, row = stack[-1]
        options = [
            (nc, nr)
            for nc, nr in ((c + 1, row), (c - 1, row), (c, row + 1), (c, row - 1))
            if 0 <= nc < cols and 0 <= nr < rows and (nc, nr) not in seen
        ]
        if not options:
            stack.pop()
            continue
        nxt = r.choice(options)
        passages.add(_edge((c, row), nxt))
        seen.add(nxt)
        stack.append(nxt)
    return Maze(cols, rows, frozenset(passages), start, end, start_side, end_side)
