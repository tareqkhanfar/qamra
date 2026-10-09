"""«قلبي يعرف الله»: the pages that frame a volume: the unit opener, the front pages (the title, the cast, how
to use the book and care for it, «هذا أنا»), the back page, the home challenge, the covers, and the marked
page that stands in a preview for content not written yet.

The child is on the cover, the title page, «هذا أنا» and every unit opener (Addendum 10 §8): the reader's
cut-out character from the character sheet, with the name and the gender's grammar. The covers carry no sacred
text."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from markupsafe import Markup
from PIL import Image

from qamra_workbook.islamic_sources import REPO
from qamra_workbook.pictures.islamic import glyph_svg, motif_strip, star8_svg, unit_glyph
from qamra_workbook.render import covers
from qamra_workbook.render.islamic_content import (
    BackPage,
    FrontCharacters,
    FrontHowTo,
    FrontMe,
    FrontTitle,
    HomeChallenge,
    Missing,
    UnitOpener,
)
from qamra_workbook.render.islamic_figures import cast_names, listeners
from qamra_workbook.render.islamic_units import UNITS, volume_units
from qamra_workbook.render.pages.family import uri
from qamra_workbook.render.pages.islamic_common import (
    chrome,
    context_of,
    islamic_page,
    page_of,
    rich,
)
from qamra_workbook.render.pages.islamic_tell import face, speaker
from qamra_workbook.render.registry import Built, PageContext
from qamra_workbook.render.spec import Geometry

ASSETS = REPO / "content/assets"
DPI = 300
GOLD = "#C9962B"
LEVELS = {1: "الْمُسْتَوَى الْأَوَّلُ", 2: "الْمُسْتَوَى الثَّانِي"}
SERIES = "قلبي يعرف الله"


def volume_info(ctx: PageContext) -> dict[str, Any]:
    info = ctx.page.params.get("volume_info")
    return dict(info) if isinstance(info, dict) else {}


def ages(ctx: PageContext, info: dict[str, Any]) -> str:
    age = info.get("age") or []
    if len(age) != 2:
        return ""
    years = "سَنَوَاتٍ" if 3 <= int(age[1]) <= 10 else "سَنَةً"  # the counted noun agrees with the number
    return f"مِنْ {ctx.num(age[0])} إِلَى {ctx.num(age[1])} {years}"


def reader(ctx: PageContext) -> str:
    return uri(ctx.assets.character)


def unit_art(unit_id: str, name: str = "") -> Path | None:
    """The unit's opener picture in content/assets: `name` (a file stem), else `F<n>-unit-<unit>` (the unit's
    id without `u-` and its trailing digits)."""
    if name:
        found = [p for p in ASSETS.glob(f"{name}.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        return found[0] if found else None
    stem = re.sub(r"\d+$", "", unit_id.removeprefix("u-"))
    found = sorted(ASSETS.glob(f"F*-unit-{stem}.jpg"))
    return found[0] if found else None


def print_width_mm(path: Path, most: float) -> float:
    """The widest an image prints at 300 DPI (and never wider than `most`)."""
    with Image.open(path) as img:
        return round(min(most, img.width / DPI * 25.4), 2)


def glyph(name: str, color: str, size: float = 24.0, stroke: float = 1.9) -> Markup:
    return Markup(  # nosec B704 (static art)
        f'<svg class="gl" viewBox="0 0 24 24" width="{size}" height="{size}" aria-hidden="true">'
        f"{glyph_svg(unit_glyph(name), color, stroke)}</svg>"
    )


# ---- the unit opener --------------------------------------------------------------------------------------


@islamic_page("islamic-unit-opener")
def unit_opener(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, UnitOpener)
    problems: list[str] = []
    unit = UNITS.get(page.unit)
    if unit is None:
        problems.append(f"no unit {page.unit!r} (units.yaml)")
    art = unit_art(page.unit, page.art) if unit else None
    if page.art and art is None:
        problems.append(f"no image {page.art!r} in content/assets")
    lessons = [ctx.text(str(t)) for t in ctx.page.params.get("lessons", [])]
    units = volume_info(ctx).get("units") or []
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "glyph": glyph(unit.icon, unit.on_color, 24, 1.7) if unit else "",
        "number": ctx.num(units.index(page.unit) + 1) if page.unit in units else "",
        "art": uri(art) if art else "",
        "art_mm": print_width_mm(art, 150.0) if art else 0,
        "motif": motif_strip(unit.motif, unit.color, 120, 14) if unit else "",
        "reader": reader(ctx),
        "hello": None,
        "question": rich(ctx, page.question, problems) if page.question else "",
        "lessons": lessons,
        "labels": {
            "unit": "الْوَحْدَةُ",
            "inside": "فِي هَذِهِ الْوَحْدَةِ",
            "think": ctx.text("{فَكِّرْ/فَكِّرِي}"),
        },
    }
    if page.hello is not None:
        data["hello"] = {
            "face": face(ctx, page.hello.who),
            "name": speaker(ctx, page.hello.who),
            "text": rich(ctx, page.hello.t, problems),
        }
    return Built(data, None, problems)


# ---- the front pages and the back page --------------------------------------------------------------------


@islamic_page("islamic-front-title")
def front_title(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, FrontTitle)
    problems: list[str] = []
    info = volume_info(ctx)
    units = volume_units(str(info.get("id", "")))
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "series": SERIES,
        "subtitle": rich(ctx, page.subtitle, problems) if page.subtitle else "",
        "level": LEVELS.get(int(info.get("level") or 0), ""),
        "ages": ages(ctx, info),
        "reader": reader(ctx),
        "owner": ctx.text("{صَاحِبُ/صَاحِبَةُ} هَذَا الْكِتَابِ"),
        "name": ctx.book.child.name,
        "units": [{"glyph": glyph(u.icon, u.on_color, 24, 1.8), "color": u.color} for u in units],
        "star": star8_svg(GOLD, 9.0, "#FFFBEE"),
        "credit": credit_line(ctx),
    }
    return Built(data, None, problems)


def credit_line(ctx: PageContext) -> str:
    """«راجعه علميًّا: …» when the review export names the scholar (print builds only; Addendum 10 §3.3)."""
    isl = ctx.page.params.get("islamic")
    name = getattr(isl, "credit", "") if isl is not None else ""
    return f"راجعه علميًّا: {name}" if name else ""


@islamic_page("islamic-front-characters")
def front_characters(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, FrontCharacters)
    problems: list[str] = []
    names = cast_names()
    kit = context_of(ctx).kit
    cards = []
    for i, intro in enumerate(page.intros):
        if intro.who == "reader":
            art = Markup(f'<img src="{reader(ctx)}" alt="">') if reader(ctx) else Markup("")  # nosec B704
        else:
            h = 22.0 if intro.who == "naanaa" else 52.0
            art = Markup(  # nosec B704 (the kit's drawing)
                f'<svg class="fc-fig" viewBox="0 0 40 56" aria-hidden="true">'
                f"{kit.figure(intro.who, 20, 55, h)}</svg>"
            )
        name = ctx.book.child.name if intro.who == "reader" else ctx.text(names.get(intro.who, intro.who))
        cards.append(
            {
                "art": art,
                "name": name,
                "text": rich(ctx, intro.t, problems),
                "me": intro.who == "reader",
                "i": i,
            }
        )
    return Built({"chrome": chrome(ctx, problems), "cards": cards}, None, problems)


@islamic_page("islamic-front-how-to-use")
def front_how_to(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, FrontHowTo)
    problems: list[str] = []
    from qamra_workbook.render import art

    for step in page.steps:
        if step.icon not in art.ICONS:
            problems.append(f"no icon {step.icon!r} (render/art.py)")
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "steps": [
            {
                "icon": s.icon if s.icon in art.ICONS else "star",
                "n": ctx.num(i),
                "text": rich(ctx, s.t, problems),
            }
            for i, s in enumerate(page.steps, start=1)
        ],
        "care": rich(ctx, page.care_note, problems),
        "labels": {"care": "لِلْأَهْلِ: نَحْفَظُ هَذَا الْكِتَابَ"},
    }
    return Built(data, None, problems)


@islamic_page("islamic-this-is-me")
def this_is_me(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, FrontMe)
    problems: list[str] = []
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "reader": reader(ctx),
        "name": ctx.book.child.name,
        "prompts": [rich(ctx, t, problems) for t in page.prompts],
        "draw_box": ctx.text(page.draw_box),
    }
    return Built(data, None, problems)


@islamic_page("islamic-back-page")
def back_page(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, BackPage)
    problems: list[str] = []
    width, height = 120.0, 56.0
    inner = listeners(context_of(ctx).kit, list(page.figures), width, height)
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "cast": Markup(  # nosec B704 (the kit's drawing)
            f'<svg class="bp-cast" viewBox="0 0 {width:g} {height:g}" aria-hidden="true">{inner}</svg>'
        ),
        "message": rich(ctx, page.message, problems),
        "next": rich(ctx, page.next, problems) if page.next else "",
        "star": star8_svg(GOLD, 9.0, "#FFFBEE"),
        "series": SERIES,
    }
    return Built(data, None, problems)


@islamic_page("islamic-home-challenge")
def home_challenge(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, HomeChallenge)
    problems: list[str] = []
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "challenge": rich(ctx, page.challenge, problems),
        "steps": [rich(ctx, s, problems) for s in page.steps],
        "days": [ctx.num(i) for i in range(1, page.days + 1)],
        "reward": ctx.text(page.reward),
        "labels": {"steps": "أَفْكَارٌ تُسَاعِدُنِي", "week": "نُجُومُ أُسْبُوعِي"},
    }
    return Built(data, None, problems)


# ---- a page not written yet (preview only) ----------------------------------------------------------------


@islamic_page("islamic-missing")
def missing(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Missing)
    problems: list[str] = []
    if context_of(ctx).mode == "print":
        problems.append(f"no content for {page.key} (a {page.planned} page): a print build needs every page")
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "key": page.key,
        "planned": page.planned,
        "lesson": page.lesson_title,
        "concepts": page.concepts,
        "sources": page.sources,
    }
    return Built(data, None, problems)


# ---- the covers -------------------------------------------------------------------------------------------


def _cover_parts(ctx: PageContext) -> tuple[covers.Front, covers.Back, list[str]]:
    """The volume's front and back (render/covers.py) and its spine's lines. No sacred text: the volume's
    title, the series' name, the units' titles."""
    info = volume_info(ctx)
    vid = str(info.get("id", "")).lower()
    part = f"islamic-{vid}"
    units = volume_units(str(info.get("id", "")))
    sc = covers.series_copy("islamic")
    title = ctx.text(str(info.get("title", ctx.page.title)))
    level = LEVELS.get(int(info.get("level") or 0), "")
    series = str(sc.get("series", SERIES))
    pills = ((series, "main"), *(((level, "alt"),) if level else ()))
    pages = int(ctx.page.params.get("pages") or 0)
    values = {
        "pages": covers.pages_phrase(pages, vowelized=True),
        "units": covers.counted(len(units), "وَحْدَة", "وَحَدَات", vowelized=True),
    }
    badges = tuple(
        (b["icon"], covers.fill(ctx, b["text"], **values))
        for b in sc.get("badges", [])
        if pages or "{pages}" not in b["text"]
    )
    front = covers.Front(
        series="islamic",
        part=part,
        title=title,
        ribbon=ctx.book.child.name,
        subtitle=ctx.text(str(sc.get("kicker", ""))),
        pills=pills,
        age=ages(ctx, info),
        badges=badges,
        one_line_max=15,
    )
    facts = [ages(ctx, info)]
    if pages:
        facts.append(ctx.num(covers.counted(pages, "صَفْحَة", "صَفَحَات", vowelized=True)))
    goal = str(info.get("goal", "")).strip()
    blurb = str(
        covers.part_copy("islamic", part).get("blurb") or (goal if goal.endswith(".") else goal + ".")
    )
    books = [
        {"title": ctx.text(str(b["title"])), "this": b["id"] == info.get("id")}
        for b in ctx.page.params.get("books", [])
    ]
    back = covers.Back(
        series="islamic",
        part=part,
        title=title,
        pills=pills,
        blurb=(ctx.text(blurb),) if blurb.strip(".") else (),
        inside=tuple((glyph(u.icon, u.on_color, 24, 1.8), ctx.text(u.title_ar), u.color) for u in units),
        inside_title="فِي هَذَا الْكِتَابِ",
        comes=tuple((c["icon"], covers.fill(ctx, str(c["text"]))) for c in sc.get("comes_with", [])),
        comes_title="يَأْتِي مَعَ الْكِتَابِ",
        facts=tuple(f for f in facts if f),
        made_for=covers.fill(ctx, "صُنِعَ هَذَا الْكِتَابُ خِصِّيصًا لِـ{child:gen}"),
        cols=2,
        extra={
            "books": books,
            "books_title": "كُتُبُ السِّلْسِلَةِ",
            "care": str(sc.get("care", "")),
        },
    )
    return front, back, [series, title, ctx.book.child.name]


@islamic_page("islamic-cover-front", frame="full")
def cover_front(ctx: PageContext) -> Built:
    """The volume's scene, the child, the title on a cream arch with the series and level, the child's name on
    the ribbon, three info badges. No sacred text, no person but the child."""
    front, _, _ = _cover_parts(ctx)
    return Built({"cv": covers.front_data(ctx, front)}, None, [])


@islamic_page("islamic-cover-back", frame="full")
def cover_back(ctx: PageContext) -> Built:
    _, back, _ = _cover_parts(ctx)
    return Built({"cv": covers.back_data(ctx, back)}, None, [])


@islamic_page("islamic-cover-wrap", frame="full")
def cover_wrap(ctx: PageContext) -> Built:
    """The perfect-bound cover as the printer lays it flat: [front | spine | back] (the book opens from the
    right), the spine sized from the page count (`covers.spine_mm`)."""
    front, back, lines = _cover_parts(ctx)
    spine = float(ctx.page.params.get("spine_mm") or 0.0)
    g = ctx.book.geometry
    trim = Geometry(trim_w=(g.trim_w - spine) / 2, trim_h=g.trim_h, bleed=g.bleed, safe=g.safe, dpi=g.dpi)
    front_box, (x, width), back_box = covers.wrap_boxes(trim, spine)
    problems = [] if spine > 0 else ["a wrap needs its spine width"]
    data = {
        "front": covers.front_data(ctx, front, front_box),
        "back": covers.back_data(ctx, back, back_box),
        "spine": covers.spine_data(ctx, covers.LOOKS["islamic"], x, width, lines),
    }
    return Built(data, None, problems)
