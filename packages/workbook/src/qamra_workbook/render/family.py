"""Render «مغامراتي مع عائلتي» from the book's plan (content/family-book/plan.yaml), personalized for the
sample child and family of content/family-book/samples.yaml.

    uv run python -m qamra_workbook.render.family --book [--size 21x28|a4|both]
    uv run python -m qamra_workbook.render.family --pages 6-23 [--size ...] [--name adventures-1-2]

`--book` renders all 112 pages as out/family-book/book-<size>.pdf and every insert sheet of the plan as
out/family-book/inserts/<id>-<size>.pdf (the art, with the die lines on their own optional-content layer)
plus <id>-<size>-die.pdf (the die lines alone). Pages come in book order from
`qamra_workbook.family.book_pages`; params the plan derives (the passport's stamps, the contents map) are
added here. Render params a page needs but the plan does not carry come from
content/family-book/page-params.yaml when it exists (the plan's own params win). Writes PNG previews,
contact sheets of spreads (right to left, the even page on the right, as the open book shows them) and
the preflight reports.
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
from qamra_workbook.family import FamilyPlan, Placed, book_pages, load
from qamra_workbook.render.dielines import LAYER, die_ink
from qamra_workbook.render.engine import book_html, build_pages, previews, print_pdf
from qamra_workbook.render.samples import FamilySamples, assets_for, book_problems, family_book
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, Geometry, PageSpec, from_family

PLAN = Path("content/family-book/plan.yaml")
SAMPLES = Path("content/family-book/samples.yaml")
PAGE_PARAMS = Path("content/family-book/page-params.yaml")
OUT = Path("out/family-book")
SIZES = ("21x28", "a4")


def page_range(text: str) -> list[int]:
    """«6-23», «37», or several: «1-5,37,47»."""
    out: list[int] = []
    for part in text.split(","):
        first, _, last = part.strip().partition("-")
        out += range(int(first), int(last or first) + 1)
    return out


def stamps(plan: FamilyPlan) -> list[dict[str, str]]:
    """Each adventure's passport stamp, in the book's order: its section and the badge it earns."""
    return [{"section": s.id, "label": s.badge} for s in plan.sections]


def toc_stops(plan: FamilyPlan, pages: list[Placed]) -> dict[str, Any]:
    """The contents map: every adventure's first page, and the front and back pages worth finding."""
    first: dict[str, int] = {}
    for p in pages:
        first.setdefault(p.section, p.n)
    marks = {"passport": "passport", "my-family": "family", "seven-day-challenge": "trophy"}
    extras = [
        {"icon": marks[p.page.type], "title": p.page.title, "n": p.n} for p in pages if p.page.type in marks
    ]
    extras.append({"icon": "cap", "title": pages[-1].page.title, "n": pages[-1].n})
    return {
        "stops": [{"section": s.id, "title": s.title_ar, "n": first[s.id]} for s in plan.sections],
        "extras": extras,
    }


def derived_params(plan: FamilyPlan, placed: Placed, pages: list[Placed]) -> dict[str, Any]:
    """Params that follow from the plan itself rather than being written on the page."""
    match placed.page.type:
        case "passport" | "badge-sticker-sheet":
            return {"stamps": stamps(plan)}
        case "toc":
            return toc_stops(plan, pages)
        case "recipe-cards":  # every recipe page's steps, in the book's order
            return {
                "recipes": [
                    {"title": a.title, "steps": page.params["steps"]}
                    for a in plan.activities
                    for page in a.pages
                    if page.type == "recipe-steps" and page.params.get("steps")
                ]
            }
    return {}


def plan_pages(
    plan: FamilyPlan, numbers: range | list[int], extra: dict[str, Any]
) -> tuple[list[PageSpec], list[int]]:
    """The plan's pages `numbers` as engine pages, with the page params the plan lacks; and which pages
    took params from `extra`."""
    specs, filled = [], []
    pages = book_pages(plan)
    for placed in pages:
        if placed.n not in numbers:
            continue
        spec = from_family(placed, plan)
        derived = derived_params(plan, placed, pages)
        if derived:
            spec = dataclasses.replace(spec, params={**derived, **spec.params})
        key = placed.activity.id if placed.activity else placed.section
        more = extra.get(key, {}).get(placed.page.type, {})
        if more:
            spec = dataclasses.replace(spec, params={**more, **spec.params})
            filled.append(placed.n)
        specs.append(spec)
    return specs, filled


def cover_specs(plan: FamilyPlan) -> list[PageSpec]:
    """The front and back cover as engine pages (printed on card, without page numbers)."""
    return [
        PageSpec(
            id=f"family-cover-{i}",
            type=page.type,
            number=0,
            section="front",
            title=page.title,
            instruction=page.instruction,
            params=dict(page.params),
        )
        for i, page in enumerate(plan.cover, start=1)
    ]


def insert_sheets(plan: FamilyPlan) -> list[tuple[str, list[PageSpec]]]:
    """Each insert of the plan as its print file's name and its sheets (engine pages without a page number).
    A sheet's `section` param picks its colors; the sticker sheet gets every adventure's stamp."""
    out = []
    for i, insert in enumerate(plan.inserts, start=1):
        name = insert.id or f"{insert.kind}-{i}"
        specs = []
        for k, sheet in enumerate(insert.sheets, start=1):
            params = dict(sheet.params)
            section = str(params.pop("section", "front"))
            placed = Placed(0, sheet, section, None)
            params = {**derived_params(plan, placed, []), **params}
            specs.append(
                PageSpec(
                    id=f"family-insert-{name}-{k}",
                    type=sheet.type,
                    number=0,
                    section=section,
                    title=sheet.title,
                    instruction=sheet.instruction,
                    params=params,
                    parent=tuple(sheet.parent),
                )
            )
        if specs:
            out.append((name, specs))
    return out


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


SPREADS_PER_SHEET = 12  # six rows of two spreads: readable at a glance


def spreads_sheets(pngs: list[Path], numbers: list[int], stem: Path) -> list[Path]:
    """The spreads on sheets of `SPREADS_PER_SHEET`: <stem>.png for a short run, <stem>-01.png… for the
    whole book."""
    spreads = spread_pairs(numbers)
    if len(spreads) <= SPREADS_PER_SHEET:
        return [spreads_sheet(pngs, numbers, stem.with_name(stem.name + ".png"))]
    by_n = dict(zip(numbers, pngs, strict=True))
    out = []
    for k in range(0, len(spreads), SPREADS_PER_SHEET):
        chunk = [n for pair in spreads[k : k + SPREADS_PER_SHEET] for n in reversed(pair) if n is not None]
        name = stem.with_name(f"{stem.name}-{k // SPREADS_PER_SHEET + 1:02d}.png")
        out.append(spreads_sheet([by_n[n] for n in chunk], chunk, name))
    return out


def _preflight(pdf: Path, g: Geometry) -> dict[str, Any]:
    return preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe).to_dict()


async def render(book: BookSpec, out: Path, name: str) -> dict[str, Any]:
    """The pages as a print PDF with previews, the spreads sheets and the preflight report."""
    out.mkdir(parents=True, exist_ok=True)
    assets = assets_for(book, out)
    pages = build_pages(book, assets)
    g = book.geometry
    pdf = await print_pdf(book_html(book, pages, assets), out / f"{name}.html", out / f"{name}.pdf", g)
    names = [f"p{p.spec.number:03d}-{p.spec.type}" for p in pages]
    pngs = previews(pdf, out / f"png-{name}", names, g)
    sheets = spreads_sheets(pngs, [p.spec.number for p in pages], out / f"{name}-spreads")
    report = _preflight(pdf, g)
    (out / f"{name}-preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    return {"pdf": str(pdf), "spreads": [str(s) for s in sheets], "preflight": report}


async def render_inserts(book: BookSpec, out: Path, name: str) -> dict[str, Any]:
    """An insert's sheets: the art PDF with the die lines on their own layer, the die PDF alone, previews of
    the art with the die lines over it, and the preflight report of the print file."""
    from qamra_workbook.render.family_order import render_insert  # (it imports this module)

    out.mkdir(parents=True, exist_ok=True)
    assets = assets_for(book, out.parent)
    pdf, die = await render_insert(book, assets, out, name)
    g = book.geometry
    names = [f"{name}-{i}-{p.type}" for i, p in enumerate(book.pages, start=1)]
    pngs = previews(pdf, out / "png", names, g)
    report = _preflight(pdf, g)
    report["die_ink"] = die_ink(die)
    (out / f"{name}-preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    return {"pdf": str(pdf), "die": str(die), "previews": [str(p) for p in pngs], "preflight": report}


async def render_cover(book: BookSpec, out: Path, name: str) -> dict[str, Any]:
    """The front and back cover (card), with previews and the preflight report."""
    assets = assets_for(book, out)
    pages = build_pages(book, assets)
    g = book.geometry
    pdf = await print_pdf(book_html(book, pages, assets), out / f"{name}.html", out / f"{name}.pdf", g)
    previews(pdf, out / f"png-{name}", [f"{name}-{p.spec.type}" for p in pages], g)
    return {"pdf": str(pdf), "preflight": _preflight(pdf, g)}


def _print_report(result: dict[str, Any], what: str) -> bool:
    report = result["preflight"]
    verdict = "passed" if report["passed"] else "FAILED"
    print(f"{result['pdf']} ({what}): preflight {verdict}")
    for check in report["checks"]:
        if not check["ok"]:
            print(f"  {'!' if check['level'] == 'warning' else '✗'} {check['name']}: {check['detail']}")
    if "die_ink" in report and not all(report["die_ink"]):
        print("  ✗ a sheet has no die lines")
        return False
    return bool(report["passed"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--book", action="store_true", help="the whole book and its inserts")
    parser.add_argument("--pages", default="6-23", help="a page or a range of pages, e.g. 6-23")
    parser.add_argument("--size", choices=[*SIZES, "both"], default="21x28")
    parser.add_argument("--name", default="adventures-1-2", help="file name of the PDF (without .pdf)")
    parser.add_argument("--no-inserts", action="store_true", help="with --book: the book pages only")
    parser.add_argument("--inserts-only", action="store_true", help="with --book: the insert sheets only")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    plan = load(PLAN)
    samples = load_samples(SAMPLES)
    if not isinstance(samples, FamilySamples):
        raise SystemExit(f"{SAMPLES} is not the family samples file")
    extra = yaml.safe_load(PAGE_PARAMS.read_text(encoding="utf-8")) if PAGE_PARAMS.exists() else {}
    numbers = list(range(1, len(book_pages(plan)) + 1)) if args.book else page_range(args.pages)
    specs, filled = plan_pages(plan, numbers, extra or {})
    if filled:
        print(f"page params from {PAGE_PARAMS}: {', '.join(f'p{n}' for n in filled)}")
    inserts = insert_sheets(plan) if args.book and not args.no_inserts else []
    passed = True
    for size in SIZES if args.size == "both" else (args.size,):
        book = family_book(samples, tuple(specs), size)
        problems = book_problems(book)
        if problems:
            print("\n".join(f"✗ {line}" for line in problems))
            return 1
        name = f"book-{size}" if args.book else args.name if size == SIZES[0] else f"{args.name}-{size}"
        if not args.inserts_only:
            result = asyncio.run(render(book, args.out, name))
            passed &= _print_report(result, f"{len(specs)} pages, {size}")
            print("  spreads:", *result["spreads"])
        if args.book:
            cover = family_book(samples, tuple(cover_specs(plan)), size)
            done_cover = asyncio.run(render_cover(cover, args.out, f"cover-{size}"))
            passed &= _print_report(done_cover, f"front and back, {size}")
        for insert, sheets in inserts:
            sheet_book = family_book(samples, tuple(sheets), size)
            done = asyncio.run(render_inserts(sheet_book, args.out / "inserts", f"{insert}-{size}"))
            passed &= _print_report(done, f"{len(sheets)} sheet(s), {size}, die lines on layer {LAYER}")
            print(f"  die lines alone: {done['die']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
