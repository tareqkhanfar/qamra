"""Render a volume of «دوسية التأسيس» (Addendum 5) from its curriculum plan, for the sample child and
character of the journey samples (content/journey/samples.yaml): every page in order, as a print-ready PDF.

    uv run python -m qamra_workbook.render.workbook --level kg2 --volume 1 [--size a4] [--pages 1-40]
                                                    [--numerals hindi|latin] [--name-en Layan] [--out DIR]

Writes into out/workbook/: <level>-v<volume>.pdf (the volume), <level>-v<volume>-answer-key.pdf, the page
previews png-<level>-v<volume>/pNNN-<type>.png, a contact sheet of the open spreads
(<level>-v<volume>-spreads.png) and <level>-v<volume>-preflight.json; then prints the preflight result.
A page whose checks fail, whose text overflows or whose printed text breaks a plan rule is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from qamra_pdf import preflight
from qamra_pdf.render import FONTS_DIR
from qamra_workbook.curriculum import REPLACED_WORDS, load
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.engine import answer_key_html, book_html, build_pages, previews, print_pdf
from qamra_workbook.render.foundation import volume_book
from qamra_workbook.render.samples import SPECS, Samples, assets_for, book_problems
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, Child, Geometry, product_geometry

CURRICULUM = Path("content/workbook/curriculum")
OUT = Path("out/workbook")
SIZES = {"a4": None}  # the workbooks print on A4 (Addendum 5 §4); A5 comes later
NAMES_EN = {"ليان": "Layan"}  # the sample child's name in English letters, for the English name page


def printed_word_problems(book: BookSpec) -> list[str]:
    """Decision 7 on the printed texts: the replaced picture words never appear, «طائرة» only as a kite."""
    out = []
    for p in book.pages:
        text = strip_tashkeel(" ".join((p.title, p.instruction, p.skill)))
        words = text.replace("،", " ").replace("؟", " ").split()
        for i, w in enumerate(words):
            bare = w[2:] if w.startswith("ال") else w
            new = REPLACED_WORDS.get(bare)
            if new and " ".join(words[i : i + len(new.split())]) != new:
                out.append(f"{p.id}: «{bare}» was replaced by «{new}» (decision 7)")
    return out


def spreads_sheet(pngs: list[Path], numbers: list[int], out: Path, per_row: int = 4) -> Path:
    """The pages as the open book shows them (right-bound: an even page on the right, the next odd page
    facing it on the left; page 1 alone on the left), spreads right to left along each row."""
    spreads: list[tuple[int | None, int | None]] = []
    for n in numbers:
        if n % 2 and spreads and spreads[-1] == (None, n - 1):
            spreads[-1] = (n, n - 1)
        else:
            spreads.append((None, n) if n % 2 == 0 else (n, None))
    by_n = dict(zip(numbers, pngs, strict=True))
    with Image.open(pngs[0]) as first:
        w, h = 210, round(first.height * 210 / first.width)
    gap, label_h = 26, 26
    rows = (len(spreads) + per_row - 1) // per_row
    sheet = Image.new("RGB", (per_row * (2 * w + gap) + gap, rows * (h + label_h + gap) + gap), "#F3EAD8")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansArabic-SemiBold.ttf"), 14)
    for i, (left, right) in enumerate(spreads):
        column = per_row - 1 - i % per_row
        x, y = gap + column * (2 * w + gap), gap + (i // per_row) * (h + label_h + gap)
        for page_n, dx in ((left, 0), (right, w)):
            if page_n is not None:
                with Image.open(by_n[page_n]) as img:
                    sheet.paste(img.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), (x + dx, y))
        draw.rectangle((x - 1, y - 1, x + 2 * w, y + h), outline="#D8C9AC")
        draw.line((x + w, y, x + w, y + h), fill="#C9B994", width=2)
        label = " | ".join(f"p{k}" for k in (left, right) if k is not None)
        draw.text((x + 2, y + h + 5), label, fill="#1C2140", font=font)
    sheet.save(out, optimize=True)
    return out


async def render(book: BookSpec, out: Path, name: str) -> dict[str, Any]:
    """The volume PDF, its answer key, previews, the spreads sheet and the preflight reports."""
    out.mkdir(parents=True, exist_ok=True)
    assets = assets_for(book, out)
    pages = build_pages(book, assets)
    g = book.geometry
    pdf = await print_pdf(book_html(book, pages, assets), out / f"{name}.html", out / f"{name}.pdf", g)
    key = None
    if any(p.built.answer for p in pages):
        key_html = answer_key_html(book, pages, assets)
        key = await print_pdf(key_html, out / f"{name}-answer-key.html", out / f"{name}-answer-key.pdf", g)
    names = [f"p{p.spec.number:03d}-{p.spec.type}" for p in pages]
    pngs = previews(pdf, out / f"png-{name}", names, g)
    sheet = spreads_sheet(pngs, [p.spec.number for p in pages], out / f"{name}-spreads.png")
    reports = {
        f.name: preflight(
            f, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe
        ).to_dict()
        for f in (pdf, key)
        if f is not None
    }
    (out / f"{name}-preflight.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), "utf-8")
    return {"pdf": pdf, "answer_key": key, "spreads": sheet, "pages": len(pages), "preflight": reports}


def sample_child() -> Child:
    samples = load_samples(SPECS["journey"])
    if not isinstance(samples, Samples):
        raise SystemExit("the journey samples file has no sample child")
    sheet = Path(samples.child.character_sheet) if samples.child.character_sheet else None
    return Child(samples.child.name, samples.child.gender, sheet)


def page_range(text: str) -> range:
    first, _, last = text.partition("-")
    return range(int(first), int(last or first) + 1)


def geometry_for(size: str) -> Geometry:
    if size not in SIZES:
        raise SystemExit(f"the workbook prints at {', '.join(SIZES)}, not {size}")
    return product_geometry("foundation", SIZES[size])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--level", choices=["kg1", "kg2"], default="kg2")
    parser.add_argument("--volume", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--size", default="a4", help="the print size (a4)")
    parser.add_argument("--pages", help="only these pages, e.g. 1-40 (for quick iterations)")
    parser.add_argument("--numerals", choices=["hindi", "latin"], default="hindi")
    parser.add_argument("--name-en", help="the child's name in English letters (default: the sample's)")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    plan = load(CURRICULUM / f"{args.level}.yaml")
    child = sample_child()
    book = volume_book(
        plan,
        args.volume,
        child,
        name_en=args.name_en or NAMES_EN.get(child.name, ""),
        numerals=args.numerals,
        geometry=geometry_for(args.size),
        pages=page_range(args.pages) if args.pages else None,
    )
    book = dataclasses.replace(book, date=load_samples(SPECS["journey"]).date or book.date)
    problems = book_problems(book) + printed_word_problems(book)
    if problems:
        print("\n".join(f"✗ {line}" for line in problems))
        return 1
    name = f"{args.level}-v{args.volume}" + ("" if args.numerals == "hindi" else "-latin")
    if args.pages:
        name += f"-p{args.pages}"
    result = asyncio.run(render(book, args.out, name))
    passed = True
    for pdf_name, report in result["preflight"].items():
        verdict = "passed" if report["passed"] else "FAILED"
        print(f"preflight {pdf_name}: {verdict} (min DPI {report['min_dpi']})")
        for check in report["checks"]:
            mark = "✓" if check["ok"] else ("!" if check["level"] == "warning" else "✗")
            print(f"  {mark} {check['name']}: {check['detail']}")
        passed &= bool(report["passed"])
    print(f"wrote {result['pdf']} ({result['pages']} pages)")
    if result["answer_key"]:
        print(f"wrote {result['answer_key']}")
    print(f"wrote {result['spreads']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
