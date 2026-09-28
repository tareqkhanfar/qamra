"""Render pages of «مغامراتي مع عائلتي» from the book's plan (content/family-book/plan.yaml), personalized for
the sample child and family of content/family-book/samples.yaml: the start of the full-book pipeline.

    uv run python -m qamra_workbook.render.family --pages 6-23 [--size 21x28|a4|both] [--name adventures-1-2]

Pages come in book order from `qamra_workbook.family.book_pages`. Render params a page needs but the plan does
not carry yet come from content/family-book/page-params.yaml (keyed by activity id and page type; the plan's
own params win). Writes <name>.pdf (and <name>-a4.pdf) into out/family-book/, PNG previews, a contact sheet
of spreads (right to left, the even page on the right, as the open book shows them) and preflight.json.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageFont

from qamra_pdf import preflight
from qamra_pdf.render import FONTS_DIR
from qamra_workbook.family import FamilyPlan, book_pages, load
from qamra_workbook.render.engine import book_html, build_pages, previews, print_pdf
from qamra_workbook.render.samples import FamilySamples, assets_for, book_problems, family_book
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, PageSpec, from_family

PLAN = Path("content/family-book/plan.yaml")
SAMPLES = Path("content/family-book/samples.yaml")
PAGE_PARAMS = Path("content/family-book/page-params.yaml")
OUT = Path("out/family-book")
SIZES = ("21x28", "a4")


def page_range(text: str) -> range:
    first, _, last = text.partition("-")
    return range(int(first), int(last or first) + 1)


def plan_pages(plan: FamilyPlan, numbers: range, extra: dict[str, Any]) -> tuple[list[PageSpec], list[int]]:
    """The plan's pages `numbers` as engine pages, with the page params the plan lacks; and which pages
    took params from `extra`."""
    specs, filled = [], []
    for placed in book_pages(plan):
        if placed.n not in numbers:
            continue
        spec = from_family(placed, plan)
        key = placed.activity.id if placed.activity else placed.section
        more = extra.get(key, {}).get(placed.page.type, {})
        if more:
            spec = dataclasses.replace(spec, params={**more, **spec.params})
            filled.append(placed.n)
        specs.append(spec)
    return specs, filled


def spread_pairs(numbers: list[int]) -> list[tuple[int | None, int | None]]:
    """(left page, right page) for each open spread of a right-bound book: an even page opens a spread on
    the right, the odd page after it faces it on the left."""
    spreads: list[tuple[int | None, int | None]] = []
    for n in numbers:
        if n % 2 and spreads and spreads[-1] == (None, n - 1):
            spreads[-1] = (n, n - 1)
        else:
            spreads.append((None, n) if n % 2 == 0 else (n, None))
    return spreads


def spreads_sheet(pngs: list[Path], numbers: list[int], out: Path, per_row: int = 2) -> Path:
    """The pages as the open book shows them: each spread's even page on the right and odd page on the
    left, spreads right to left along each row, a lone first or last page on its own side."""
    with Image.open(pngs[0]) as first:
        w, h = 260, round(first.height * 260 / first.width)
    by_n = dict(zip(numbers, pngs, strict=True))
    spreads = spread_pairs(numbers)
    gap, label_h = 34, 30
    rows = (len(spreads) + per_row - 1) // per_row
    sheet = Image.new("RGB", (per_row * (2 * w + gap) + gap, rows * (h + label_h + gap) + gap), "#F3EAD8")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansArabic-SemiBold.ttf"), 15)
    for i, (left, right) in enumerate(spreads):
        column = per_row - 1 - i % per_row  # right to left
        x, y = gap + column * (2 * w + gap), gap + (i // per_row) * (h + label_h + gap)
        for page_n, dx in ((left, 0), (right, w)):
            if page_n is None:
                continue
            with Image.open(by_n[page_n]) as img:
                sheet.paste(img.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), (x + dx, y))
        draw.rectangle((x - 1, y - 1, x + 2 * w, y + h), outline="#D8C9AC")
        draw.line((x + w, y, x + w, y + h), fill="#C9B994", width=2)
        label = " | ".join(f"p{k}" for k in (left, right) if k is not None)
        draw.text((x + 2, y + h + 7), label, fill="#1C2140", font=font)
    sheet.save(out, optimize=True)
    return out


async def render(book: BookSpec, out: Path, name: str) -> dict[str, Any]:
    """The pages as a print PDF with previews, the spreads sheet and the preflight report."""
    out.mkdir(parents=True, exist_ok=True)
    assets = assets_for(book, out)
    pages = build_pages(book, assets)
    g = book.geometry
    pdf = await print_pdf(book_html(book, pages, assets), out / f"{name}.html", out / f"{name}.pdf", g)
    names = [f"p{p.spec.number:03d}-{p.spec.type}" for p in pages]
    pngs = previews(pdf, out / f"png-{name}", names, g)
    sheet = spreads_sheet(pngs, [p.spec.number for p in pages], out / f"{name}-spreads.png")
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe).to_dict()
    (out / f"{name}-preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    return {"pdf": str(pdf), "spreads": str(sheet), "preflight": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pages", default="6-23", help="a page or a range of pages, e.g. 6-23")
    parser.add_argument("--size", choices=[*SIZES, "both"], default="21x28")
    parser.add_argument("--name", default="adventures-1-2", help="file name of the PDF (without .pdf)")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    plan = load(PLAN)
    samples = load_samples(SAMPLES)
    if not isinstance(samples, FamilySamples):
        raise SystemExit(f"{SAMPLES} is not the family samples file")
    extra = yaml.safe_load(PAGE_PARAMS.read_text(encoding="utf-8")) if PAGE_PARAMS.exists() else {}
    specs, filled = plan_pages(plan, page_range(args.pages), extra or {})
    if filled:
        print(f"page params from {PAGE_PARAMS}: {', '.join(f'p{n}' for n in filled)}")
    passed = True
    for size in SIZES if args.size == "both" else (args.size,):
        book = family_book(samples, tuple(specs), size)
        problems = book_problems(book)
        if problems:
            print("\n".join(f"✗ {line}" for line in problems))
            return 1
        name = args.name if size == SIZES[0] else f"{args.name}-{size}"
        result = asyncio.run(render(book, args.out, name))
        report = result["preflight"]
        verdict = "passed" if report["passed"] else "FAILED"
        print(f"{result['pdf']} ({len(specs)} pages, {size}): preflight {verdict}")
        for check in report["checks"]:
            if not check["ok"]:
                print(f"  {'!' if check['level'] == 'warning' else '✗'} {check['name']}: {check['detail']}")
        print(f"  spreads: {result['spreads']}")
        passed &= bool(report["passed"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
