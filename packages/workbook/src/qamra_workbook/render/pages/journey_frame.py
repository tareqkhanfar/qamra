"""The journey book's own pages (Addendum 6 §2, §7): the owner page, the section openers (the map with the
child's character at the section's stop, where the child moves a sticker), and the cover. The mini-certificate
at the end of a stage is the journey's `certificate` page with its own line."""

from __future__ import annotations

from typing import Any

from qamra_workbook.render import covers, draw
from qamra_workbook.render.pages.journey import (
    MAP_H,
    MAP_W,
    ROAD,
    ROAD_EDGE,
    ROWS_Y,
    _positions,
    _road,
    _stop,
    stop_key,
    stops_of,
)
from qamra_workbook.render.pages.journey_kit import SOFT, W, card, svg, text
from qamra_workbook.render.pages.motor import character_image
from qamra_workbook.render.registry import Built, PageContext, page_type

STAGE_AGES = {1: "٣–٤", 2: "٤–٥", 3: "٥–٦"}
AGES_LATIN = {1: "3–4", 2: "4–5", 3: "5–6"}


def stage_name(stage: int) -> str:
    return {1: "المحطة الأولى", 2: "المحطة الثانية", 3: "المحطة الثالثة"}.get(stage, "")


@page_type("journey-owner", frame="full")
def journey_owner(ctx: PageContext) -> Built:
    """«هذا الكتاب لـ…»: the name, the child's character, a hand to draw around, age and start date."""
    stage = ctx.page.stage or 1
    data = {
        "name": ctx.book.child.name,
        "character": ctx.assets.character.resolve().as_uri() if ctx.assets.character else "",
        "level_title": "رِحْلَتي الأولى لِلتَّعَلُّمِ",
        "volume_title": str(ctx.page.params.get("subtitle", stage_name(stage))),
        "lines": [str(line) for line in ctx.page.params.get("lines", ["عُمْري", "بَدَأْتُ رِحْلَتي في"])],
    }
    return Built(data)


@page_type("journey-opener")
def journey_opener(ctx: PageContext) -> Built:
    """A section opens on the journey map: the character stands at the section's stop (or stops, when two
    small sections share the page), with a dashed circle for the child's sticker, and what the section
    holds."""
    stops = stops_of(ctx)
    labels = [s["label"] for s in stops]
    raw = ctx.page.params.get("here") or [ctx.page.params.get("stop", labels[0])]
    here = [stop_key(s) for s in (raw if isinstance(raw, list) else [raw])]
    finish = "finish" in here
    problems = [f"no stop {s!r} on the map" for s in here if s not in labels and s != "finish"]
    positions = _positions(len(stops))
    body = [draw.el("rect", x=0, y=0, width=MAP_W, height=MAP_H, rx=8, fill="#F4F9FD")]
    road = _road([(176.0, ROWS_Y[0]), *positions, (14.0, ROWS_Y[-1])])
    body += [
        draw.path(road, stroke=ROAD_EDGE, width=15),
        draw.path(road, stroke=ROAD, width=12.4),
        draw.path(road, stroke="#FFFFFF", width=0.9, stroke_dasharray="2.6 3.4"),
    ]
    spots = [(14.0, ROWS_Y[-1])] if finish else [positions[labels.index(s)] for s in here if s in labels]
    for x, y in spots:
        body.append(draw.el("circle", cx=x, cy=y, r=17, fill="#F7C84A", opacity=0.35))
    body += [
        _stop(x, y, s, ctx.num(k))
        for k, ((x, y), s) in enumerate(zip(positions, stops, strict=True), start=1)
    ]
    fx, fy = 14.0, ROWS_Y[-1]
    body.append(
        draw.path(draw.d_path(("M", (fx, fy + 2)), ("L", (fx, fy - 24))), stroke="#7E5236", width=1.6)
    )
    flag = draw.d_path(("M", (fx, fy - 24)), ("L", (fx + 15, fy - 20)), ("L", (fx, fy - 15)))
    body.append(draw.el("path", d=flag + " Z", fill="#E5604E", stroke="#A7432D", stroke_width=0.6))
    if spots:
        x, y = spots[-1]
        body.append(
            draw.el(
                "circle",
                cx=x + (14 if x < MAP_W / 2 else -14),
                cy=y - 22,
                r=8,
                fill="#FFFFFF",
                stroke="#E27D63",
                stroke_width=0.9,
                stroke_dasharray="2.4 1.8",
            )
        )
        # 32 mm tall: the head stays under the name of the stop on the row above (it hid it at 40)
        body.append(character_image(ctx, x - 9, y - 1, 32))
    inside = [ctx.text(str(t)) for t in ctx.page.params.get("inside", [])]
    area = [
        f'<svg x="{draw.n((W - MAP_W * 0.8) / 2)}" y="0" width="{draw.n(MAP_W * 0.8)}" '
        f'height="{draw.n(MAP_H * 0.8)}" viewBox="0 0 {MAP_W} {MAP_H}">{"".join(body)}</svg>'
    ]
    if inside:
        top = MAP_H * 0.8 + 6
        area.append(card(0, top, W, 204 - top, r=10, fill=SOFT, stroke="none"))
        area.append(
            text("في هَذِهِ المَحَطَّةِ", W - 10, top + 11, 5.2, cls="wb-label", color="#676B83", anchor="end")
        )
        for k, line in enumerate(inside[:3]):
            y = top + 22 + k * 9
            area.append(draw.el("circle", cx=W - 13, cy=y - 1.8, r=2, fill=ctx.style.color))
            area.append(text(line, W - 19, y, 5, cls="wb-label", color="#1C2140", anchor="end"))
    return Built({"svg": svg(area)}, None, problems)


def _stage_cover(ctx: PageContext) -> tuple[int, str, dict[str, Any], dict[str, Any]]:
    stage = int(ctx.page.params.get("stage", ctx.page.stage or 1))
    part = f"journey-{stage}"
    return stage, part, covers.series_copy("journey"), covers.part_copy("journey", part)


def _badges(ctx: PageContext, sc: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    pages = int(ctx.page.params.get("pages") or 0)
    out = []
    for b in sc.get("badges", []) or []:
        if "{pages}" in b["text"] and not pages:
            continue  # a cover rendered without its interior's count
        out.append((b["icon"], covers.fill(ctx, b["text"], pages=covers.pages_phrase(pages))))
    return tuple(out)


@page_type("journey-cover-front", frame="full")
def journey_cover_front(ctx: PageContext) -> Built:
    """The stage's scene, the child among blocks of what the stage teaches, the title on a trail sign, the
    stage, the ribbon «رحلة …», three info badges (render/covers.py)."""
    stage, part, sc, pc = _stage_cover(ctx)
    p = ctx.page.params
    front = covers.Front(
        series="journey",
        part=part,
        title=str(ctx.page.title or "رحلتي الأولى للتعلّم"),
        ribbon=ctx.text(str(p.get("kicker") or sc.get("ribbon", "رحلة {child}"))),
        subtitle=str(p.get("subtitle", "")),
        pills=((stage_name(stage), "main"),),
        age=ctx.book.num(AGES_LATIN.get(stage, "")) + " سنوات",
        badges=_badges(ctx, sc),
        blocks=tuple(str(x) for x in pc.get("blocks", []) or []),
    )
    return Built({"cv": covers.front_data(ctx, front), "kicker": front.ribbon})


@page_type("journey-cover-back", frame="full")
def journey_cover_back(ctx: PageContext) -> Built:
    stage, part, sc, pc = _stage_cover(ctx)
    p = ctx.page.params
    pages = int(p.get("pages") or 0)
    facts = [ctx.book.num(AGES_LATIN.get(stage, "")) + " سنوات"]
    if pages:
        facts.append(ctx.book.num(covers.counted(pages, "صفحة", "صفحات")))
    facts.append(str(sc.get("binding", "")))
    back = covers.Back(
        series="journey",
        part=part,
        title=str(ctx.page.title or "رحلتي الأولى للتعلّم"),
        pills=((stage_name(stage), "main"),),
        blurb=(ctx.text(str(p.get("blurb", ""))),) if p.get("blurb") else (),
        inside=tuple((i["icon"], ctx.text(str(i["text"])), "") for i in pc.get("inside", []) or []),
        inside_title="في هذه المحطة",
        comes=tuple((c["icon"], covers.fill(ctx, str(c["text"]))) for c in pc.get("comes_with", []) or []),
        facts=tuple(facts),
        made_for=covers.fill(ctx, "صُنع هذا الكتاب خصيصًا لـ{child}"),
    )
    return Built({"cv": covers.back_data(ctx, back), "stage": stage_name(stage)})
