"""The journey book's own pages (Addendum 6 §2, §7): the owner page, the section openers (the map with the
child's character at the section's stop, where the child moves a sticker), and the cover. The mini-certificate
at the end of a stage is the journey's `certificate` page with its own line."""

from __future__ import annotations

from qamra_workbook.render import art, draw
from qamra_workbook.render.pages.journey import (
    MAP_H,
    MAP_W,
    ROAD,
    ROAD_EDGE,
    ROWS_Y,
    _positions,
    _road,
    _stop,
    stops_of,
)
from qamra_workbook.render.pages.journey_kit import SOFT, W, card, svg, text
from qamra_workbook.render.pages.motor import character_image
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import SECTIONS

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
    here = [str(s) for s in (raw if isinstance(raw, list) else [raw])]
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
        body.append(character_image(ctx, x - 11, y - 2, 40))
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


@page_type("journey-cover-front", frame="full")
def journey_cover_front(ctx: PageContext) -> Built:
    stage = int(ctx.page.params.get("stage", ctx.page.stage or 1))
    return Built(
        {
            "name": ctx.book.child.name,
            "character": ctx.assets.character.resolve().as_uri() if ctx.assets.character else "",
            "stage": stage_name(stage),
            "subtitle": str(ctx.page.params.get("subtitle", "")),
            "ages": ctx.book.num(AGES_LATIN.get(stage, "")) + " سنوات",
            "stops": [{"icon": art.icon(s["icon"]), "color": s["color"]} for s in stops_of(ctx)],
            "kicker": ctx.text(str(ctx.page.params.get("kicker", "رحلة {child}"))),
        }
    )


@page_type("journey-cover-back", frame="full")
def journey_cover_back(ctx: PageContext) -> Built:
    stage = int(ctx.page.params.get("stage", ctx.page.stage or 1))
    order = [s for s in SECTIONS.values() if s.id != "intro"]
    return Built(
        {
            "blurb": ctx.text(str(ctx.page.params.get("blurb", ""))),
            "points": [ctx.text(str(p)) for p in ctx.page.params.get("points", [])],
            "sections": [{"name": s.name_ar, "icon": art.icon(s.icon), "color": s.color} for s in order],
            "stage": stage_name(stage),
            "ages": ctx.book.num(AGES_LATIN.get(stage, "")) + " سنوات",
        }
    )
