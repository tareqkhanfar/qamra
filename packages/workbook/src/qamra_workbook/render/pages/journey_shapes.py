"""Journey shapes, colours, patterns and smart colouring (Addendum 6 §4.4–4.6): a shape's journey (meet,
trace, find, colour, draw), a colour's journey, shapes hidden in a garden, pattern trains and necklaces, the
child's own pattern, and colouring by a rule.
The printed colour models are why this book is full colour only."""

from __future__ import annotations

from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.journey_words import COLORS
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_hand import shape_of
from qamra_workbook.render.pages.journey_kit import SOFT, H, W, card, dots_mark, picture, pid, star, svg, text
from qamra_workbook.render.pages.workbook_pen import traced
from qamra_workbook.render.registry import Built, PageContext, page_type

SHAPE_NAMES = {
    "circle": "الدائرة",
    "square": "المربع",
    "triangle": "المثلث",
    "rectangle": "المستطيل",
    "star": "النجمة",
    "heart": "القلب",
}
STEP = "#676B83"


def filled(kind: str, cx: float, cy: float, s: float, fill: str, css: str = "") -> str:
    attrs: dict[str, str | float] = {"class_": css} if css else {}
    return draw.el(
        "path",
        d=shape_of(kind, cx, cy, s).d + " Z",
        fill=fill,
        stroke="#2B2E4A",
        stroke_width=0.9,
        stroke_linejoin="round",
        **attrs,
    )


def colored(word: str, x: float, y: float, size: float, color: str) -> str:
    """A line-art picture to colour, with its coloured version for the answer key."""
    return picture(word, x, y, size, "line") + picture(word, x, y, size, main=color).replace(
        "<svg", '<svg class="key-ring"', 1
    )


@page_type("shape-journey")
def shape_journey(ctx: PageContext) -> Built:
    """One shape's six steps on a page: meet it (name), trace it (three sizes), find it in pictures and colour
    them, then draw it alone."""
    kind = str(ctx.page.params.get("shape", "circle"))
    examples = [str(w) for w in ctx.page.params.get("examples", [])]
    problems = [] if kind in SHAPE_NAMES and examples else ["a known shape and pictures that have it"]
    body = [card(0, 0, W, 78, r=10)]
    body.append(card(W - 62, 6, 56, 66, r=8, fill=ctx.style.tint, stroke="none"))
    body.append(filled(kind, W - 34, 32, 36, ctx.style.color))
    body.append(text(SHAPE_NAMES.get(kind, kind), W - 34, 66, 7.5, cls="wb-title", color=ctx.style.deep))
    sizes = (30.0, 24.0, 18.0) if kind == "rectangle" else (38.0, 30.0, 22.0)
    for k, size in enumerate(sizes):
        body.append(
            traced(
                shape_of(kind, (W - 92, W - 136, W - 166)[k], 40, size),
                spacing=3.8,
                r=1.1,
                start=2.3,
                example=k == 0 and ctx.page.example,
            )
        )
    body.append(card(0, 86, W, 70, r=10))
    size = min(56.0, (W - 20) / max(len(examples), 1) - 8)
    for k, w in enumerate(examples):
        x = W - 12 - (k + 1) * (W - 24) / len(examples) + ((W - 24) / len(examples) - size) / 2
        body.append(colored(w, x, 93, size, ctx.style.color))
    body.append(card(0, 164, W, 40, r=10, fill=SOFT, stroke="#8C90A6", dash="3 2.4", width=0.7))
    body.append(picture("crayons", W - 36, 168, 30))
    return Built(
        {"svg": svg(body)},
        [f"{SHAPE_NAMES.get(kind, kind)} في: " + "، ".join(PICTURES[pid(w)].word_ar for w in examples)],
        problems,
    )


def crayon(x: float, y: float, color: str, w: float = 44.0) -> str:
    """A big crayon pointing left, in the colour to use."""
    tip = draw.polyline([(x + 10, y), (x, y + 7), (x + 10, y + 14)]) + " Z"
    return (
        draw.el(
            "rect", x=x + 10, y=y, width=w, height=14, rx=3, fill=color, stroke="#2B2E4A", stroke_width=0.7
        )
        + draw.el("path", d=tip, fill=color, stroke="#2B2E4A", stroke_width=0.7, stroke_linejoin="round")
        + draw.el("rect", x=x + w - 4, y=y + 2, width=4, height=10, rx=1, fill="#FFFFFF", opacity=0.6)
    )


@page_type("color-journey")
def color_journey(ctx: PageContext) -> Built:
    """Meet a colour (a crayon and its name), then colour the things that have it; or several colours, one row
    each (`colors` with `items` in the same order)."""
    params = ctx.page.params
    names = [str(c) for c in params.get("colors", [params.get("color", "red")])]
    items = [str(w) for w in params.get("items", [])]
    problems = [f"no colour {c!r}" for c in names if c not in COLORS]
    if problems:
        return Built({"svg": svg([])}, None, problems)
    body, key = [], []
    if len(names) == 1:
        color, name, _ = COLORS[names[0]]
        body.append(card(0, 0, W, 64, r=10, fill=SOFT, stroke="none"))
        body.append(crayon(W - 120, 20, color, 70))
        body.append(text(name, 50, 42, 13, cls="wb-title", color="#1C2140"))
        from qamra_workbook.render.pages.journey_think import grid

        for w, (x, y, size) in zip(items, grid(len(items), 2, h=H - 72), strict=True):
            body.append(card(x - 4, 72 + y - 4, size + 8, size + 8, r=8))
            body.append(colored(w, x, 72 + y, size, color))
            body.append(
                draw.el(
                    "circle",
                    cx=x + size - 3,
                    cy=72 + y + 3,
                    r=4.5,
                    fill=color,
                    stroke="#2B2E4A",
                    stroke_width=0.5,
                )
            )
        key.append(f"{name}: " + "، ".join(PICTURES[pid(w)].word_ar for w in items))
    else:
        pitch = H / len(names)
        for i, (c, w) in enumerate(zip(names, items, strict=True)):
            color, name, _ = COLORS[c]
            y = i * pitch
            body.append(card(0, y + 2, W, pitch - 6, r=8))
            body.append(crayon(W - 70, y + pitch / 2 - 16, color, 50))
            body.append(text(name, W - 36, y + pitch / 2 + 14, 7, cls="wb-title", color="#1C2140"))
            body.append(colored(w, 30, y + 6, pitch - 16, color))
            key.append(f"{PICTURES[pid(w)].word_ar}: {name}")
    return Built({"svg": svg(body)}, key)


# a garden made of shapes: (kind, cx, cy, size) in a 186 × 150 scene
GARDEN: list[tuple[str, float, float, float]] = [
    ("circle", 150, 26, 30),
    ("star", 30, 22, 24),
    ("square", 92, 100, 48),
    ("triangle", 92, 56, 52),
    ("rectangle", 92, 110, 30),
    ("heart", 158, 92, 26),
    ("circle", 40, 112, 14),
    ("star", 60, 36, 14),
]


@page_type("shape-hunt")
def shape_hunt(ctx: PageContext) -> Built:
    """Shapes hidden in a garden picture; the key at the bottom says each shape's colour."""
    legend = {str(k): str(v) for k, v in dict(ctx.page.params.get("key", {})).items()}
    body = [
        card(0, 0, W, 150, r=10, fill="#F4F9FD", stroke="none"),
        card(0, 128, W, 22, r=8, fill="#DDEFD6", stroke="none"),
    ]
    body.append(draw.path("M158 128 L158 106", stroke="#7E5236", width=2.2))
    counts: dict[str, int] = {}
    for kind, cx, cy, size in GARDEN:
        s = size * 0.55 if kind == "rectangle" else size
        body.append(filled(kind, cx, cy, s, "#FFFFFF"))
        if kind in legend:
            body.append(filled(kind, cx, cy, s, COLORS[legend[kind]][0], "key-ring"))
        counts[kind] = counts.get(kind, 0) + 1
    step = W / max(len(legend), 1)
    for k, (kind, c) in enumerate(legend.items()):
        cx = W - step * (k + 0.5)
        body.append(card(cx - step / 2 + 3, 158, step - 6, 44, r=8))
        body.append(filled(kind, cx, 176, 18, COLORS[c][0]))
        body.append(text(SHAPE_NAMES[kind], cx, 197, 4.8, cls="wb-label", color=STEP))
    key = [f"{SHAPE_NAMES[k]}: {ctx.num(counts.get(k, 0))}" for k in legend]
    return Built({"svg": svg(body)}, key, [f"no {k} in the garden" for k in legend if k not in counts])


def period_answer(seq: list[str]) -> tuple[int, list[str]]:
    """The pattern's period and the values of its blanks ("__")."""
    for p in range(2, 4):
        known = [(i, v) for i, v in enumerate(seq) if v != "__"]
        if all(v == seq[i % p] and seq[i % p] != "__" for i, v in known):
            return p, [seq[i % p] for i, v in enumerate(seq) if v == "__"]
    return 0, []


@page_type("pattern-train")
def pattern_train(ctx: PageContext) -> Built:
    """A train of pictures in a pattern, from right to left; the empty wagon waits for a sticker."""
    seq = [str(w) for w in ctx.page.params.get("sequence", [])]
    period, blanks = period_answer(seq)
    problems = [] if period and blanks else ["the train must repeat and have an empty wagon"]
    per_row = 3
    rows = (len(seq) + per_row - 1) // per_row
    size, pitch = 44.0, 170.0 / rows
    body = [
        card(W - 40, 22, 34, 36, r=6, fill="#E5604E", stroke="#2B2E4A", width=0.9),
        card(W - 34, 12, 12, 14, r=2, fill="#3D4262", stroke="none"),
    ]
    for k, w in enumerate(seq):
        row, col = divmod(k, per_row)
        x, y = W - 50 - (col + 1) * (size + 8), 10 + row * pitch
        track = y + size + 12
        if col == 0:
            body.append(draw.path(f"M8 {track} L{W - 8} {track}", stroke="#8C90A6", width=1.6))
        blank = w == "__"
        body.append(
            card(
                x,
                y,
                size,
                size + 4,
                r=5,
                fill="#FFFFFF",
                stroke="#8C90A6" if blank else "#E27D63",
                dash="3 2" if blank else "none",
                width=0.9,
            )
        )
        body += [
            draw.el("circle", cx=x + size * f, cy=y + size + 7, r=4.2, fill="#3D4262") for f in (0.25, 0.75)
        ]
        if blank:
            body.append(
                picture(blanks[0], x + 4, y + 4, size - 8).replace("<svg", '<svg class="key-ring"', 1)
            )
        else:
            body.append(picture(w, x + 4, y + 4, size - 8))
    key = [f"العربة الفارغة: {PICTURES[pid(blanks[0])].word_ar}"] if blanks else None
    return Built({"svg": svg(body)}, key, problems)


BEAD_COLORS = {"أحمر": "red", "أصفر": "yellow", "أزرق": "blue", "أخضر": "green"}


@page_type("bead-pattern")
def bead_pattern(ctx: PageContext) -> Built:
    """A necklace in a colour pattern: colour the empty beads to go on."""
    seq = [BEAD_COLORS.get(str(c), str(c)) for c in ctx.page.params.get("sequence", [])]
    period, blanks = period_answer(seq)
    problems = [] if period and blanks else ["the necklace must repeat and have empty beads"]
    n = len(seq)
    body = [draw.path(f"M{W - 6} 60 C{W - 10} 170 16 170 8 60", stroke="#8C90A6", width=1.2)]
    string = Stroke(f"M{W - 6} 60 C{W - 10} 170 16 170 8 60")
    for k, c in enumerate(seq):
        (x, y), _ = string.at((k + 0.5) / n)
        if c == "__":
            color = COLORS[seq[k % period]][0] if period else "#FFFFFF"
            body.append(
                draw.el(
                    "circle",
                    cx=x,
                    cy=y,
                    r=11,
                    fill="#FFFFFF",
                    stroke="#2B2E4A",
                    stroke_width=0.9,
                    stroke_dasharray="2.6 2",
                )
            )
            body.append(draw.el("circle", cx=x, cy=y, r=9.5, fill=color, class_="key-ring"))
        else:
            body.append(
                draw.el("circle", cx=x, cy=y, r=11, fill=COLORS[c][0], stroke="#2B2E4A", stroke_width=0.9)
            )
    key = ["الخرزات: " + "، ".join(COLORS[b][1] for b in blanks)]
    return Built({"svg": svg(body)}, key, problems)


@page_type("create-your-pattern")
def create_your_pattern(ctx: PageContext) -> Built:
    """A caterpillar with empty segments: the child makes a pattern with stickers or crayons."""
    slots = int(ctx.page.params.get("slots", 8))
    stickers = [str(s) for s in ctx.page.params.get("stickers", ["star", "heart"])]
    body = [card(0, 0, W, 44, r=10, fill=SOFT, stroke="none")]
    for k, s in enumerate(stickers):
        cx = W / 2 + (len(stickers) / 2 - k - 0.5) * 40
        body.append(filled(s, cx, 22, 24, ("#F7C84A", "#E97A98", "#5E86D6")[k % 3]))
    r = min(12.0, (W - 50) / slots / 2)
    y = 120
    body.append(
        draw.el("circle", cx=W - 20, cy=y - 4, r=r + 5, fill="#7DB46C", stroke="#2B2E4A", stroke_width=0.9)
    )
    body += [draw.el("circle", cx=W - 20 + dx, cy=y - 8, r=2, fill="#2B2E4A") for dx in (-4, 4)]
    for k in range(slots):
        cx = W - 44 - k * (2 * r + 2)
        cy = y + (4 if k % 2 else -2)
        body.append(
            draw.el(
                "circle",
                cx=cx,
                cy=cy,
                r=r,
                fill="#FFFFFF",
                stroke="#2B2E4A",
                stroke_width=0.9,
                stroke_dasharray="2.6 2",
            )
        )
        if ctx.page.example and k < len(stickers):
            body.append(filled(stickers[k], cx, cy, r * 1.3, ("#F7C84A", "#E97A98", "#5E86D6")[k % 3]))
    return Built({"svg": svg(body)})


def _coloring_answer(w: str, x: float, y: float, s: float, yes: bool) -> list[str]:
    out = [picture(w, x, y, s, "line")]
    if yes:
        out.append(picture(w, x, y, s).replace("<svg", '<svg class="key-ring"', 1))
    return out


@page_type("rule-coloring")
def rule_coloring(ctx: PageContext) -> Built:
    """Colour by a rule: only the big ones (`rule: big`), only `count` of them (`rule: count`), each shape in
    its key colour (`rule: key`), or only what belongs (`rule: category`, `take`)."""
    params = ctx.page.params
    rule = str(params.get("rule", "big"))
    body: list[str] = []
    key: list[str] = []
    problems: list[str] = []
    if rule == "big":
        things = [str(w) for w in params.get("pairs", [])]
        pitch = H / len(things)
        r = ctx.rng("big")
        for i, w in enumerate(things):
            y = i * pitch
            body.append(card(0, y + 2, W, pitch - 6, r=8))
            big_right = r.random() < 0.5
            for k, big in enumerate((big_right, not big_right)):
                s = (pitch - 12) if big else (pitch - 12) * 0.5
                cx = W * (0.72 if k == 0 else 0.28)
                body += _coloring_answer(w, cx - s / 2, y + pitch - 6 - s - 2, s, big)
        key.append("الكبيرة: " + "، ".join(PICTURES[pid(w)].word_ar for w in things))
    elif rule == "count":
        w, shown, count = (
            str(params.get("items", "apple")),
            int(params.get("shown", 5)),
            int(params.get("count", 3)),
        )
        problems += [] if 0 < count < shown else ["colour fewer than are shown"]
        body.append(card(W / 2 - 40, 0, 80, 40, r=10, fill=SOFT, stroke="none"))
        body.append(dots_mark(count, W / 2, 20))
        lines = (shown + 2) // 3
        size = min(52.0, (W - 20) / 3 - 8, (H - 56) / lines - 12)
        for k in range(shown):
            row, col = divmod(k, 3)
            x = W - 16 - (col + 1) * (size + 10)
            body += _coloring_answer(w, x, 56 + row * (size + 12), size, k < count)
        key.append(f"يلوّن {ctx.num(count)} فقط")
    elif rule == "key":
        legend = {str(k): str(v) for k, v in dict(params.get("key", {})).items()}
        parts = [
            ("square", 150, 110, 40),
            ("triangle", 150, 68, 40),
            ("square", 100, 110, 40),
            ("triangle", 100, 68, 40),
            ("square", 50, 110, 40),
            ("circle", 150, 140, 16),
            ("circle", 100, 140, 16),
            ("circle", 50, 140, 16),
            ("circle", 20, 70, 18),
        ]
        for kind, cx, cy, s in parts:
            body.append(filled(kind, cx, cy, s, "#FFFFFF"))
            if kind in legend:
                body.append(filled(kind, cx, cy, s, COLORS[legend[kind]][0], "key-ring"))
        for k, (kind, c) in enumerate(legend.items()):
            cx = W - 30 - k * 60
            body.append(card(cx - 26, 164, 52, 36, r=8))
            body.append(filled(kind, cx + 10, 182, 16, COLORS[c][0]))
            body.append(text(COLORS[c][1], cx - 12, 185, 4.6, cls="wb-label", color=STEP))
        key.append("، ".join(f"{SHAPE_NAMES[k]}: {COLORS[c][1]}" for k, c in legend.items()))
    else:
        items, yes = [str(w) for w in params.get("items", [])], {str(w) for w in params.get("take", [])}
        problems += [] if yes and yes < set(items) else ["some things belong and some do not"]
        size = min(54.0, (W - 20) / 3 - 10)
        for k, w in enumerate(items):
            row, col = divmod(k, 3)
            x, y = W - 12 - (col + 1) * (size + 10), 8 + row * (size + 24)
            body.append(card(x - 4, y - 4, size + 8, size + 8, r=8))
            body += _coloring_answer(w, x, y, size, w in yes)
        key.append("نلوّن: " + "، ".join(PICTURES[pid(w)].word_ar for w in items if w in yes))
    return Built({"svg": svg(body)}, key, problems)


@page_type("mirror-coloring")
def mirror_coloring(ctx: PageContext) -> Built:
    """Half the picture is coloured: colour the other half the same way."""
    w = pid(str(ctx.page.params.get("picture", "butterfly")))
    size = 170.0
    x, y = (W - size) / 2, 14.0
    color, line = PICTURES[w].inner("color"), PICTURES[w].inner("line")
    right = str(ctx.page.params.get("colored_half", "right")) == "right"

    def half(inner: str, on_right: bool, css: str = "") -> str:
        box = "50 0 50 100" if on_right else "0 0 50 100"
        attrs: dict[str, str | float] = {"class_": css} if css else {}
        return draw.el(
            "svg",
            inner,
            x=x + (size / 2 if on_right else 0),
            y=y,
            width=size / 2,
            height=size,
            viewBox=box,
            style="overflow: hidden",
            **attrs,
        )

    body = [
        card(0, 0, W, H, r=10),
        half(color, right),
        half(line, not right),
        half(color, not right, "key-ring"),
    ]
    body.append(
        draw.path(f"M{W / 2} 8 L{W / 2} {H - 8}", stroke="#C9B994", width=0.6, stroke_dasharray="2 2")
    )
    return Built({"svg": svg(body)}, ["النصفان متشابهان"])


@page_type("draw-myself")
def draw_myself(ctx: PageContext) -> Built:
    """A mirror frame to draw yourself in, and a box to sign with a fingerprint."""
    body = [
        draw.el("ellipse", cx=W / 2, cy=92, rx=78, ry=88, fill="#F2B33D", stroke="#9A620A", stroke_width=1),
        draw.el("ellipse", cx=W / 2, cy=92, rx=70, ry=80, fill="#FFFFFF", stroke="#9A620A", stroke_width=0.6),
    ]
    body += [star(W / 2 + dx, 8 + abs(dx) / 5, 5, "#F7C84A") for dx in (-36, 0, 36)]
    body.append(card(W / 2 - 30, 184, 60, 20, r=6, fill="#FFFFFF", stroke="#8C90A6", dash="3 2.4", width=0.7))
    body.append(text("بصمتي", W / 2 + 22, 197, 4.2, cls="wb-muted", color=STEP))
    return Built({"svg": svg(body)})
