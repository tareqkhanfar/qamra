"""«دوسية التأسيس» Volume 3 adding and subtracting with pictures within 10 (Addendum 5 §3): count all, the
number sentence, making ten, a picture story, the number line and choosing the operation. The picture rows and
the number sentences read left to right, like the numerals in them (and like the number line); the story
around them is Arabic text, right to left."""

from __future__ import annotations

import random

from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_common import INK, W, card, svg, text
from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES
from qamra_workbook.render.pages.workbook_math3 import (
    MINUS,
    PLUS,
    Token,
    answer_box,
    crossed_group,
    group_pics,
    ltr,
    number_line,
    sentence_row,
    sign,
)
from qamra_workbook.render.registry import Built, PageContext, page_type

# the story pictures → (one, two, three to ten), vowelled; all feminine nouns (draft: educator review)
FORMS = {
    "ball": ("كُرَة", "كُرَتان", "كُرات"),
    "fish": ("سَمَكَة", "سَمَكَتان", "سَمَكات"),
    "apple": ("تُفّاحَة", "تُفّاحَتان", "تُفّاحات"),
    "flower": ("زَهْرَة", "زَهْرَتان", "زَهَرات"),
    "duck": ("بَطَّة", "بَطَّتان", "بَطّات"),
    "star": ("نَجْمَة", "نَجْمَتان", "نُجوم"),
}
STORY_THINGS = tuple(FORMS)


def pairs_of(
    r: random.Random, top: int, rows: int, subtract: bool = False, least: int = 1
) -> list[tuple[int, int]]:
    """`rows` different problems whose answers stay within `top` (a − b > 0 when subtracting); the first
    number is at least `least`."""
    out: list[tuple[int, int]] = []
    for _ in range(500):
        if len(out) == rows:
            break
        if subtract:
            a = r.randint(max(2, least), top)
            b = r.randint(1, a - 1)
        else:
            a = r.randint(least, top - 1)
            b = r.randint(1, top - a)
        if (a, b) not in out:
            out.append((a, b))
    return out


def counted(ctx: PageContext, n: int, thing: str) -> str:
    """«كُرَة واحِدَة»، «كُرَتان»، «٣ كُرات»: the noun that goes with the number."""
    one, two, many = FORMS[thing]
    if n == 1:
        return f"{one} واحِدَة"
    return two if n == 2 else f"{ctx.num(n)} {many}"


def story_text(ctx: PageContext, a: int, b: int, thing: str, subtract: bool) -> str:
    more = "واحِدَة أُخْرى" if b == 1 else f"{ctx.num(b)} أُخْرى"
    gave = "واحِدَة" if b == 1 else ctx.num(b)
    if subtract:
        return f"كانَ عِنْدي {counted(ctx, a, thing)}، وَأَعْطَيْتُ {gave} مِنْها لِصَديقي. كَمْ بَقِيَ عِنْدي؟"
    return f"كانَ عِنْدي {counted(ctx, a, thing)}، وَأَخَذْتُ {more}. كَمْ أَصْبَحَ عِنْدي؟"


def divider(x: float, y0: float, y1: float) -> str:
    return draw.path(
        draw.d_path(("M", (x, y0)), ("L", (x, y1))), stroke="#D8C9AC", width=0.6, stroke_dasharray="1.6 1.4"
    )


def sentence_tokens(a: int, b: int, subtract: bool) -> list[Token]:
    total = a - b if subtract else a + b
    return [("num", a), ("op", MINUS if subtract else PLUS), ("num", b), ("eq", ""), ("box", total)]


def sentence_key(ctx: PageContext, a: int, b: int, subtract: bool) -> str:
    total = a - b if subtract else a + b
    return ltr(f"{ctx.num(a)} {'−' if subtract else '+'} {ctx.num(b)} = {ctx.num(total)}")


def _story_rows(ctx: PageContext, r: random.Random, subtract: bool) -> tuple[list[str], list[str]]:
    """Two picture stories, each with its pictures, its number sentence and an answer box (draft: educator
    review). The pictures and the sentence read left to right; the story is Arabic."""
    body, answer = [], []
    for i, (a, b) in enumerate(pairs_of(r, 10, 2, subtract, least=3)):
        y = i * 102
        thing = STORY_THINGS[(i + 3 * int(subtract)) % len(STORY_THINGS)]
        body.append(card(0, y + 1, W, 98, r=7))
        body.append(text(story_text(ctx, a, b, thing, subtract), W - 6, y + 13, 4.8, anchor="end", color=INK))
        if subtract:
            body.append(crossed_group(thing, a, b, 10, y + 22, 112, 46))
        else:
            body.append(group_pics(thing, a, 8, y + 22, 62, 46))
            body.append(sign(PLUS, 77, y + 46, 8))
            body.append(group_pics(thing, b, 84, y + 22, 62, 46))
        body.append(
            draw.path(draw.d_path(("M", (8, y + 72)), ("L", (W - 8, y + 72))), stroke="#EFE5D2", width=0.5)
        )
        body.append(sentence_row(ctx, sentence_tokens(a, b, subtract), 14, y + 85, 12))
        answer.append(sentence_key(ctx, a, b, subtract))
    return body, answer


@page_type("picture-add")
def picture_add(ctx: PageContext) -> Built:
    params = ctx.page.params
    top = int(params.get("max", 5))
    mode = str(params.get("mode", "count"))
    r = ctx.rng(f"add-{mode}")
    body: list[str] = []
    answer: list[str] = []
    if mode == "story":
        body, answer = _story_rows(ctx, r, False)
    elif mode == "number-line":
        for i, (a, b) in enumerate(pairs_of(r, 10, 3)):
            y = i * 68
            body.append(card(0, y + 1, W, 64, r=7))
            body.append(sentence_row(ctx, sentence_tokens(a, b, False), 14, y + 15, 12))
            body.append(number_line(12, y + 42, W - 24, 10, ctx, jumps=(a, b)))
            answer.append(sentence_key(ctx, a, b, False))
    elif mode == "make-ten":
        for i, k in enumerate(r.sample(range(1, 10), 4)):
            y = i * 51
            body.append(card(0, y + 1, W, 47, r=7))
            for j in range(10):
                cx, cy = 16 + (j % 5) * 15, y + 14 + (j // 5) * 17
                body.append(
                    draw.el(
                        "circle",
                        cx=cx,
                        cy=cy,
                        r=6.2,
                        fill=ctx.style.color if j < k else "#FFFFFF",
                        stroke=INK,
                        stroke_width=0.6,
                    )
                )
            tokens: list[Token] = [("box", k), ("op", PLUS), ("box", 10 - k), ("eq", ""), ("num", 10)]
            body.append(sentence_row(ctx, tokens, 98, y + 24, 13))
            answer.append(ltr(f"{ctx.num(k)} + {ctx.num(10 - k)} = {ctx.num(10)}"))
    elif mode == "choose-operation":
        for i in range(3):
            y = i * 68
            subtract = i % 2 == 1
            a, b = pairs_of(r, 10, 1, subtract)[0]
            thing = GROUP_PICTURES[(i + 5) % len(GROUP_PICTURES)]
            body.append(card(0, y + 1, W, 64, r=7))
            if subtract:
                body.append(crossed_group(thing, a, b, 10, y + 4, 100, 38))
            else:
                body.append(group_pics(thing, a, 8, y + 4, 56, 38))
                body.append(sign(PLUS, 70, y + 23))
                body.append(group_pics(thing, b, 76, y + 4, 56, 38))
            total = a - b if subtract else a + b
            tokens = [
                ("num", a),
                ("choice", MINUS if subtract else PLUS),
                ("num", b),
                ("eq", ""),
                ("box", total),
            ]
            body.append(sentence_row(ctx, tokens, 14, y + 53, 12))
            answer.append(sentence_key(ctx, a, b, subtract))
    else:
        for i, (a, b) in enumerate(pairs_of(r, top, 4)):
            y = i * 51
            thing = GROUP_PICTURES[(i + 1) % len(GROUP_PICTURES)]
            body.append(card(0, y + 1, W, 47, r=7))
            if mode == "number-sentence":
                body.append(group_pics(thing, a, 4, y + 4, 46, 42))
                body.append(sign(PLUS, 55, y + 24))
                body.append(group_pics(thing, b, 60, y + 4, 46, 42))
                body.append(divider(112, y + 8, y + 40))
                body.append(sentence_row(ctx, sentence_tokens(a, b, False), 122, y + 24, 11))
            else:
                body.append(group_pics(thing, a, 6, y + 4, 56, 42))
                body.append(sign(PLUS, 68, y + 24))
                body.append(group_pics(thing, b, 74, y + 4, 56, 42))
                body.append(sign("=", 138, y + 24))
                body.append(answer_box(162, y + 24, a + b, ctx, 22, 24))
            answer.append(sentence_key(ctx, a, b, False))
    return Built({"svg": svg(body)}, answer, [])


@page_type("picture-subtract")
def picture_subtract(ctx: PageContext) -> Built:
    params = ctx.page.params
    top = int(params.get("max", 5))
    mode = str(params.get("mode", "count"))
    r = ctx.rng(f"sub-{mode}")
    if mode == "story":
        body, answer = _story_rows(ctx, r, True)
        return Built({"svg": svg(body)}, answer, [])
    body, answer = [], []
    for i, (a, b) in enumerate(pairs_of(r, top, 4, True)):
        y = i * 51
        thing = GROUP_PICTURES[(i + 2) % len(GROUP_PICTURES)]
        body.append(card(0, y + 1, W, 47, r=7))
        if mode == "number-sentence":
            body.append(crossed_group(thing, a, b, 4, y + 4, 92, 42))
            body.append(divider(102, y + 8, y + 40))
            body.append(sentence_row(ctx, sentence_tokens(a, b, True), 112, y + 24, 11))
        else:
            body.append(crossed_group(thing, a, b, 6, y + 4, 100, 42))
            body.append(sign("=", 116, y + 24))
            body.append(answer_box(146, y + 24, a - b, ctx, 22, 24))
        answer.append(sentence_key(ctx, a, b, True))
    return Built({"svg": svg(body)}, answer, [])
