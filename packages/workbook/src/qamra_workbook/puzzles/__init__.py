"""Programmatic puzzles (Addendum 6 §5): generated from a seed, each with an answer key and a `problems()`
check that must come back empty before a page is printed."""

from qamra_workbook.puzzles.base import Box, rng
from qamra_workbook.puzzles.coloring import ColoringScene, Shape, generate_coloring
from qamra_workbook.puzzles.counting import CountRow, generate_count_rows, layout
from qamra_workbook.puzzles.maze import Maze, generate_maze
from qamra_workbook.puzzles.odd import OddRow, generate_odd_rows
from qamra_workbook.puzzles.pattern import PatternRow, generate_pattern_rows, minimal_period, pattern_row
from qamra_workbook.puzzles.spot import Scene, SpotPuzzle, compose, generate_spot

__all__ = [
    "Box",
    "ColoringScene",
    "CountRow",
    "Maze",
    "OddRow",
    "PatternRow",
    "Scene",
    "Shape",
    "SpotPuzzle",
    "compose",
    "generate_coloring",
    "generate_count_rows",
    "generate_maze",
    "generate_odd_rows",
    "generate_pattern_rows",
    "generate_spot",
    "layout",
    "minimal_period",
    "pattern_row",
    "rng",
]
