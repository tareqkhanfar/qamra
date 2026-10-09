"""Render a volume of «دوسية التأسيس» (Addendum 5) from its curriculum plan: every page in order, as a
print-ready PDF, for a child and their approved character.

**For an order** (the worker's `qamra_worker.jobs.workbook_book`): `render_order(child, level, volume, out)`
draws one volume for a real child (name, gender, character sheet, the parent's English spelling `name_en`,
numerals ١٢٣ by default): interior.pdf, cover.pdf (front and back on card) and answer-key.pdf, each with its
preflight. The interior is in colour; the black-and-white interior is not built yet, so `interior="bw"` raises
`VariantNotBuilt` (owner decision 2026-10-07: the B&W variants are off sale until it exists). The English name
page prints the parent's spelling; without one, a transliteration (`WorkbookFiles.name_en_guessed`).

**The CLI** renders the sample child (content/journey/samples.yaml) or a child given on the command line:

    uv run python -m qamra_workbook.render.workbook --level kg2 --volume 1 [--size a4] [--pages 1-40]
        [--numerals hindi|latin] [--name-en Layan] [--name ليان --gender f --sheet sheet.png] [--cover]
        [--out DIR]

Writes into out/workbook/: <level>-v<volume>.pdf (the volume), <level>-v<volume>-answer-key.pdf, the page
previews png-<level>-v<volume>/pNNN-<type>.png, a contact sheet of the open spreads
(<level>-v<volume>-spreads.png) and <level>-v<volume>-preflight.json; with `--cover` also
<level>-v<volume>-cover.pdf and png-<level>-v<volume>-cover/; then prints the preflight result.
A page whose checks fail, whose text overflows or whose printed text breaks a plan rule is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageDraw, ImageFont

from qamra_pdf import preflight
from qamra_pdf.render import FONTS_DIR
from qamra_workbook.curriculum import REPLACED_WORDS, SUBJECTS, Curriculum, load
from qamra_workbook.journey_book import english_name, uses_name_en
from qamra_workbook.names import can_trace
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import covers
from qamra_workbook.render.engine import (
    PageProblems,
    answer_key_html,
    book_html,
    build_pages,
    previews,
    print_pdf,
)
from qamra_workbook.render.foundation import VOLUME_AR, volume_book, volume_of
from qamra_workbook.render.journey_order import OrderFiles, render_book, report
from qamra_workbook.render.samples import SPECS, Samples, assets_for, book_problems
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, Child, Geometry, Numerals, PageSpec, product_geometry

# the repo's content/workbook (QAMRA_CONTENT_DIR overrides content/, as for the journey and the story themes)
CURRICULUM = (
    Path(os.environ.get("QAMRA_CONTENT_DIR") or Path(__file__).resolve().parents[5] / "content")
    / "workbook"
    / "curriculum"
)
OUT = Path("out/workbook")
SIZES = {"a4": None}  # the workbooks print on A4 (Addendum 5 §4); A5 comes later
NAMES_EN = {"ليان": "Layan"}  # the sample child's name in English letters, for the English name page
LEVELS = ("kg1", "kg2")
VOLUMES = (1, 2, 3)
Interior = Literal["color", "bw"]
# the back cover's line for grown-ups: the store's description of the series (content/store/catalog.yaml)
BLURB = "منهج متكامل للروضة في ثلاثة أجزاء، باسم طفلكم وشخصيته."


class VariantNotBuilt(ValueError):
    """A variant the engine cannot draw yet: the black-and-white interior."""


def printed_word_problems(book: BookSpec) -> list[str]:
    """Decision 7 on the printed texts: the replaced picture words never appear, «طائرة» only as a kite."""
    out = []
    for p in book.pages:
        text = strip_tashkeel(" ".join((p.title, p.instruction, p.skill)))
        words = text.replace("،", " ").replace("؟", " ").split()
        for i, w in enumerate(words):
            bare = w[2:] if w.startswith("ال") else w
            new = REPLACED_WORDS.get(bare)
            if not new:
                continue
            following = [x[2:] if x.startswith("ال") else x for x in words[i : i + len(new.split())]]
            if " ".join(following) != new:  # «الطائرة الورقية» is still a kite
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


def plan_of(level: str) -> Curriculum:
    if level not in LEVELS:
        raise ValueError(f"«دوسية التأسيس» has the levels {LEVELS}, not {level!r}")
    return load(CURRICULUM / f"{level}.yaml")


def _split(title: str) -> tuple[str, str]:
    """«الجزء الأول — أمسك قلمي…» or «الجزء الأول: أمسك قلمي…» → (the volume, its subtitle)."""
    for sep in (" — ", ": "):
        if sep in title:
            head, _, tail = title.partition(sep)
            return head.strip(), tail.strip()
    return title.strip(), ""


def cover_specs(plan: Curriculum, number: int, domain: str = "qamra.app") -> list[PageSpec]:
    """The volume's front and back cover (card, no page numbers): the product, the level, the volume and its
    subjects, from the plan."""
    volume = volume_of(plan, number)
    title, _, level = plan.title_ar.partition(" — ")
    chip, subtitle = _split(volume.title_v or volume.title_ar)
    taught = {unit.subject for unit in volume.units}
    subjects = [s for s in SUBJECTS if s in taught and s not in ("intro", "mixed")]
    params = {
        "title": title.strip(),
        "level": level.strip(),
        "code": plan.level.upper(),
        "volume": chip or VOLUME_AR.get(number, ""),
        "subtitle": subtitle,
        "ages": plan.age,
        "subjects": subjects,
        "blurb": BLURB,
        "domain": domain.strip().rstrip("/") or "qamra.app",
        "part": f"{plan.level}-v{number}",  # the cover's scene and copy (render/covers.py)
        "pages": len(volume.pages),
        "certificate": any(p.type == "certificate" for p in volume.pages),
    }
    return [
        PageSpec(
            id=f"{plan.level}-v{number}-cover-{side}",
            type=f"workbook-cover-{side}",
            number=0,
            section="intro",
            title=title.strip(),
            instruction=level.strip(),
            params=params,
        )
        for side in ("front", "back")
    ]


@dataclass
class WorkbookFiles(OrderFiles):
    """One volume's print files, with what the name pages printed (the order job flags a guess)."""

    name_en: str = ""  # the English spelling on the English name page
    name_en_guessed: bool = False  # the parent gave none: a transliteration was printed
    name_traceable: bool = True  # every word of the Arabic name could be traced (`names.can_trace`)


def volume_specs(
    child: Child,
    level: str,
    number: int,
    *,
    name_en: str = "",
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    domain: str = "qamra.app",
    pages: range | None = None,
) -> tuple[BookSpec, BookSpec, str, bool]:
    """The volume's interior and cover for `child`, checked before anything is drawn, with the English name
    the interior prints and whether it is a guess (only when a page prints it)."""
    plan = plan_of(level)
    latin, guessed = english_name(child, name_en)
    interior = volume_book(
        plan,
        number,
        child,
        name_en=latin,
        date=day,
        numerals=numerals,
        geometry=geometry_for("a4"),
        pages=pages,
    )
    cover = dataclasses.replace(interior, pages=tuple(cover_specs(plan, number, domain)))
    problems = book_problems(interior) + printed_word_problems(interior)
    if problems:
        raise PageProblems("\n".join(problems))
    return interior, cover, latin, guessed and any(uses_name_en(p) for p in interior.pages)


async def render_order(
    child: Child,
    level: str,
    number: int,
    out: Path,
    *,
    interior: Interior = "color",
    name_en: str = "",
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    domain: str = "qamra.app",
) -> WorkbookFiles:
    """Every file of one volume for an order into `out`: interior.pdf, cover.pdf and answer-key.pdf."""
    if interior != "color":
        raise VariantNotBuilt(
            "«دوسية التأسيس» has no black-and-white interior yet (owner decision 2026-10-07: the B&W "
            "variants are off sale until it exists); this volume can only be printed in colour"
        )
    out.mkdir(parents=True, exist_ok=True)
    book, cover, latin, guessed = volume_specs(
        child, level, number, name_en=name_en, numerals=numerals, day=day, domain=domain
    )
    assets = assets_for(book, out)
    key = await render_book(book, assets, out / "interior.pdf", key=out / "answer-key.pdf")
    cover = covers.with_thumbs(cover, book, out / "interior.pdf", out / "assets", covers.THUMBS["foundation"])
    await render_book(cover, assets, out / "cover.pdf")
    files = WorkbookFiles(
        out / "interior.pdf",
        out / "cover.pdf",
        key,
        pages=len(book.pages),
        name_en=latin,
        name_en_guessed=guessed,
        name_traceable=can_trace(child.name),
    )
    g = book.geometry
    files.preflight = {"interior.pdf": report(files.interior, g), "cover.pdf": report(files.cover, g)}
    return files


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


def cli_child(args: argparse.Namespace) -> Child:
    """The sample child, or the child given with --name/--gender/--sheet (a staff render of one order)."""
    if not args.name:
        return sample_child()
    sheet = Path(args.sheet) if args.sheet else None
    return Child(args.name, args.gender, sheet)


async def render_cover(book: BookSpec, out: Path, name: str) -> dict[str, Any]:
    """The cover PDF (front and back on card), its previews and its preflight."""
    assets = assets_for(book, out)
    pdf = out / f"{name}-cover.pdf"
    await render_book(book, assets, pdf)
    pngs = previews(pdf, out / f"png-{name}-cover", [p.type for p in book.pages], book.geometry)
    return {"pdf": pdf, "pngs": pngs, "preflight": {pdf.name: report(pdf, book.geometry)}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--level", choices=list(LEVELS), default="kg2")
    parser.add_argument("--volume", type=int, choices=list(VOLUMES), default=1)
    parser.add_argument("--size", default="a4", help="the print size (a4)")
    parser.add_argument("--pages", help="only these pages, e.g. 1-40 (for quick iterations)")
    parser.add_argument("--numerals", choices=["hindi", "latin"], default="hindi")
    parser.add_argument("--name-en", help="the child's name in English letters (default: the sample's)")
    parser.add_argument("--name", help="a child's name (default: the sample child)")
    parser.add_argument("--gender", choices=["f", "m"], default="f")
    parser.add_argument("--sheet", help="the child's character sheet (PNG), with --name")
    parser.add_argument("--cover", action="store_true", help="also render the cover (front and back)")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    geometry_for(args.size)
    child = cli_child(args)
    day = load_samples(SPECS["journey"]).date if not args.name else None
    try:
        book, cover, latin, guessed = volume_specs(
            child,
            args.level,
            args.volume,
            name_en=args.name_en or NAMES_EN.get(child.name, ""),
            numerals=args.numerals,
            day=day,
            pages=page_range(args.pages) if args.pages else None,
        )
    except PageProblems as e:
        print("\n".join(f"✗ {line}" for line in str(e).splitlines()))
        return 1
    if guessed:
        print(f"! no English spelling given: the English name page prints the guess «{latin}»")
    if not can_trace(child.name):
        print(f"! «{child.name}» cannot be traced whole in Arabic letters: the name page falls back")
    name = f"{args.level}-v{args.volume}" + ("" if args.numerals == "hindi" else "-latin")
    if args.pages:
        name += f"-p{args.pages}"
    result = asyncio.run(render(book, args.out, name))
    if args.cover:
        cover = covers.with_thumbs(
            cover, book, Path(result["pdf"]), args.out / "assets", covers.THUMBS["foundation"]
        )
        done = asyncio.run(render_cover(cover, args.out, name))
        result["preflight"].update(done["preflight"])
        print(f"wrote {done['pdf']}")
    passed = True
    for pdf_name, report_ in result["preflight"].items():
        verdict = "passed" if report_["passed"] else "FAILED"
        print(f"preflight {pdf_name}: {verdict} (min DPI {report_['min_dpi']})")
        for check in report_["checks"]:
            mark = "✓" if check["ok"] else ("!" if check["level"] == "warning" else "✗")
            print(f"  {mark} {check['name']}: {check['detail']}")
        passed &= bool(report_["passed"])
    print(f"wrote {result['pdf']} ({result['pages']} pages)")
    if result["answer_key"]:
        print(f"wrote {result['answer_key']}")
    print(f"wrote {result['spreads']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
