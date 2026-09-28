"""Math pages: quantity first (Addendum 6 §4.7), before any numerals."""

from __future__ import annotations

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.puzzles import generate_count_rows, layout
from qamra_workbook.render import draw
from qamra_workbook.render.pages.thinking import ring
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.spec import arabic_digits

# rows are marked with little pictures, not numbers: numerals come after quantities (Addendum 6 §4.7)
ROW_MARKS = ("star", "heart", "shapes", "puzzle")
ROW_MARKS_AR = {"star": "النجمة", "heart": "القلب", "shapes": "الأشكال", "puzzle": "قطعة البازل"}


def group_svg(picture_id: str, count: int, w: float = 60, h: float = 40) -> Markup:
    """`count` pictures in a dice layout (the same layout as the dot cards)."""
    size = min(w, h) * (0.62 if count <= 2 else 0.5)
    inner = picture(picture_id).inner("color")
    body = "".join(
        draw.el(
            "svg",
            inner,
            x=u * w - size / 2,
            y=v * h - size / 2,
            width=size,
            height=size,
            viewBox="0 0 100 100",
            data_count_item=picture_id,
        )
        for u, v in layout(count)
    )
    return draw.svg(w, h, body, "group")


def dots_svg(count: int, color: str, size: float = 30) -> Markup:
    """A dot card: `count` big dots in the dice layout."""
    pad, span = size * 0.08, size * 0.84
    body = "".join(
        draw.el("circle", cx=pad + u * span, cy=pad + v * span, r=size * 0.1, fill=color, data_dot=1)
        for u, v in layout(count)
    )
    return draw.svg(size, size, body, "dots")


@page_type("quantity-first")
def quantity_first(ctx: PageContext) -> Built:
    params = ctx.page.params
    pic = str(params.get("picture", "apple"))
    counts = [int(x) for x in params.get("counts", [1, 2, 3])]
    options = [int(x) for x in params.get("options", [1, 2, 3])]
    example = int(params["example"]) if "example" in params else (2 if ctx.page.example else None)
    rows = generate_count_rows(ctx.page.seed, counts, options, pic, example)
    color = ctx.style.color
    data = {
        "rows": [
            {
                "group": group_svg(pic, row.count),
                "cards": [dots_svg(n, color) for n in row.options],
                "answer": row.answer,
                "count": row.count,
                "example": row.example,
                "mark": ROW_MARKS[k % len(ROW_MARKS)],
            }
            for k, row in enumerate(rows)
        ],
        "ring": ring,
    }
    answer = ["البطاقة التي نقاطها بعدد الصور:"] + [
        f"صف {ROW_MARKS_AR[ROW_MARKS[k % len(ROW_MARKS)]]}: {arabic_digits(row.count)}"
        for k, row in enumerate(rows)
        if not row.example
    ]
    return Built(data, answer, [p for row in rows for p in row.problems()])
