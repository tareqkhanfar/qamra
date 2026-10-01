"""«دوسية التأسيس» Volume 2 thinking pages: sorting into three groups, which picture disappeared, connecting
things that go together, and patterns of three elements (ABC). Each has an answer key and checks."""

from __future__ import annotations

from qamra_workbook.pictures import PICTURES
from qamra_workbook.puzzles.coloring import Shape
from qamra_workbook.render import draw
from qamra_workbook.render.pages.thinking import SHAPE_COLORS, shape_kind
from qamra_workbook.render.pages.workbook_common import (
    W,
    answer_line,
    card,
    hook,
    pic,
    ring_at,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_review import compact
from qamra_workbook.render.pages.workbook_thinking import POOL, _deranged, two_columns
from qamra_workbook.render.registry import Built, PageContext, page_type

CATEGORIES = {
    "حيوانات": ("rabbit", "cat", "sheep", "cow", "dog"),
    "فواكه": ("apple", "banana", "strawberry", "grapes", "orange"),
    "أدوات": ("hammer", "scissors", "broom", "spoon", "key"),
}
# the group names as printed on the page (the plan's words are the keys)
GROUP_WORDS = {"حيوانات": "حَيَوانات", "فواكه": "فَواكِه", "أدوات": "أَدَوات", "البر": "البَرّ", "البحر": "البَحْر"}
GROUP_WORDS |= {"أحمر": "أَحْمَر", "أصفر": "أَصْفَر", "أزرق": "أَزْرَق"}
RELATED = (
    ("bee", "flower"),
    ("bird", "nest"),
    ("key", "door"),
    ("umbrella", "raindrop"),
    ("hen", "egg"),
    ("rabbit", "carrot"),
    ("spoon", "plate"),
)


@page_type("classify-category")
def classify_category(ctx: PageContext) -> Built:
    """Nine pictures on top, three labelled boxes below: a line from each picture to its group."""
    r = ctx.rng("classify")
    groups = list(CATEGORIES)
    items = [(t, g) for g, name in enumerate(groups) for t in r.sample(CATEGORIES[name], 3)]
    r.shuffle(items)
    body, key = [], []
    step = W / 5
    for k, (thing, _) in enumerate(items):
        row, col = divmod(k, 5)
        cx, cy = W - (col + 0.5) * step, 22 + row * 44
        body.append(card(cx - 17, cy - 19, 34, 38, r=5))
        body.append(pic(thing, cx - 15, cy - 17, 30))
        body.append(hook(cx, cy + 20))
    gw = W / 3
    anchors = []
    for g, name in enumerate(groups):
        cx = W - (g + 0.5) * gw
        body.append(card(cx - gw / 2 + 4, 140, gw - 8, 60, r=8, fill=ctx.style.tint, stroke="none"))
        body.append(text(GROUP_WORDS.get(name, name), cx, 158, 6.4, cls="wb-title", color=ctx.style.deep))
        body.append(pic(CATEGORIES[name][-1], cx - 13, 164, 26, "line"))
        body.append(hook(cx, 140))
        anchors.append((cx, 140))
    for k, (_, g) in enumerate(items):
        row, col = divmod(k, 5)
        key.append(answer_line((W - (col + 0.5) * step, 22 + row * 44 + 20), anchors[g]))
    answer = [
        f"{name}: " + "، ".join(PICTURES[t].word_ar for t, h in items if h == g)
        for g, name in enumerate(groups)
    ]
    return Built({"svg": svg(body + key)}, compact(answer), [])


@page_type("memory-gone")
def memory_gone(ctx: PageContext) -> Built:
    """Look at six pictures; under the fold, five of them are back: circle the one that disappeared."""
    count = int(ctx.page.params.get("items", 6))
    r = ctx.rng("memory")
    seen = r.sample(POOL, count)
    gone = r.choice(seen)
    body = [card(0, 0, W, 60, r=8, fill="#FFF6F2")]
    body.append(text("أَنْظُرُ جَيِّدًا وَأَتَذَكَّرُ", W - 8, 10, 5, anchor="end", color=ctx.style.deep))
    step = (W - 16) / count
    for k, thing in enumerate(seen):
        body.append(pic(thing, W - 8 - (k + 1) * step + (step - 24) / 2, 18, 24))
    body.append(
        draw.path(
            draw.d_path(("M", (2, 66)), ("L", (W - 2, 66))),
            stroke="#B8B2A6",
            width=0.7,
            stroke_dasharray="3 2",
        )
    )
    body.append(
        text("أُغَطّي الصُّوَرَ بِوَرَقَةٍ، ثُمَّ أَنْظُرُ: أَيُّها اخْتَفى؟", W - 8, 78, 5, anchor="end", color=ctx.style.deep)
    )
    left = [t for t in seen if t != gone]
    r.shuffle(left)
    body.append(card(0, 84, W, 48, r=7))
    step = (W - 16) / count
    for k, thing in enumerate(left):
        body.append(pic(thing, W - 8 - (k + 1) * step + (step - 30) / 2, 92, 30))
    body.append(text("أُحَوِّطُ الصّورَةَ الَّتي اخْتَفَتْ", W - 8, 148, 5, anchor="end", color=ctx.style.deep))
    others = r.sample([p for p in POOL if p not in seen], 2)
    choices = [gone, *others]
    r.shuffle(choices)
    for k, thing in enumerate(choices):
        cx = W - (k + 0.5) * W / 3
        body.append(card(cx - 21, 154, 42, 46, r=6))
        body.append(pic(thing, cx - 18, 158, 36))
        if thing == gone:
            body.append(ring_at(cx, 177, 24, 25))
    return Built({"svg": svg(body)}, [f"اختفت: {PICTURES[gone].word_ar}"], [])


@page_type("connect-related")
def connect_related(ctx: PageContext) -> Built:
    count = int(ctx.page.params.get("pairs", 5))
    r = ctx.rng("related")
    pairs = r.sample(RELATED, count)
    right = [a for a, _ in pairs]
    order = _deranged(r, count)
    left = [""] * count
    for i, j in enumerate(order):
        left[j] = pairs[i][1]
    body, key = two_columns(right, left, order)
    answer = [f"{PICTURES[a].word_ar} ← {PICTURES[b].word_ar}" for a, b in pairs]
    return Built({"svg": svg(body + key)}, answer, [])


TRIPLES = (
    ("shape:circle", "shape:square", "shape:triangle"),
    ("apple", "ball", "star"),
    ("shape:heart", "shape:star", "shape:circle"),
    ("duck", "fish", "flower"),
)


def _element(item: str, cx: float, cy: float, size: float) -> str:
    if item.startswith("shape:"):
        kind = shape_kind(item.removeprefix("shape:"))
        return draw.shape(
            Shape(kind, cx, cy, size * 0.8, size * 0.8), fill=SHAPE_COLORS.get(kind, "#F7C84A"), width=0.9
        )
    return pic(item, cx - size / 2, cy - size / 2, size)


def _name(item: str) -> str:
    names = {"circle": "دائرة", "triangle": "مثلث", "square": "مربع", "heart": "قلب", "star": "نجمة"}
    return names[item.removeprefix("shape:")] if item.startswith("shape:") else PICTURES[item].word_ar


@page_type("pattern-abc")
def pattern_abc(ctx: PageContext) -> Built:
    """Four rows of an ABC pattern (the first solved): six shown, then two to draw."""
    body, answer = [], []
    for i, triple in enumerate(TRIPLES):
        y = i * 51
        body.append(
            card(
                0,
                y + 1,
                W,
                47,
                r=7,
                fill="#FFFDF9" if i == 0 else "#FFFFFF",
                dash="2 1.4" if i == 0 else "none",
            )
        )
        slots = 8
        step = (W - 8) / slots
        size = min(step - 4, 22.0)
        for k in range(slots):
            cx, cy = W - 4 - (k + 0.5) * step, y + 24
            item = triple[k % 3]
            if k < 6 or i == 0:
                body.append(_element(item, cx, cy, size))
            else:
                body.append(
                    card(
                        cx - size / 2,
                        cy - size / 2,
                        size,
                        size,
                        r=4,
                        fill="#FFFFFF",
                        stroke=ctx.style.color,
                        dash="2 1.4",
                    )
                )
                body.append(
                    _element(item, cx, cy, size * 0.8).replace("<svg ", '<svg class="key-ring" ', 1)
                    if not item.startswith("shape:")
                    else _element(item, cx, cy, size * 0.8)
                    .replace("<path ", '<path class="key-ring" ', 1)
                    .replace("<ellipse ", '<ellipse class="key-ring" ', 1)
                    .replace("<rect ", '<rect class="key-ring" ', 1)
                )
        if i:
            answer.append(f"الصف {ctx.num(i)}: {_name(triple[0])} ثم {_name(triple[1])}")
    return Built({"svg": svg(body)}, answer, [])
