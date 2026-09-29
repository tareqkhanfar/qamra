"""One personalized «مغامراتي مع عائلتي» for an order (Addendum 9 §2: no new AI cost): the 112-page interior,
the cover (front and back, on card) and the insert sheets (stickers and card stock, each with its die lines
on their own layer), rendered from the plan for one child, their approved character and their family, with
a preflight report per file.

The worker's order job (`qamra_worker.jobs.family_book`) calls `render_order`; the CLI
(`qamra_workbook.render.family --book`) renders the sample child's copy the same way.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qamra_pdf import preflight
from qamra_workbook.family import FamilyPlan, book_pages, load
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
) -> OrderFiles:
    """Every print file of one family book into `out`: interior.pdf, cover.pdf and inserts/<name>.pdf."""
    plan = plan or load(PLAN)
    out.mkdir(parents=True, exist_ok=True)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    interior = family_spec(tuple(specs), child, family, size, numerals, day)
    assets = assets_for(interior, out)
    g = interior.geometry
    files = OrderFiles(
        interior=await render_pages(interior, assets, out / "interior.pdf"),
        cover=await render_pages(
            family_spec(tuple(cover_specs(plan)), child, family, size, numerals, day),
            assets,
            out / "cover.pdf",
        ),
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
