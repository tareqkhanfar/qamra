"""Product mockups for every catalog theme (Addendum 11 §2.7), for the website and the social kit.

For each active catalog theme it looks for a rendered sample book in the PDF folder (searched recursively,
newest first) and renders `hardcover.png` (1600 × 1600) and `spread.png` (2000 × 1250) into
`out/mockups/<theme>/`. No AI, no paid service: Chromium only.

A sample is found as any of:
  <dir>/<theme>/cover.pdf + interior.pdf, or a run folder ending in `-<theme>` (scripts/sample_book.py)
  <theme>-cover.pdf + <theme>-interior.pdf
  <theme>.pdf or *-<theme>.pdf: one file with the cover wrap first, then the interior pages

Examples:
  uv run scripts/theme_mockups.py out/redesign
  uv run scripts/theme_mockups.py out/samples --theme graduation=out/redesign/offline-graduation.pdf
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pypdfium2 as pdfium
import yaml

from qamra_pdf.mockups import mockups_from_pdfs

ROOT = Path(__file__).resolve().parents[1]
THEMES_DIR = ROOT / "content" / "themes"
OUT_DIR = ROOT / "out" / "mockups"


@dataclass(frozen=True)
class Sample:
    cover: Path
    interior: Path

    @property
    def mtime(self) -> float:
        return max(self.cover.stat().st_mtime, self.interior.stat().st_mtime)


def catalog_themes(themes_dir: Path = THEMES_DIR) -> list[str]:
    out = []
    for path in sorted(themes_dir.glob("*/theme.yaml")):
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("active", True) and data.get("catalog"):
            out.append(str(data.get("slug") or path.parent.name))
    return out


def _is_wrap(pdf: Path) -> bool:
    """The first page is wider than tall: a cover wrap (front | spine | back)."""
    try:
        doc = pdfium.PdfDocument(str(pdf))
    except pdfium.PdfiumError:
        return False
    try:
        w, h = doc[0].get_size()
        return bool(w > 1.5 * h)
    finally:
        doc.close()


def _named(stem: str, slug: str) -> bool:
    return stem == slug or stem.endswith(f"-{slug}")


def find_sample(folder: Path, slug: str) -> Sample | None:
    found: list[Sample] = []
    for d in [folder, *(p for p in folder.rglob("*") if p.is_dir())]:
        cover, interior = d / "cover.pdf", d / "interior.pdf"
        if _named(d.name, slug) and cover.is_file() and interior.is_file():
            found.append(Sample(cover, interior))
    for cover in folder.rglob(f"*{slug}-cover.pdf"):
        interior = cover.with_name(cover.name.replace("-cover.pdf", "-interior.pdf"))
        if _named(cover.name.removesuffix("-cover.pdf"), slug) and interior.is_file():
            found.append(Sample(cover, interior))
    for pdf in folder.rglob(f"*{slug}.pdf"):
        if _named(pdf.stem, slug) and _is_wrap(pdf):
            found.append(Sample(pdf, pdf))
    return max(found, key=lambda s: s.mtime) if found else None


def detect_lang(pdf: Path) -> Literal["ar", "en"]:
    """Arabic when the book's text is mostly Arabic letters."""
    doc = pdfium.PdfDocument(str(pdf))
    try:
        text = "".join(doc[i].get_textpage().get_text_range() for i in range(min(len(doc), 8)))
    finally:
        doc.close()
    arabic = sum("؀" <= c <= "ۿ" for c in text)
    latin = sum(c.isascii() and c.isalpha() for c in text)
    return "ar" if arabic >= latin else "en"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("pdfs", type=Path, help="folder with rendered sample books")
    p.add_argument(
        "--theme", action="append", default=[], metavar="SLUG=PDF", help="explicit sample (repeat)"
    )
    p.add_argument("--only", action="append", default=[], metavar="SLUG", help="render only these themes")
    p.add_argument("--lang", choices=["ar", "en"], help="the samples' language (default: from the PDF text)")
    p.add_argument("--out", type=Path, default=OUT_DIR)
    return p.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.pdfs.is_dir():
        print(f"not a folder: {args.pdfs}", file=sys.stderr)
        return 2
    explicit: dict[str, Sample] = {}
    for item in args.theme:
        slug, _, path = item.partition("=")
        pdf = Path(path)
        sibling = pdf.parent / "interior.pdf"
        explicit[slug] = Sample(pdf, sibling if pdf.name == "cover.pdf" and sibling.is_file() else pdf)
    themes = args.only or catalog_themes()
    missing = []
    for slug in themes:
        sample = explicit.get(slug) or find_sample(args.pdfs, slug)
        if sample is None:
            missing.append(slug)
            continue
        lang = args.lang or detect_lang(sample.interior)
        made = await mockups_from_pdfs(sample.cover, sample.interior, lang, args.out / slug)
        modes = ", ".join(f"{k}: {v}" for k, v in made.modes.items())
        print(f"{slug:24} {lang}  {made.hardcover.parent}  ({modes})  ← {sample.cover}")
    if missing:
        print(f"no rendered sample for: {', '.join(missing)} (render one with scripts/sample_book.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
