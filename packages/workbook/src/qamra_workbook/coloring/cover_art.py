"""The covers' scenes, drawn in code in colour (`Pen(mode="color")`): the books' own line art, painted.

The front's scene fills the page (bleed included) behind the title panel, the name ribbon and the child;
without a character (the family has none), the middle holds a drawn centrepiece instead, so the cover is
never empty. The back's band is the same scene, cropped.
"""

from __future__ import annotations

from markupsafe import Markup

from qamra_workbook.coloring.ink import (
    CLOUD,
    GRASS,
    HILL,
    HILL_FAR,
    Pen,
    fmt,
    place,
    rect,
)
from qamra_workbook.coloring.letters import picture_svg
from qamra_workbook.coloring.parts.common import cloud, flower, ground, hills, sun
from qamra_workbook.coloring.parts.qamra import crayon_box, crayon_fan, moon_friend, star_field

SKY = "#CFEAF8"
PAPER_WARM = "#FFF6E6"
COVER_LINE = 1.7  # the cover paints the line art with thinner outlines (2.6 mm / 1.7 ≈ 1.5 mm)


def _wrap(body: str, w: float, h: float, *, slice_: bool = True, align: str = "xMidYMax") -> Markup:
    aspect = f"{align} slice" if slice_ else "xMidYMid meet"
    return Markup(  # nosec B704 (drawn in code)
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}" preserveAspectRatio="{aspect}" '
        f'aria-hidden="true">{body}</svg>'
    )


def _pic(pid: str, x: float, y: float, size: float) -> str:
    """A library picture in colour, `size` mm wide, its centre at (x, y)."""
    inner = picture_svg(pid, size, mode="color", line_mm=1.3)
    s = size * 1.08
    return f'<svg x="{fmt(x - s / 2)}" y="{fmt(y - s / 2)}" width="{fmt(s)}" height="{fmt(s)}" viewBox="-4 -4 108 108" overflow="visible">{inner.split(">", 1)[1].rsplit("</svg>", 1)[0]}</svg>'


def letters_scene(w: float, h: float, hero: bool) -> str:
    pen = Pen(scale=COVER_LINE, mode="color")
    out = [f'<rect x="0" y="0" width="{fmt(w)}" height="{fmt(h)}" fill="{SKY}"/>']
    out.append(hills(pen, w, h * 0.66, 14, 3, fill=HILL_FAR, seed=3, floor=h + 10))
    out.append(hills(pen, w, h * 0.74, 10, 4, fill=HILL, seed=5, floor=h + 10))
    out.append(ground(pen, w, h * 0.84, floor=h + 10, fill=GRASS))
    out.append(_pic("butterfly", w * 0.14, h * 0.55, 30))
    out.append(_pic("apple", w * 0.1, h * 0.8, 30))
    out.append(_pic("duck", w * 0.88, h * 0.78, 34))
    out.append(_pic("star", w * 0.87, h * 0.55, 24))
    out.append(place(pen, flower, w * 0.25, h * 0.92, 0.9))
    out.append(place(pen, flower, w * 0.75, h * 0.93, 0.8, fill="#F7C84A", centre="#E5604E"))
    if not hero:
        out.append(place(pen, moon_friend, w * 0.42, h * 0.56, 1.35))
        out.append(place(pen, crayon_box, w * 0.66, h * 0.86, 0.75))
    return "".join(out)


def sketch_scene(w: float, h: float, hero: bool) -> str:
    pen = Pen(scale=COVER_LINE, mode="color")
    out = [f'<rect x="0" y="0" width="{fmt(w)}" height="{fmt(h)}" fill="{PAPER_WARM}"/>']
    out.append(place(pen, sun, w * 0.15, h * 0.4, 0.8))
    out.append(place(pen, cloud, w * 0.85, h * 0.38, 0.8))
    out.append(
        star_field(
            pen,
            [
                (w * 0.1, h * 0.58, 7),
                (w * 0.9, h * 0.56, 8),
                (w * 0.84, h * 0.72, 5),
                (w * 0.16, h * 0.74, 5),
            ],
        )
    )
    out.append(place(pen, crayon_fan, w * 0.12, h + 4, 1.4, n=5))
    out.append(place(pen, crayon_fan, w * 0.88, h + 4, 1.4, n=5))
    if not hero:
        out.append(place(pen, moon_friend, w * 0.5, h * 0.62, 1.6))
    return "".join(out)


def scene_book(book: str, w: float, h: float, hero: bool) -> str:
    """A scene book's cover: its first scene, painted, scaled to cover the page."""
    from qamra_workbook.coloring.book import content
    from qamra_workbook.coloring.scenes import SCENE_H, SCENE_W, get

    cover_id = str(content(book).get("cover_scene") or content(book)["pages"][0]["id"])
    sc = get(book, cover_id)
    k = max(w / SCENE_W, h / SCENE_H)
    dx = (w - SCENE_W * k) / 2
    dy = h - SCENE_H * k
    body = sc.draw(Pen(scale=COVER_LINE * k, mode="color"), SCENE_W, SCENE_H)
    return (
        f'<rect x="0" y="0" width="{fmt(w)}" height="{fmt(h)}" fill="{CLOUD}"/>'
        f'<g transform="translate({fmt(dx)} {fmt(dy)}) scale({fmt(k)})">{body}</g>'
    )


def cover_scene(key: str, w: float, h: float, *, hero: bool) -> Markup:
    if key == "letters":
        body = letters_scene(w, h, hero)
    elif key == "sketchbook":
        body = sketch_scene(w, h, hero)
    else:
        body = scene_book(key, w, h, hero)
    return _wrap(f"<g>{body}</g>", w, h)


def band_scene(key: str, w: float, h: float) -> Markup:
    """The back's band: the front's scene without a centrepiece, its lower part."""
    full_h = w * 303 / 216
    inner = cover_scene(key, w, full_h, hero=True)
    return Markup(  # nosec B704
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {fmt(full_h * 0.62)} {fmt(w)} {fmt(h)}" '
        f'preserveAspectRatio="xMidYMid slice" aria-hidden="true">{inner.split(">", 1)[1].rsplit("</svg>", 1)[0]}</svg>'
    )


_ = rect
