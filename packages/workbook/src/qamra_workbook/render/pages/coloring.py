"""The pages of «دفاتر التلوين والرسم» (`qamra_workbook.coloring`): black-only line art on white paper.

Every page is a `sheet` frame (no section tab, no engine footer): the page draws its own small page number.
Text is set in code with the book's fonts, never inside a drawing. Big words the child colours (the book's
title, the child's name) are hollow: white letters with a black ring of offset copies (`HOLLOW`), so they
stay real, embedded text (an SVG or CSS stroke on text would print as a Type 3 font).
"""

from __future__ import annotations

import math
from typing import Any

from markupsafe import Markup

from qamra_workbook.coloring.checks import line_problems
from qamra_workbook.coloring.letters import letter_panel, load, picture_svg
from qamra_workbook.coloring.parts.qamra import medal_svg, title_vignette
from qamra_workbook.coloring.titles import Title, title_of
from qamra_workbook.render.registry import Built, PageContext, page_type


def hollow(radius_mm: float, n: int = 24) -> str:
    """A CSS text-shadow ring: white text with this shadow prints as an outlined, colourable word."""
    parts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        parts.append(f"{radius_mm * math.cos(a):.3f}mm {radius_mm * math.sin(a):.3f}mm 0 #000")
    return ", ".join(parts)


HOLLOW = hollow(0.75)
HOLLOW_BIG = hollow(1.2, 32)


def _checked(markup: str, problems: list[str], what: str) -> Markup:
    problems.extend(f"{what}: {x}" for x in line_problems(markup))
    return Markup(markup)  # nosec B704 (drawn in code, no user text)


@page_type("cb-title", frame="sheet")
def cb_title(ctx: PageContext) -> Built:
    """The first page: the book's title in hollow letters, «{صاحِبُ/صاحِبَةُ} هذا الدَّفْتَرِ» and the child's
    name to colour."""
    title = title_of(str(ctx.page.params["title"]))
    problems: list[str] = []
    art = _checked(title_vignette("line"), problems, "vignette")
    return Built(
        {
            "title": title.name_ar,
            "owner": ctx.text(str(ctx.page.params.get("owner", "هذا الدَّفْتَرُ لِـ"))),
            "name": ctx.book.child.name,
            "art": art,
            "hollow": HOLLOW,
            "hollow_big": HOLLOW_BIG,
        },
        problems=problems,
    )


@page_type("cb-me", frame="sheet")
def cb_me(ctx: PageContext) -> Built:
    """«اسمي …»: the child's name to colour, and a frame to draw themselves in."""
    return Built(
        {
            "lead": ctx.text(ctx.page.title),
            "name": ctx.book.child.name,
            "prompt": ctx.text(ctx.page.instruction),
            "hollow": HOLLOW_BIG,
        }
    )


@page_type("cb-letter", frame="sheet")
def cb_letter(ctx: PageContext) -> Built:
    """One letter: the big letter to colour, its name, and pictures whose word starts with it."""
    char = str(ctx.page.params["char"])
    page = next(x for x in load().letters if x.char == char)
    problems: list[str] = []
    big = _checked(letter_panel(char, 186.0, 150.0), problems, "letter")
    size = 52.0 if len(page.pictures) == 3 else 62.0
    pictures = [
        {"svg": _checked(picture_svg(s.picture, size), problems, s.picture), "word": s.word_ar}
        for s in page.pictures
    ]
    return Built({"name": page.name_ar, "letter": big, "pictures": pictures, "size": size}, problems=problems)


@page_type("cb-scene", frame="sheet")
def cb_scene(ctx: PageContext) -> Built:
    """A full-page coloring scene in its frame, its caption above it."""
    from qamra_workbook.coloring.scenes import framed, get

    sc = get(str(ctx.page.params["book"]), str(ctx.page.params["scene"]))
    problems: list[str] = []
    drawing = _checked(framed(sc, "line", uid=f"clip-{ctx.page.id}"), problems, sc.id)
    return Built({"caption": ctx.text(ctx.page.title), "drawing": drawing}, problems=problems)


@page_type("cb-draw", frame="sheet")
def cb_draw(ctx: PageContext) -> Built:
    """A drawing page: a prompt (or none) above a framed space (`coloring.sketch` art)."""
    from qamra_workbook.coloring.sketch import DATE_LINES, W, art_svg

    problems: list[str] = []
    drawing = _checked(art_svg(str(ctx.page.params["art"])), problems, str(ctx.page.params["art"]))
    # the date page: each writing line's label at its start (its right end), sitting on the line
    texts = [ctx.text(str(x)) for x in ctx.page.params.get("labels", []) or []]
    if texts and len(texts) != len(DATE_LINES):
        problems.append(f"{len(texts)} labels for {len(DATE_LINES)} writing lines")
    labels = [
        {"text": text, "right": round(W - x1, 2), "top": round(y - 11.5, 2)}
        for text, (_, x1, y) in zip(texts, DATE_LINES, strict=False)
    ]
    return Built(
        {"prompt": ctx.text(ctx.page.title), "drawing": drawing, "labels": labels}, problems=problems
    )


@page_type("cb-certificate", frame="sheet")
def cb_certificate(ctx: PageContext) -> Built:
    """The last coloring page: «أحسنت!» with the child's name, a medal and stars to colour."""
    problems: list[str] = []
    art = _checked(medal_svg("line", 92), problems, "medal")
    return Built(
        {
            "lead": ctx.text(ctx.page.title),
            "line": ctx.text(ctx.page.instruction),
            "art": art,
            "hollow": HOLLOW_BIG,
        },
        problems=problems,
    )


# ---- the cover (front and back on card, render/covers.py) --------------------------------------------------


def _cover_copy(ctx: PageContext) -> tuple[str, dict[str, Any], dict[str, Any]]:
    from qamra_workbook.render import covers

    part = f"colorbook-{ctx.page.params['title']}"
    return part, covers.series_copy("colorbook"), covers.part_copy("colorbook", part)


def _pill(t: Title, sc: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    pill = str(sc.get("pill_sketchbook" if t.key == "sketchbook" else "pill_coloring", ""))
    return ((pill, "main"),) if pill else ()


@page_type("cb-cover-front", frame="full")
def cb_cover_front(ctx: PageContext) -> Built:
    """The book's painted scene, the title on the notebook panel, the child (when the family has a
    character, else a drawn centrepiece), «دفتر …» on the ribbon and three badges."""
    from qamra_workbook.coloring.cover_art import cover_scene
    from qamra_workbook.render import covers

    part, sc, pc = _cover_copy(ctx)
    t = title_of(str(ctx.page.params["title"]))
    pages = int(ctx.page.params.get("pages") or 0)
    badges = []
    listed = list(sc.get("badges", []) or [])
    if pc.get("badge"):  # the book's own badge in the middle
        listed.insert(1, pc["badge"])
    for b in listed:
        text = str(b["text"])
        if "{pages}" in text and not pages:
            continue
        text = text.replace("{pages}", covers.counted(pages, "صفحة", "صفحات"))
        badges.append((str(b["icon"]), ctx.book.num(covers.fill(ctx, text))))
    g = ctx.book.geometry
    hero = ctx.assets.character is not None
    front = covers.Front(
        series="colorbook",
        part=part,
        title=t.name_ar,
        ribbon=covers.fill(ctx, str(sc.get("ribbon", "{child}"))),
        pills=_pill(t, sc),
        age=ctx.book.num(str(sc.get("age", "3–7"))) + " سنوات",
        badges=tuple(badges),
        blocks=tuple(str(x) for x in pc.get("blocks", []) or []),
        scene_svg=cover_scene(t.key, g.page_w, g.page_h, hero=hero),
    )
    return Built({"cv": covers.front_data(ctx, front)})


@page_type("cb-cover-back", frame="full")
def cb_cover_back(ctx: PageContext) -> Built:
    """What grown-ups read: the blurb, «في هذا الدفتر», three real pages, the ages, pages and binding."""
    from qamra_workbook.coloring.cover_art import band_scene
    from qamra_workbook.render import covers

    part, sc, pc = _cover_copy(ctx)
    t = title_of(str(ctx.page.params["title"]))
    pages = int(ctx.page.params.get("pages") or 0)
    facts = [ctx.book.num(str(sc.get("age", "3–7"))) + " سنوات"]
    if pages:
        facts.append(ctx.book.num(covers.counted(pages, "صفحة", "صفحات")))
    facts.append(str(sc.get("binding_wire" if t.binding == "wire-o" else "binding_stapled", "")))
    g = ctx.book.geometry
    back = covers.Back(
        series="colorbook",
        part=part,
        title=t.name_ar,
        pills=_pill(t, sc),
        blurb=(covers.fill(ctx, str(pc["blurb"])),) if pc.get("blurb") else (),
        inside=tuple(
            (str(i["icon"]), ctx.book.num(covers.fill(ctx, str(i["text"]))), "")
            for i in pc.get("inside", []) or []
        ),
        inside_title="في هذا الدفتر",
        facts=tuple(ctx.book.num(f) for f in facts if f),
        made_for=covers.fill(ctx, "صُنع هذا الدفتر خصيصًا لـ{child:gen}"),
        scene_svg=band_scene(t.key, g.page_w, round(0.27 * g.page_h, 1)),
    )
    return Built({"cv": covers.back_data(ctx, back)})
