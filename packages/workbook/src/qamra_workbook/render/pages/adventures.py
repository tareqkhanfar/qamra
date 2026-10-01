"""«مغامراتي مع عائلتي» activity pages (Addendum 7 §6): free drawing, counting and comparing, sorting and
choosing, the observation journal, conversation and role cards, and price tags paid with Qamra play money.

Each builder reads the plan page's params and falls back to a complete page when a param is missing, so a
page never renders half-designed. Numbers go through `ctx.num` (the book's numerals: ١٢٣ or 123).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import scallop_d, strip_tashkeel
from qamra_workbook.puzzles.coloring import Shape
from qamra_workbook.render import art, draw
from qamra_workbook.render.pages import family_art, family_choose, family_count
from qamra_workbook.render.pages.family import uri
from qamra_workbook.render.pages.inserts import qamra_count
from qamra_workbook.render.pages.thinking import shape_kind
from qamra_workbook.render.registry import Built, PageContext, page_type

FRAMES = (
    "plain",
    "circle",
    "tray",
    "portrait",
    "cup",
    "landscape",
    "room",
    "words",
    "rules",
    "stage",
    "id-card",
)


def tray_svg(spots: int, extra: int) -> Markup:
    """A round serving tray seen from above, with a dashed place for each thing (the ⭐⭐ ones in gold)."""
    w, h = 150.0, 78.0
    body = [
        draw.el("ellipse", cx=w / 2, cy=h / 2 + 2, rx=73, ry=36, fill="#C98A4B"),
        draw.el("ellipse", cx=w / 2, cy=h / 2, rx=73, ry=36, fill="#E7B070"),
        draw.el("ellipse", cx=w / 2, cy=h / 2, rx=64, ry=29, fill="#F3CC93"),
        draw.el("ellipse", cx=w / 2 - 30, cy=h / 2 - 14, rx=16, ry=4, fill="#FFFFFF", opacity=0.35),
    ]
    total = spots + extra
    for i in range(total):
        row, k = (0, i) if i < (total + 1) // 2 else (1, i - (total + 1) // 2)
        per = (total + 1) // 2 if row == 0 else total - (total + 1) // 2
        x = w / 2 + (k - (per - 1) / 2) * 30
        y = h / 2 + (row - 0.5) * 24 if total > 3 else h / 2
        gold = i >= spots
        body.append(
            draw.el(
                "circle",
                cx=x,
                cy=y,
                r=11,
                fill="#FFF6E6",
                stroke="#B77A36" if not gold else "#E2A32A",
                stroke_width=0.7,
                stroke_dasharray="2 1.6",
            )
        )
    return draw.svg(w, h, "".join(body), "tray")


@page_type("drawing")
def drawing(ctx: PageContext) -> Built:
    """A big drawing space: plain (with the child cheering in a corner), inside a circle, or a memory tray
    whose missing thing the child draws."""
    params = ctx.page.params
    frame = str(params.get("frame", "plain"))
    problems = [] if frame in FRAMES else [f"no drawing frame {frame!r} (have {', '.join(FRAMES)})"]
    spots, extra = int(params.get("spots", 3)), int(params.get("challenge_spots", 0))
    data = {
        "frame": frame,
        "character": uri(ctx.assets.character),
        "tray": tray_svg(spots, extra) if frame == "tray" else "",
        "legend": [(1, ctx.num(spots)), (2, ctx.num(spots + extra))] if frame == "tray" and extra else [],
        "missing": ctx.text(str(params.get("missing", "ماذا اخْتَفى؟ {ارْسُمْهُ/ارْسُميهِ} هُنا"))),
        "caption": ctx.text(str(params.get("caption", "اسْمُ رَسْمَتي:"))),
        **frame_data(ctx, frame),
    }
    return Built(data, None, problems)


def layers_ar(n: int, ctx: PageContext) -> str:
    """«طبقة واحدة», «طبقتان», «٣ طبقات»."""
    if n == 1:
        return "طَبَقَةٌ واحِدَةٌ"
    return "طَبَقَتانِ" if n == 2 else f"{ctx.num(n)} {'طَبَقاتٍ' if 3 <= n <= 10 else 'طَبَقَةً'}"


def frame_data(ctx: PageContext, frame: str) -> dict[str, Any]:
    """What a frame draws besides the drawing space: the art around it and its labels (⭐ / ⭐⭐ parts)."""
    params = ctx.page.params
    labels = [ctx.text(str(x)) for x in params.get("labels", [])]
    match frame:
        case "portrait":
            return {"name": ctx.book.child.name, "star": family_art.corner_stars(), "date_label": "التّاريخُ"}
        case "cup":
            layers, more = int(params.get("layers", 2)), int(params.get("challenge_layers", 2))
            return {
                "art": family_art.cup_svg(layers, more),
                "legend": [(1, layers_ar(layers, ctx)), (2, layers_ar(layers + more, ctx))],
            }
        case "landscape":
            return {"art": family_art.landscape_svg()}
        case "stage":
            return {"art": family_art.stage_svg()}
        case "room":
            return {"art": family_art.room_svg(), "labels": labels or [ctx.text("ماذا يُساعِدُني عَلى الهُدوءِ؟")]}
        case "words":
            count, more = int(params.get("count", 1)), int(params.get("challenge", 2))
            return {
                "cards": [{"level": 1 if i < count else 2, "n": ctx.num(i + 1)} for i in range(count + more)],
                "labels": labels or ["الكَلِمَةُ:", ctx.text("جُمْلَتي:")],
            }
        case "rules":
            return {"labels": labels or ["القاعِدَةُ الأولى:", "القاعِدَةُ الثّانِيَةُ:", "كَيْفَ نَرْبَحُ النِّقاطَ؟"]}
        case "id-card":
            return {
                "name": ctx.book.child.name,
                "labels": labels or ["الاسْمُ", "مِهْنَتي", "أُساعِدُ النّاسَ بِـ"],
                "photo_hint": ctx.text("صورَتي وَأَنا {كَبيرٌ/كَبيرَةٌ}"),
            }
    return {}


# ---- counting ---------------------------------------------------------------------------------------------

COLORS = {  # a color hunt's colors: name, paint
    "red": ("أَحْمَرُ", "#E4675A"),
    "yellow": ("أَصْفَرُ", "#F7C84A"),
    "blue": ("أَزْرَقُ", "#4F8BC9"),
    "green": ("أَخْضَرُ", "#5DAF4A"),
    "orange": ("بُرْتُقالِيٌّ", "#F39A3D"),
    "purple": ("بَنَفْسَجِيٌّ", "#9376CF"),
}
FRUITS = ("apple", "orange", "banana", "strawberry", "tomato", "carrot", "grapes")


def group(picture_id: str, count: int, w: float = 50, h: float = 30) -> Markup:
    """`count` pictures in rows of up to five, as they would sit in a basket."""
    rows = [min(5, count - k) for k in range(0, count, 5)]
    size = min(w / (max(rows) + 0.4), h / (len(rows) + 0.3), h * 0.62)
    inner = picture(picture_id).inner("color")
    body = []
    for r, n in enumerate(rows):
        y = h / 2 + (r - (len(rows) - 1) / 2) * size * 0.95 - size / 2
        for k in range(n):
            x = w / 2 + (k - (n - 1) / 2) * size * 1.02 - size / 2
            body.append(
                draw.el(
                    "svg",
                    inner,
                    x=x,
                    y=y,
                    width=size,
                    height=size,
                    viewBox="0 0 100 100",
                    data_count_item=picture_id,
                )
            )
    return draw.svg(w, h, "".join(body), "group")


def compare_rows(ctx: PageContext) -> list[dict[str, Any]]:
    """Two baskets per row: two rows up to 5 (⭐) and one up to 10 (⭐⭐); the counts never tie."""
    r = ctx.rng("compare")
    fruits = list(FRUITS)
    r.shuffle(fruits)
    rows = []
    for i, top in enumerate((5, 5, 10)):
        low = 1 if top == 5 else 5
        a, b = r.sample(range(low, top + 1), 2)
        rows.append(
            {
                "level": 1 if top == 5 else 2,
                "baskets": [
                    {"art": group(fruits[2 * i], a), "count": a},
                    {"art": group(fruits[2 * i + 1], b), "count": b},
                ],
                "more": 0 if a > b else 1,
                "diff": ctx.num(abs(a - b)),
            }
        )
    return rows


@page_type("counting")
def counting(ctx: PageContext) -> Built:
    """Count and compare: which basket has more (`mode: compare`, the default), or a tally chart where the
    child colors a square for each thing found, per color (`mode: tally`)."""
    params = ctx.page.params
    mode = str(params.get("mode", "compare"))
    if mode in family_count.MODES:  # pictures, things, table, money, change (the whole book's pages)
        return family_count.more_counting(ctx, mode)
    problems = [] if mode in ("compare", "tally") else [f"no counting mode {mode!r} (compare, tally)"]
    data: dict[str, Any] = {"mode": mode}
    if mode == "tally":
        colors = [str(c) for c in params.get("colors", ["red", "yellow", "blue"])]
        extra = [str(c) for c in params.get("challenge_colors", ["green"])]
        problems += [f"no color {c!r}" for c in [*colors, *extra] if c not in COLORS]
        squares = int(params.get("squares", 6))
        data["columns"] = [
            {"name": COLORS[c][0], "paint": COLORS[c][1], "level": 1 if c in colors else 2}
            for c in [*colors, *extra]
            if c in COLORS
        ]
        data["squares"] = list(range(squares))
        data["question"] = ctx.text(str(params.get("question", "أَيُّ لَوْنٍ أَكْثَرُ؟ {ضَعْ/ضَعي} دائِرَةً حَوْلَهُ")))
    else:
        data["rows"] = compare_rows(ctx)
        data["star_hint"] = ctx.text("{ضَعْ/ضَعي} نَجْمَةً هُنا")
    answer = [
        f"السلة الأكثر: {'اليمنى' if row['more'] == 0 else 'اليسرى'} (فرق {row['diff']})"
        for row in data.get("rows", [])
    ]
    return Built(data, answer or None, problems)


# ---- sorting and choosing -------------------------------------------------------------------------------

# a group: its label, how it is drawn (a shape's house, or a basket with an icon), its things; `open`: a
# choice with no single right answer («لا توجد إجابة واحدة صحيحة دائمًا»), so no answer key
SORT_GROUPS: dict[str, dict[str, Any]] = {
    "circle": {"label": "دائِرَةٌ", "shape": "circle", "items": ["plate", "clock", "orange"]},
    "square": {"label": "مُرَبَّعٌ", "shape": "square", "items": ["gift", "window"]},
    "triangle": {"label": "مُثَلَّثٌ", "shape": "triangle", "items": ["watermelon"]},
    "rectangle": {"label": "مُسْتَطيلٌ", "shape": "rectangle", "items": ["door", "book"]},
    "healthy": {
        "label": "صِحِّيٌّ",
        "icon": "heart",
        "color": "#E4769D",
        "items": ["apple", "carrot"],
        "open": True,
    },
    "needed": {
        "label": "نَحْتاجُهُ",
        "icon": "check",
        "color": "#2FA36B",
        "items": ["milk", "bread"],
        "open": True,
    },
    "not-needed": {
        "label": "لا نَحْتاجُهُ اليَوْمَ",
        "icon": "cross",
        "color": "#8A8FA8",
        "items": ["candy", "soda"],
        "open": True,
    },
    # the whole book's groups: fruit colors, the weather, the time of day, toy boxes, jobs and their tools
    "red": {"label": "أَحْمَرُ", "paint": "#E4675A", "items": ["apple", "strawberry"]},
    "yellow": {"label": "أَصْفَرُ", "paint": "#F7C84A", "items": ["banana", "lemon"]},
    "orange": {"label": "بُرْتُقالِيٌّ", "paint": "#F39A3D", "items": ["orange"]},
    "green": {"label": "أَخْضَرُ", "paint": "#8DBF4A", "items": ["pear"]},
    "sunny": {"label": "مُشْمِسٌ", "pic": "sun", "items": ["sun-hat"]},
    "rainy": {"label": "ماطِرٌ", "pic": "umbrella", "items": ["boots"]},
    "windy": {"label": "عاصِفٌ", "pic": "wind", "items": ["kite"]},
    "cold": {"label": "بارِدٌ", "pic": "snowflake", "items": ["scarf"]},
    "morning": {"label": "الصَّباحُ", "pic": "sun", "items": ["backpack", "bread"]},
    "evening": {"label": "المَساءُ", "pic": "moon", "items": ["bed", "book"]},
    "blocks": {"label": "المُكَعَّباتُ", "chip": "blocks", "color": "#F08A3E", "items": ["blocks", "dice"]},
    "dolls": {"label": "الدُّمى", "chip": "doll", "color": "#E4769D", "items": ["doll", "teddy"]},
    "cars": {"label": "السَّيّاراتُ", "chip": "car", "color": "#2E9FD6", "items": ["car", "boat"]},
    "doctor": {"label": "الطَّبيبَةُ", "bust": "doctor", "items": ["stethoscope"]},
    "baker": {"label": "الخَبّازُ", "bust": "baker", "items": ["bread"]},
    "farmer": {"label": "المُزارِعُ", "bust": "farmer", "items": ["watering-can"]},
    "teacher": {"label": "المُعَلِّمَةُ", "bust": "teacher", "items": ["book"]},
    "barber": {"label": "الحَلّاقُ", "bust": "barber", "items": ["scissors"]},
    "builder": {"label": "البَنّاءُ", "bust": "builder", "items": ["hammer"]},
}
PAIRS_MAX = 6  # a page of one-to-one pairs (a job and its tool) may show up to six groups


def group_mark(ctx: PageContext, spec: dict[str, Any]) -> Markup:
    """A group's sign: the shape inside a little house, or the basket's icon."""
    if "shape" in spec:
        target = Shape(
            shape_kind(spec["shape"]),
            20,
            23,
            17 if spec["shape"] != "rectangle" else 21,
            14 if spec["shape"] == "rectangle" else 17,
        )
        roof = draw.el(
            "path",
            d="M3 16 L20 3 L37 16 L37 38 L3 38 Z",
            fill="#FFFFFF",
            stroke=ctx.style.color,
            stroke_width=1.3,
            stroke_linejoin="round",
        )
        return draw.svg(
            40,
            40,
            roof + draw.shape(target, fill=ctx.style.tint, stroke=ctx.style.deep, width=1.1),
            "group-mark",
        )
    if "paint" in spec:
        blob = "M6 20 C3 8 16 3 24 6 C34 2 39 12 35 20 C39 30 28 37 20 34 C11 38 2 31 6 20 Z"
        return draw.svg(
            40,
            40,
            draw.el("path", d=blob, fill=spec["paint"], stroke="#FFFFFF", stroke_width=1.2),
            "group-mark",
        )
    if "pic" in spec:
        return ctx.pic(str(spec["pic"]), css_class="pic group-pic")
    if "bust" in spec:
        from qamra_workbook.render import people

        return draw.svg(60, people.BUST_H, people.job_bust(str(spec["bust"]), 1.2), "group-bust")
    if "chip" in spec:
        return ctx.pic(str(spec["chip"]), css_class="pic group-chip")
    return art.icon(str(spec["icon"]), "ico group-ico")


@page_type("sort-choose")
def sort_choose(ctx: PageContext) -> Built:
    """Join each thing to its group with a line: shapes to their houses, products to the right basket."""
    mode = str(ctx.page.params.get("mode", "join"))
    if mode in family_choose.MODES:  # choosing within a budget, choosing the best solution
        return family_choose.more_choosing(ctx, mode)
    keys = [str(g) for g in ctx.page.params.get("groups", ["circle", "square"])]
    simple = int(ctx.page.params.get("simple", len(keys)))  # the groups after the first `simple` are ⭐⭐
    problems = [f"no sorting group {k!r} yet" for k in keys if k not in SORT_GROUPS]
    groups = [SORT_GROUPS[k] for k in keys if k in SORT_GROUPS]
    items = [(pic, i) for i, g in enumerate(groups) for pic in g["items"][:2]]
    ctx.rng("sort").shuffle(items)
    pairs = all(len(g["items"][:2]) == 1 for g in groups)
    most = PAIRS_MAX if pairs else 4
    if not 2 <= len(groups) <= most or not 4 <= len(items) <= 8:
        problems.append(
            f"a sorting page joins 4–8 things to 2–{most} groups, not {len(items)} to {len(groups)}"
        )
    data = {
        "groups": [
            {
                "label": g["label"],
                "mark": group_mark(ctx, g),
                "color": g.get("color", g.get("paint", "")),
                "basket": "icon" in g or "chip" in g,
                "level": 1 if i < simple else 2,
            }
            for i, g in enumerate(groups)
        ],
        "levels": [(1 if i < simple else 2) for _, i in items],
        "things": [{"pic": ctx.pic(pic), "word": picture(pic).word_ar} for pic, _ in items],
        "basket": ctx.pic("basket"),
    }
    open_choice = any(g.get("open") for g in groups)
    answer = (
        None
        if open_choice
        else [
            "، ".join(
                f"{strip_tashkeel(picture(pic).word_ar)} ← {strip_tashkeel(groups[i]['label'])}"
                for pic, i in items
            )
        ]
    )
    return Built(data, answer, problems)


# ---- the observation journal ------------------------------------------------------------------------------


@page_type("observation-journal")
def observation_journal(ctx: PageContext) -> Built:
    """Journal entries to draw and name what the child observed (saw, heard, collected): `entries` for ⭐ and
    `challenge` more for ⭐⭐, which may carry `chips` to circle (near / far…); `hints` are examples."""
    params = ctx.page.params
    entries, extra = int(params.get("entries", 3)), int(params.get("challenge", 2))
    problems = (
        [] if 1 <= entries + extra <= 6 else [f"a journal page holds 1–6 entries, not {entries + extra}"]
    )
    hints = [str(h) for h in params.get("hints", [])]
    labels = [ctx.text(str(x)) for x in params.get("labels", [])]  # instead of numbers: «اليوم الأول»…
    data = {
        "big": entries + extra == 1,  # one big entry: a magnifying glass to draw in, and notes
        "notes": [ctx.text(str(x)) for x in params.get("notes", [])],
        "how": [
            {"icon": str(h.get("icon", "star")), "text": ctx.text(str(h["text"]))}
            for h in params.get("how", [])
        ],
        "labels": labels,
        "water": bool(params.get("water", False)),
        "icon": str(params.get("icon", "eye")),
        "lead": ctx.text(str(params.get("lead", "{لاحِظْ/لاحِظي} جَيِّدًا"))),
        "hints": [{"pic": ctx.pic(h), "word": picture(h).word_ar} for h in hints],
        "entries": [{"n": ctx.num(i + 1), "level": 1 if i < entries else 2} for i in range(entries + extra)],
        "chips": [ctx.text(str(c)) for c in params.get("chips", [])],
        "name_label": ctx.text(str(params.get("name_label", "ما هُوَ؟"))),
        "character": uri(ctx.assets.character),
        "say": ctx.text(str(params.get("say", "هَيّا نُلاحِظُ!"))),
    }
    return Built(data, None, problems)


def face_mark(feeling: str) -> Markup:
    """A small feelings face for a conversation card."""
    from qamra_workbook.render import people

    kind = feeling if feeling in people.FEELING_COLORS else "happy"
    return draw.svg(20, 20, people.feeling_face(kind, 10, 10, 9.2), "face")


# ---- conversation and role cards --------------------------------------------------------------------------


@page_type("conversation-cards")
def conversation_cards(ctx: PageContext) -> Built:
    """Things to say, read aloud by the grown-up: `roles` (each with a picture, its ⭐ `lines` and ⭐⭐
    `challenge` lines, for play-acting a scene) or `cards` (questions to pick from)."""
    params = ctx.page.params
    roles = [
        {
            "name": ctx.text(str(r["name"])),
            "pic": ctx.pic(str(r["picture"])) if r.get("picture") else Markup(""),
            "icon": str(r.get("icon", "talk")),
            "lines": [ctx.text(str(x)) for x in r.get("lines", [])],
            "challenge": [ctx.text(str(x)) for x in r.get("challenge", [])],
        }
        for r in params.get("roles", [])
    ]
    cards = [
        {
            "text": ctx.text(str(c["text"] if isinstance(c, dict) else c)),
            "face": face_mark(str(c["face"])) if isinstance(c, dict) and c.get("face") else Markup(""),
            "icon": str(c.get("icon", "")) if isinstance(c, dict) else "",
            "level": int(c.get("level", 1)) if isinstance(c, dict) else 1,
        }
        for c in params.get("cards", [])
    ]
    problems = [] if roles or cards else ["conversation cards need `roles` or `cards` to say"]
    if any(not 2 <= len(r["lines"]) <= 4 for r in roles):
        problems.append("a role has 2–4 lines at ⭐")
    data = {
        "roles": roles,
        "cards": cards,
        "answers": bool(params.get("answers", False)),  # a line under each card for the answer
        "swap": ctx.text(str(params.get("swap", ""))),
        "character": uri(ctx.assets.character),
    }
    return Built(data, None, problems)


# ---- price tags and Qamra play money ---------------------------------------------------------------------

SHOP_ITEMS = ("apple", "banana", "milk", "bread", "carrot", "orange", "tomato", "grapes")


@dataclass(frozen=True)
class PriceRow:
    items: list[tuple[str, int]]  # (picture, price)
    pieces: list[int]  # the coins and notes to color
    level: int


def payable(price: int, pieces: list[int]) -> list[int] | None:
    """Some of `pieces` that add up to `price` (largest first), or None."""
    best: dict[int, list[int]] = {0: []}
    for piece in sorted(pieces, reverse=True):
        for total, used in list(best.items()):
            if total + piece not in best:
                best[total + piece] = [*used, piece]
    return best.get(price)


def money_piece(ctx: PageContext, value: int) -> Markup:
    """A Qamra coin (1, 2, 5) or note (10, 20) in outline, for the child to color."""
    ink = "#B27A0C"  # Qamra gold, like the play money
    label = draw.el(
        "text",
        ctx.num(value),
        x=20 if value < 10 else 24,
        y=24 if value < 10 else 16.5,
        text_anchor="middle",
        class_="piece-num",
        fill=ink,
    )
    if value < 10:
        body = draw.el(
            "path", d=scallop_d(20, 20, 17, 17, 18, 0.6), fill="#FFFFFF", stroke=ink, stroke_width=0.9
        )
        body += draw.el(
            "circle",
            cx=20,
            cy=20,
            r=12.5,
            fill="none",
            stroke=ink,
            stroke_width=0.5,
            stroke_dasharray="1.2 1.2",
        )
        return draw.svg(40, 40, body + label, "piece coin")
    body = draw.el("rect", x=1, y=1, width=46, height=22, rx=4, fill="#FFFBEF", stroke=ink, stroke_width=0.9)
    body += draw.el("path", d=draw.star_points(9, 12, 5, 2.3), fill="none", stroke=ink, stroke_width=0.6)
    return draw.svg(48, 24, body + label, "piece note")


@page_type("price-tags")
def price_tags(ctx: PageContext) -> Built:
    """Things with price tags; the child colors pieces of Qamra money that make the price. ⭐ rows: prices up
    to 5 with the ⭐ pieces; the ⭐⭐ row: two things together, with every piece."""
    params = ctx.page.params
    if params.get("mode") == "blank":  # the child's own shop: draw the things, write the prices
        spots = int(params.get("spots", 6))
        data = {
            "mode": "blank",
            "sign": ctx.text(str(params.get("sign", "مَتْجَرُ {child}"))),
            "spots": [{"n": ctx.num(i + 1)} for i in range(spots)],
            "levels": [ctx.text(str(x)) for x in params.get("levels", ["أَسْعارٌ مِنْ ١ إِلى ٥", "أَسْعارٌ حَتّى ٢٠"])],
            "order": ctx.text(str(params.get("order", "{رَتِّبْ/رَتِّبي} مِنَ الأَرْخَصِ إِلى الأَغْلى"))),
            "unit": "قَمْرَة",
        }
        return Built(data, None, [] if 4 <= spots <= 8 else ["a shop shelf has 4–8 spots"])
    denoms = params.get("denominations", {"simple": [1, 2, 5], "challenge": [1, 2, 5, 10, 20]})
    simple, challenge = [int(x) for x in denoms["simple"]], [int(x) for x in denoms["challenge"]]
    r = ctx.rng("prices")
    items = list(SHOP_ITEMS)
    r.shuffle(items)
    purse = sorted([*simple, *simple[:2]])  # 1, 1, 2, 2, 5: every price up to 5
    rows = [PriceRow([(items[i], p)], purse, 1) for i, p in enumerate(r.sample(range(2, 6), 3))]
    a, b = r.sample(range(3, 10), 2)
    rows.append(PriceRow([(items[3], a), (items[4], b)], sorted([*challenge, 2]), 2))
    problems, answer = [], []
    for row in rows:
        price = sum(p for _, p in row.items)
        way = payable(price, row.pieces)
        if way is None:
            problems.append(f"{price} cannot be paid with {row.pieces}")
        answer.append(f"{ctx.num(price)} = " + " + ".join(ctx.num(x) for x in way or []))
    data = {
        "rows": [
            {
                "level": row.level,
                "items": [{"pic": ctx.pic(i), "price": qamra_count(p, ctx.numerals)} for i, p in row.items],
                "pieces": [money_piece(ctx, v) for v in row.pieces],
            }
            for row in rows
        ],
        "total": ctx.text("كَمِ المَجْموعُ؟"),
    }
    return Built(data, answer, problems)


# ---- the color hunt (a scavenger hunt with `colors`) ----------------------------------------------------

COLOR_HINTS = {
    "red": "apple",
    "yellow": "banana",
    "blue": "bird",
    "green": "leaf",
    "orange": "orange",
    "purple": "grapes",
}


def color_hunt(ctx: PageContext) -> Built:
    """Collect things of each color and draw them: `per_color` boxes a color; `challenge_colors` are ⭐⭐."""
    params = ctx.page.params
    colors = [str(c) for c in params.get("colors", ["red", "yellow", "blue"])]
    extra = [str(c) for c in params.get("challenge_colors", ["green"])]
    per = int(params.get("per_color", 2))
    problems = [f"no color {c!r}" for c in [*colors, *extra] if c not in COLORS]
    if not 2 <= len(colors) + len(extra) <= 4 or not 1 <= per <= 3:
        problems.append("a color hunt has 2–4 colors with 1–3 things each")
    columns = [
        {
            "name": COLORS[c][0],
            "paint": COLORS[c][1],
            "level": 1 if c in colors else 2,
            "hint": ctx.pic(COLOR_HINTS[c]) if c in COLOR_HINTS else Markup(""),
        }
        for c in [*colors, *extra]
        if c in COLORS
    ]
    data = {
        "mode": "colors",
        "columns": columns,
        "boxes": [ctx.num(i + 1) for i in range(per)],
        "character": uri(ctx.assets.character),
        "basket": ctx.pic("basket"),
        "lead": ctx.text(str(params.get("lead", "{اجْمَعْ/اجْمَعي} فِي السَّلَّةِ، ثُمَّ {ارْسُمْ/ارْسُمي}"))),
    }
    return Built(data, None, problems)
