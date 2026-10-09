"""Render a stage of «رحلتي الأولى للتعلّم» from the plan and its print layer (content/journey/), personalized
for the sample child of content/journey/samples.yaml (an invented «ليان», AI-drawn character).

    uv run python -m qamra_workbook.render.journey --stage 1 --book
    uv run python -m qamra_workbook.render.journey --stage 1 --pages 1-20 [--name first-20] [--numerals latin]

`--book` renders every page of the stage as out/journey/stage-<n>/book.pdf, the cover as cover.pdf and the
parents' answer key as answer-key.pdf; `--pages` renders a range. Writes PNG previews (png-<name>/), contact
sheets of spreads (right to left, as the open book shows them) and the preflight reports, then prints them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from qamra_workbook.render import covers
from qamra_workbook.render.engine import previews
from qamra_workbook.render.family import _print_report, page_range, spreads_sheets
from qamra_workbook.render.journey_order import render_book, report, stage_specs
from qamra_workbook.render.samples import SPECS, Samples, _child, assets_for
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, Numerals

OUT = Path("out/journey")


async def render(book: BookSpec, cover: BookSpec | None, out: Path, name: str) -> dict[str, Any]:
    """The pages as a print PDF (with the answer key for a whole book), previews, spreads and preflight."""
    out.mkdir(parents=True, exist_ok=True)
    assets = assets_for(book, out)
    pdf = out / f"{name}.pdf"
    key = await render_book(book, assets, pdf, key=out / "answer-key.pdf" if cover else None)
    names = [f"p{p.number:03d}-{p.type}" for p in book.pages]
    pngs = previews(pdf, out / f"png-{name}", names, book.geometry)
    sheets = spreads_sheets(pngs, [p.number for p in book.pages], out / f"{name}-spreads")
    result: dict[str, Any] = {
        "pdf": str(pdf),
        "spreads": [str(s) for s in sheets],
        "preflight": report(pdf, book.geometry),
    }
    (out / f"{name}-preflight.json").write_text(
        json.dumps(result["preflight"], ensure_ascii=False, indent=2), "utf-8"
    )
    if key is not None:
        result["answer_key"] = str(key)
    if cover is not None:
        cover_pdf = out / "cover.pdf"
        cover = covers.with_thumbs(cover, book, pdf, out / "assets", covers.THUMBS["journey"])
        await render_book(cover, assets, cover_pdf)
        previews(cover_pdf, out / "png-cover", [p.type for p in cover.pages], cover.geometry)
        result["cover"] = {"pdf": str(cover_pdf), "preflight": report(cover_pdf, cover.geometry)}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--stage", type=int, default=1)
    parser.add_argument("--book", action="store_true", help="the whole stage, its cover and answer key")
    parser.add_argument("--pages", default="1-20", help="a page or a range of pages, e.g. 1-20")
    parser.add_argument("--name", default="", help="file name of the PDF (without .pdf)")
    parser.add_argument("--numerals", choices=["hindi", "latin"], default="hindi")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    samples = load_samples(SPECS["journey"])
    if not isinstance(samples, Samples):
        raise SystemExit("content/journey/samples.yaml is not the journey samples file")
    numerals: Numerals = args.numerals
    numbers = None if args.book else page_range(args.pages)
    book, cover = stage_specs(
        _child(samples.child), args.stage, numerals=numerals, day=samples.date, numbers=numbers
    )
    name = args.name or ("book" if args.book else f"pages-{args.pages}")
    result = asyncio.run(render(book, cover if args.book else None, args.out / f"stage-{args.stage}", name))
    passed = _print_report(result, f"stage {args.stage}, {len(book.pages)} pages")
    if "cover" in result:
        passed &= _print_report(result["cover"], "front and back")
    if "answer_key" in result:
        print(f"  answer key: {result['answer_key']}")
    print("  spreads:", *result["spreads"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
