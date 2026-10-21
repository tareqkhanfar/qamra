"""The coloring scenes: one function per page of «أُلَوِّنُ فِلَسْطين» and «أُلَوِّنُ رَمَضان».

    @scene("palestine", "olive-harvest")
    def olive_harvest(pen: Pen, w: float, h: float) -> str:   # draws in a w × h mm box (SCENE_W × SCENE_H)
        ...

A scene draws the whole picture inside its box (the page adds the rounded frame, the caption above it and
the page number). Its pen is `line` on the page and `color` on the cover and the web previews. A scene drawn
from cleaned AI line art (`coloring.lineart`) returns its stored vector paths the same way.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from qamra_workbook.coloring.ink import BOLD, INK, PAPER, Mode, Pen, clip, fmt, rect, svg

SCENE_W = 186.0  # mm: the drawing's box on an A4 page (the frame's inside edge)
SCENE_H = 232.0
FRAME_R = 7.0  # the frame's corner radius

Draw = Callable[[Pen, float, float], str]


@dataclass(frozen=True)
class Scene:
    book: str
    id: str
    draw: Draw
    source: str = "code"  # "code" (drawn here) or "ai" (cleaned line art, `coloring.lineart`)

    def body(self, mode: Mode = "line", w: float = SCENE_W, h: float = SCENE_H) -> str:
        return self.draw(Pen(mode=mode), w, h)


SCENES: dict[str, Scene] = {}


def scene(book: str, scene_id: str, *, source: str = "code") -> Callable[[Draw], Draw]:
    def register(draw: Draw) -> Draw:
        key = f"{book}/{scene_id}"
        if key in SCENES:
            raise ValueError(f"scene {key} is registered twice")
        SCENES[key] = Scene(book, scene_id, draw, source)
        return draw

    return register


def get(book: str, scene_id: str) -> Scene:
    import qamra_workbook.coloring.scenes  # noqa: F401  (registers every scene)

    try:
        return SCENES[f"{book}/{scene_id}"]
    except KeyError:
        raise KeyError(f"no coloring scene {book}/{scene_id}") from None


def framed(sc: Scene, mode: Mode = "line", w: float = SCENE_W, h: float = SCENE_H, *, uid: str = "") -> str:
    """The scene clipped to its rounded frame, with the frame drawn on top: a complete `<svg>` in mm."""
    uid = uid or f"clip-{sc.book}-{sc.id}-{mode}"
    pad = BOLD / 2
    body = clip(uid, rect(0, 0, w, h, FRAME_R), sc.body(mode, w, h))
    frame = (
        f'<rect x="0" y="0" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(FRAME_R)}" fill="none" '
        f'stroke="{INK}" stroke-width="{fmt(BOLD)}"/>'
    )
    background = f'<rect x="0" y="0" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(FRAME_R)}" fill="{PAPER}"/>'
    return svg(w, h, background + body + frame, pad=pad)
