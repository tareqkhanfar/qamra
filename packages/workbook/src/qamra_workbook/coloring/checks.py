"""Automated checks on a coloring drawing (run by the tests and by every page builder).

A coloring page prints pure black line art on white: no other colour, no grey, no transparency, no text or
raster image inside the drawing, and lines no thinner than the house minimum at print size.
"""

from __future__ import annotations

import re

from qamra_workbook.coloring.ink import INK, PAPER

_COLOR = re.compile(r'(?:fill|stroke|stop-color)="([^"]+)"')
_FORBIDDEN = re.compile(r"<(text|image|foreignObject|tspan)\b|opacity=|url\(#(?!clip)")
ALLOWED = {INK.lower(), PAPER.lower(), "none", "#000", "#fff", "black", "white"}


def line_problems(markup: str) -> list[str]:
    """What keeps `markup` (a drawing in `line` mode) from printing as clean black-and-white line art."""
    problems = []
    colors = {m.lower() for m in _COLOR.findall(markup)} - ALLOWED
    if colors:
        problems.append(f"colours other than black and white: {sorted(colors)[:6]}")
    bad = sorted({m.group(0) for m in _FORBIDDEN.finditer(markup)})
    if bad:
        problems.append(f"not allowed in line art: {bad[:6]}")
    return problems
