"""Path geometry for tracing: parse simple SVG paths (absolute M, L, Q, C), measure them, and place points
at equal distances (tracing dots) or read the point and direction at a fraction of the length (arrows).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import cached_property
from itertools import pairwise

Point = tuple[float, float]

_TOKEN = re.compile(r"[MLQC]|-?\d+(?:\.\d+)?")
_ARGS = {"M": 2, "L": 2, "Q": 4, "C": 6}
_SAMPLES = 48  # per curve segment; plenty at print sizes


def _bezier(pts: list[Point], t: float) -> Point:
    while len(pts) > 1:
        pts = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in pairwise(pts)]
    return pts[0]


def _parse(d: str) -> list[list[Point]]:
    """Subpaths as dense polylines."""
    tokens = _TOKEN.findall(d)
    subpaths: list[list[Point]] = []
    i, here = 0, (0.0, 0.0)
    while i < len(tokens):
        cmd = tokens[i]
        if cmd not in _ARGS:
            raise ValueError(f"unsupported path token {cmd!r} in {d!r} (absolute M, L, Q, C only)")
        n = _ARGS[cmd]
        nums = [float(x) for x in tokens[i + 1 : i + 1 + n]]
        if len(nums) != n:
            raise ValueError(f"path command {cmd} needs {n} numbers: {d!r}")
        i += 1 + n
        pts = [(nums[k], nums[k + 1]) for k in range(0, n, 2)]
        if cmd == "M":
            subpaths.append([pts[0]])
        elif not subpaths:
            raise ValueError(f"path must start with M: {d!r}")
        elif cmd == "L":
            subpaths[-1].append(pts[0])
        else:
            ctrl = [here, *pts]
            subpaths[-1] += [_bezier(ctrl, s / _SAMPLES) for s in range(1, _SAMPLES + 1)]
        here = pts[-1]
    return subpaths


@dataclass(frozen=True)
class Stroke:
    """One pen stroke: a single subpath, drawn in the direction it is written."""

    d: str

    @cached_property
    def polyline(self) -> list[Point]:
        subpaths = _parse(self.d)
        if len(subpaths) != 1:
            raise ValueError(f"a stroke is one subpath: {self.d!r}")
        return subpaths[0]

    @cached_property
    def _cumulative(self) -> list[float]:
        out = [0.0]
        for a, b in pairwise(self.polyline):
            out.append(out[-1] + math.dist(a, b))
        return out

    @property
    def length(self) -> float:
        return self._cumulative[-1]

    @property
    def start(self) -> Point:
        return self.polyline[0]

    @property
    def end(self) -> Point:
        return self.polyline[-1]

    def at(self, fraction: float) -> tuple[Point, float]:
        """(point, direction in degrees) at a fraction of the length."""
        target = max(0.0, min(1.0, fraction)) * self.length
        cum = self._cumulative
        for k in range(1, len(cum)):
            if cum[k] >= target or k == len(cum) - 1:
                a, b = self.polyline[k - 1], self.polyline[k]
                seg = cum[k] - cum[k - 1]
                t = 0.0 if seg == 0 else (target - cum[k - 1]) / seg
                point = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                return point, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        return self.start, 0.0

    def dots(self, spacing: float) -> list[Point]:
        """Points at (nearly) `spacing` apart, including both ends."""
        count = max(1, round(self.length / spacing))
        return [self.at(k / count)[0] for k in range(count + 1)]

    def scaled(self, scale: float, dx: float = 0, dy: float = 0) -> Stroke:
        """The same stroke scaled about the origin, then moved by (dx, dy)."""
        out, axis = [], 0
        for tok in _TOKEN.findall(self.d):
            if tok in _ARGS:
                out.append(tok)
                axis = 0
                continue
            out.append(f"{float(tok) * scale + (dx if axis == 0 else dy):.2f}")
            axis ^= 1
        return Stroke(" ".join(out))


def bounds(strokes: list[Stroke]) -> tuple[float, float, float, float]:
    xs = [x for s in strokes for x, _ in s.polyline]
    ys = [y for s in strokes for _, y in s.polyline]
    return min(xs), min(ys), max(xs), max(ys)
