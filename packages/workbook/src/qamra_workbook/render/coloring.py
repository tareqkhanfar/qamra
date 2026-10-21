"""Render «دفاتر التلوين والرسم»: one copy for an order, or the samples for the owner and the website.

    uv run python -m qamra_workbook.render.coloring --title letters [--gender f|m] [--name ليان]
                                                    [--no-character] [--out DIR]

Writes interior.pdf and cover.pdf (print-ready: 3 mm bleed, trim/bleed boxes, fonts embedded, 300 DPI
pictures), png/NN.png previews, contact-sheet.png and preflight.json. The sample children are «ليان» (the
sample character of every activity book) and «يوسف» (the cartoon test sheet): AI-drawn samples, no real
child. Nothing here calls a paid API.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
from pathlib import Path
from typing import Any

from qamra_pdf import preflight
from qamra_pdf.imprint import Imprint
from qamra_workbook.coloring.book import book_spec, cover_pages, interior_pages, page_problems
from qamra_workbook.coloring.titles import TITLES, title_of
from qamra_workbook.render import covers
from qamra_workbook.render.engine import (
    PageProblems,
    book_html,
    build_pages,
    contact_sheet,
    previews,
    print_pdf,
)
from qamra_workbook.render.journey_order import OrderFiles
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import assets_for
from qamra_workbook.render.spec import BookSpec, Child, Geometry, Numerals

REPO = Path(__file__).resolve().parents[5]
SAMPLES = {
    "f": ("ليان", REPO / "content/workbook/samples/sample-character.png"),
    "m": ("يوسف", REPO / "packages/workbook/tests/fixtures/sheets/cartoon.webp"),
}
SAMPLE_DATE = dt.date(2026, 10, 21)
# what the back cover shows of the inside: the page types to prefer, slot by slot
THUMBS = {
    "letters": (("cb-letter",), ("cb-letter",), ("cb-letter",)),
    "palestine": (("cb-scene",), ("cb-scene",), ("cb-scene",)),
    "ramadan": (("cb-scene",), ("cb-scene",), ("cb-scene",)),
    "sketchbook": (("cb-draw",), ("cb-draw",), ("cb-draw",)),
}


def report(pdf: Path, g: Geometry, signature: int | None = None) -> dict[str, Any]:
    return preflight(
        pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe, signature=signature
    ).to_dict()


def specs(
    child: Child,
    title: str,
    *,
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    imprint: Imprint | None = None,
) -> tuple[BookSpec, BookSpec]:
    """The interior and the cover of one copy, checked before anything is drawn."""
    t = title_of(title)
    pages = interior_pages(t.key)
    problems = page_problems(t.key, pages)
    if problems:
        raise PageProblems("\n".join(problems))
    interior = book_spec(t.key, child, pages, numerals=numerals, day=day, imprint=imprint)
    cover = book_spec(t.key, child, cover_pages(t.key), numerals=numerals, day=day, imprint=imprint)
    return interior, cover


async def render_book(book: BookSpec, assets: Assets, pdf: Path) -> Path:
    pages = build_pages(book, assets)
    return await print_pdf(book_html(book, pages, assets), pdf.with_suffix(".html"), pdf, book.geometry)


async def render_copy(
    child: Child,
    title: str,
    out: Path,
    *,
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    domain: str = "qamra.app",
    imprint: Imprint | None = None,
) -> OrderFiles:
    """interior.pdf and cover.pdf of one copy into `out` (`render.coloring_order.render_order`)."""
    t = title_of(title)
    out.mkdir(parents=True, exist_ok=True)
    imprint = imprint or Imprint(child_name=child.name, gender=child.gender, product=t.name_plain)
    interior, cover = specs(child, t.key, numerals=numerals, day=day, imprint=imprint)
    assets = assets_for(interior, out)
    await render_book(interior, assets, out / "interior.pdf")
    cover = covers.with_thumbs(cover, interior, out / "interior.pdf", out / "assets", THUMBS[t.key])
    await render_book(cover, assets, out / "cover.pdf")
    files = OrderFiles(out / "interior.pdf", out / "cover.pdf", None, pages=len(interior.pages))
    files.cutout_fallback = assets.framed
    files.cutout_feet = assets.feet_cut
    g = interior.geometry
    files.preflight = {
        "interior.pdf": report(files.interior, g, t.signature),
        "cover.pdf": report(files.cover, g),
    }
    del domain  # the info page's QR follows the imprint's contact (admin settings)
    return files


def contact(files: OrderFiles, out: Path, g: Geometry) -> Path:
    """Cover then interior as PNGs and one contact sheet (right to left, as the book opens)."""
    cover_png = previews(files.cover, out / "png", ["00a-cover-front", "00b-cover-back"], g, dpi=80)
    names = [f"{i:02d}" for i in range(1, files.pages + 1)]
    pngs = previews(files.interior, out / "png", names, g, dpi=80)
    labels = ["الغلاف", "الغلاف الخلفي", *names]
    return contact_sheet([*cover_png, *pngs], out / "contact-sheet.png", labels, columns=6, rtl=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--title", required=True, choices=sorted(TITLES))
    ap.add_argument("--gender", default="f", choices=["f", "m"])
    ap.add_argument("--name")
    ap.add_argument("--no-character", action="store_true", help="the cover without the child's character")
    ap.add_argument("--numerals", default="hindi", choices=["hindi", "latin"])
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    name, sheet = SAMPLES[args.gender]
    child = Child(args.name or name, args.gender, None if args.no_character else sheet)
    out = (
        args.out
        or Path("out/coloring") / args.title / f"{args.gender}{'-plain' if args.no_character else ''}"
    )
    files = asyncio.run(render_copy(child, args.title, out, numerals=args.numerals, day=SAMPLE_DATE))
    (out / "preflight.json").write_text(
        json.dumps(files.preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sheet_png = contact(files, out, book_spec(args.title, child, []).geometry)
    for name_, rep in files.preflight.items():
        print(
            name_,
            "passed" if rep.get("passed") else "FAILED",
            [c for c in rep.get("checks", []) if not c.get("ok")],
        )
    print(f"{files.pages} pages · {sheet_png}")


if __name__ == "__main__":
    main()
