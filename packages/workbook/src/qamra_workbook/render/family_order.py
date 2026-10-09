"""One personalized «مغامراتي مع عائلتي» for an order (Addendum 9 §2: no new AI cost): the 112-page interior,
the cover (front and back, on card) and the insert sheets (stickers and card stock, each with its die lines
on their own layer), rendered from the plan for one child, their approved character and their family, with
a preflight report per file.

The worker's order job (`qamra_worker.jobs.family_book`) calls `render_order`; the CLI
(`qamra_workbook.render.family --book`) renders the sample child's copy the same way.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qamra_pdf import preflight
from qamra_workbook.family import FamilyPlan, book_pages, load
from qamra_workbook.render import covers
from qamra_workbook.render.character import aspect, front_view
from qamra_workbook.render.dielines import ART_CSS, DIE_CSS, die_ink, merge_layer, with_css
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.family import PLAN, cover_specs, insert_sheets, plan_pages
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import assets_for
from qamra_workbook.render.spec import BookSpec, Child, Family, Geometry, Numerals, PageSpec, product_geometry


@dataclass
class OrderFiles:
    interior: Path
    cover: Path
    inserts: dict[str, Path] = field(default_factory=dict)  # print file name → the layered PDF
    dies: dict[str, Path] = field(default_factory=dict)  # print file name → its die lines alone
    preflight: dict[str, dict[str, Any]] = field(default_factory=dict)  # file name → report
    pages: int = 0

    @property
    def passed(self) -> bool:
        return all(r.get("passed") for r in self.preflight.values())


def family_spec(
    pages: tuple[PageSpec, ...],
    child: Child,
    family: Family,
    size: str = "21x28",
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
) -> BookSpec:
    return BookSpec(
        product="family",
        title_ar="مغامراتي مع عائلتي",
        child=child,
        pages=pages,
        date=day or dt.date.today(),
        numerals=numerals,
        geometry=product_geometry("family", size),
        family=family,
    )


def _report(pdf: Path, g: Geometry) -> dict[str, Any]:
    return preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe).to_dict()


def with_org(covers: list[PageSpec], org: dict[str, Any] | None) -> list[PageSpec]:
    """The back cover with the organization's name and logo (its copies only)."""
    if not org:
        return covers
    return [
        dataclasses.replace(p, params={**p.params, "org": dict(org)}) if p.type == "cover-back" else p
        for p in covers
    ]


def with_members(assets: Assets, sheets: dict[int, Path], out: Path) -> Assets:
    """The approved family members' characters, cut out of their sheets like the child's front view."""
    if not sheets:
        return assets
    cutouts = {}
    for index, sheet in sheets.items():
        front = front_view(sheet, out / f"member-{index}")
        cutouts[index] = (front, aspect(front))
    return dataclasses.replace(assets, family=cutouts)


async def render_pages(book: BookSpec, assets: Assets, pdf: Path) -> Path:
    pages = build_pages(book, assets)
    return await print_pdf(book_html(book, pages, assets), pdf.with_suffix(".html"), pdf, book.geometry)


async def render_insert(book: BookSpec, assets: Assets, out: Path, name: str) -> tuple[Path, Path]:
    """An insert print file: the art with its die lines on the «CutContour» layer, and the die alone."""
    html = book_html(book, build_pages(book, assets), assets)
    work = out / "work"
    g = book.geometry
    art = await print_pdf(with_css(html, ART_CSS), work / f"{name}-art.html", work / f"{name}-art.pdf", g)
    die = await print_pdf(with_css(html, DIE_CSS), work / f"{name}-die.html", out / f"{name}-die.pdf", g)
    return merge_layer(art, die, out / f"{name}.pdf"), die


async def render_order(
    child: Child,
    family: Family,
    out: Path,
    *,
    size: str = "21x28",
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    plan: FamilyPlan | None = None,
    org: dict[str, Any] | None = None,
    member_sheets: dict[int, Path] | None = None,
) -> OrderFiles:
    """Every print file of one family book into `out`: interior.pdf, cover.pdf and inserts/<name>.pdf.
    `org` ({name, logo: path}) puts an organization's logo on the back cover of its copies (A7 §8);
    `member_sheets` (the family member's index → their approved character sheet) draws those members as
    their illustrated characters instead of the placeholder figures (the illustrated-family add-on)."""
    plan = plan or load(PLAN)
    out.mkdir(parents=True, exist_ok=True)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    interior = family_spec(tuple(specs), child, family, size, numerals, day)
    assets = with_members(assets_for(interior, out), member_sheets or {}, out / "assets")
    g = interior.geometry
    interior_pdf = await render_pages(interior, assets, out / "interior.pdf")
    cover = family_spec(tuple(with_org(cover_specs(plan), org)), child, family, size, numerals, day)
    cover = covers.with_thumbs(cover, interior, interior_pdf, out / "assets", covers.THUMBS["family"])
    files = OrderFiles(
        interior=interior_pdf,
        cover=await render_pages(cover, assets, out / "cover.pdf"),
        pages=len(specs),
    )
    files.preflight = {"interior.pdf": _report(files.interior, g), "cover.pdf": _report(files.cover, g)}
    for name, sheets in insert_sheets(plan):
        book = family_spec(tuple(sheets), child, family, size, numerals, day)
        pdf, die = await render_insert(book, assets, out / "inserts", name)
        files.inserts[name], files.dies[name] = pdf, die
        report = _report(pdf, g)
        report["die_ink"] = die_ink(die)
        if not all(report["die_ink"]):
            report["passed"] = False
        files.preflight[f"inserts/{name}.pdf"] = report
    return files
