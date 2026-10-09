"""«دوسية التأسيس» front pages (Addendum 5 §5): «هذا الكتاب لـ…» with the handprint, tracing the child's own
name in Arabic and English, the table of contents, unit openers with the character, the blank back of a
cut-and-paste sheet, and the volume's cover (front and back, printed on card apart from the interior).

The name pages follow the name rules of `qamra_workbook.names` (the API checks a name at order time with the
same `can_trace`): they never raise on a name. A word the tracing hand cannot write is left out; with nothing
left, the name is printed as a model in the book's type over empty writing lines."""

from __future__ import annotations

import dataclasses

from markupsafe import Markup, escape

from qamra_workbook.letters import ARABIC, LEFT_OPEN, RIGHT_OPEN
from qamra_workbook.letters.model import Guides, Letter
from qamra_workbook.names import MIN_CAP_MM, can_trace, check_name, latin_words, name_parts
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import covers, draw
from qamra_workbook.render.pages.letters import dotted_letter, letter_extent
from qamra_workbook.render.pages.workbook_common import (
    HAMZA_STROKE,
    Number,
    arabic_shape,
    glyph,
    shape_of,
)
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import section_style

__all__ = ["can_trace", "spell", "spell_name", "traced_name"]

_FORM = {(False, False): "isolated", (False, True): "initial", (True, True): "medial", (True, False): "final"}
ALIFS = "اأإآ"
WORD_GAP = 60.0  # the space between the words of a compound name, in letter units (about half a cap height)
# ؤ and ئ: the waw, the tooth of ي or the body of ى with a small hamza over it. (base letter, form) → where
# the hamza's centre and bottom go in the base letter's units. draft: educator review (size and height)
_SEATS = {
    "ؤ": {"isolated": ("و", 71.0, 48.0), "final": ("و", 75.0, 48.0)},
    "ئ": {
        "initial": ("ي", 56.0, 28.0),
        "medial": ("ي", 32.0, 28.0),
        "isolated": ("ى", 104.0, 40.0),
        "final": ("ى", 108.0, 86.0),
    },
}
_HAMZA_CENTRE, _HAMZA_BOTTOM = 45.0, 96.0  # the hamza stroke's own centre and bottom (unscaled)
_LEFT_OPEN = LEFT_OPEN | set(ALIFS) | {"ؤ"}  # never join the next letter


def seated(char: str, form: str) -> Letter:
    """ؤ or ئ in `form`: its base letter (without dots) and a small hamza over it."""
    base_char, cx, bottom = _SEATS[char][form]
    base = ARABIC[(base_char, form)]
    mark = HAMZA_STROKE.scaled(0.5, cx - _HAMZA_CENTRE * 0.5, bottom - _HAMZA_BOTTOM * 0.5)
    return dataclasses.replace(base, char=char, strokes=(*base.strokes, mark), dots=(), dot_r=0.0)


def letter_shape(char: str, form: str) -> Letter:
    return seated(char, form) if char in _SEATS else arabic_shape(char, form)


SPACE = Letter(" ", "isolated", WORD_GAP, ARABIC[("ا", "isolated")].guides, ())


def spell_word(word: str) -> list[Letter]:
    """The forms that write one word in Qamra's hand, joined as in `letters.word` (أ إ آ are alifs, ؤ a waw,
    and لا is the ligature). Every letter must be traceable (`names.TRACEABLE_AR`)."""
    chars: list[str] = []
    for c in word:
        if c == "ا" and chars and chars[-1] == "ل":
            chars[-1] = "لا"
        else:
            chars.append(c)
    out = []
    for i, c in enumerate(chars):
        joins_prev = i > 0 and chars[i - 1] not in _LEFT_OPEN and c not in RIGHT_OPEN
        joins_next = i + 1 < len(chars) and c not in _LEFT_OPEN and chars[i + 1] not in RIGHT_OPEN
        out.append(letter_shape(c, _FORM[(joins_prev, joins_next)]))
    return out


def spell(word: str) -> list[Letter]:
    """The forms that write a word of the book's content in Qamra's hand (tashkeel and spaces dropped).
    Strict: a letter the hand does not have raises `KeyError`, so a content mistake never prints quietly. A
    child's name goes through `spell_name`, which never raises."""
    return spell_word(strip_tashkeel(word).replace(" ", ""))


def spell_name(name: str) -> list[Letter]:
    """The letters that write a child's name on the tracing row: each traceable word in order, a `SPACE`
    between words (`names.check_name`). Words the hand cannot write are left out; an empty list when none
    can be traced."""
    out: list[Letter] = []
    for word in check_name(name).traceable_words:
        if out:
            out.append(SPACE)
        out += spell_word(word)
    return out


def _units(letters: list[Letter]) -> float:
    return sum(x.width for x in letters)


def _guides(letters: list[Letter]) -> Guides:
    return next(x.guides for x in letters if x.strokes)


def traced_name(name: str, width: float = 176.0, cap: float = 22.0) -> str:
    """What the Arabic name page traces: the traceable words of the name, as many parts from the start as fit
    the row at `MIN_CAP_MM` or more (a compound such as «عبد الرحمن» stays whole), and at least the first."""
    parts = name_parts(check_name(name).traceable_words)
    taken = parts[:1]
    for part in parts[1:]:
        if name_scale(spell_name(" ".join([*taken, part])), width, cap) < MIN_CAP_MM:
            break
        taken.append(part)
    return " ".join(taken)


def arabic_name_row(
    letters: list[Letter], width: float, cap: float, *, first: bool, mode: str, number: Number
) -> Markup:
    """The name on writing lines, right to left, box to box so the joins meet: `dotted` to trace (numbered
    start dots where the pen starts: the first letter and after each letter that does not join), `solid` as
    the model, or `empty` lines to write alone (a green dot where the name starts). A `SPACE` leaves the gap
    between two words."""
    g = _guides(letters)
    scale = cap / (g.base - g.top)
    ext = [letter_extent(x) for x in letters if x.strokes]
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
        if not shape.strokes:  # the gap between two words: the pen lifts
            lifted = True
            continue
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
    if not letters:
        return cap
    g = _guides(letters)
    return min(cap, (width - 16) / _units(letters) * (g.base - g.top))


def empty_rows(width: float, cap: float, count: int) -> list[Markup]:
    """Writing lines with nothing to trace (the name could not be drawn in the tracing hand): the four lines
    of a row and a green dot at the right where the name starts."""
    g = ARABIC[("ا", "isolated")].guides
    scale = cap / (g.base - g.top)
    low = g.low if g.low is not None else g.base
    height = 5 + (low - g.top) * scale + 4
    y = 5 - g.top * scale
    rows = []
    for _ in range(count):
        body = [
            draw.el(
                "path",
                d=draw.d_path(("M", (2, y + units * scale)), ("L", (width - 2, y + units * scale))),
                stroke=color,
                stroke_width=sw,
                stroke_dasharray=dash,
            )
            for units, color, sw, dash in (
                (g.top, "#9BB7E0", 0.5, "none"),
                (g.mid, "#9BB7E0", 0.45, "2 1.6"),
                (g.base, "#E27D63", 0.6, "none"),
                (low, "#C9D6EA", 0.4, "1 1.6"),
            )
            if units is not None
        ]
        body.append(draw.start_dot((width - 10, y + (g.mid or g.base) * scale), 1.9))
        rows.append(draw.svg(width, height, "".join(body), "name-row"))
    return rows


def typed_model(name: str) -> Markup:
    """The name as printed text (the fallback model when it cannot be drawn in the tracing hand)."""
    return Markup('<span class="wb-name-typed" data-fit="40">{}</span>').format(escape(name))


LONG_NAME = 16  # characters: a longer name wraps on the owner page and the cover instead of shrinking away


@page_type("owner-page", frame="full")
def owner_page(ctx: PageContext) -> Built:
    character = ctx.assets.character.resolve().as_uri() if ctx.assets.character else ""
    data = {
        "name": ctx.book.child.name,
        "long": len(ctx.book.child.name) > LONG_NAME,
        "character": character,
        "volume_title": str(ctx.page.params.get("volume_title", "")),
        "level_title": str(ctx.page.params.get("level_title", "")),
        "lines": ["رَوْضَتي", "صَفّي", "عُمْري"],  # draft: educator review
    }
    return Built(data)


@page_type("name-trace")
def name_trace(ctx: PageContext) -> Built:
    """The child's own name to trace twice, then write alone. Arabic: the name in the tracing hand (see the
    name rules in `qamra_workbook.names`). English: the parent's spelling (`name_en`), which it needs."""
    script = str(ctx.page.params.get("script", "ar"))
    width = 176.0
    problems = []
    if script == "en":
        name = str(ctx.page.params.get("name_en", "")).strip()
        if not latin_words(name):
            problems.append("the English name page needs the child's name in English letters (name_en)")
            name = "Name"
        name = traced_latin(name, width, 24.0)
        rows = [en_name_row(name, width, 24.0, first=i == 0, mode="dotted", number=ctx.num) for i in range(2)]
        rows.append(en_name_row(name, width, 24.0, first=False, mode="empty", number=ctx.num))
        model = en_name_row(name, width, 24.0, first=False, mode="solid", number=ctx.num)
        return Built({"name": name, "model": model, "rows": rows, "script": script}, None, problems)
    name = traced_name(ctx.book.child.name, width, 22.0)
    letters = spell_name(name)
    if not letters:  # nothing the tracing hand can write: the name as printed, and lines to copy it on
        typed = ctx.book.child.name
        return Built(
            {"name": typed, "model": typed_model(typed), "rows": empty_rows(width, 18.0, 3), "script": script}
        )
    cap = name_scale(letters, width, 22.0)
    rows = [
        arabic_name_row(letters, width, cap, first=i == 0, mode="dotted", number=ctx.num) for i in range(2)
    ]
    rows.append(arabic_name_row(letters, width, cap, first=False, mode="empty", number=ctx.num))
    model = arabic_name_row(letters, width, cap * 0.8, first=False, mode="solid", number=ctx.num)
    return Built({"name": name, "model": model, "rows": rows, "script": script}, None, problems)


_EN_GAP, _EN_WORD_GAP = 5.0, 12.0  # mm between letters, and between the words of a name


def _en_layout(name: str, width: float, cap: float) -> tuple[list[list[Letter]], float]:
    """The words' letter shapes and the scale (mm per unit) that fits them in the row (at most `cap`)."""
    words = [[shape_of(c) for c in w] for w in latin_words(name)] or [[shape_of("N")]]
    scale = cap / 100.0
    gaps = _EN_GAP * sum(len(w) - 1 for w in words) + _EN_WORD_GAP * (len(words) - 1)
    ink = sum((letter_extent(s)[2] - letter_extent(s)[0]) for w in words for s in w)
    if ink * scale + gaps > width - 16:
        scale = max((width - 16 - gaps) / ink, 0.01)
    return words, scale


def traced_latin(name: str, width: float = 176.0, cap: float = 24.0) -> str:
    """The English spelling the page traces: as many words from the start as fit the row at `MIN_CAP_MM` or
    more, and at least the first."""
    words = latin_words(name)
    taken = words[:1]
    for word in words[1:]:
        if _en_layout(" ".join([*taken, word]), width, cap)[1] * 100 < MIN_CAP_MM:
            break
        taken.append(word)
    return " ".join(taken)


def en_name_row(name: str, width: float, cap: float, *, first: bool, mode: str, number: Number) -> Markup:
    """The name in print letters on English lines (capital first), left to right: dotted, solid or empty.
    Spaces and hyphens leave a gap; only the letters A–Z and a–z are drawn."""
    words, scale = _en_layout(name, width, cap)
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
    head = words[0][0]
    if mode == "empty":
        sx, sy = head.strokes[0].start
        at = (10 + (sx - letter_extent(head)[0]) * scale, top + (sy - 10) * scale)
        body.append(draw.start_dot(at, 1.9))
        return draw.svg(width, height, "".join(body), "name-row")
    x = 10.0
    for k, word in enumerate(words):
        if k:
            x += _EN_WORD_GAP - _EN_GAP
        for s in word:
            x0, _, x1, _ = letter_extent(s)
            if mode == "dotted":
                body.append(
                    dotted_letter(
                        s, scale=scale, x=x - x0 * scale, y=top - 10 * scale, first=first, number=number
                    )
                )
            else:
                body.append(glyph(s, scale, x - x0 * scale, top - 10 * scale, color="#1C2140", width=11))
            x += (x1 - x0) * scale + _EN_GAP
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


# ---- the cover (front and back, printed on card apart from the interior; render/covers.py) --------------


def _cover_pills(ctx: PageContext) -> tuple[tuple[str, str], ...]:
    p = ctx.page.params
    code, level, volume = str(p.get("code", "")), str(p.get("level", "")), str(p.get("volume", ""))
    level_pill = f"{code} · {level}" if code and level else level or code
    volume = strip_tashkeel(volume)  # plain, like the level beside it
    return tuple(x for x in ((level_pill, "main"), (volume, "alt")) if x[0])


def _ages(ctx: PageContext) -> str:
    ages = ctx.page.params.get("ages")
    return ctx.num(str(ages)) + " سنوات" if ages else ""


@page_type("workbook-cover-front", frame="full")
def workbook_cover_front(ctx: PageContext) -> Built:
    """The scene of the volume, the child's character among toy blocks of its letters and numbers, the title
    on a notebook page with the level and volume, the child's name on a ribbon, three info badges."""
    p = ctx.page.params
    part = str(p.get("part", ""))
    sc, pc = covers.series_copy("foundation"), covers.part_copy("foundation", part)
    pages = covers.pages_phrase(int(p.get("pages") or 0))
    front = covers.Front(
        series="foundation",
        part=part,
        title=str(p.get("title", "دوسية التأسيس")),
        ribbon=ctx.text(str(sc.get("ribbon", "دوسية {child}"))),
        subtitle=str(p.get("subtitle", "")),
        pills=_cover_pills(ctx),
        age=_ages(ctx),
        badges=tuple((b["icon"], covers.fill(ctx, b["text"], pages=pages)) for b in sc.get("badges", [])),
        blocks=tuple(str(x) for x in pc.get("blocks", [])),
    )
    data = {"cv": covers.front_data(ctx, front), "kicker": front.ribbon}
    problems = [] if p.get("volume") and p.get("level") else ["the cover names the level and the volume"]
    return Built(data, None, problems)


@page_type("workbook-cover-back", frame="full")
def workbook_cover_back(ctx: PageContext) -> Built:
    """For the grown-ups: the scene with the child waving, what this volume teaches, three of its pages, what
    comes with it, the ages, pages and binding, and the site."""
    p = ctx.page.params
    part = str(p.get("part", ""))
    sc, pc = covers.series_copy("foundation"), covers.part_copy("foundation", part)
    comes = [(c["icon"], covers.fill(ctx, c["text"])) for c in sc.get("comes_with", [])]
    if p.get("certificate") and sc.get("certificate"):
        comes.append((sc["certificate"]["icon"], ctx.text(sc["certificate"]["text"])))
    facts = [
        _ages(ctx),
        covers.counted(int(p.get("pages") or 0), "صفحة", "صفحات"),
        str(sc.get("binding", "")),
    ]
    back = covers.Back(
        series="foundation",
        part=part,
        title=str(p.get("title", "دوسية التأسيس")),
        pills=_cover_pills(ctx),
        blurb=tuple(
            x for x in (ctx.text(str(pc.get("blurb", ""))), ctx.text(str(sc.get("series_line", "")))) if x
        ),
        inside=tuple((i["icon"], ctx.text(str(i["text"])), "") for i in pc.get("inside", [])),
        comes=tuple(comes),
        facts=tuple(ctx.num(f) for f in facts if f),
        made_for=covers.fill(ctx, "صُنعت خصيصًا لـ{child}"),
        domain=str(p.get("domain", "qamra.app")),
    )
    return Built({"cv": covers.back_data(ctx, back), "kicker": ctx.text("دوسية {child}")})
