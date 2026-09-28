"""Generated book → print files: lay the images and texts onto the planned pages and render the PDFs.

Shared by the worker and the scripts. Images are written into `out_dir/images`, then `qamra_pdf` renders
interior.pdf, cover.pdf and the web proof, and the preflight runs on both print files.
"""

import io
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops

from qamra_ai.pipeline.book import BookRun
from qamra_ai.pipeline.layout import BookPlan
from qamra_ai.pipeline.models import Child, Lang, StoryOut
from qamra_ai.pipeline.printimg import split_spread
from qamra_pdf import (
    BookSpec,
    Brand,
    CoverSpec,
    KeepsakeSpec,
    PageSpec,
    Panel,
    ParentsSpec,
    PreflightReport,
    TitleSpec,
    panel_for,
    preflight,
    render_book,
)
from qamra_pdf.spec import PanelArea
from qamra_pdf.strings import STRINGS

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
PORTRAIT_PX = 700  # 52 mm circle at ≥ 300 DPI needs 614 px
KEEPSAKE_PX = 800  # 62 mm frame at ≥ 300 DPI needs 733 px


def plain(text: str) -> str:
    return _TASHKEEL.sub("", text)


_OPENERS: dict[Lang, tuple[str, ...]] = {"ar": ("إلى", "الى"), "en": ("to ", "for ", "dear ")}


def dedication_text(name: str, message: str, lang: Lang) -> str:
    """«إلى ليان… <message>», unless the message already addresses the child (its own «إلى …» or the name):
    parents often write «إلى ليان… مبارك», which would print as «إلى ليان… إلى ليان… مبارك»."""
    text = plain(message).strip().lower()
    if plain(name).strip().lower() in text or text.startswith(_OPENERS[lang]):
        return message.strip()
    return f"{'إلى' if lang == 'ar' else 'To'} {name}… {message.strip()}"


def split_title(title: str, name: str) -> tuple[str, str]:
    """("سَلْمَى", "في أوّل يوم بالروضة") when the title starts with the child's name, else (title, "")."""
    words = title.split()
    target = plain(name).split()
    for i in range(1, len(words) + 1):
        if [plain(w).strip("،,:") for w in words[:i]] == target:
            return " ".join(words[:i]), " ".join(words[i:])
    return title, ""


def _save(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _to_jpeg(img: Image.Image, quality: int = 92, dpi: int = 300) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, dpi=(dpi, dpi))
    return buf.getvalue()


def portrait_from_sheet(sheet: bytes, px: int = PORTRAIT_PX) -> bytes:
    """Head-and-shoulders square from the front view (left third) of the character sheet.

    The figure is found as everything that differs from the sheet's plain background; the square starts at
    the top of the figure and is as wide as it, so it frames the head and shoulders.
    """
    with Image.open(io.BytesIO(sheet)) as original:
        im = original.convert("RGB")
        w, h = im.size
        region = im.crop((0, 0, w // 3, h)) if w >= 1.3 * h else im
        rw, rh = region.size
        bg = region.getpixel((2, 2))
        mask = ImageChops.difference(region, Image.new("RGB", region.size, bg)).convert("L")
        x0, y0, x1, _ = mask.point(lambda v: 255 if v > 28 else 0).getbbox() or (0, 0, rw, rh)
        side = max(64, min(rw, rh, x1 - x0))
        left = max(0, min(rw - side, (x0 + x1) // 2 - side // 2))
        top = max(0, min(rh - side, y0 - side // 12))
        square = region.crop((left, top, left + side, top + side))
        return _to_jpeg(square.resize((px, px), Image.Resampling.LANCZOS))


def front_view(sheet: bytes, px: int = KEEPSAKE_PX) -> bytes:
    """The first of the two companion views, at keepsake print size."""
    with Image.open(io.BytesIO(sheet)) as im:
        w, h = im.size
        half = im.crop((0, 0, w // 2, h)) if w >= 1.3 * h else im
        half.thumbnail((px, px), Image.Resampling.LANCZOS)
        scale = px / max(half.size)
        if scale > 1:
            half = half.resize(
                (round(half.size[0] * scale), round(half.size[1] * scale)), Image.Resampling.LANCZOS
            )
        return _to_jpeg(half)


def as_jpeg(data: bytes) -> bytes:
    if data[:3] == b"\xff\xd8\xff":
        return data
    with Image.open(io.BytesIO(data)) as im:
        return _to_jpeg(im)


def fit_long_side(data: bytes, px: int) -> bytes:
    with Image.open(io.BytesIO(data)) as im:
        scale = px / max(im.size)
        im2 = im.resize((round(im.size[0] * scale), round(im.size[1] * scale)), Image.Resampling.LANCZOS)
        return _to_jpeg(im2)


def _panel_area(text_area: str) -> PanelArea:
    if text_area.startswith("bottom"):
        return "bottom"
    if text_area in ("left", "right"):
        return text_area  # type: ignore[return-value]
    return "top"


@dataclass
class BookFiles:
    spec: BookSpec
    interior_pdf: Path | None
    cover_pdf: Path | None
    proof_pdf: Path | None
    preflight: dict[str, PreflightReport]
    flags: dict[int, list[str]] = field(default_factory=dict)  # physical page → layout flags

    @property
    def preflight_passed(self) -> bool:
        return bool(self.preflight) and all(r.passed for r in self.preflight.values())


@dataclass
class AssemblyInputs:
    run: BookRun
    story: StoryOut
    child: Child
    lang: Lang
    brand: Brand
    character_sheet: bytes
    parent_message: str | None = None
    companion_name: str | None = None
    drawing: bytes | None = None  # cleaned drawing for «وهكذا وُلد صاحبي»
    companion_sheet: bytes | None = None
    qr_url: str | None = None
    made_on: date | None = None
    watermark: bool = False


async def assemble_book(
    inp: AssemblyInputs, out_dir: Path, *, proof: bool = True, print_files: bool = True
) -> BookFiles:
    """Print files + preflight (final books), or only the watermarked web proof (previews)."""
    run, plan = inp.run, inp.run.plan
    images = out_dir / "images"
    s = STRINGS[inp.lang]
    texts = {p.index: p.text for p in inp.story.pages}
    last_beat = max(texts)
    flags: dict[int, list[str]] = {}

    def page_image(beat: int) -> bytes | None:
        res = run.pages.get(beat)
        if res is None or res.image is None:
            return None
        return res.print_image or res.image.data

    pages: list[PageSpec] = []
    spread_halves: dict[int, tuple[Path, Path]] = {}
    for slot in plan.slots:
        if slot.kind != "story" or slot.beat is None:
            pages.append(PageSpec(number=slot.number, kind=slot.kind, side=slot.side))
            continue
        beat = plan.beats[slot.beat]
        data = page_image(slot.beat)
        if data is None:
            if print_files:  # a preview proof simply shows the pages drawn so far
                flags.setdefault(slot.number, []).append("missing_image")
                pages.append(PageSpec(number=slot.number, kind="blank", side=slot.side))
            continue
        if beat.layout == "spread":
            if slot.beat not in spread_halves:
                left, right = (
                    split_spread(data, plan.spec.page_px[0])
                    if run.pages[slot.beat].print_image
                    else _halves(data)
                )
                spread_halves[slot.beat] = (
                    _save(images / f"p{beat.pages[0]:02d}-{beat.pages[1]:02d}-left.jpg", left),
                    _save(images / f"p{beat.pages[0]:02d}-{beat.pages[1]:02d}-right.jpg", right),
                )
            left_path, right_path = spread_halves[slot.beat]
            path = left_path if slot.side == "left" else right_path
        else:
            path = _save(images / f"p{slot.number:02d}.jpg", as_jpeg(data))
        first = slot.spread_half in (None, "first")
        panel: Panel | None = None
        if first and beat.layout in ("full", "spread"):
            panel = panel_for(path, _panel_area(beat.text_area))
            if panel.busy:
                flags.setdefault(slot.number, []).append("busy_text_area")
        pages.append(
            PageSpec(
                number=slot.number,
                kind="story",
                side=slot.side,
                layout=beat.layout,  # type: ignore[arg-type]
                image=path,
                text=texts.get(slot.beat) if first else None,
                panel=panel,
                is_last_story=first and slot.beat == last_beat,
            )
        )

    name, subtitle = split_title(inp.story.title, inp.child.name)
    portrait = _save(images / "portrait.jpg", portrait_from_sheet(inp.character_sheet))
    dedication = (
        dedication_text(inp.child.name, inp.parent_message, inp.lang)
        if inp.parent_message
        else inp.story.dedication
    )
    title_page = TitleSpec(
        name=name,
        subtitle=subtitle,
        made_for=s["made_for"].format(name=inp.child.name),
        dedication=dedication,
        portrait=portrait,
    )
    cover_data = page_image(0)
    if cover_data is None:
        raise ValueError("the cover image is missing")
    cover_path = _save(images / "cover.jpg", as_jpeg(cover_data))
    keepsake = None
    if (
        inp.drawing is not None
        and inp.companion_sheet is not None
        and any(p.kind == "companion" for p in pages)
    ):
        keepsake = KeepsakeSpec(
            drawing=_save(images / "keepsake-drawing.jpg", fit_long_side(inp.drawing, KEEPSAKE_PX)),
            companion=_save(images / "keepsake-companion.jpg", front_view(inp.companion_sheet)),
            child_name=inp.child.name,
            companion_name=inp.companion_name or "",
            date_text=(inp.made_on or date.today()).strftime("%d / %m / %Y"),
        )
    spec = BookSpec(
        lang=inp.lang,
        title=inp.story.title,
        child_name=inp.child.name,
        child_age=inp.child.age,
        gender=inp.child.gender,
        brand=inp.brand,
        title_page=title_page,
        cover=CoverSpec(
            front_image=cover_path, name=name, subtitle=subtitle, blurb=inp.story.blurb, qr_url=inp.qr_url
        ),
        pages=pages,
        parents=ParentsSpec(inp.story.parents_lesson, inp.story.parents_questions)
        if inp.story.parents_lesson
        else None,
        keepsake=keepsake,
        watermark=inp.watermark,
        trim_mm=plan.spec.trim_mm,
        bleed_mm=plan.spec.bleed_mm,
        safe_mm=plan.spec.safe_mm,
        spine_mm=plan.spec.spine_mm,
    )
    rendered = await render_book(spec, out_dir, proof=proof, print_files=print_files)
    for f in rendered.fit:
        flags.setdefault(f.page, []).append("text_overflow" if f.overflow else "text_shrunk")
    if not print_files:
        return BookFiles(spec, None, None, rendered.proof_pdf, {}, flags)
    assert rendered.interior_pdf is not None and rendered.cover_pdf is not None  # nosec B101 (typing)
    reports = {
        "interior": preflight(
            rendered.interior_pdf,
            width_mm=spec.page_mm,
            height_mm=spec.page_mm,
            bleed_mm=spec.bleed_mm,
            safe_mm=spec.safe_mm,
            signature=plan.spec.signature,
            min_dpi=plan.spec.dpi,
        ),
        "cover": preflight(
            rendered.cover_pdf,
            width_mm=spec.wrap_width_mm,
            height_mm=spec.page_mm,
            bleed_mm=spec.bleed_mm,
            safe_mm=spec.safe_mm,
            min_dpi=plan.spec.dpi,
        ),
    }
    return BookFiles(spec, rendered.interior_pdf, rendered.cover_pdf, rendered.proof_pdf, reports, flags)


def _halves(data: bytes) -> tuple[bytes, bytes]:
    """Preview spreads (not print size): cut the image in two halves."""
    with Image.open(io.BytesIO(data)) as im:
        w, h = im.size
        return _to_jpeg(im.crop((0, 0, w // 2, h))), _to_jpeg(im.crop((w // 2, 0, w, h)))


def plan_pages(plan: BookPlan) -> list[dict[str, object]]:
    """JSON-friendly page map for the reader and the review queue."""
    return [
        {"number": s.number, "kind": s.kind, "side": s.side, "beat": s.beat, "half": s.spread_half}
        for s in plan.slots
    ]
