"""«دوسية التأسيس» KG1 thinking pages beyond KG2's: connecting what belongs together (a bird and its nest),
what we need something for (an umbrella and the rain), the order of a story, and the mixed end-of-year
connect page; classifying by kind (animals and fruit) and by habitat (land and sea). Six items a page."""

from __future__ import annotations

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_activity2 import STORY
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    fit_lines,
    glyph,
    hook,
    pic,
    picture_id,
    ring_at,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_kg1_activity import code_shape
from qamra_workbook.render.pages.workbook_math import group
from qamra_workbook.render.pages.workbook_review import compact
from qamra_workbook.render.pages.workbook_thinking import POOL
from qamra_workbook.render.pages.workbook_thinking2 import GROUP_WORDS
from qamra_workbook.render.registry import Built, PageContext, page_type

NEED = {"umbrella": "raindrop", "coat": "snowflake", "water": "sprout", "lamp": "moon"}
GROUPS = {
    "حيوانات": ("rabbit", "cat", "sheep", "cow", "horse"),
    "فواكه": ("apple", "banana", "strawberry", "grapes", "orange"),
    "البر": ("cat", "cow", "sheep", "horse", "rabbit"),
    "البحر": ("fish", "whale", "octopus"),
    "أحمر": ("apple", "strawberry", "tomato"),
    "أصفر": ("sun", "banana", "corn"),
    "أزرق": ("raindrop", "whale", "hat"),
}
BASKETS = {"أحمر": ("#E5604E", "#FFFFFF"), "أصفر": ("#F7C84A", INK), "أزرق": ("#5E86D6", "#FFFFFF")}
ORDER_AR = ("أولًا", "ثانيًا", "ثالثًا", "أخيرًا")


def columns(
    ctx: PageContext, right: list[str], left: list[str], order: list[int]
) -> tuple[list[str], list[str]]:
    """Cards in two columns (SVG snippets sized 40 mm, placed at @X @Y), with the answer lines."""
    body, key = [], []
    pitch = 204 / len(right)
    for i, (a, j) in enumerate(zip(right, order, strict=True)):
        cy = (i + 0.5) * pitch
        body.append(card(W - 46, cy - 21, 42, 42, r=6))
        body.append(a.replace("@X", draw.n(W - 44)).replace("@Y", draw.n(cy - 19)))
        body.append(hook(W - 50, cy))
        py = (j + 0.5) * pitch
        body.append(card(4, py - 21, 42, 42, r=6))
        body.append(left[j].replace("@X", draw.n(6)).replace("@Y", draw.n(py - 19)))
        body.append(hook(50, py))
        key.append(answer_line((W - 50, cy), (50, py)))
    return body, key


def picture_cell(picture: str) -> str:
    return pic(picture, 0, 0, 38).replace('x="0"', 'x="@X"', 1).replace('y="0"', 'y="@Y"', 1)


def glyph_cell(ctx: PageContext, char: str) -> str:
    shape = code_shape(char)
    scale, dx, dy = fit_lines(shape, 6, 6, 26, 26)
    return (
        f'<g transform="translate(@X @Y)">{glyph(shape, scale, dx, dy, color=ctx.style.deep, width=15)}</g>'
    )


def _deranged(ctx: PageContext, n: int, salt: str) -> list[int]:
    r = ctx.rng(salt)
    order = list(range(n))
    while any(i == j for i, j in enumerate(order)):
        r.shuffle(order)
    return order


@page_type("kg1-connect")
def kg1_connect(ctx: PageContext) -> Built:
    params = ctx.page.params
    mode = str(params.get("mode", "related"))
    words = [picture_id(str(w)) for w in params.get("words", [])]
    right: list[str]
    left: list[str]
    answer: list[str] = []
    if mode == "sequence":  # the story's pictures shuffled on the right, the numbers 1–4 in order on the left
        steps = int(params.get("steps", 4))
        story = list(STORY[:steps])
        shown = _deranged(ctx, steps, "sequence")  # shown[i]: which step sits in row i
        right = [picture_cell(story[j]) for j in shown]
        left = [
            f'<g transform="translate(@X @Y)">'
            f"{text(ctx.num(i + 1), 19, 26, 14, cls='wb-num', color=ctx.style.deep)}</g>"
            for i in range(steps)
        ]
        answer = [f"{ORDER_AR[i]}: {PICTURES[s].word_ar}" for i, s in enumerate(story)]
        body, key = columns(ctx, right, left, shown)
        return Built({"svg": svg(body + key)}, answer, [])
    if mode == "mixed-review":
        things = [("أ", "rabbit"), ("B", "ball"), (ctx.num(3), "apple"), ("ت", "apple")]
        right = [glyph_cell(ctx, c) for c, _ in things]
        left = [
            picture_cell("rabbit"),
            picture_cell("ball"),
            f'<g transform="translate(@X @Y)">{group("star", 3, 2, 4, 34, 30)}</g>',
            picture_cell("apple"),
        ]
        answer = ["أ ← أرنب", "B ← ball", f"{ctx.num(3)} ← ثلاث نجوم", "ت ← تفاحة"]
    else:
        partners = [NEED.get(w, "sun") for w in words] if mode == "need" else words[1::2]
        firsts = words if mode == "need" else words[0::2]
        right = [picture_cell(w) for w in firsts]
        left = [picture_cell(w) for w in partners]
        answer = [
            f"{PICTURES[a].word_ar} ← {PICTURES[b].word_ar}" for a, b in zip(firsts, partners, strict=True)
        ]
    order = _deranged(ctx, len(right), "connect")
    body, key = columns(ctx, right, [left[order.index(j)] for j in range(len(left))], order)
    return Built(
        {"svg": svg(body + key)}, answer, [] if len(right) >= 3 else ["a connect page needs 3+ pairs"]
    )


STORY_KG1 = {3: ("seed", "sprout", "flower"), 4: STORY}


@page_type("kg1-story-sequence")
def kg1_story_sequence(ctx: PageContext) -> Built:
    """Cut and paste a story in order: three numbered frames on top (seed, sprout, flower; four steps give
    the rain story), the same pictures shuffled below, big enough for small hands to cut and paste."""
    steps = int(ctx.page.params.get("steps", 3))
    story = STORY_KG1.get(steps)
    if story is None:
        return Built({"svg": svg([])}, None, [f"no story with {steps} steps"])
    r = ctx.rng("story")
    order = list(range(steps))
    while order == sorted(order):
        r.shuffle(order)
    cols = steps if steps <= 3 else 2
    rows = (steps + cols - 1) // cols
    fw = (W - 6 * (cols - 1) - 8) / cols if rows == 1 else 76.0
    fh = fw + 12 if rows == 1 else 38.0
    gap = 6.0

    def cell(k: int, top: float) -> tuple[float, float]:
        row, col = divmod(k, cols)
        return W - 4 - (col + 1) * fw - col * gap, top + row * (fh + gap)

    body = []
    for k in range(steps):
        x, y = cell(k, 6)
        body.append(card(x, y, fw, fh, r=5, fill="#FFFFFF", stroke="#B8B2A6", dash="2.4 1.6"))
        body.append(draw.el("circle", cx=x + fw - 6, cy=y + 6, r=4.5, fill=ctx.style.color))
        body.append(text(ctx.num(k + 1), x + fw - 6, y + 7.8, 4.6, cls="wb-num", color="#FFFFFF"))
        body.append(pic(story[k], x + 5, y + 10, fw - 10, class_="key-ring"))  # the number says the order
    cut_top = 6 + rows * (fh + gap) + 14
    body.append(
        text(
            "أَقُصُّ عَلى الخَطِّ المُتَقَطِّعِ وَأُلْصِقُ بِالتَّرْتيبِ", W - 6, cut_top - 4, 4.8, anchor="end", color=ctx.style.deep
        )
    )
    for k, i in enumerate(order):
        x, y = cell(k, cut_top)
        body.append(card(x, y, fw, fh - 8, r=0, fill="#FFFFFF", stroke=INK, dash="2.4 1.6", width=0.6))
        body.append(pic(story[i], x + 4, y + 2, min(fw - 8, fh - 12)))
    answer = ["الترتيب: " + " ← ".join(PICTURES[t].word_ar for t in story)]
    problems = [] if cut_top + rows * (fh + gap) <= 206 else ["the story frames do not fit"]
    return Built({"svg": svg(body)}, answer, problems)


@page_type("kg1-classify")
def kg1_classify(ctx: PageContext) -> Built:
    """Six pictures on top, two or three labelled boxes below (animals and fruit, land and sea, three colors):
    a line from each picture to its group."""
    params = ctx.page.params
    names = [str(c) for c in params.get("categories", params.get("colors", ["حيوانات", "فواكه"]))][:3]
    problems = [f"no group «{n}»" for n in names if n not in GROUPS]
    r = ctx.rng("classify")
    per = 6 // len(names)
    items = [(t, g) for g, name in enumerate(names) if name in GROUPS for t in r.sample(GROUPS[name], per)]
    r.shuffle(items)
    body, key = [], []
    step = W / 3
    for k, (thing, _) in enumerate(items):
        row, col = divmod(k, 3)
        cx, cy = W - (col + 0.5) * step, 26 + row * 56
        body.append(card(cx - 23, cy - 24, 46, 48, r=6))
        body.append(pic(thing, cx - 20, cy - 21, 40))
        body.append(hook(cx, cy + 25))
    anchors = []
    gw = W / len(names)
    for g, name in enumerate(names):
        cx = W - (g + 0.5) * gw
        body.append(card(cx - gw / 2 + 6, 138, gw - 12, 66, r=8, fill=ctx.style.tint, stroke="none"))
        if name in BASKETS:
            fill, ink = BASKETS[name]
            top, bottom = 160, 196
            basket = draw.polyline([(cx - 24, top), (cx + 24, top), (cx + 18, bottom), (cx - 18, bottom)])
            body.append(
                draw.el(
                    "path", d=basket + " Z", fill=fill, stroke=INK, stroke_width=0.8, stroke_linejoin="round"
                )
            )
            body.append(text(GROUP_WORDS.get(name, name), cx, 183, 6.4, cls="wb-title", color=ink))
        else:
            body.append(text(GROUP_WORDS.get(name, name), cx, 158, 7, cls="wb-title", color=ctx.style.deep))
            if name in GROUPS:
                body.append(pic(GROUPS[name][-1], cx - 14, 164, 28, "line"))
        body.append(hook(cx, 138))
        anchors.append((cx, 138))
    for k, (_, g) in enumerate(items):
        row, col = divmod(k, 3)
        key.append(answer_line((W - (col + 0.5) * step, 26 + row * 56 + 25), anchors[g]))
    answer = [
        f"{n}: " + "، ".join(PICTURES[t].word_ar for t, h in items if h == g) for g, n in enumerate(names)
    ]
    return Built({"svg": svg(body + key)}, compact(answer), problems)


@page_type("kg1-memory")
def kg1_memory(ctx: PageContext) -> Built:
    """Five pictures to look at; cover them, then one has vanished from the second row: circle it among
    three."""
    count = int(ctx.page.params.get("items", 5))
    r = ctx.rng("memory")
    seen = r.sample(POOL, count)
    gone = r.randrange(count)
    options = [seen[gone], *r.sample([p for p in POOL if p not in seen], 2)]
    r.shuffle(options)
    step = (W - 16) / count
    size = min(30.0, step - 3)
    body = [card(0, 0, W, 66, r=8, fill="#FFF6F2")]
    body.append(text("أَنْظُرُ جَيِّدًا وَأَتَذَكَّرُ", W - 8, 10, 5, anchor="end", color=ctx.style.deep))
    slots = [W - 8 - (k + 1) * step + (step - size) / 2 for k in range(count)]
    for x, thing in zip(slots, seen, strict=True):
        body.append(pic(thing, x, 22, size))
    body.append(
        draw.path(
            draw.d_path(("M", (2, 74)), ("L", (W - 2, 74))),
            stroke="#B8B2A6",
            width=0.7,
            stroke_dasharray="3 2",
        )
    )
    body.append(text("أُغَطّي الصُّوَرَ بِوَرَقَةٍ، ثُمَّ أَنْظُرُ هُنا", W - 8, 86, 5, anchor="end", color=ctx.style.deep))
    body.append(card(0, 92, W, 50, r=8))
    for k, (x, thing) in enumerate(zip(slots, seen, strict=True)):
        if k == gone:
            body.append(card(x, 102, size, size, r=5, fill="#FFFDF6", stroke="#B8B2A6", dash="2 1.6"))
            body.append(text("؟", x + size / 2, 124, 11, cls="wb-title", color="#B8B2A6"))
        else:
            body.append(pic(thing, x, 102, size))
    body.append(text("أَيُّ صورَةٍ اخْتَفَتْ؟ أُحَوِّطُها", W - 8, 156, 5, anchor="end", color=ctx.style.deep))
    for k, thing in enumerate(options):
        cx = W - 36 - k * 58
        body.append(card(cx - 24, 162, 48, 40, r=6))
        body.append(pic(thing, cx - 17, 165, 34))
        if thing == seen[gone]:
            body.append(ring_at(cx, 182, 27, 22))
    answer = [f"الصورة التي اختفت: {PICTURES[seen[gone]].word_ar}"]
    return Built({"svg": svg(body)}, answer, [] if len(set(options)) == 3 else ["the choices repeat"])


__all__ = ["INK", "kg1_classify", "kg1_connect"]
