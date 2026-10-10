"""Automated preflight for print files (Addendum 3 §4).

Checks: bleed present (page = trim + 2 × bleed, TrimBox/BleedBox set), every image ≥ 300 DPI effective,
fonts embedded (no Type 3), no text outside the trim box (errors) or inside the safe margin (warnings), and
the interior page count divisible by the printer's signature.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import pdfplumber
from pypdf import PdfReader

MM = 72 / 25.4
SIZE_TOLERANCE_PT = 0.6
DPI_TOLERANCE = 0.5  # 2551 px over 216 mm is 299.98 DPI


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    level: Literal["error", "warning"] = "error"


@dataclass
class PreflightReport:
    file: str
    checks: list[Check] = field(default_factory=list)
    min_dpi: float | None = None

    @property
    def passed(self) -> bool:
        return all(c.ok for c in self.checks if c.level == "error")

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "passed": self.passed,
            "min_dpi": self.min_dpi,
            "checks": [asdict(c) for c in self.checks],
        }


def _fonts_ok(reader: PdfReader) -> tuple[bool, str]:
    problems: set[str] = set()
    for page in reader.pages:
        resources: Any = page.get("/Resources") or {}
        fonts: Any = resources.get("/Font") or {}
        for ref in fonts.values():
            font = ref.get_object()
            name = str(font.get("/BaseFont", "?"))
            if font.get("/Subtype") == "/Type3":
                problems.add(f"{name} is Type 3")
                continue
            descriptors = []
            if font.get("/Subtype") == "/Type0":
                for d in font.get("/DescendantFonts") or []:
                    descriptors.append(d.get_object().get("/FontDescriptor"))
            else:
                descriptors.append(font.get("/FontDescriptor"))
            for desc in descriptors:
                desc = desc.get_object() if desc is not None else None
                if desc is None or not any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                    problems.add(f"{name} not embedded")
    return not problems, "; ".join(sorted(problems)) or "all fonts embedded"


def preflight(
    pdf: Path,
    *,
    width_mm: float,
    height_mm: float,
    bleed_mm: float,
    safe_mm: float,
    signature: int | None = None,
    min_dpi: float = 300,
) -> PreflightReport:
    report = PreflightReport(file=pdf.name)
    reader = PdfReader(pdf)
    n = len(reader.pages)
    if signature:
        report.checks.append(Check("page_count", n % signature == 0, f"{n} pages, signature {signature}"))

    w, h, b = width_mm * MM, height_mm * MM, bleed_mm * MM
    size_ok = boxes_ok = True
    for page in reader.pages:
        mb = page.mediabox
        size_ok &= (
            abs(float(mb.width) - w) <= SIZE_TOLERANCE_PT and abs(float(mb.height) - h) <= SIZE_TOLERANCE_PT
        )
        tb = page.trimbox
        boxes_ok &= (
            "/TrimBox" in page
            and "/BleedBox" in page
            and abs(float(tb.width) - (w - 2 * b)) <= SIZE_TOLERANCE_PT
            and abs(float(tb.left) - b) <= SIZE_TOLERANCE_PT
        )
    report.checks.append(
        Check("bleed_size", size_ok, f"{width_mm:.1f} × {height_mm:.1f} mm incl. {bleed_mm} mm bleed")
    )
    report.checks.append(Check("trim_bleed_boxes", boxes_ok, "TrimBox inset by the bleed, BleedBox = page"))
    ok, detail = _fonts_ok(reader)
    report.checks.append(Check("fonts_embedded", ok, detail))

    low_dpi: list[str] = []
    outside_trim: list[int] = []
    in_margin: list[int] = []
    dpis: list[float] = []
    margin = b + safe_mm * MM
    with pdfplumber.open(pdf) as doc:
        for i, pl_page in enumerate(doc.pages, start=1):
            images: list[dict[str, Any]] = pl_page.images
            for img in images:
                shown_w, shown_h = float(img["x1"] - img["x0"]), float(img["bottom"] - img["top"])
                src_w, src_h = img.get("srcsize") or (0, 0)
                if shown_w < 1 or shown_h < 1:
                    continue
                dpi = min(src_w / (shown_w / 72), src_h / (shown_h / 72))
                dpis.append(dpi)
                if dpi + DPI_TOLERANCE < min_dpi:
                    low_dpi.append(f"p{i}: {dpi:.0f} DPI ({src_w}×{src_h} px)")
            pw, ph = float(pl_page.width), float(pl_page.height)
            chars: list[dict[str, Any]] = pl_page.chars
            for ch in chars:
                if not ch["text"].strip():
                    continue
                x0, x1, top, bottom = float(ch["x0"]), float(ch["x1"]), float(ch["top"]), float(ch["bottom"])
                if x1 - x0 < 0.01 * float(ch.get("size") or 1):
                    # a zero-advance mark (tashkeel, Aref Ruqaa's dots) sits on its letter, which is checked
                    # itself; its font box (a whole em up from a raised origin) says nothing about its ink
                    continue
                if x0 < b or top < b or x1 > pw - b or bottom > ph - b:
                    outside_trim.append(i)
                elif x0 < margin or top < margin or x1 > pw - margin or bottom > ph - margin:
                    in_margin.append(i)
            pl_page.close()  # free the parsed page now: a 112-page book otherwise holds every page (1.5 GB)
    report.min_dpi = round(min(dpis), 1) if dpis else None
    report.checks.append(
        Check(
            "image_dpi",
            not low_dpi,
            "; ".join(low_dpi[:6]) or f"all images ≥ {min_dpi:.0f} DPI (min {report.min_dpi})",
        )
    )
    report.checks.append(
        Check(
            "text_in_bleed",
            not outside_trim,
            f"pages {sorted(set(outside_trim))}" if outside_trim else "no text in the bleed",
        )
    )
    report.checks.append(
        Check(
            "text_in_safe_margin",
            not in_margin,
            f"pages {sorted(set(in_margin))}" if in_margin else f"all text ≥ {safe_mm} mm inside the trim",
            level="warning",
        )
    )
    return report
