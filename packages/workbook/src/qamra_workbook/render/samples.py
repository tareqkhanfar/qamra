"""Render the sample pages of a workbook product for approval: the 12 samples of «رحلتي الأولى للتعلّم»
(Addendum 6 §3.7) or the samples of «مغامراتي مع عائلتي» (Addendum 7 §3.5), with its inserts.

    uv run python -m qamra_workbook.render.samples [--product journey|family] [--spec FILE] [--out DIR]
                                                   [--only TYPE,TYPE]

Writes samples.pdf (print-ready), answer-key.pdf when a page has answers, inserts.pdf for the family book's
sticker sheet and card stock, png/NN-<type>.png previews, contact-sheet.png and preflight.json, then prints
the preflight result.
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
from pydantic import BaseModel, ConfigDict, Field

from qamra_pdf import preflight
from qamra_workbook.family import MAX_CHILD_WORDS
from qamra_workbook.family import Page as FamilyPage
from qamra_workbook.journey import MAX_INSTRUCTION_WORDS, JourneyPage
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.character import aspect, front_view, pose
from qamra_workbook.render.engine import (
    RenderedPage,
    answer_key_html,
    book_html,
    build_pages,
    contact_sheet,
    previews,
    print_pdf,
)
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import (
    ActivityTags,
    BookSpec,
    Child,
    Family,
    Figure,
    Member,
    PageSpec,
    Where,
    family_page_id,
    from_journey,
    product_geometry,
)

SPECS = {"journey": Path("content/journey/samples.yaml"), "family": Path("content/family-book/samples.yaml")}
OUTS = {"journey": Path("out/samples/journey"), "family": Path("out/samples/family")}
SPEC, OUT = SPECS["journey"], OUTS["journey"]
STORY_TYPES = {"section-opener"}  # their "instruction" is the story read to the child, not a mission


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


# ---- «مغامراتي مع عائلتي» ---------------------------------------------------------------------------------


class SampleMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    name: str = ""
    figure: Figure | None = None
    scarf: bool = False


class SampleFamily(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    city: str = ""
    members: list[SampleMember]

    def spec(self) -> Family:
        members = tuple(Member(m.role, m.name, m.figure, m.scarf) for m in self.members)
        return Family(self.name, members, self.city)


class SampleActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    where: Where = "home"
    together: bool = False
    minutes: int | None = None
    challenge: bool = False


class FamilySample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int  # the page number in the book; a section-opener is the spread n, n + 1
    section: str
    skill: str = ""
    activity: SampleActivity | None = None
    page: FamilyPage

    def specs(self) -> list[PageSpec]:
        tags = ActivityTags(**self.activity.model_dump()) if self.activity else None
        numbers = [self.n, self.n + 1] if self.page.type == "section-opener" else [self.n]
        return [
            PageSpec(
                id=family_page_id(n) if n else f"family-insert-{self.page.type}",
                type=self.page.type,
                number=n,
                section=self.section,
                title=self.page.title,
                instruction=self.page.instruction,
                skill=self.skill,
                params=self.page.params,
                parent=tuple(self.page.parent),
                activity=tags,
            )
            for n in numbers
        ]


class FamilySamples(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: Literal["family"]
    title_ar: str
    child: SampleChild
    family: SampleFamily
    date: dt.date | None = None
    samples: list[FamilySample]
    inserts: list[FamilySample] = Field(default_factory=list)


def load(path: Path) -> Samples | FamilySamples:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw.get("product") == "family":
        return FamilySamples.model_validate(raw)
    return Samples.model_validate(raw)


def _child(child: SampleChild) -> Child:
    sheet = Path(child.character_sheet) if child.character_sheet else None
    return Child(child.name, child.gender, sheet)


def book_problems(book: BookSpec) -> list[str]:
    """Rules the engine can check on its own, on the text as printed for this child and family: a short
    instruction (≤ 7 words in the journey, ≤ 10 in the family book), a title and an instruction on each
    page."""
    limit = MAX_CHILD_WORDS if book.product == "family" else MAX_INSTRUCTION_WORDS
    out = []
    for p in book.pages:
        texts = [] if p.type in STORY_TYPES else [book.personalize(p.instruction, p), p.instruction_en]
        for text in texts:
            words = len(text.split())
            if words > limit:
                out.append(f"{p.id}: instruction has {words} words (max {limit}): {text}")
        if not p.title.strip() or not p.instruction.strip():
            out.append(f"{p.id}: every page needs a title and an instruction")
    return out


def spec_problems(pages: list[PageSpec], child: Child) -> list[str]:
    """`book_problems` for journey pages."""
    return book_problems(BookSpec("journey", "", child, tuple(pages), dt.date.today()))


def book_from(samples: Samples | FamilySamples, only: set[str] | None = None) -> BookSpec:
    if isinstance(samples, FamilySamples):
        pages = tuple(
            spec for s in samples.samples if only is None or s.page.type in only for spec in s.specs()
        )
        return _family_book(samples, pages)
    pages = tuple(
        from_journey(s.page, s.stage) for s in samples.samples if only is None or s.page.type in only
    )
    return BookSpec(
        product=samples.product,
        title_ar=samples.title_ar,
        child=_child(samples.child),
        pages=pages,
        date=samples.date or dt.date.today(),
    )


def inserts_from(samples: Samples | FamilySamples, only: set[str] | None = None) -> BookSpec | None:
    """The family book's insert sheets, as a book of their own (they print on other paper)."""
    if not isinstance(samples, FamilySamples):
        return None
    pages = tuple(spec for s in samples.inserts if only is None or s.page.type in only for spec in s.specs())
    return _family_book(samples, pages) if pages else None


def _family_book(samples: FamilySamples, pages: tuple[PageSpec, ...]) -> BookSpec:
    return BookSpec(
        product="family",
        title_ar=samples.title_ar,
        child=_child(samples.child),
        pages=pages,
        date=samples.date or dt.date.today(),
        geometry=product_geometry("family"),
        family=samples.family.spec(),
    )


def assets_for(book: BookSpec, out: Path) -> Assets:
    """The picture library and the child's character cut out of the sheet (front view, and the waving pose
    when the sheet has one)."""
    sheet = book.child.character_sheet
    if not sheet:
        return Assets(LibraryStore())
    character = front_view(sheet, out / "assets")
    try:
        wave: Path | None = pose(sheet, out / "assets", 1)
    except ValueError:
        wave = None
    return Assets(
        LibraryStore(), character, aspect(character), wave, aspect(wave) if wave else Assets.wave_aspect
    )


def _label(i: int, p: RenderedPage) -> str:
    if p.spec.stage is not None:
        return f"{i:02d} · S{p.spec.stage} p{p.spec.number} · {p.spec.type}"
    where = f"p{p.spec.number}" if p.spec.number else "insert"
    return f"{i:02d} · {where} · {p.spec.type}"


async def render_samples(book: BookSpec, out: Path, inserts: BookSpec | None = None) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    assets = assets_for(book, out)
    pages = build_pages(book, assets)
    extra = build_pages(inserts, assets) if inserts else []
    g = book.geometry
    samples_pdf = await print_pdf(
        book_html(book, pages, assets), out / "samples.html", out / "samples.pdf", g
    )
    key_pdf = None
    if any(p.built.answer for p in pages):
        key_html = answer_key_html(book, pages, assets)
        key_pdf = await print_pdf(key_html, out / "answer-key.html", out / "answer-key.pdf", g)
    inserts_pdf = None
    if inserts and extra:
        inserts_pdf = await print_pdf(
            book_html(inserts, extra, assets), out / "inserts.html", out / "inserts.pdf", inserts.geometry
        )
    names = [f"{i:02d}-{p.spec.type}" for i, p in enumerate(pages, start=1)]
    pngs = previews(samples_pdf, out / "png", names, g)
    if inserts_pdf is not None and inserts is not None:
        insert_names = [f"{i:02d}-{p.spec.type}" for i, p in enumerate(extra, start=len(pages) + 1)]
        pngs += previews(inserts_pdf, out / "png", insert_names, inserts.geometry)
    labels = [_label(i, p) for i, p in enumerate([*pages, *extra], start=1)]
    sheet = contact_sheet(pngs, out / "contact-sheet.png", labels, rtl=book.product == "family")
    reports = {
        pdf.name: preflight(
            pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe
        ).to_dict()
        for pdf in (samples_pdf, key_pdf, inserts_pdf)
        if pdf is not None
    }
    result = {
        "samples_pdf": str(samples_pdf),
        "answer_key_pdf": str(key_pdf) if key_pdf else None,
        "inserts_pdf": str(inserts_pdf) if inserts_pdf else None,
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
    parser.add_argument("--product", choices=sorted(SPECS), default="journey")
    parser.add_argument("--spec", type=Path, help="default: the product's samples.yaml")
    parser.add_argument("--out", type=Path, help="default: out/samples/<product>")
    parser.add_argument("--only", help="comma-separated page types (for quick iterations)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    only = set(args.only.split(",")) if args.only else None
    samples = load(args.spec or SPECS[args.product])
    book, inserts = book_from(samples, only), inserts_from(samples, only)
    problems = book_problems(book) + (book_problems(inserts) if inserts else [])
    if problems:
        for line in problems:
            print("✗", line)
        return 1
    result = asyncio.run(render_samples(book, args.out or OUTS[args.product], inserts))
    passed = True
    for name, report in result["preflight"].items():
        print(f"preflight {name}:")
        for check in report["checks"]:
            mark = "✓" if check["ok"] else ("!" if check["level"] == "warning" else "✗")
            print(f"  {mark} {check['name']}: {check['detail']}")
        print("  passed" if report["passed"] else "  FAILED", f"(min image DPI {report['min_dpi']})")
        passed &= bool(report["passed"])
    written = [
        result["samples_pdf"],
        result["answer_key_pdf"],
        result["inserts_pdf"],
        result["contact_sheet"],
    ]
    print("wrote", *(w for w in written if w))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
