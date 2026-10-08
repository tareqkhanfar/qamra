"""The reward sticker sheet of «رحلتي الأولى للتعلّم» (a stage) and «قلبي يعرف الله» (a volume) as a print
file.

The sheet is one A4 page of matte sticker paper with kiss-cut lines, printed apart from the book like the
family book's (`render.family_order.render_insert`): `stickers.pdf` (the art, with the cut lines on the
optional layer «CutContour») and `stickers-die.pdf` (the cut lines alone). What it holds is read from the
very pages of the book being printed (`pages.reward_stickers.journey_needs` / `islamic_needs`). The order
jobs store it as `book.generation["files"]["stickers"]`: the print batch sends it to the printer as an
insert, and a digital copy's download includes it (docs/plans/order-flows.md, «The included sticker
sheets»).

    uv run python -m qamra_workbook.render.stickers --journey 1 [--name ليان --gender f] [--out DIR]
    uv run python -m qamra_workbook.render.stickers --islamic v1 [--name ليان --gender f] [--out DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qamra_pdf import preflight
from qamra_workbook.render.dielines import die_ink
from qamra_workbook.render.engine import previews
from qamra_workbook.render.family_order import render_insert
from qamra_workbook.render.pages.reward_stickers import (
    IslamicNeeds,
    JourneyNeeds,
    islamic_needs,
    journey_needs,
)
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import BookSpec, Geometry, PageSpec

NAME = "stickers"  # the insert's name: `generation["files"]["stickers"]`, `printing.INSERT_LABELS`
SHEET = Geometry(safe=9.0)  # A4 sticker paper, whatever the book's size; a kiss-cut sheet needs less margin
TITLE = {"journey": "وَرَقَةُ المُلْصَقاتِ", "islamic": "وَرَقَةُ الْمُلْصَقَاتِ"}
INSTRUCTION = {  # the family sheet's words (language-reviewed), in each series' spelling
    "journey": "{انْزِعْ/انْزِعي} كُلَّ مُلْصَقٍ بِرِفْقٍ، {وَأَلْصِقْهُ/وَأَلْصِقيهِ} فِي مَكانِهِ مِنَ الكِتابِ",
    "islamic": "{انْزِعْ/انْزِعِي} كُلَّ مُلْصَقٍ بِرِفْقٍ، {وَأَلْصِقْهُ/وَأَلْصِقِيهِ} فِي مَكَانِهِ مِنَ الْكِتَابِ",
}
SECTION = {"journey": "intro", "islamic": "finale"}
STAGE_NAMES = {1: "المحطّة الأولى", 2: "المحطّة الثانية", 3: "المحطّة الثالثة"}  # as «للتعلّم» beside it
# the footer never names the Islamic series or a volume's title: they carry the name of Allah or ﷺ, and
# the sheet's backing is thrown away
VOLUME_NAMES = {
    "V1": "المجلّد الأوّل",
    "V2": "المجلّد الثاني",
    "V3": "المجلّد الثالث",
    "V4": "المجلّد الرابع",
    "V5": "المجلّد الخامس",
    "R": "كتاب رمضان والعيد",
}


def brand_line(needs: JourneyNeeds | IslamicNeeds) -> str:
    if isinstance(needs, JourneyNeeds):
        return f"قمرة · رحلتي الأولى للتعلّم · {STAGE_NAMES.get(needs.stage, '')}"
    return f"قمرة · {VOLUME_NAMES.get(needs.volume.upper(), needs.volume)}"


def needs_of(book: BookSpec) -> JourneyNeeds | IslamicNeeds:
    """What the book's pages ask the child to stick."""
    if book.product == "journey":
        return journey_needs(book.pages)
    if book.product == "islamic":
        return islamic_needs(book.pages)
    raise ValueError(f"no reward sticker sheet for {book.product!r}")


def sheet_book(book: BookSpec, needs: JourneyNeeds | IslamicNeeds | None = None) -> BookSpec:
    """The sticker sheet of `book` (the interior, for the same child) as a one-page book on A4."""
    needs = needs or needs_of(book)
    page = PageSpec(
        id=f"{book.product}-stickers",
        type="reward-stickers",
        number=0,
        section=SECTION[book.product],
        title=TITLE[book.product],
        instruction=INSTRUCTION[book.product],
        params={"needs": needs, "brand": brand_line(needs)},
    )
    return BookSpec(
        product=book.product,
        title_ar=book.title_ar,
        child=book.child,
        pages=(page,),
        date=book.date,
        numerals=book.numerals,
        geometry=SHEET,
    )


@dataclass
class SheetFiles:
    pdf: Path  # the art with its die lines on the «CutContour» layer
    die: Path  # the die lines alone
    report: dict[str, Any] = field(default_factory=dict)  # preflight, with `die_ink`
    stickers: int = 0

    @property
    def passed(self) -> bool:
        return bool(self.report.get("passed"))


async def render_sheet(book: BookSpec, assets: Assets, out: Path, *, name: str = NAME) -> SheetFiles:
    """`book`'s sticker sheet into `out`: <name>.pdf and <name>-die.pdf, with the preflight of the sheet (a
    die with no line on it fails it)."""
    sheet = sheet_book(book)
    pdf, die = await render_insert(sheet, assets, out, name)
    g = sheet.geometry
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe).to_dict()
    report["die_ink"] = die_ink(die)
    if not all(report["die_ink"]):
        report["passed"] = False
    needs = sheet.pages[0].params["needs"]
    return SheetFiles(pdf, die, report, needs.total)


# ---- the staff CLI: one sheet for the sample child --------------------------------------------------


def _journey_book(stage: int, child: Any, numerals: str) -> BookSpec:
    from qamra_workbook.render.journey_order import stage_specs

    interior, _ = stage_specs(child, stage, numerals=numerals, day=dt.date(2026, 10, 1))  # type: ignore[arg-type]
    return interior


def _islamic_book(volume: str, child: Any, numerals: str, out: Path) -> BookSpec:
    from qamra_workbook import islamic
    from qamra_workbook.islamic_sources import Resolver
    from qamra_workbook.render.islamic_content import IslamicContext
    from qamra_workbook.render.islamic_figures import kit_for
    from qamra_workbook.render.islamic_volume import check_volume, volume_book, volume_id

    vid = volume_id(volume)
    plan, resolver = islamic.load(), Resolver.load()
    content = check_volume(plan, vid, resolver)
    kit = kit_for(child.character_sheet, out / "assets")
    context = IslamicContext(resolver, kit, "preview", dt.date(2026, 10, 1))
    return volume_book(plan, content, context, child, numerals=numerals)  # type: ignore[arg-type]


def main(argv: list[str] | None = None) -> int:
    from qamra_workbook.render.islamic_figures import SAMPLE_SHEET
    from qamra_workbook.render.samples import assets_for
    from qamra_workbook.render.spec import Child

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--journey", type=int, choices=(1, 2, 3), help="a stage of «رحلتي الأولى للتعلّم»")
    which.add_argument("--islamic", help="a volume of «قلبي يعرف الله»: v1 … v5 or r")
    parser.add_argument("--name", default="ليان")
    parser.add_argument("--gender", choices=("m", "f"), default="f")
    parser.add_argument("--numerals", choices=("hindi", "latin"), default="hindi")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    child = Child(args.name, args.gender, SAMPLE_SHEET if SAMPLE_SHEET.is_file() else None)
    if args.journey:
        out = args.out or Path("out/stickers") / f"journey-s{args.journey}"
        book = _journey_book(args.journey, child, args.numerals)
    else:
        out = args.out or Path("out/stickers") / f"islamic-{args.islamic.lower()}"
        book = _islamic_book(args.islamic, child, args.numerals, out)
    out.mkdir(parents=True, exist_ok=True)
    needs = needs_of(book)
    files = asyncio.run(render_sheet(book, assets_for(book, out), out))
    png = previews(files.pdf, out / "png", [NAME], SHEET, dpi=110)[0]
    (out / "preflight.json").write_text(json.dumps(files.report, ensure_ascii=False, indent=2), "utf-8")
    print(
        f"{files.pdf}: {files.stickers} stickers ({needs.asked} the book asks for, {needs.rewards} rewards)"
    )
    print(f"  die: {files.die} · preview: {png}")
    print(f"  preflight {'passed' if files.passed else 'FAILED'} · die ink {files.report['die_ink']}")
    return 0 if files.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
