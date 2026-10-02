"""HTML/CSS → print PDFs with Playwright Chromium (Addendum 3 §4).

Outputs, from one Chromium session:
- `interior.pdf`: 216 × 216 mm pages in reading order, fonts embedded;
- `cover.pdf`: one wrap sheet (front | spine | back for right-bound Arabic books);
- `proof.pdf`: the low-res web proof (front, interior, back as squares).

Story pages come from the layout library in `packages/pdf/layouts/` (Addendum 11 §3); the cover title is
lettered in code (`lettering`). Story text that overflows its container shrinks in 0.5 pt steps down to the
age minimum (24 pt for ages 3–5, 20 pt for 6–8); anything still overflowing is reported for review, and every
text container reports how much of it the text fills (never a mostly empty box). Chromium rounds page sizes
to CSS pixels, so the page boxes are rewritten to the exact size and TrimBox/BleedBox are added.
"""

import io
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape
from PIL import Image
from playwright.async_api import Browser, async_playwright
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from qamra_pdf import ornaments
from qamra_pdf.assets import LAYOUTS_DIR, Assets, prepare
from qamra_pdf.lettering import TITLE_FIT_JS, title_svg, treatment
from qamra_pdf.page_layouts import LAYOUTS, drop_word, normalize, split_dialogue
from qamra_pdf.spec import BookSpec
from qamra_pdf.strings import STRINGS

logging.getLogger("pypdf").setLevel(logging.ERROR)  # Chromium's xref trailers trigger harmless warnings

PKG_DIR = Path(__file__).parent
FONTS_DIR = PKG_DIR / "fonts"
MM = 72 / 25.4  # points per millimetre
PROOF_MAX_PX = 900

_env = Environment(
    loader=FileSystemLoader([PKG_DIR / "templates", LAYOUTS_DIR]),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Shrink-to-fit for every text container ([data-panel] holding .story-text): all its texts shrink together
# in 0.5 pt steps down to the age minimum. `fill` is how much of the container's content box the text uses.
_FIT_JS = """
(minPt) => {
  const out = [];
  // computed sizes are CSS px (16 pt = 21.333… px): round to 0.01 pt so an unshrunk size compares equal
  const ptOf = el => Math.round(parseFloat(getComputedStyle(el).fontSize) * 75) / 100;
  for (const box of document.querySelectorAll('[data-panel]')) {
    const texts = [...box.querySelectorAll('.story-text')];
    if (!texts.length) continue;
    // in-flow content only: decorative shapes (absolute) may spill out of the box on purpose
    const flow = [...box.children].filter(c => {
      const st = getComputedStyle(c);
      return st.position !== 'absolute' && st.display !== 'none';
    });
    const measure = () => {
      const cs = getComputedStyle(box);
      const inner = box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const gap = (parseFloat(cs.rowGap) || 0) * Math.max(0, flow.length - 1);
      const used = flow.reduce((a, c) => {
        const st = getComputedStyle(c);
        return a + c.getBoundingClientRect().height + parseFloat(st.marginTop) + parseFloat(st.marginBottom);
      }, gap);
      return {inner, used};
    };
    const over = () => {
      const {inner, used} = measure();
      return used > inner + 1 || texts.some(t => t.scrollWidth > t.clientWidth + 1);
    };
    let pts = texts.map(ptOf);
    while (over() && Math.max(...pts) > minPt) {
      pts = pts.map(p => Math.max(minPt, p - 0.5));
      texts.forEach((t, i) => { t.style.fontSize = pts[i] + 'pt'; });
    }
    const {inner, used} = measure();
    out.push({page: Number(box.dataset.panel), pt: Math.min(...pts), overflow: over(),
              fill: inner > 0 ? Math.round(used / inner * 1000) / 1000 : 1});
  }
  return out;
}
"""
_NAME_EDGE = "ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوىي"
_MARKS = "\u064b-\u0652\u0670\u0640"


def hero_text(text: str | None, name: str, lang: str = "ar") -> Markup:
    """Story text with the child's name in the accent color, semi-bold (Addendum 11 §3). Matches the name with
    or without tashkeel, only as a whole word (never half of a joined word)."""
    if not text:
        return Markup("")
    plain = re.sub(f"[{_MARKS}]", "", name).strip()
    if not plain:
        return escape(text)
    if lang == "ar":
        letters = f"[{_MARKS}]*".join(re.escape(c) for c in plain)
        pattern = re.compile(f"(?<![{_NAME_EDGE}])({letters}[{_MARKS}]*)(?![{_NAME_EDGE}])")
    else:
        pattern = re.compile(rf"\b({re.escape(plain)})\b", re.IGNORECASE)
    out, last = [], 0
    for m in pattern.finditer(text):
        out.append(escape(text[last : m.start()]))
        out.append(Markup('<span class="hero-name">%s</span>') % m.group(1))
        last = m.end()
    out.append(escape(text[last:]))
    return Markup("").join(out)


def qr_svg(url: str | None) -> Markup | None:
    """QR as an inline vector (sharp at any print size)."""
    if not url:
        return None
    qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    path = "".join(f"M{x} {y}h1v1h-1z" for y, row in enumerate(matrix) for x, on in enumerate(row) if on)
    return Markup(  # nosec B704 (built from a boolean matrix, no user text)
        f'<svg viewBox="0 0 {n} {n}" shape-rendering="crispEdges"><path d="{path}" fill="#16204A"/></svg>'
    )


def render_html(
    template: str,
    spec: BookSpec,
    img: Callable[[Path | None], str] | None = None,
    assets: Assets | None = None,
) -> str:
    def uri(p: Path | None) -> str:
        return p.resolve().as_uri() if p else ""

    def hero(text: str | None) -> Markup:
        return hero_text(text, spec.child_name, spec.lang)

    def rgba(color: str, alpha: float) -> str:
        c = color.lstrip("#")
        r, g, b = (int(c[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"

    return _env.get_template(template).render(
        spec=spec,
        s=STRINGS[spec.lang],
        fonts=FONTS_DIR.as_uri(),
        img=img or uri,
        qr_svg=qr_svg(spec.cover.qr_url),
        qr=qr_svg,
        t=treatment(spec.title_style),
        assets=assets or Assets(),
        hero=hero,
        layout_of=normalize,
        layouts=LAYOUTS,
        dialogue=split_dialogue,
        drop_word=drop_word,
        title_svg=title_svg,
        orn=ornaments,
        rgba=rgba,
    )


@dataclass(frozen=True)
class TextFit:
    page: int
    pt: float
    overflow: bool
    fill: float = 1.0  # share of the container's content box the text uses


@dataclass
class RenderedBook:
    interior_pdf: Path | None
    cover_pdf: Path | None
    proof_pdf: Path | None
    fit: list[TextFit] = field(default_factory=list)  # pages whose text shrank or still overflows
    boxes: list[TextFit] = field(default_factory=list)  # every text container, with its fill

    @property
    def overflowing_pages(self) -> list[int]:
        return [f.page for f in self.fit if f.overflow]

    @property
    def shrunk_pages(self) -> list[int]:
        return [f.page for f in self.fit if not f.overflow]


def _small_copy(src: Path, out_dir: Path) -> Path:
    """Proof-size copy: JPEG, or PNG when the source has transparency (cut-outs, decor)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as original:
        alpha = original.mode in ("RGBA", "LA") or "transparency" in original.info
        dest = out_dir / f"{src.parent.name}-{src.stem}.{'png' if alpha else 'jpg'}"
        if not dest.exists():
            im = original.convert("RGBA" if alpha else "RGB")
            im.thumbnail((PROOF_MAX_PX, PROOF_MAX_PX), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            if alpha:
                im.save(buf, format="PNG", optimize=True)
            else:
                im.save(buf, format="JPEG", quality=78)
            dest.write_bytes(buf.getvalue())
    return dest


def set_boxes(pdf: Path, width_mm: float, height_mm: float, bleed_mm: float) -> None:
    """Exact MediaBox/BleedBox, TrimBox inset by the bleed (what printers expect)."""
    reader = PdfReader(pdf)
    writer = PdfWriter(clone_from=reader)
    w, h, b = width_mm * MM, height_mm * MM, bleed_mm * MM
    for page in writer.pages:
        box = RectangleObject([0, 0, w, h])
        page.mediabox = box
        page.cropbox = RectangleObject([0, 0, w, h])
        page.bleedbox = RectangleObject([0, 0, w, h])
        page.trimbox = RectangleObject([b, b, w - b, h - b])
    with pdf.open("wb") as f:
        writer.write(f)


async def _to_pdf(
    browser: Browser, html_path: Path, pdf_path: Path, width_mm: float, height_mm: float, fit_pt: float | None
) -> list[dict[str, Any]]:
    page = await browser.new_page()
    try:
        await page.goto(html_path.as_uri(), wait_until="load")
        await page.evaluate("document.fonts.ready.then(() => true)")
        await page.evaluate(TITLE_FIT_JS)
        fit: list[dict[str, Any]] = []
        if fit_pt is not None:
            fit = await page.evaluate(_FIT_JS, fit_pt)
        await page.pdf(
            path=str(pdf_path),
            width=f"{width_mm}mm",
            height=f"{height_mm}mm",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        return fit
    finally:
        await page.close()


async def render_book(
    spec: BookSpec, out_dir: Path, *, proof: bool = True, print_files: bool = True
) -> RenderedBook:
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = prepare(spec.cover.front_image, spec.companion, out_dir)
    interior_html, cover_html = out_dir / "interior.html", out_dir / "cover.html"
    interior_html.write_text(render_html("interior.html.j2", spec, assets=assets), encoding="utf-8")
    cover_html.write_text(render_html("cover.html.j2", spec, assets=assets), encoding="utf-8")
    proof_html = out_dir / "proof.html"
    if proof:
        small_dir = out_dir / "proof-img"

        def small(p: Path | None) -> str:
            return _small_copy(p, small_dir).resolve().as_uri() if p else ""

        proof_html.write_text(render_html("proof.html.j2", spec, small, assets), encoding="utf-8")

    interior_pdf, cover_pdf, proof_pdf = (
        out_dir / "interior.pdf",
        out_dir / "cover.pdf",
        out_dir / "proof.pdf",
    )
    fit: list[dict[str, Any]] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            if print_files:
                fit = await _to_pdf(
                    browser, interior_html, interior_pdf, spec.page_mm, spec.page_mm, spec.min_text_pt
                )
                await _to_pdf(browser, cover_html, cover_pdf, spec.wrap_width_mm, spec.page_mm, None)
            if proof:
                proof_fit = await _to_pdf(
                    browser, proof_html, proof_pdf, spec.page_mm, spec.page_mm, spec.min_text_pt
                )
                fit = fit or proof_fit
        finally:
            await browser.close()
    if print_files:
        set_boxes(interior_pdf, spec.page_mm, spec.page_mm, spec.bleed_mm)
        set_boxes(cover_pdf, spec.wrap_width_mm, spec.page_mm, spec.bleed_mm)
    boxes = [
        TextFit(int(f["page"]), float(f["pt"]), bool(f["overflow"]), float(f.get("fill", 1))) for f in fit
    ]
    return RenderedBook(
        interior_pdf if print_files else None,
        cover_pdf if print_files else None,
        proof_pdf if proof else None,
        [b for b in boxes if b.pt < spec.text_pt or b.overflow],
        boxes,
    )
