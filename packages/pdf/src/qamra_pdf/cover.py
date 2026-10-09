"""The story-book cover wrap (front | spine | back): what goes on it, decided from the book and its cover art.

The templates (`_cover_parts.html.j2`) only lay out a `CoverDesign`; everything that depends on the picture or
on the book is decided here:

- **Reading the art** (`read_art`): the illustration's own palette (a deep tone for the spine and the back, a
  vivid accent, a pale tint), whether it is a light or a dark picture, and how far down from the top it stays
  calm. The title block, its soft backing (scrim) and the glow of the lettering follow from that, so the title
  sits in the picture's quiet sky instead of fighting the scene. Colors are kept inside a print-safe range
  (no neon RGB-only blues or greens, never pure black).
- **Front**: the title in poster lines (the child's name on its own line, in the name colors), the «بطولة»
  ribbon, and a small series pill (moon mark, brand, product line) in the outer bottom corner.
- **Back**: the title again, the story's own blurb, three small pages from the book, the facts (ages from the
  theme, the page count, fully vowelized text when it is), «نُسْخَةٌ خاصَّةٌ بِـ…», the child's waving figure from
  the approved character sheet (and the companion when there is one), the logo, the domain and an empty
  reserved area for a barcode. The QR card appears only when family voice exists.
- **Spine**: the deep tone of the art; title, name and moon when the spine is wide enough for type.

Class books (`classbook.py`) build the same design from their own data.
"""

import colorsys
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np
from markupsafe import Markup, escape
from PIL import Image

from qamra_pdf.assets import Assets
from qamra_pdf.lettering import Treatment, display_text, name_units, poster_layout, treatment
from qamra_pdf.spec import BookSpec, Brand, PageSpec
from qamra_pdf.strings import AR_DIGITS, STRINGS, page_count

if TYPE_CHECKING:
    from qamra_pdf.classbook import ChildCopy, ClassBookSpec

ArtMode = Literal["light", "dark"]
SPINE_TYPE_MM = 6.0  # narrower spines carry no type (printers ask for ≥ 1.5 mm clear on each side)
TITLE_TOP_MM = 8.5  # the title block starts this far below the trim (its letters then sit ≥ 10 mm in)
RIBBON_MM = 14.0  # the ribbon's height under the title
HERO_MAX_MM = 74.0  # the waving figure on the back, at most this tall (and never under 300 DPI)
PRINT_DPI = 300
_MARKS = re.compile("[\\u064b-\\u0652]")
_ARABIC = re.compile("[\\u0621-\\u064a]")


@dataclass(frozen=True)
class ArtReading:
    """What the cover picture tells the layout."""

    mode: ArtMode = "dark"
    deep: str = "#16204A"  # spine, back tint, the series pill on light art
    accent: str = "#D9922A"  # chips, the name on the back, rules
    light: str = "#FBF3E2"  # pale tint: the back of light art, the scrim on light art
    calm_mm: float = 60.0  # from the top of the page (bleed included): where the scene's detail begins
    busy: float = 0.5  # 0 calm … 1 busy, in the title block


DEFAULT_ART = ArtReading()


def _hex(r: float, g: float, b: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(v * 255))) for v in (r, g, b)))


def _hls_hex(h: float, lightness: float, s: float) -> str:
    # print-safe: saturated blues and greens beyond what CMYK reproduces are pulled back
    if 0.25 <= h <= 0.72:
        s = min(s, 0.58)
    return _hex(*colorsys.hls_to_rgb(h % 1.0, lightness, max(0.0, min(1.0, s))))


def _mean_hls(pixels: np.ndarray, weights: np.ndarray | None = None) -> tuple[float, float, float]:
    """Mean color of RGB rows (0–1) as HLS; the hue averaged on the circle."""
    if pixels.size == 0:
        return 0.62, 0.3, 0.3
    w = np.ones(len(pixels)) if weights is None else weights + 1e-6
    hls = np.array([colorsys.rgb_to_hls(*p) for p in pixels])
    ang = hls[:, 0] * 2 * np.pi
    h = (
        np.arctan2((np.sin(ang) * w * hls[:, 2]).sum(), (np.cos(ang) * w * hls[:, 2]).sum()) / (2 * np.pi)
    ) % 1
    return float(h), float((hls[:, 1] * w).sum() / w.sum()), float((hls[:, 2] * w).sum() / w.sum())


@lru_cache(maxsize=64)
def _read(path: str, mtime: float, page_mm: float) -> ArtReading:
    with Image.open(path) as original:
        small = original.convert("RGB").resize((48, 48), Image.Resampling.BILINEAR)
        rows = original.convert("L").resize((108, 108), Image.Resampling.BILINEAR)
    rgb = np.asarray(small, dtype=float).reshape(-1, 3) / 255
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722])
    hls = np.array([colorsys.rgb_to_hls(*p) for p in rgb])
    sat, lig = hls[:, 2], hls[:, 1]

    # the deep tone: the most common hue among the dark quarter of the picture (a mean would drift between
    # a navy sky and brown wood to an unrelated purple)
    shadow = luma <= np.percentile(luma, 25)
    h, _, s = _mean_hls(rgb[shadow], sat[shadow])
    tinted = shadow & (sat > 0.12)
    if tinted.sum() >= 8:
        hist, edges = np.histogram(hls[tinted, 0], bins=18, range=(0, 1), weights=sat[tinted])
        peak = int(hist.argmax())
        h = float((edges[peak] + edges[peak + 1]) / 2)
    deep = _hls_hex(h, 0.17, min(0.55, max(0.3, s)))
    bright = rgb[luma >= np.percentile(luma, 75)]
    h, _, s = _mean_hls(bright)
    light = _hls_hex(h, 0.94, min(0.5, max(0.2, s * 0.8)))
    vivid = (sat > 0.35) & (lig > 0.25) & (lig < 0.8)
    if vivid.sum() >= 12:
        hues = hls[vivid, 0]
        hist, edges = np.histogram(hues, bins=24, range=(0, 1), weights=sat[vivid])
        peak = int(hist.argmax())
        in_peak = (hues >= edges[peak]) & (hues < edges[peak + 1])
        accent = _hls_hex(
            float(hues[in_peak].mean()), 0.5, min(0.68, max(0.45, float(sat[vivid][in_peak].mean())))
        )
    else:
        accent = DEFAULT_ART.accent

    # detail per row (2 mm a row on a 216 mm page), over the middle 70 % of the width, smoothed over 7 rows
    y = np.asarray(rows, dtype=float) / 255
    grad = np.abs(np.diff(y, axis=1))[:-1, :] + np.abs(np.diff(y, axis=0))[:, :-1]
    profile = grad[:, 16:92].mean(axis=1)
    profile = np.convolve(profile, np.ones(7) / 7, mode="same")
    # the scene begins where the detail stays high for 10 mm, looked for below 36 mm: a busy strip at the very
    # top (a moon, lanterns, leaves) can sit behind the title, the hero's head and the scene below cannot
    mm_per_row = page_mm / len(profile)
    threshold = max(0.022, 0.55 * float(np.median(profile)))
    run = max(2, round(10 / mm_per_row))
    calm = page_mm * 0.6
    for i in range(round(36 / mm_per_row), len(profile) - run):
        if (profile[i : i + run] > threshold).all():
            calm = i * mm_per_row
            break
    block = profile[round(6 / mm_per_row) : round(80 / mm_per_row)]
    busy = float(np.clip(block.mean() / max(1e-6, 2.2 * float(np.median(profile))), 0, 1))
    return ArtReading(
        mode="dark" if float(luma.mean()) < 0.47 else "light",
        deep=deep,
        accent=accent,
        light=light,
        calm_mm=round(max(30.0, min(calm, page_mm * 0.6)), 1),
        busy=round(busy, 2),
    )


def read_art(path: Path | None, page_mm: float = 216.0) -> ArtReading:
    if path is None or not path.is_file():
        return DEFAULT_ART
    return _read(str(path), path.stat().st_mtime, page_mm)


def rgba(color: str, alpha: float) -> str:
    c = color.lstrip("#")
    r, g, b = (int(c[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


@dataclass(frozen=True)
class Chip:
    icon: Literal["age", "pages", "marks", "school"]
    text: str


@dataclass(frozen=True)
class CoverDesign:
    """Everything the cover templates lay out (front, back, spine), for one book or one class-book copy."""

    lang: Literal["ar", "en"]
    trim_mm: float
    bleed_mm: float
    safe_mm: float
    spine_mm: float
    art: Path
    back_art: Path | None
    reading: ArtReading
    t: Treatment
    title: str  # display lettering (short vowels dropped)
    name: str  # the child's name, painted in the name colors
    ribbon_label: str
    ribbon_name: str
    brand: Brand
    series: str | None  # «سحري»: shown after the brand on the front pill
    hook: str  # the title on the back
    blurb: str
    made_for: str
    chips: list[Chip]
    thumbs: list[Path]
    hero: Path | None
    hero_mm: tuple[float, float]  # (width, height) of the waving figure on the back
    companion: Path | None
    companion_mm: tuple[float, float]
    portrait: Path | None  # the round portrait, when there is no clean figure
    qr: Markup | None = None
    qr_caption: str = ""
    logo: Path | None = None  # a school's logo (class books)
    school_line: str | None = None
    spine_title: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def dir(self) -> str:
        return "rtl" if self.lang == "ar" else "ltr"

    @property
    def made_for_html(self) -> Markup:
        """«نُسْخَةٌ خاصَّةٌ بِـ{name}» with the name in its color (it is glued to «بِـ», so it is not a word of
        its own that `cover_name` could find)."""
        before, found, after = self.made_for.rpartition(self.name)
        if not found:
            return escape(self.made_for)
        return escape(before) + Markup('<span class="nm">%s</span>') % found + escape(after)

    @property
    def brand_name(self) -> str:
        return self.brand.name_ar if self.lang == "ar" else self.brand.name_en

    @property
    def dark(self) -> bool:
        return self.reading.mode == "dark"

    @property
    def title_lines(self) -> int:
        return len(poster_layout(self.title, self.name)[0])

    @property
    def title_h_mm(self) -> float:
        """The lettering's box: down to where the scene begins (10 mm into it at most), never smaller than a
        phone thumbnail can read; a title on two or three lines gets 6 mm more."""
        room = self.reading.calm_mm + 10 - (self.bleed_mm + TITLE_TOP_MM) - RIBBON_MM
        extra = 6.0 if self.title_lines > 1 else 0.0
        return round(max(44.0, min(62.0, room)) + extra, 1)

    @property
    def scrim(self) -> str:
        """A soft wash of the art's own tone behind the title block, stronger over busy art."""
        bottom = self.bleed_mm + TITLE_TOP_MM + self.title_h_mm + RIBBON_MM
        if self.dark:
            a = 0.42 + 0.3 * self.reading.busy
            tone = self.reading.deep
        else:
            a = 0.38 + 0.34 * self.reading.busy
            tone = self.reading.light
        return (
            f"radial-gradient(ellipse 82% {bottom + 26:.0f}mm at 50% 0%, {rgba(tone, a)} 0%, "
            f"{rgba(tone, a * 0.82)} 55%, {rgba(tone, 0)} 100%)"
        )

    @property
    def glow(self) -> float:
        return 1.0 if self.dark else 0.35

    @property
    def spine_type(self) -> bool:
        return self.spine_mm >= SPINE_TYPE_MM

    @property
    def spine_pt(self) -> float:
        return round(min(13.0, (self.spine_mm - 2.6) / 1.45 / 0.3528), 1)

    @property
    def ink(self) -> str:
        """Text on the back: cream on dark art, the deep tone on light art."""
        return "#FFF8EA" if self.dark else self.reading.deep

    @property
    def gold_ink(self) -> str:
        """Titles, icons and rules on the back: moon gold on dark art, the book's accent on light art."""
        return "#F6C35A" if self.dark else self.t.accent

    @property
    def name_ink(self) -> str:
        """The child's name in the back's texts (the same accent as the name inside the book)."""
        return "#FFD36B" if self.dark else self.t.accent

    @property
    def spine_edge(self) -> str:
        return _shade(self.reading.deep, 0.11)


def _shade(color: str, lightness: float) -> str:
    """The same hue at another lightness (print-safe saturation)."""
    c = color.lstrip("#")
    h, _, s = colorsys.rgb_to_hls(*(int(c[i : i + 2], 16) / 255 for i in (0, 2, 4)))
    return _hls_hex(h, lightness, min(0.7, s))


def cover_name(text: str, name: str) -> Markup:
    """`text` with the child's name in a `span.nm` (the name's color on the back and the spine)."""
    units, at = name_units(text, name)
    if at is None:
        return escape(text)
    return Markup(" ").join(
        escape(u) if i != at else Markup('<span class="nm">%s</span>') % u for i, u in enumerate(units)
    )


def _digits(text: str, lang: str) -> str:
    return text.translate(AR_DIGITS) if lang == "ar" else text


def is_vowelized(texts: Sequence[str | None]) -> bool:
    """Fully vowelized Arabic: every story text (of a few words or more) has at least one short-vowel mark for
    every two letters, so one page a parent retyped without marks drops the claim."""
    counted = 0
    for text in texts:
        letters = len(_ARABIC.findall(text or ""))
        if letters < 8:
            continue
        if len(_MARKS.findall(text or "")) < 0.5 * letters:
            return False
        counted += letters
    return counted >= 40


def pick_thumbs(images: Sequence[Path], n: int = 3) -> list[Path]:
    """`n` pictures spread through the story (not the first or the last page), each picture once."""
    seen: list[Path] = []
    for p in images:
        if p not in seen:
            seen.append(p)
    if len(seen) <= n:
        return seen
    inner = seen[1:-1] if len(seen) > n + 2 else seen
    step = len(inner) / n
    return [inner[min(len(inner) - 1, int(step * i + step / 2))] for i in range(n)]


def story_thumbs(pages: Sequence[PageSpec]) -> list[Path]:
    """Single-page story pictures (a spread's half would cut the scene)."""
    single = [
        p.image
        for p in pages
        if p.kind == "story" and p.image is not None and p.layout not in ("spread", "spread-panorama")
    ]
    return pick_thumbs(single)


def figure_mm(path: Path | None, max_h: float, dpi: int = PRINT_DPI) -> tuple[float, float]:
    """A cut-out's printed size: up to `max_h` tall, never below `dpi` at its own resolution."""
    if path is None or not path.is_file():
        return 0.0, 0.0
    with Image.open(path) as im:
        w, h = im.size
    height = min(max_h, h / dpi * 25.4 * 0.99)  # 1 % under the limit: rounding never drops it below `dpi`
    return round(w * height / h, 2), round(height, 2)


def series_label(series: str | None, lang: str) -> str | None:
    if not series:
        return None
    return STRINGS[lang].get(f"series_{series}")


def story_design(spec: BookSpec, assets: Assets, qr: Markup | None = None) -> CoverDesign:
    s = STRINGS[spec.lang]
    c = spec.cover
    reading = read_art(c.front_image, spec.page_mm)
    chips: list[Chip] = []
    if spec.age_range:
        low, high = spec.age_range
        chips.append(Chip("age", _digits(s["ages"].format(low=low, high=high), spec.lang)))
    chips.append(Chip("pages", page_count(len(spec.pages), spec.lang)))
    if spec.lang == "ar" and is_vowelized([p.text for p in spec.pages]):
        chips.append(Chip("marks", s["vowelized"]))
    hero_mm = figure_mm(assets.hero, HERO_MAX_MM)
    companion_mm = figure_mm(assets.companion, round(hero_mm[1] * 0.58, 1) or 40.0)
    title = display_text(f"{c.name} {c.subtitle}".strip())
    name = display_text(spec.child_name)
    return CoverDesign(
        lang=spec.lang,
        trim_mm=spec.trim_mm,
        bleed_mm=spec.bleed_mm,
        safe_mm=spec.safe_mm,
        spine_mm=spec.spine_mm,
        art=c.front_image,
        back_art=assets.back,
        reading=reading,
        t=treatment(spec.title_style),
        title=title,
        name=name,
        ribbon_label=s["ribbon_f"] if spec.gender == "f" else s["ribbon_m"],
        ribbon_name=name,
        brand=spec.brand,
        series=series_label(spec.series, spec.lang),
        hook=title,
        blurb=c.blurb,
        made_for=s["made_for_copy"].format(name=name),
        chips=chips,
        thumbs=list(assets.thumbs),
        hero=assets.hero,
        hero_mm=hero_mm,
        companion=assets.companion if assets.hero else None,
        companion_mm=companion_mm,
        portrait=spec.title_page.portrait,
        qr=qr,
        qr_caption=s["back_voice"],
        spine_title=spine_text(display_text(spec.title), name),
    )


def spine_text(title: str, name: str) -> str:
    """The title, followed by the name when the title does not already carry it."""
    if name_units(title, name)[1] is not None:
        return title
    return f"{title} · {name}"


def class_design(
    spec: "ClassBookSpec",
    copy: "ChildCopy",
    assets: Assets,
) -> CoverDesign:
    """A child's personal cover of a «كتاب الصف»: the same design, with the class book's own words, the
    child's cut-out portrait, the school (and its logo) on the back."""
    s = STRINGS[spec.lang]
    reading = read_art(copy.cover_image, spec.page_mm)
    name = display_text(copy.name)
    chips: list[Chip] = []
    if spec.age_range:
        low, high = spec.age_range
        chips.append(Chip("age", _digits(s["ages"].format(low=low, high=high), spec.lang)))
    chips.append(Chip("pages", page_count(spec.interior_pages, spec.lang)))
    if spec.lang == "ar" and is_vowelized([p.text for p in spec.pages]):
        chips.append(Chip("marks", s["vowelized"]))
    school = spec.school
    sep = "، " if spec.lang == "ar" else ", "
    title = display_text(f"{copy.name} {spec.cover_subtitle}".strip())
    gendered = {"f": s["ribbon_f"], "m": s["ribbon_m"]}
    return CoverDesign(
        lang=spec.lang,
        trim_mm=spec.trim_mm,
        bleed_mm=spec.bleed_mm,
        safe_mm=spec.safe_mm,
        spine_mm=spec.spine_mm,
        art=copy.cover_image,
        back_art=assets.back,
        reading=reading,
        t=treatment(spec.title_style),
        title=title,
        name=name,
        ribbon_label=gendered.get(copy.gender or "", school.school),
        ribbon_name=name if copy.gender else "",
        brand=spec.brand,
        series=series_label("class", spec.lang),
        hook=display_text(spec.title),
        blurb=spec.blurb,
        made_for=s["made_for_copy"].format(name=name),
        chips=chips,
        thumbs=list(assets.thumbs),
        hero=assets.hero,
        hero_mm=figure_mm(assets.hero, HERO_MAX_MM, spec.dpi),
        companion=None,
        companion_mm=(0.0, 0.0),
        portrait=None,
        logo=school.logo,
        school_line=sep.join(p for p in (school.school, _digits(school.year or "", spec.lang)) if p),
        spine_title=spine_text(display_text(spec.title), name),
    )
