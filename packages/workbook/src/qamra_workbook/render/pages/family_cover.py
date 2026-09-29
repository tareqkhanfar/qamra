"""The family book's cover (Addendum 7 §10): the front and the back, printed on 350 g card with matte
lamination, each its own page at the book's size with bleed (wire-o binding has no spine). The front shows
the child in the middle of the family, as on the title page; the back tells grown-ups what is inside.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.render.pages.family import CORE_BADGES, family_group, family_of, rosette
from qamra_workbook.render.pages.family_front import split_name, title_art
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import FAMILY

ADVENTURES = [s for k, s in FAMILY.items() if k not in ("front", "back")]


@page_type("cover-front", frame="full")
def cover_front(ctx: PageContext) -> Built:
    problems: list[str] = []
    family = family_of(ctx, problems)
    before, name, after = split_name(ctx, ctx.page.title)
    group, tags = Markup(""), list[dict[str, Any]]()
    if family is not None:
        group, tags = family_group(ctx, family, 186.0, 126.0)
    data = {
        "art": title_art(ctx),
        "before": before,
        "name": name,
        "after": after,
        "sub": ctx.text(ctx.page.instruction),
        "group": group,
        "tags": tags,
        "family": family.name if family else "",
        "adventures": [{"icon": s.icon, "color": s.color} for s in ADVENTURES],
        "count": ctx.num(len(ADVENTURES)),
    }
    return Built(data, None, problems)


@page_type("cover-back", frame="full")
def cover_back(ctx: PageContext) -> Built:
    problems: list[str] = []
    family = family_of(ctx, problems)
    data = {
        "blurb": [ctx.text(str(x)) for x in ctx.page.params.get("blurb", [])],
        "adventures": [{"icon": s.icon, "color": s.color, "name": ctx.text(s.name_ar)} for s in ADVENTURES],
        "made_for": ctx.text(
            f"صُنع خصيصًا لـ{{child}} وعائلة {family.name}" if family else "صُنع خصيصًا لـ{child}"
        ),
        "kit": [ctx.text(str(x)) for x in ctx.page.params.get("kit", [])],
        "ages": ctx.text(str(ctx.page.params.get("ages", "من ٣ إلى ٧ سنوات"))),
        "badges": [rosette(b, css_class="cb-badge") for b in CORE_BADGES],
        "collect": ctx.text(str(ctx.page.params.get("collect", ""))),
    }
    return Built(data, None, problems)
