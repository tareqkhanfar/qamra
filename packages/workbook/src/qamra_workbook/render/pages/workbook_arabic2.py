"""«دوسية التأسيس» Volume 2 Arabic: the twin letters of a unit (ر/ز، س/ش، ص/ض، ط/ظ، ع/غ) share one writing
page, because only their dots differ (the plan's fading scaffold): a model of both, then for each letter a
guided row and a row to write alone."""

from __future__ import annotations

from markupsafe import Markup

from qamra_workbook.render import draw
from qamra_workbook.render.foundation_text import letters_head
from qamra_workbook.render.pages.letters import letter_extent, tracing_row
from qamra_workbook.render.pages.workbook_arabic import empty_row, row_svg
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    card,
    fit_lines,
    glyph,
    shape_of,
    start_marks,  # nosec B704: SVG built from the letter path, no user input
    svg,
    text,
)
from qamra_workbook.render.registry import Built, PageContext, page_type


def alone_row(ctx: PageContext, char: str, cap: float, y: float) -> tuple[str, float]:
    """Empty writing lines with a green dot where the letter starts."""
    shape = shape_of(char)
    part, height = row_svg(Markup(empty_row(shape, W - 10, cap)[0]), 5, y)  # nosec B704: SVG built from the letter path, no user input
    _, y0, x1, _ = letter_extent(shape)
    g = shape.guides
    s = cap / (g.base - g.top)
    start = shape.strokes[0].start
    sx = 5 + (W - 10) - 10 - (x1 - start[0]) * s
    sy = y + 5 + max(0.0, (g.top - y0) * s) + (start[1] - g.top) * s
    return part + draw.start_dot((sx, sy), 1.9), height


@page_type("letters-write")
def letters_write(ctx: PageContext) -> Built:
    params = ctx.page.params
    chars = [str(c) for c in params.get("letters", ["ر", "ز"])]
    guided, alone = int(params.get("guided", 1)), int(params.get("independent", 1))
    body = [card(0, 0, W, 30, r=7)]
    for k, char in enumerate(chars):
        shape = shape_of(char)
        scale, dx, dy = fit_lines(shape, W - 40 - k * 42, 3, 34, 24)
        body.append(glyph(shape, scale, dx, dy, color=ctx.style.color, width=15))
        body.append(start_marks(shape, scale, dx, dy, 2.0, ctx.num))
    body.append(text("الحَرْفانِ يَخْتَلِفانِ بِالنِّقاطِ فَقَطْ", 50, 13, 5, color=INK))
    body.append(text("أَكْتُبُ عَلى النِّقاطِ، ثُمَّ وَحْدي", 50, 22, 4.6, color="#676B83"))
    y = 35.0
    rows = len(chars) * (guided + alone)
    cap = 14.0 if rows <= 4 else 11.0
    problems = []
    for char in chars:
        shape = shape_of(char)
        body.append(card(W - 30, y - 1, 28, 10, r=5, fill=ctx.style.tint, stroke="none"))
        body.append(text(letters_head([char]), W - 16, y + 6, 4.2, color=ctx.style.deep))
        if len(chars) >= 3:  # three letters: one row each, two dotted then room to write alone
            row = tracing_row(shape, width=W - 10, cap=cap, count=2, number=ctx.num)
            part, height = row_svg(row, 5, y + 10)
            body.append(card(0, y + 8, W, height + 3, r=6))
            body.append(part)
            y += height + 12
            continue
        for k in range(guided + alone):
            if k < guided:
                part, height = row_svg(tracing_row(shape, width=W - 10, cap=cap, number=ctx.num), 5, y + 10)
            else:
                part, height = alone_row(ctx, char, cap, y + 10)
            body.append(card(0, y + 8, W, height + 3, r=6, fill="#FFFFFF" if k < guided else "#FFFDF6"))
            body.append(part)
            y += height + 8
        y += 2
    if y > 210:
        problems.append(f"the writing rows need {y:.0f} mm (max 204)")
    return Built({"svg": svg(body)}, None, problems)
