"""«قلبي يعرف الله»: the activity pages: the wudu cards to put in order (shuffled by a seed, the answer key
lists the right
order), the blessings hunt (a scene with eight blessings to ring) and the colouring page (line art, no
sacred text on it).

Addendum 10 §3.6: a page the child colours, cuts or may throw away never carries a verse, a hadith or a
dhikr: the colouring
page prints none and cites no source, and the check refuses it if the file adds one.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.islamic_sources import letters
from qamra_workbook.pictures import get as library_picture
from qamra_workbook.pictures.islamic import BLESSING_SPOTS, SCENES, WUDU_ICONS, body_icon, glyph_svg
from qamra_workbook.pictures.islamic_backdrops import GLYPH_PREFIX
from qamra_workbook.pictures.islamic_scenes import crescent, sun_disc
from qamra_workbook.pictures.model import OUTLINE
from qamra_workbook.render.islamic_content import Coloring, Hunt, OrderSteps, PrayerSteps
from qamra_workbook.render.pages.islamic_common import (
    chrome,
    claim,
    context_of,
    islamic_page,
    page_of,
    picture_problems,
    plain,
    references,
    rich,
    scene,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

# the blessings of the hunt: the word (letters only) → the spot of the scene it names, and what its card draws
FIND: dict[str, tuple[str, str]] = {
    letters(word): (spot, art)
    for word, spot, art in (
        ("الشمس", "sun", "@sun"),
        ("الماء", "water", "water"),
        ("الشجرة", "tree", "tree"),
        ("الثمرة", "fruit", "apple"),
        ("الطائر", "bird", "bird"),
        ("الخبز", "bread", "loaf"),
        ("القمر", "moon", "@moon"),
        ("الأسرة", "family", "@family"),
    )
}


def sign(name: str) -> Markup:
    """The small drawn cards of the hunt's list: the sun, the moon (no faces) and the family (a house with a
    heart)."""
    match name:
        case "@sun":
            inner = sun_disc(12, 12, 6.5)
        case "@moon":
            inner = crescent(12, 12, 8.5)
        case _:
            inner = (
                f'<g transform="translate(-1 -1) scale(1.08)">{glyph_svg("heart-house", "#E4675A", 1.7)}</g>'
            )
    return Markup(f'<svg class="hunt-pic" viewBox="0 0 24 24" aria-hidden="true">{inner}</svg>')  # nosec B704


def shuffled(count: int, rng: Any) -> list[int]:
    """A deterministic shuffle (by the page's seed) that is never the right order."""
    order = list(range(count))
    for _ in range(20):
        rng.shuffle(order)
        if order != sorted(order):
            break
    else:
        order = order[1:] + order[:1]
    return order


def order_cards(ctx: PageContext, require_art: bool) -> Built:
    page = page_of(ctx)
    assert isinstance(page, OrderSteps | PrayerSteps)
    problems: list[str] = []
    steps = sorted(page.steps, key=lambda s: s.n)
    if [s.n for s in steps] != list(range(1, len(steps) + 1)):
        problems.append("the steps must be numbered 1, 2, 3… without gaps")
    for s in steps:
        if (require_art or s.art) and s.art not in WUDU_ICONS:
            problems.append(f"step {s.n}: no card art {s.art!r} (a body part, never a person)")
    if len(steps) < 2:
        problems.append("an ordering page needs at least two steps")
    review = context_of(ctx).review_marks
    cards = []
    for k in shuffled(len(steps), ctx.rng("order")) if len(steps) > 1 else range(len(steps)):
        s = steps[k]
        cards.append(
            {
                "art": body_icon(s.art) if s.art in WUDU_ICONS else Markup(""),
                "text": rich(ctx, s.t, problems),
                "times": ctx.num(s.times) if s.times else "",
                "flag": bool(s.scholar_decision and review),
            }
        )
    ids = [src for s in steps for src in [*s.sources, *source_ids(s.t)]] + page.scholar_points
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "cards": cards,
        "parent": rich(ctx, page.parent_line, problems),
        "labels": {"parent": "لِلْأَهْلِ", "times": "مَرَّاتٍ", "write": ""},
        "refs": references(ctx, ids),
    }
    answer = [
        f"{ctx.num(s.n)}) {plain(ctx, s.t)}" + (f" ×{ctx.num(s.times)}" if s.times else "") for s in steps
    ]
    return Built(data, answer, problems)


@islamic_page("wudu-steps")
def wudu_steps(ctx: PageContext) -> Built:
    """The wudu cards, shuffled by the page's seed; the answer key lists the right order."""
    return order_cards(ctx, require_art=True)


@islamic_page("prayer-steps", shared="wudu-steps")
def prayer_steps(ctx: PageContext) -> Built:
    """The prayer's steps to put in order (art optional): the same cards as the wudu page."""
    return order_cards(ctx, require_art=False)


def rings(spots: list[str], box: tuple[float, float]) -> Markup:
    """The answer rings round the blessings, in the scene's own units (the answer key shows them)."""
    parts = "".join(
        f'<ellipse class="answer-ring" cx="{x}" cy="{y}" rx="{r * 1.15}" ry="{r}"/>'
        for x, y, r in (BLESSING_SPOTS[s] for s in spots)
    )
    return Markup(  # nosec B704 (numbers only)
        f'<svg class="hunt-rings" viewBox="0 0 {box[0]:g} {box[1]:g}" '
        f'preserveAspectRatio="xMidYMid slice" aria-hidden="true">{parts}</svg>'
    )


@islamic_page("blessings-hunt")
def blessings_hunt(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Hunt)
    problems: list[str] = []
    if page.art not in SCENES:
        problems.append(f"no scene art {page.art!r}")
    items, spots = [], []
    for word in page.find:
        found = FIND.get(letters(word))
        if found is None:
            problems.append(f"nothing in the scene for {word!r}")
            continue
        spot, art = found
        spots.append(spot)
        items.append(
            {
                "word": ctx.text(word),
                "art": sign(art) if art.startswith("@") else ctx.pic(art, "color", "hunt-pic"),
            }
        )
    box = SCENES[page.art].box if page.art in SCENES else (186.0, 118.0)
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "scene": scene(ctx, page.art, "hunt-art"),
        "rings": rings(spots, box),
        "finds": items,
        "closing": claim(ctx, page.closing, problems),
        "draw_box": ctx.text(page.draw_box),
        "refs": references(ctx, source_ids(page.closing)),
    }
    return Built(data, [ctx.text(w) for w in page.find], problems)


def line_art(name: str, css_class: str = "col-pic") -> Markup:
    """A picture to colour: the library's line art, or a series icon in outline."""
    if name.startswith(GLYPH_PREFIX):
        glyph = glyph_svg(name[len(GLYPH_PREFIX) :], OUTLINE, 1.1)
        inner = f'<g transform="translate(8 8) scale(3.5)">{glyph}</g>'
    else:
        inner = library_picture(name).inner("line")
    return Markup(  # nosec B704 (static art)
        f'<svg class="{css_class}" viewBox="0 0 100 100" aria-hidden="true">{inner}</svg>'
    )


@islamic_page("islamic-coloring")
def coloring(ctx: PageContext) -> Built:
    """A line-art scene, or one to six pictures laid out big on the page, to colour."""
    page = page_of(ctx)
    assert isinstance(page, Coloring)
    problems: list[str] = []
    if page.art and page.art not in SCENES:
        problems.append(f"no scene art {page.art!r}")
    problems += picture_problems(page.pics, "pics")
    if page.sacred_text != "none":
        problems.append(
            "a colouring page must say `sacred_text: none` (it carries no verse, hadith or dhikr)"
        )
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "art": scene(ctx, page.art, "col-art", "meet") if page.art and not problems else "",
        "pics": [line_art(p) for p in page.pics] if not problems else [],
        "grid": len(page.pics),
    }
    return Built(data, None, problems)
