"""The family book's cover (Addendum 7 §10): the front and the back, printed on 350 g card with matte
lamination, each its own page at the book's size with bleed (wire-o binding has no spine). The front shows
the child in the middle of the family, as on the title page; the back tells grown-ups what is inside.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from markupsafe import Markup
from PIL import Image

from qamra_workbook.render import covers
from qamra_workbook.render.pages.family import family_group, family_of, uri
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import FAMILY

ADVENTURES = [s for k, s in FAMILY.items() if k not in ("front", "back")]


@page_type("cover-front", frame="full")
def cover_front(ctx: PageContext) -> Built:
    """The family book's scene, the child in the middle of the family, the title with the child's name on a
    house-shaped panel, the family's name on the ribbon, three info badges (render/covers.py)."""
    problems: list[str] = []
    family = family_of(ctx, problems)
    sc = covers.series_copy("family")
    pages = int(ctx.page.params.get("pages") or 0)
    badges = []
    for b in sc.get("badges", []):
        if "{pages}" in b["text"] and not pages:
            continue
        badges.append((b["icon"], covers.fill(ctx, b["text"], pages=covers.pages_phrase(pages))))
    age = str(sc.get("age", ""))

    def group(w: float, h: float) -> tuple[Markup, list[dict[str, Any]]]:
        return family_group(ctx, family, w, h) if family is not None else (Markup(""), [])

    front = covers.Front(
        series="family",
        part="family",
        title=ctx.text(ctx.page.title),
        ribbon=ctx.text(str(sc.get("ribbon", ""))) if family is not None else ctx.book.child.name,
        subtitle=ctx.text(ctx.page.instruction),
        pills=((str(sc.get("pill", "")), "main"),) if sc.get("pill") else (),
        age=ctx.num(age) + " سنوات" if age else "",
        badges=tuple(badges),
        group=group,
        one_line_max=12,
    )
    data = {
        "cv": covers.front_data(ctx, front),
        "family": family.name if family else "",
        "adventures": [{"icon": s.icon, "color": s.color} for s in ADVENTURES],
    }
    return Built(data, None, problems)


LOGO_BOX_MM = (44.0, 22.0)  # the organization's logo on the back cover, at most
LOGO_DPI = 300


def logo_size(path: Path) -> tuple[float, float]:
    """The logo's printed size (mm): as big as its box allows, never below 300 DPI."""
    with Image.open(path) as im:
        w_px, h_px = im.size
    k = min(LOGO_BOX_MM[0] / w_px, LOGO_BOX_MM[1] / h_px, 25.4 / LOGO_DPI)
    return round(w_px * k, 2), round(h_px * k, 2)


def org_slot(org: Any) -> dict[str, Any]:
    """An organization's copies (A7 §8): its name and logo in the back cover's slot."""
    if not isinstance(org, dict) or not org.get("name"):
        return {"org_name": "", "org_logo": "", "org_logo_mm": (0.0, 0.0)}
    logo = Path(str(org["logo"])) if org.get("logo") else None
    return {
        "org_name": str(org["name"]),
        "org_logo": uri(logo) if logo else "",
        "org_logo_mm": logo_size(logo) if logo else (0.0, 0.0),
    }


@page_type("cover-back", frame="full")
def cover_back(ctx: PageContext) -> Built:
    problems: list[str] = []
    family = family_of(ctx, problems)
    sc = covers.series_copy("family")
    p = ctx.page.params
    pages = int(p.get("pages") or 0)
    blurb = [ctx.text(str(x)) for x in p.get("blurb", [])]
    if p.get("collect"):
        blurb.append(ctx.text(str(p["collect"])))
    age = str(sc.get("age", ""))
    facts = [ctx.num(age) + " سنوات" if age else ctx.text(str(p.get("ages", "")))]
    if pages:
        facts.append(ctx.num(covers.counted(pages, "صفحة", "صفحات")))
    if sc.get("binding"):
        facts.append(str(sc["binding"]))
    back = covers.Back(
        series="family",
        part="family",
        title=ctx.text(ctx.page.title),
        pills=((str(sc.get("pill", "")), "main"),) if sc.get("pill") else (),
        blurb=tuple(blurb),
        inside=tuple((s.icon, ctx.text(s.name_ar), s.color) for s in ADVENTURES),
        inside_title="في هذا الكتاب",
        comes=tuple((c["icon"], covers.fill(ctx, str(c["text"]))) for c in sc.get("comes_with", [])),
        facts=tuple(facts),
        made_for=covers.fill(
            ctx, f"صُنع خصيصًا لـ{{child}} وعائلة {family.name}" if family else "صُنع خصيصًا لـ{child}"
        ),
        org=org_slot(p.get("org")),
    )
    data = {"cv": covers.back_data(ctx, back), **org_slot(p.get("org"))}
    return Built(data, None, problems)
