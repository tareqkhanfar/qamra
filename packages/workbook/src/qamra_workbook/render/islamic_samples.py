"""Render the 12 sample pages of «قلبي يعرف الله» (Addendum 10 §4.8), personalized for the sample child.

    uv run python -m qamra_workbook.render.islamic_samples [--size 21x28|a4] [--print] [--only s01,s02]
    [--out DIR]
                                                           [--gender m|f] [--name NAME] [--review-marks]

Writes, under out/samples/islamic/: png/<id>.png (about 150 DPI, cropped to the trim), contact-sheet.png,
samples.pdf (print-ready, fonts embedded, 3 mm bleed) with preflight.json, and answer-key.pdf for the pages
that have
answers. A preview build prints a source's candidate text or a clearly marked placeholder block where the
verified text
is missing, and marks the drafter's own texts. `--print` checks first and writes NOTHING while any
placeholder or any
source that is not `scholar_approved` remains. No religious wording is typed here: it comes from
`islamic_sources`.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from qamra_pdf import preflight
from qamra_workbook import islamic_checks as checks
from qamra_workbook.islamic_sources import SAMPLES, Resolver, SourceError
from qamra_workbook.render.engine import (
    PageProblems,
    answer_key_html,
    book_html,
    build_pages,
    contact_sheet,
    previews,
    print_pdf,
)
from qamra_workbook.render.islamic_content import IslamicContext, Page, load_pages, page_spec
from qamra_workbook.render.islamic_figures import SAMPLE_SHEET, kit_for
from qamra_workbook.render.samples import assets_for
from qamra_workbook.render.spec import BookSpec, Child, product_geometry

OUT = Path("out/samples/islamic")
SIZES = ("21x28", "a4")
TITLE_AR = "قلبي يعرف الله"
MAX_INSTRUCTION_WORDS = 7  # a child's instruction (Addendum 10 §4: short, readable by a 4-6 year old)
SAMPLE_DATE = dt.date(2026, 10, 1)
CHILDREN = {"f": "ليان", "m": "يوسف"}
# the fields of a page that tell the child what to do (≤ 7 words each)
INSTRUCTION_FIELDS = ("instruction", "tracker", "stars", "role_play", "draw_box")


def instruction_problems(pages: list[Page], book: BookSpec) -> list[str]:
    out = []
    for page in pages:
        for name in INSTRUCTION_FIELDS:
            text = getattr(page, name, "")
            if isinstance(text, str) and text:
                words = book.words(text)  # the child's name is one word, however long
                if words > MAX_INSTRUCTION_WORDS:
                    out.append(f"{page.id}: {name} has {words} words (max {MAX_INSTRUCTION_WORDS}): {text}")
    return out


def sample_book(
    pages: list[Page],
    context: IslamicContext,
    child: Child,
    size: str,
    out: Path,
    only: set[str] | None = None,
) -> BookSpec:
    picked = [
        (i, p)
        for i, p in enumerate(pages, start=1)
        if only is None or p.id in only or p.id.split("-")[0] in only
    ]
    return BookSpec(
        product="islamic",
        title_ar=TITLE_AR,
        child=child,
        pages=tuple(page_spec(p, i, context) for i, p in picked),
        date=context.date,
        geometry=product_geometry("family", size),
    )


async def render(book: BookSpec, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    assets = assets_for(book, out)
    pages = build_pages(book, assets)
    g = book.geometry
    pdf = await print_pdf(book_html(book, pages, assets), out / "samples.html", out / "samples.pdf", g)
    pngs = previews(pdf, out / "png", [p.spec.id for p in pages], g, dpi=150)
    sheet = contact_sheet(
        pngs,
        out / "contact-sheet.png",
        [f"{p.spec.number:02d} · {p.spec.id}" for p in pages],
        columns=4,
        rtl=True,
    )
    key = None
    if any(p.built.answer for p in pages):
        key = await print_pdf(
            answer_key_html(book, pages, assets), out / "answer-key.html", out / "answer-key.pdf", g
        )
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe).to_dict()
    (out / "preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "pdf": str(pdf),
        "pngs": [str(p) for p in pngs],
        "sheet": str(sheet),
        "key": str(key) if key else None,
        "preflight": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--size", choices=SIZES, default="21x28")
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_build",
        help="a print build: fails on any placeholder or unapproved source",
    )
    parser.add_argument("--only", help="comma-separated page ids or prefixes (s01,s02-wudu)")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--samples", type=Path, default=SAMPLES)
    parser.add_argument("--gender", choices=("m", "f"), default="f")
    parser.add_argument("--name", help="the sample child's name (default: ليان / يوسف)")
    parser.add_argument(
        "--review-marks", action="store_true", help="mark the points the scholar still decides"
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    only = set(args.only.split(",")) if args.only else None
    try:
        resolver = Resolver.load()
        pages = load_pages(args.samples)
    except (SourceError, ValueError) as err:
        print(f"✗ {err}")
        return 1
    raw = checks.load_pages(args.samples)
    found = [*checks.check_register(resolver), *checks.check_pages(raw, resolver, checks.PageRules.load())]
    if args.print_build:
        found += checks.check_print(raw, resolver)
    for problem in found:
        print(problem)
    failures = checks.errors(found)
    if args.print_build and failures:
        print(f"✗ print build refused: {len(failures)} problem(s); nothing was written")
        return 1
    child = Child(
        args.name or CHILDREN[args.gender], args.gender, SAMPLE_SHEET if SAMPLE_SHEET.is_file() else None
    )
    out = args.out
    kit = kit_for(child.character_sheet, out / "assets")
    context = IslamicContext(
        resolver, kit, "print" if args.print_build else "preview", SAMPLE_DATE, args.review_marks
    )
    book = sample_book(pages, context, child, args.size, out, only)
    words = instruction_problems(pages, book)
    for line in words:
        print(f"✗ {line}")
    if words:
        return 1
    try:
        result = asyncio.run(render(book, out))
    except PageProblems as err:
        print(f"✗ {err}")
        return 1
    report = result["preflight"]
    print(
        f"{result['pdf']}: preflight {'passed' if report['passed'] else 'FAILED'} "
        f"(min image DPI {report.get('min_dpi')})"
    )
    for check in report["checks"]:
        if not check["ok"]:
            print(f"  {'!' if check['level'] == 'warning' else '✗'} {check['name']}: {check['detail']}")
    print("contact sheet:", result["sheet"])
    return 0 if report["passed"] and not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
