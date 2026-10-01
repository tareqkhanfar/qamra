"""«دوسية التأسيس» front pages (Addendum 5 §5): «هذا الكتاب لـ…» with the handprint, tracing the child's own
name in Arabic and English, the table of contents, unit openers with the character, and the blank back of a
cut-and-paste sheet."""

from __future__ import annotations

from markupsafe import Markup

from qamra_workbook.letters import LEFT_OPEN, RIGHT_OPEN
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import dotted_letter, letter_extent
from qamra_workbook.render.pages.workbook_common import Number, arabic_shape, glyph, shape_of
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import section_style

_FORM = {(False, False): "isolated", (False, True): "initial", (True, True): "medial", (True, False): "final"}
ALIFS = "اأإآ"


def spell(name: str) -> list[Letter]:
    """The forms that write `name` in Qamra's hand, joined as in `letters.word` (أ إ آ are alifs, and لا is
    the ligature)."""
    chars: list[str] = []
    for c in strip_tashkeel(name).replace(" ", ""):
        if c == "ا" and chars and chars[-1] == "ل":
            chars[-1] = "لا"
        else:
            chars.append(c)
    left_open = LEFT_OPEN | set(ALIFS)
    out = []
    for i, c in enumerate(chars):
        joins_prev = i > 0 and chars[i - 1] not in left_open and c not in RIGHT_OPEN
        joins_next = i + 1 < len(chars) and c not in left_open and chars[i + 1] not in RIGHT_OPEN
        out.append(arabic_shape(c, _FORM[(joins_prev, joins_next)]))
    return out


def arabic_name_row(
    letters: list[Letter], width: float, cap: float, *, first: bool, mode: str, number: Number
) -> Markup:
    """The name on writing lines, right to left, box to box so the joins meet: `dotted` to trace (numbered
    start dots where the pen starts: the first letter and after each letter that does not join), `solid` as
    the model, or `empty` lines to write alone (a green dot where the name starts)."""
    g = letters[0].guides
    scale = cap / (g.base - g.top)
    ext = [letter_extent(x) for x in letters]
    top_room = max(0.0, max((g.top - e[1]) * scale for e in ext))
    low = g.low if g.low is not None else g.base
    height = 5 + top_room + (low - g.top) * scale + 4
    right = width - 8.0
    y = 5 + top_room - g.top * scale
    body = []
    for units, color, sw, dash in (
        (g.top, "#9BB7E0", 0.5, "none"),
        (g.mid, "#9BB7E0", 0.45, "2 1.6"),
        (g.base, "#E27D63", 0.6, "none"),
        (low, "#C9D6EA", 0.4, "1 1.6"),
    ):
        if units is None:
            continue
        yy = y + units * scale
        body.append(
            draw.el(
                "path",
                d=draw.d_path(("M", (2, yy)), ("L", (width - 2, yy))),
                stroke=color,
                stroke_width=sw,
                stroke_dasharray=dash,
            )
        )
    if mode == "empty":
        sx, sy = letters[0].strokes[0].start
        body.append(draw.start_dot((right - (letters[0].width - sx) * scale, y + sy * scale), 1.9))
        return draw.svg(width, height, "".join(body), "name-row")
    lifted = True
    for shape in letters:
        right -= shape.width * scale
        if mode == "dotted":
            body.append(
                dotted_letter(shape, scale=scale, x=right, y=y, first=first and lifted, number=number)
            )
        else:
            body.append(glyph(shape, scale, right, y, color="#1C2140", width=11))
        lifted = shape.join_left is None
    return draw.svg(width, height, "".join(body), "name-row")


def name_scale(letters: list[Letter], width: float, cap: float) -> float:
    """The cap height that fits the whole name in the row (at most `cap`)."""
    g = letters[0].guides
    units = sum(x.width for x in letters)
    return min(cap, (width - 16) / units * (g.base - g.top))


@page_type("owner-page", frame="full")
def owner_page(ctx: PageContext) -> Built:
    character = ctx.assets.character.resolve().as_uri() if ctx.assets.character else ""
    data = {
        "name": ctx.book.child.name,
        "character": character,
        "volume_title": str(ctx.page.params.get("volume_title", "")),
        "level_title": str(ctx.page.params.get("level_title", "")),
        "lines": ["رَوْضَتي", "صَفّي", "عُمْري"],  # draft: educator review
    }
    return Built(data)


@page_type("name-trace")
def name_trace(ctx: PageContext) -> Built:
    script = str(ctx.page.params.get("script", "ar"))
    width = 176.0
    problems = []
    if script == "en":
        name = str(ctx.page.params.get("name_en", "")).strip()
        if not name:
            problems.append("the English name page needs the child's name in English letters (name_en)")
            name = "Name"
        rows = [en_name_row(name, width, 24.0, first=i == 0, mode="dotted", number=ctx.num) for i in range(2)]
        rows.append(en_name_row(name, width, 24.0, first=False, mode="empty", number=ctx.num))
        model = en_name_row(name, width, 24.0, first=False, mode="solid", number=ctx.num)
    else:
        name = ctx.book.child.name
        letters = spell(name)
        cap = name_scale(letters, width, 22.0)
        rows = [
            arabic_name_row(letters, width, cap, first=i == 0, mode="dotted", number=ctx.num)
            for i in range(2)
        ]
        rows.append(arabic_name_row(letters, width, cap, first=False, mode="empty", number=ctx.num))
        model = arabic_name_row(letters, width, cap * 0.8, first=False, mode="solid", number=ctx.num)
    return Built({"name": name, "model": model, "rows": rows, "script": script}, None, problems)


def en_name_row(name: str, width: float, cap: float, *, first: bool, mode: str, number: Number) -> Markup:
    """The name in print letters on English lines (capital first), left to right: dotted, solid or empty."""
    shapes = [shape_of(c) for c in name if c.isalpha()]
    scale = cap / 100.0
    gap = 5.0
    total = sum((letter_extent(s)[2] - letter_extent(s)[0]) * scale for s in shapes) + gap * (len(shapes) - 1)
    if total > width - 16:
        scale *= (width - 16 - gap * (len(shapes) - 1)) / (total - gap * (len(shapes) - 1))
    top, height = 5.0, 5 + 140 * scale + 4
    body = []
    for units, color, sw, dash in (
        (10, "#9BB7E0", 0.5, "none"),
        (60, "#9BB7E0", 0.45, "2 1.6"),
        (110, "#E27D63", 0.6, "none"),
    ):
        yy = top + (units - 10) * scale
        body.append(
            draw.el(
                "path",
                d=draw.d_path(("M", (2, yy)), ("L", (width - 2, yy))),
                stroke=color,
                stroke_width=sw,
                stroke_dasharray=dash,
            )
        )
    if mode == "empty":
        sx, sy = shapes[0].strokes[0].start
        body.append(
            draw.start_dot((10 + (sx - letter_extent(shapes[0])[0]) * scale, top + (sy - 10) * scale), 1.9)
        )
        return draw.svg(width, height, "".join(body), "name-row")
    x = 10.0
    for s in shapes:
        x0, _, x1, _ = letter_extent(s)
        if mode == "dotted":
            body.append(
                dotted_letter(
                    s, scale=scale, x=x - x0 * scale, y=top - 10 * scale, first=first, number=number
                )
            )
        else:
            body.append(glyph(s, scale, x - x0 * scale, top - 10 * scale, color="#1C2140", width=11))
        x += (x1 - x0) * scale + gap
    return draw.svg(width, height, "".join(body), "name-row")


@page_type("workbook-toc")
def workbook_toc(ctx: PageContext) -> Built:
    """The volume's units in book order, each with its subject's tab color and icon and its first page."""
    rows = []
    for unit in ctx.page.params.get("units", []):
        style = section_style(str(unit["subject"]), ctx.book.product)
        rows.append(
            {
                "title": str(unit["title"]),
                "page": ctx.book.num(int(unit["page"])),
                "subject": style.name_ar,
                "icon": style.icon,
                "color": style.color,
                "tint": style.tint,
                "deep": style.deep,
            }
        )
    problems = [] if 4 <= len(rows) <= 26 else [f"the table of contents lists 4–26 units, not {len(rows)}"]
    return Built({"rows": rows, "volume_title": str(ctx.page.params.get("volume_title", ""))}, None, problems)


@page_type("unit-opener")
def unit_opener(ctx: PageContext) -> Built:
    """The child's character opens a subject: what they will learn in this volume (the plan's objectives)."""
    objectives = [str(x) for x in ctx.page.params.get("objectives", [])][:5]
    character = ctx.assets.wave or ctx.assets.character
    data = {
        "objectives": objectives,
        "character": character.resolve().as_uri() if character else "",
        "subject_ar": str(ctx.page.params.get("subject_ar", "")),
    }
    problems = [] if objectives else ["a unit opener lists what the child will learn (objectives)"]
    return Built(data, None, problems)


@page_type("blank", frame="full")
def blank(ctx: PageContext) -> Built:
    """The back of a one-sided sheet (cut & paste): left blank so cutting never destroys an activity."""
    return Built({"note": "تُركت هذه الصفحة فارغة: على الوجه الآخر من الورقة نشاط القصّ واللصق."})
