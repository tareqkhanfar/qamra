from collections import Counter
from dataclasses import replace
from itertools import pairwise

import pytest
from qamra_workbook.puzzles import (
    CountRow,
    OddRow,
    PatternRow,
    generate_coloring,
    generate_count_rows,
    generate_maze,
    generate_odd_rows,
    generate_pattern_rows,
    generate_spot,
    layout,
    minimal_period,
    pattern_row,
)
from qamra_workbook.puzzles.spot import Placed

SEEDS = range(40)


# ---- mazes


@pytest.mark.parametrize(("cols", "rows"), [(4, 4), (5, 5), (5, 6), (8, 10)])
def test_mazes_are_solvable_perfect_mazes(cols: int, rows: int) -> None:
    for seed in SEEDS:
        maze = generate_maze(cols, rows, seed)
        assert maze.problems() == []
        path = maze.solve()
        assert path is not None and path[0] == maze.start and path[-1] == maze.end
        assert len(maze.passages) == cols * rows - 1  # a spanning tree: one way between any two cells


def test_a_blocked_maze_fails_its_check() -> None:
    maze = generate_maze(5, 5, 1)
    path = maze.solve()
    assert path is not None
    blocked = replace(maze, passages=maze.passages - {frozenset((path[0], path[1]))})
    problems = blocked.problems()
    assert "no path from the entrance to the exit" in problems
    assert "some cells cannot be reached" in problems


def test_maze_walls_leave_the_two_openings() -> None:
    maze = generate_maze(5, 5, 3, start_side="top", end_side="left")
    walls = maze.walls()
    start_col = maze.start[0]
    top_walls = [((a, b)) for a, b in walls if a[1] == 0 and b[1] == 0]
    covered = {c for (x0, _), (x1, _) in top_walls for c in range(int(x0), int(x1))}
    assert start_col not in covered and set(range(5)) - {start_col} <= covered


# ---- spot the difference


def test_spot_the_difference_has_exactly_the_promised_differences() -> None:
    for seed in SEEDS:
        puzzle = generate_spot(176, 92, seed, count=5)
        assert puzzle.problems() == []
        assert len(puzzle.changed_keys()) == 5 == len(puzzle.differences)
        assert {d.kind for d in puzzle.differences} == {"remove", "recolor", "swap", "resize", "add"}


def test_an_extra_edit_breaks_the_answer_key() -> None:
    puzzle = generate_spot(176, 92, 7)
    untouched = next(o for o in puzzle.b.objects if o.key not in puzzle.changed_keys())
    moved = Placed(untouched.key, untouched.picture, untouched.box, flip=not untouched.flip)
    b = replace(puzzle.b, objects=tuple(moved if o.key == untouched.key else o for o in puzzle.b.objects))
    tampered = replace(puzzle, b=b)
    assert len(tampered.changed_keys()) == 6
    assert any("differ in 6 objects" in p for p in tampered.problems())


# ---- odd one out


def test_exactly_one_picture_differs_in_every_row() -> None:
    for seed in SEEDS:
        rows = generate_odd_rows(seed, ["same", "same", "category"], [4, 4, 5])
        assert rows[0].example and not rows[1].example
        for row in rows:
            assert row.problems() == []
            keys = Counter(row.key(i) for i in row.items)
            assert keys[row.key(row.items[row.odd])] == 1


def test_odd_one_out_catches_two_odd_pictures_and_a_wrong_key() -> None:
    assert OddRow(("apple", "apple", "car", "ball"), 2, "same").problems()
    assert OddRow(("apple", "apple", "apple", "car"), 0, "same").problems() == [
        "the answer key points at the wrong picture"
    ]
    assert OddRow(("cat", "dog", "cow", "apple"), 3, "category").problems() == []


# ---- quantity first


def test_quantity_rows_show_exact_counts() -> None:
    for seed in SEEDS:
        rows = generate_count_rows(seed, [1, 2, 3], [1, 2, 3], "apple", example=2)
        assert rows[0].example and rows[0].count == 2
        assert sorted(r.count for r in rows[1:]) == [1, 2, 3]
        for row in rows:
            assert row.problems() == []
            assert len(layout(row.count)) == row.count
            assert row.options[row.answer] == row.count
        assert all(a.answer != b.answer for a, b in pairwise(rows))


def test_quantity_row_rejects_ambiguous_cards() -> None:
    assert CountRow("apple", 2, (2, 2, 3)).problems()
    assert CountRow("apple", 2, (1, 3, 4)).problems()


# ---- patterns


def test_patterns_are_valid_and_the_answer_continues_them() -> None:
    for seed in SEEDS:
        rows = generate_pattern_rows(seed, ["AB", "AB", "AB", "ABB"], [4, 4, 5, 6])
        for row in rows:
            assert row.problems() == []
            assert minimal_period(row.shown) == len(row.unit)
            full = row.shown + row.answer
            assert all(full[i] == row.unit[i % len(row.unit)] for i in range(len(full)))
    ab = pattern_row("AB", ("sun", "cloud"), 5)
    assert ab.answer == ("cloud",)


def test_ambiguous_or_short_patterns_are_rejected() -> None:
    assert pattern_row("AB", ("sun", "cloud"), 3).problems()  # the unit is shown only once and a half
    assert PatternRow(("sun", "sun"), ("sun", "sun", "sun", "sun")).problems()  # one element, not two
    shown_as_ab = PatternRow(("sun", "cloud", "sun", "cloud"), ("sun", "cloud", "sun", "cloud"))
    assert any("different rule" in p for p in shown_as_ab.problems())  # ABAB read as a 4-long unit


# ---- smart coloring


def test_smart_coloring_count_matches_the_key() -> None:
    for seed in SEEDS:
        scene = generate_coloring(150, 128, seed, "circle")
        assert scene.problems() == []
        assert sum(1 for s in scene.shapes if s.kind == "circle") == scene.count >= 3
    scene = generate_coloring(150, 128, 1, "circle")
    assert replace(scene, count=scene.count + 1).problems()


# ---- determinism


def test_the_same_seed_gives_the_same_puzzle() -> None:
    assert generate_maze(5, 5, "p19") == generate_maze(5, 5, "p19")
    assert generate_spot(176, 92, 97) == generate_spot(176, 92, 97)
    assert generate_odd_rows(6, ["same", "category"], [4, 5]) == generate_odd_rows(
        6, ["same", "category"], [4, 5]
    )
    assert generate_count_rows(71, [1, 2, 3], [1, 2, 3], "apple") == generate_count_rows(
        71, [1, 2, 3], [1, 2, 3], "apple"
    )
    assert generate_pattern_rows(43, ["AB", "ABB"], [4, 6]) == generate_pattern_rows(
        43, ["AB", "ABB"], [4, 6]
    )
    assert generate_coloring(150, 128, 52) == generate_coloring(150, 128, 52)
    assert generate_maze(5, 5, 1) != generate_maze(5, 5, 2)
