"""«دوسية التأسيس» Volume 3 English: the vocabulary units (Addendum 5 §3): a card per word with its picture,
the English word (first letter in colour) and the Arabic word under it. Registered as `vocab-cards` (the
journey book owns `vocab-unit`)."""

from __future__ import annotations

from markupsafe import escape

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_common import INK, W, card, pic, picture_id, svg, text
from qamra_workbook.render.registry import Built, PageContext, page_type

UNIT_AR = {
    "Numbers": "الأعداد",
    "Colors": "الألوان",
    "Shapes": "الأشكال",
    "Family": "العائلة",
    "Body Parts": "أعضاء الجسم",
    "Animals": "الحيوانات",
    "Fruits": "الفواكه",
    "Food": "الطعام",
    "Toys": "الألعاب",
    "School Objects": "أدوات المدرسة",
}


def en_word(word: str, x: float, y: float, size: float, color: str) -> str:
    head, rest = word[:1].upper(), word[1:]
    return (
        f'<text x="{draw.n(x)}" y="{draw.n(y)}" font-size="{draw.n(size)}" text-anchor="middle" fill="{INK}" '
        f'class="wb-en"><tspan fill="{color}">{escape(head)}</tspan>{escape(rest)}</text>'
    )


@page_type("vocab-cards")
def vocab_cards(ctx: PageContext) -> Built:
    params = ctx.page.params
    unit = str(params.get("unit", "Animals"))
    words = [str(w) for w in params.get("words", [])]
    problems = []
    ids = []
    for w in words:
        try:
            ids.append(picture_id(w))
        except KeyError:
            problems.append(f"no picture for «{w}»")
    cols = 2 if len(ids) <= 6 else 3 if len(ids) <= 9 else 4
    rows = -(-len(ids) // cols)
    cw, ch = (W - 4 * (cols - 1)) / cols, (194 - 4 * (rows - 1)) / rows
    body = [
        text(
            f"{unit} · {UNIT_AR.get(unit, '')}", W / 2, 6, 5, cls="wb-muted", color=ctx.style.deep, rtl=False
        )
    ]
    coloring = unit == "Colors"
    for k, pid in enumerate(ids):
        row, col = divmod(k, cols)
        x, y = col * (cw + 4), 10 + row * (ch + 4)
        body.append(card(x, y, cw, ch, r=6))
        size = min(cw - 10, ch - 22)
        body.append(pic(pid, x + (cw - size) / 2, y + 3, size, "line" if coloring else "color"))
        p = PICTURES[pid]
        body.append(en_word(p.word_en, x + cw / 2, y + ch - 10, min(7.0, cw / 8), ctx.style.color))
        body.append(text(p.word_ar, x + cw / 2, y + ch - 3, 3.6, cls="wb-muted", color="#676B83"))
        if coloring:
            body.append(
                draw.el(
                    "circle",
                    cx=x + cw - 6,
                    cy=y + 6,
                    r=3,
                    fill=p.palette.get("main", "#888"),
                    stroke=INK,
                    stroke_width=0.4,
                )
            )
    answer = [f"{unit}: " + ", ".join(PICTURES[i].word_en for i in ids)]
    return Built({"svg": svg(body)}, answer, problems)
