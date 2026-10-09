"""«كتاب الصف» print files (Addendum 1 §2): N personal copies of one class book, and one combined print file.

Every copy has the same interior (the school page, the shared story pages and the class group page) with the
child's own portrait page inserted as page 2, and its own cover. The shared pages are rendered once, each
portrait and cover once per child, and the copies are assembled with pypdf; the combined print file reuses
the shared pages' images, so N copies don't store N copies of every picture. Preflight runs on the shared
interior once and on every portrait page and cover.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter

from qamra_pdf import ornaments
from qamra_pdf.assets import LAYOUTS_DIR, prepare
from qamra_pdf.cover import class_design, cover_name, pick_thumbs, rgba
from qamra_pdf.lettering import title_svg, treatment
from qamra_pdf.preflight import Check, PreflightReport, preflight
from qamra_pdf.render import FONTS_DIR, PKG_DIR, _to_pdf, hero_text, set_boxes
from qamra_pdf.spec import Brand

_env = Environment(
    loader=FileSystemLoader([PKG_DIR / "templates", LAYOUTS_DIR]),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
_UNSAFE = re.compile(r"[^\w؀-ۿ-]+")


@dataclass(frozen=True)
class SchoolPage:
    title: str  # «كِتابُ صف الفراشات»
    school: str
    year: str | None = None
    teacher_title: str = ""
    teacher_message: str | None = None
    teacher_name: str | None = None
    logo: Path | None = None
    class_photo: Path | None = None


@dataclass(frozen=True)
class StoryPage:
    image: Path
    text: str


@dataclass(frozen=True)
class Classmate:
    name: str
    face: Path  # a square head-and-shoulders crop of the approved character


@dataclass(frozen=True)
class ChildCopy:
    stem: str  # file name without .pdf: {school}-{class}-{child}
    name: str
    cover_image: Path  # the child's personal cover picture, print size
    portrait: Path  # the child's character, front view
    portrait_line: str
    companion: Path | None = None  # the child's drawing companion, when there is one
    companion_name: str | None = None
    gender: Literal["m", "f"] | None = None  # the cover's «بطولة» ribbon; None: the ribbon names the school


@dataclass(frozen=True)
class ClassBookSpec:
    lang: Literal["ar", "en"]
    brand: Brand
    title: str  # the book: «كِتابُ صف الفراشات»
    cover_subtitle: str  # under the child's name on the cover
    blurb: str
    portrait_title: str
    group_title: str
    school: SchoolPage
    pages: list[StoryPage]
    classmates: list[Classmate]
    memories_title: str = ""
    trim_mm: float = 210.0
    bleed_mm: float = 3.0
    safe_mm: float = 10.0
    spine_mm: float = 8.0
    signature: int = 4
    dpi: int = 300
    child_age: int = 5
    extra: dict[str, str] = field(default_factory=dict)
    title_style: str = "gold-magic"  # the theme's cover lettering (`lettering.TITLE_STYLES`)
    age_range: tuple[int, int] | None = None  # the theme's ages, a fact on the back cover

    @property
    def page_mm(self) -> float:
        return self.trim_mm + 2 * self.bleed_mm

    @property
    def wrap_width_mm(self) -> float:
        return 2 * self.trim_mm + self.spine_mm + 2 * self.bleed_mm

    @property
    def dir(self) -> str:
        return "rtl" if self.lang == "ar" else "ltr"

    @property
    def text_pt(self) -> float:
        return 20.0 if self.child_age <= 5 else 16.0

    @property
    def min_text_pt(self) -> float:
        return 18.0 if self.child_age <= 5 else 15.0

    @property
    def interior_pages(self) -> int:
        """School page + portrait + story pages + group page, padded to the printer's signature."""
        n = 3 + len(self.pages)
        return n + (-n % max(1, self.signature))

    def folio(self, n: int) -> str:
        text = str(n)
        return text.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")) if self.lang == "ar" else text


def file_stem(*parts: str) -> str:
    """`{school}-{class}-{child}`: letters (Arabic included) and digits, words joined by dashes."""
    words = [_UNSAFE.sub("-", " ".join(p.split())).strip("-") for p in parts if p and p.strip()]
    return re.sub(r"-{2,}", "-", "-".join(w for w in words if w))[:120] or "book"


@dataclass
class ClassFiles:
    interiors: dict[str, Path]  # by stem
    covers: dict[str, Path]
    combined: Path
    preflight: dict[str, dict[str, PreflightReport]]  # stem → {"interior", "cover"}
    overflow_pages: list[int] = field(default_factory=list)

    def passed(self, stem: str) -> bool:
        reports = self.preflight.get(stem, {})
        return bool(reports) and all(r.passed for r in reports.values())


def _render(template: str, spec: ClassBookSpec, **extra: object) -> str:
    def uri(p: Path | None) -> str:
        return p.resolve().as_uri() if p else ""

    return _env.get_template(template).render(spec=spec, fonts=FONTS_DIR.as_uri(), img=uri, **extra)


def cover_html(spec: ClassBookSpec, copy: ChildCopy, work: Path) -> str:
    """A child's cover wrap: the story cover's design (`cover.class_design`) with the class book's words."""
    assets = prepare(
        copy.cover_image,
        None,
        work,
        hero=copy.portrait,
        hero_is_sheet=False,
        thumbs=pick_thumbs([p.image for p in spec.pages]),
    )
    design = class_design(spec, copy, assets)

    def hero(text: str | None) -> object:
        return hero_text(text, copy.name, spec.lang)

    return _render(
        "class_cover.html.j2",
        spec,
        copy=copy,
        cover=design,
        cover_name=cover_name,
        assets=assets,
        t=treatment(spec.title_style),
        title_svg=title_svg,
        orn=ornaments,
        rgba=rgba,
        hero=hero,
    )


def _merged(name: str, parts: list[PreflightReport], pages: int, signature: int) -> PreflightReport:
    """One copy's interior report from the shared interior's and its portrait page's reports."""
    report = PreflightReport(file=name)
    report.checks.append(Check("page_count", pages % signature == 0, f"{pages} pages, signature {signature}"))
    for part in parts:
        report.checks += [Check(c.name, c.ok, f"{part.file}: {c.detail}", c.level) for c in part.checks]
    dpis = [p.min_dpi for p in parts if p.min_dpi is not None]
    report.min_dpi = min(dpis) if dpis else None
    return report


async def render_class_book(
    spec: ClassBookSpec,
    copies: list[ChildCopy],
    out_dir: Path,
    *,
    on_copy: Callable[[int], None] | None = None,
) -> ClassFiles:
    """Shared interior once, then a portrait page and a cover per child (one Chromium session), then the
    copies and the combined print file (cover, then interior, child after child)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stems = [c.stem for c in copies]
    if len(set(stems)) != len(stems):
        raise ValueError("every copy needs its own file name")
    fillers = spec.interior_pages - 3 - len(spec.pages)
    shared_html, shared_pdf = out_dir / "shared.html", out_dir / "shared.pdf"
    shared_html.write_text(_render("class_interior.html.j2", spec, fillers=fillers), encoding="utf-8")
    portraits: list[Path] = []
    covers: list[Path] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            fit = await _to_pdf(
                browser, shared_html, shared_pdf, spec.page_mm, spec.page_mm, spec.min_text_pt
            )
            for i, copy in enumerate(copies):
                html, pdf = out_dir / f"portrait-{i}.html", out_dir / f"portrait-{i}.pdf"
                html.write_text(_render("class_portrait.html.j2", spec, copy=copy), encoding="utf-8")
                await _to_pdf(browser, html, pdf, spec.page_mm, spec.page_mm, None)
                portraits.append(pdf)
                html, pdf = out_dir / f"cover-{i}.html", out_dir / f"cover-{i}.pdf"
                html.write_text(cover_html(spec, copy, out_dir / f"cover-{i}"), encoding="utf-8")
                await _to_pdf(browser, html, pdf, spec.wrap_width_mm, spec.page_mm, None)
                covers.append(pdf)
                if on_copy is not None:
                    on_copy(i)
        finally:
            await browser.close()
    set_boxes(shared_pdf, spec.page_mm, spec.page_mm, spec.bleed_mm)
    for pdf in portraits:
        set_boxes(pdf, spec.page_mm, spec.page_mm, spec.bleed_mm)
    for pdf in covers:
        set_boxes(pdf, spec.wrap_width_mm, spec.page_mm, spec.bleed_mm)

    shared = PdfReader(shared_pdf)
    shared_report = preflight(
        shared_pdf,
        width_mm=spec.page_mm,
        height_mm=spec.page_mm,
        bleed_mm=spec.bleed_mm,
        safe_mm=spec.safe_mm,
        min_dpi=spec.dpi,
    )
    combined = PdfWriter()
    files = ClassFiles(interiors={}, covers={}, combined=out_dir / "combined.pdf", preflight={})
    files.overflow_pages = [int(f["page"]) for f in fit if f.get("overflow")]
    for i, copy in enumerate(copies):
        portrait = PdfReader(portraits[i])
        interior = PdfWriter()
        for writer in (interior, combined):
            if writer is combined:
                writer.append(PdfReader(covers[i]))
            writer.add_page(shared.pages[0])
            writer.add_page(portrait.pages[0])
            for page in shared.pages[1:]:
                writer.add_page(page)
        path = out_dir / f"interior-{i}.pdf"
        with path.open("wb") as f:
            interior.write(f)
        files.interiors[copy.stem] = path
        files.covers[copy.stem] = covers[i]
        portrait_report = preflight(
            portraits[i],
            width_mm=spec.page_mm,
            height_mm=spec.page_mm,
            bleed_mm=spec.bleed_mm,
            safe_mm=spec.safe_mm,
            min_dpi=spec.dpi,
        )
        cover_report = preflight(
            covers[i],
            width_mm=spec.wrap_width_mm,
            height_mm=spec.page_mm,
            bleed_mm=spec.bleed_mm,
            safe_mm=spec.safe_mm,
            min_dpi=spec.dpi,
        )
        files.preflight[copy.stem] = {
            "interior": _merged(
                f"{copy.stem}.pdf", [shared_report, portrait_report], len(shared.pages) + 1, spec.signature
            ),
            "cover": cover_report,
        }
    with files.combined.open("wb") as f:
        combined.write(f)
    return files
