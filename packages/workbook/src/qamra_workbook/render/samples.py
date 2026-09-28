"""Render the 12 sample pages of «رحلتي الأولى للتعلّم» (Addendum 6 §3.7) for approval.

    uv run python -m qamra_workbook.render.samples [--spec content/journey/samples.yaml] [--out DIR]
                                                   [--only TYPE,TYPE]

Writes samples.pdf (print-ready), answer-key.pdf, png/NN-<type>.png previews, contact-sheet.png and
preflight.json, then prints the preflight result.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from qamra_pdf import preflight
from qamra_workbook.journey import MAX_INSTRUCTION_WORDS, JourneyPage
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.character import aspect, front_view
from qamra_workbook.render.engine import (
    answer_key_html,
    book_html,
    build_pages,
    contact_sheet,
    previews,
    print_pdf,
)
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import BookSpec, Child, PageSpec, from_journey

SPEC = Path("content/journey/samples.yaml")
OUT = Path("out/samples/journey")


class SampleChild(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    gender: Literal["m", "f"]
    character_sheet: str | None = None  # front view + two poses (qamra_ai character sheet)


class Sample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: int
    page: JourneyPage


class Samples(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: str
    title_ar: str
    child: SampleChild
    date: dt.date | None = None
    samples: list[Sample]


def load(path: Path) -> Samples:
    return Samples.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def spec_problems(pages: list[PageSpec], child: Child) -> list[str]:
    """Addendum 6 §6 rules the engine can check on its own (on the text as printed for this child)."""
    out = []
    for p in pages:
        for text in (child.personalize(p.instruction), p.instruction_en):
            words = len(text.split())
            if words > MAX_INSTRUCTION_WORDS:
                out.append(f"{p.id}: instruction has {words} words (max {MAX_INSTRUCTION_WORDS}): {text}")
        if not p.title.strip() or not p.instruction.strip():
            out.append(f"{p.id}: every page needs a title and an instruction")
    return out


def book_from(samples: Samples, only: set[str] | None = None) -> BookSpec:
    sheet = Path(samples.child.character_sheet) if samples.child.character_sheet else None
    pages = tuple(
        from_journey(s.page, s.stage) for s in samples.samples if only is None or s.page.type in only
    )
    return BookSpec(
        product=samples.product,
        title_ar=samples.title_ar,
        child=Child(samples.child.name, samples.child.gender, sheet),
        pages=pages,
        date=samples.date or dt.date.today(),
    )


async def render_samples(book: BookSpec, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    assets = Assets(LibraryStore())
    if book.child.character_sheet:
        character = front_view(book.child.character_sheet, out / "assets")
        assets = Assets(LibraryStore(), character, aspect(character))
    pages = build_pages(book, assets)
    g = book.geometry
    samples_pdf = await print_pdf(
        book_html(book, pages, assets), out / "samples.html", out / "samples.pdf", g
    )
    key_pdf = None
    if any(p.built.answer for p in pages):
        key_html = answer_key_html(book, pages, assets)
        key_pdf = await print_pdf(key_html, out / "answer-key.html", out / "answer-key.pdf", g)
    names = [f"{i:02d}-{p.spec.type}" for i, p in enumerate(pages, start=1)]
    pngs = previews(samples_pdf, out / "png", names, g)
    labels = [
        f"{i:02d} · S{p.spec.stage} p{p.spec.number} · {p.spec.type}" for i, p in enumerate(pages, start=1)
    ]
    sheet = contact_sheet(pngs, out / "contact-sheet.png", labels)
    reports = {
        pdf.name: preflight(
            pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe
        ).to_dict()
        for pdf in (samples_pdf, key_pdf)
        if pdf is not None
    }
    result = {
        "samples_pdf": str(samples_pdf),
        "answer_key_pdf": str(key_pdf) if key_pdf else None,
        "previews": [str(p) for p in pngs],
        "contact_sheet": str(sheet),
        "preflight": reports,
    }
    (out / "preflight.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--spec", type=Path, default=SPEC)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--only", help="comma-separated page types (for quick iterations)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    only = set(args.only.split(",")) if args.only else None
    book = book_from(load(args.spec), only)
    problems = spec_problems(list(book.pages), book.child)
    if problems:
        for line in problems:
            print("✗", line)
        return 1
    result = asyncio.run(render_samples(book, args.out))
    passed = True
    for name, report in result["preflight"].items():
        print(f"preflight {name}:")
        for check in report["checks"]:
            mark = "✓" if check["ok"] else ("!" if check["level"] == "warning" else "✗")
            print(f"  {mark} {check['name']}: {check['detail']}")
        print("  passed" if report["passed"] else "  FAILED", f"(min image DPI {report['min_dpi']})")
        passed &= bool(report["passed"])
    print(
        "wrote", result["samples_pdf"], result["answer_key_pdf"] or "(no answer key)", result["contact_sheet"]
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
