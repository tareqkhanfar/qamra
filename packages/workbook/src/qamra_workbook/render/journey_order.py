"""One personalized «رحلتي الأولى للتعلّم» stage for an order (Addendum 9 §2: no new AI cost): the interior
(every page of the stage's plan with its print layer), the cover (front and back, on card), the parents'
answer key (Addendum 6 §5, a free download) and the stage's sticker sheet (`render.stickers`: the stickers
its map, openers and pattern pages ask for, on A4 sticker paper with its die lines), drawn for one child and
their approved character, with a preflight report per file. Audio QR codes point to `https://{domain}/a/{code}`.

The worker's order job (`qamra_worker.jobs.journey_book`) calls `render_order`; the CLI
(`qamra_workbook.render.journey --book`) renders the sample child's copy the same way.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qamra_pdf import preflight
from qamra_workbook.journey import Journey, load
from qamra_workbook.journey_book import PLAN, cover_specs, layer_problems, load_layer, page_specs, stage_book
from qamra_workbook.render import covers
from qamra_workbook.render.engine import PageProblems, answer_key_html, book_html, build_pages, print_pdf
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import assets_for, book_problems
from qamra_workbook.render.spec import BookSpec, Child, Geometry, Numerals
from qamra_workbook.render.stickers import NAME as STICKERS
from qamra_workbook.render.stickers import render_sheet


@dataclass
class OrderFiles:
    interior: Path
    cover: Path
    answer_key: Path | None = None
    preflight: dict[str, dict[str, Any]] = field(default_factory=dict)  # file name → report
    pages: int = 0
    inserts: dict[str, Path] = field(default_factory=dict)  # print file name → the layered PDF (stickers)
    dies: dict[str, Path] = field(default_factory=dict)  # print file name → its die lines alone

    @property
    def passed(self) -> bool:
        return all(r.get("passed") for r in self.preflight.values())


def report(pdf: Path, g: Geometry) -> dict[str, Any]:
    return preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe).to_dict()


def stage_specs(
    child: Child,
    stage: int,
    *,
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    domain: str = "qamra.app",
    plan: Journey | None = None,
    numbers: list[int] | None = None,
    name_en: str = "",
) -> tuple[BookSpec, BookSpec]:
    """The stage's interior (all pages, or `numbers`) and its cover, checked before anything is drawn."""
    plan = plan or load(PLAN)
    layer = load_layer(stage)
    every = page_specs(plan, layer)
    pages = [p for p in every if numbers is None or p.number in numbers]
    interior = stage_book(pages, child, numerals=numerals, day=day, domain=domain, name_en=name_en)
    cover = stage_book(cover_specs(layer, len(every)), child, numerals=numerals, day=day, domain=domain)
    problems = layer_problems(plan, layer) + book_problems(interior)
    if problems:
        raise PageProblems("\n".join(problems))
    return interior, cover


async def render_book(book: BookSpec, assets: Assets, pdf: Path, *, key: Path | None = None) -> Path | None:
    """The book's PDF; with `key`, also its answer key (None when no page has answers)."""
    pages = build_pages(book, assets)
    await print_pdf(book_html(book, pages, assets), pdf.with_suffix(".html"), pdf, book.geometry)
    if key is None or not any(p.built.answer for p in pages):
        return None
    return await print_pdf(answer_key_html(book, pages, assets), key.with_suffix(".html"), key, book.geometry)


async def render_order(
    child: Child,
    stage: int,
    out: Path,
    *,
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    domain: str = "qamra.app",
    plan: Journey | None = None,
    name_en: str = "",
) -> OrderFiles:
    """Every file of one stage into `out`: interior.pdf, cover.pdf, answer-key.pdf and
    inserts/stickers.pdf (with inserts/stickers-die.pdf)."""
    out.mkdir(parents=True, exist_ok=True)
    interior, cover = stage_specs(
        child, stage, numerals=numerals, day=day, domain=domain, plan=plan, name_en=name_en
    )
    assets = assets_for(interior, out)
    key = await render_book(interior, assets, out / "interior.pdf", key=out / "answer-key.pdf")
    cover = covers.with_thumbs(
        cover, interior, out / "interior.pdf", out / "assets", covers.THUMBS["journey"]
    )
    await render_book(cover, assets, out / "cover.pdf")
    files = OrderFiles(out / "interior.pdf", out / "cover.pdf", key, pages=len(interior.pages))
    g = interior.geometry
    files.preflight = {"interior.pdf": report(files.interior, g), "cover.pdf": report(files.cover, g)}
    sheet = await render_sheet(interior, assets, out / "inserts")
    files.inserts[STICKERS], files.dies[STICKERS] = sheet.pdf, sheet.die
    files.preflight[f"inserts/{STICKERS}.pdf"] = sheet.report
    return files
