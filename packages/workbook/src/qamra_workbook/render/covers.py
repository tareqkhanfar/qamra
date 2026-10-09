"""The covers of the four activity series (the owner's request of 2026-10-09: «بدنا اشي أكثر احترافية…»).

One system for «دوسية التأسيس», «رحلتي الأولى للتعلّم», «مغامراتي مع عائلتي» and «قلبي يعرف الله», each in
its own colors and title panel. A cover is a layered composition in code (docs/plans/cover-scenes.md):

1. **Scene:** a full-bleed picture of what the part holds (`content/covers/scenes/<part>.jpg`, drawn once per
   part, no text and no people). Until a part has one, its older plate (`content/assets/G*`, `F5`–`F10`) or a
   vector landscape stands in, so every cover is complete without it.
2. **Props:** the part's real letters, numbers or shapes as toy blocks (SVG; a scene never draws letters).
3. **Child:** the approved character, cut out with its white sticker edge, standing in the scene's lit spot.
4. **Lettering:** the series title as sticker letters (one color per word, a white keyline, a dark outline
   and a toy-block extrusion), on the series' panel; the child's name on a ribbon; level, volume and age
   pills; three info badges; the Qamra moon. Every word is set in code.

The back repeats the scene as a band with the child waving, then a short blurb, «في هذا الجزء» from the
part's real content, three real pages of the volume, «يأتي مع الكتاب» (only what the book holds), the ages,
pages and binding, and qamra.app. The Islamic volumes are perfect-bound: their cover is one wrap
[front | spine | back] with the spine sized from the page count (`spine_mm`).

Every word the covers add is in `content/covers/covers.yaml`. Print rules: the scene and the pages are
resampled to 300 DPI at their printed size, every letter stays vector (outlines are filled copies, never an
SVG stroke, which Chromium would print as a Type 3 font), and text keeps to the safe area.
"""

from __future__ import annotations

import functools
import hashlib
import math
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pypdfium2 as pdfium
import yaml
from markupsafe import Markup, escape
from PIL import Image, ImageEnhance

from qamra_pdf.arabic_names import case_forms
from qamra_pdf.lettering import honorific_runs, honorific_tspan, with_honorifics
from qamra_workbook.render import art, draw
from qamra_workbook.render.character import pose
from qamra_workbook.render.registry import PageContext
from qamra_workbook.render.spec import BookSpec, Geometry, Numerals, format_number

REPO = Path(__file__).resolve().parents[5]
CONTENT = REPO / "content" / "covers"
COPY = CONTENT / "covers.yaml"
SCENES = CONTENT / "scenes"
ASSETS = REPO / "content" / "assets"
DPI = 300
Series = Literal["foundation", "journey", "family", "islamic"]

# The older plates (2D, drawn 2026-10-03) a part shows until its own scene is installed.
PLATES: dict[str, str] = {
    **dict.fromkeys(("kg1-v1", "kg1-v2", "kg1-v3"), "G4-foundation-kg1"),
    **dict.fromkeys(("kg2-v1", "kg2-v2", "kg2-v3"), "G5-foundation-kg2"),
    "journey-1": "G1-journey-stage-1",
    "journey-2": "G2-journey-stage-2",
    "journey-3": "G3-journey-stage-3",
    "islamic-v1": "F5-cover-v1",
    "islamic-v2": "F6-cover-v2",
    "islamic-v3": "F7-cover-v3",
    "islamic-v4": "F8-cover-v4",
    "islamic-v5": "F9-cover-v5",
    "islamic-r": "F10-cover-ramadan",
}

# The perfect-bound spine (the Islamic volumes): one leaf of the interior paper and the cover card's share.
# Placeholders until the print partner confirms its paper (docs/decisions.md 2026-10-09).
GRADE = (1.12, 1.04)  # the scenes' saturation and contrast in print (matte card dulls them a little)
SOFTCOVER_LEAF_MM = 0.12
SOFTCOVER_COVER_MM = 0.6
SPINE_TEXT_MIN_MM = 6.0  # narrower spines carry the color and the moon only
SPINE_HINGE_MM = 7.0  # keep the front's and back's text this far from the fold (the glued hinge)


# ---- the series' looks -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Look:
    """One series' identity on its covers."""

    font: str  # the title's CSS family
    words: tuple[tuple[str, str], ...]  # per title word, cycled: (top, bottom) of its vertical gradient
    name_word: tuple[str, str]  # the child's name when the title holds it (the family book)
    outline: str  # dark line around the white keyline, and the block extrusion
    keyline: str
    panel: str  # the title panel
    panel_edge: str  # its offset "card" shadow
    panel_shape: Literal["notebook", "trail", "house", "arch"]
    ribbon: tuple[str, str]  # gradient of the name ribbon
    ribbon_fold: str
    ribbon_ink: str
    pill: str  # level and volume pills
    pill_ink: str
    pill_alt: str
    pill_alt_ink: str
    accent: str  # icons and headings on the back
    ink: str  # dark text
    paper: str  # the back's paper
    soft: str  # light cards on the back
    blocks: tuple[str, ...]  # toy block colors, cycled
    spine: str = "#1F5A46"


LOOKS: dict[str, Look] = {
    "foundation": Look(
        font="Baloo Bhaijaan 2",
        words=(
            ("#FFB38F", "#F0582D"),
            ("#7DD6FF", "#1E88D6"),
            ("#FFE27A", "#F2A516"),
            ("#9BE38E", "#2FA36B"),
        ),
        name_word=("#FFE27A", "#F2A516"),
        outline="#1C2140",
        keyline="#FFFFFF",
        panel="#FFFFFF",
        panel_edge="#F2B33D",
        panel_shape="notebook",
        ribbon=("#2B3A85", "#16204A"),
        ribbon_fold="#0D1433",
        ribbon_ink="#FFFFFF",
        pill="#16204A",
        pill_ink="#FFFFFF",
        pill_alt="#F2B33D",
        pill_alt_ink="#16204A",
        accent="#E9A62B",
        ink="#1C2140",
        paper="#FFF9EE",
        soft="#FFFFFF",
        blocks=("#F0643C", "#2E9FD6", "#F2B21E", "#2FA36B", "#8C6CCB", "#E4769D"),
    ),
    "journey": Look(
        font="Baloo Bhaijaan 2",
        words=(("#8FF0E2", "#0E9C8C"), ("#FFC37A", "#F07B1E"), ("#C7F08A", "#4BAF3A")),
        name_word=("#FFC37A", "#F07B1E"),
        outline="#163A4C",
        keyline="#FFFFFF",
        panel="#FFFFFF",
        panel_edge="#0E9C8C",
        panel_shape="trail",
        ribbon=("#FF9A3D", "#E8701A"),
        ribbon_fold="#A84A0C",
        ribbon_ink="#FFFFFF",
        pill="#163A4C",
        pill_ink="#FFFFFF",
        pill_alt="#0E9C8C",
        pill_alt_ink="#FFFFFF",
        accent="#0E9C8C",
        ink="#163A4C",
        paper="#F6FBF8",
        soft="#FFFFFF",
        blocks=("#F07B1E", "#0E9C8C", "#F2B21E", "#5A79CF", "#E4675A", "#4BAF3A"),
    ),
    "family": Look(
        font="Baloo Bhaijaan 2",
        words=(("#FFB0C9", "#E4497F"), ("#FFD27A", "#F08A3E"), ("#8FD3FF", "#2E8FD6")),
        name_word=("#FFE27A", "#F2A516"),
        outline="#3A1830",
        keyline="#FFFFFF",
        panel="#FFFFFF",
        panel_edge="#E4497F",
        panel_shape="house",
        ribbon=("#2E9FD6", "#1D74B5"),
        ribbon_fold="#114A78",
        ribbon_ink="#FFFFFF",
        pill="#3A1830",
        pill_ink="#FFFFFF",
        pill_alt="#F08A3E",
        pill_alt_ink="#FFFFFF",
        accent="#E4497F",
        ink="#2A1626",
        paper="#FFF8F3",
        soft="#FFFFFF",
        blocks=("#E4497F", "#F08A3E", "#2E9FD6"),
    ),
    "islamic": Look(
        font="Baloo Bhaijaan 2",
        words=(("#FFF3C4", "#E2A21F"),),
        name_word=("#FFF3C4", "#E2A21F"),
        outline="#0F3B2E",
        keyline="#FFFFFF",
        panel="#FFFBF0",
        panel_edge="#C9962B",
        panel_shape="arch",
        ribbon=("#2A7A5E", "#1F5A46"),
        ribbon_fold="#103326",
        ribbon_ink="#FFFFFF",
        pill="#1F5A46",
        pill_ink="#FFFFFF",
        pill_alt="#C9962B",
        pill_alt_ink="#FFFFFF",
        accent="#C9962B",
        ink="#173B30",
        paper="#FFFAF0",
        soft="#FFFFFF",
        blocks=("#C9962B",),
        spine="#1F5A46",
    ),
}


@functools.cache
def copy() -> dict[str, Any]:
    """The covers' words (content/covers/covers.yaml)."""
    data = yaml.safe_load(COPY.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def series_copy(series: str) -> dict[str, Any]:
    out = copy().get(series) or {}
    return dict(out) if isinstance(out, dict) else {}


def part_copy(series: str, part: str) -> dict[str, Any]:
    parts = series_copy(series).get("parts") or {}
    out = parts.get(part) or {}
    return dict(out) if isinstance(out, dict) else {}


# ---- Arabic counts -----------------------------------------------------------------------------------------


def counted(n: int, one: str, plural: str, *, vowelized: bool = False) -> str:
    """«١٢٠ صفحة», «٨ وحدات»: the counted noun agrees with the number (3–10 plural, 11–99 singular; the
    hundreds count by their last part). `one` and `plural` are the bare forms; with `vowelized`, the noun
    takes its case: accusative singular after 11–99 («صَفْحَةً»), genitive after 3–10 and round hundreds."""
    rest = n % 100
    if 3 <= rest <= 10:
        word = plural + ("ٍ" if vowelized else "")
    elif rest >= 11:
        word = one + ("ً" if vowelized else "")
    else:  # 100, 200…, or 101/102: a genitive singular reads right after a round hundred
        word = one + ("ٍ" if vowelized else "")
    return f"{n} {word}"


# ---- scene plates ------------------------------------------------------------------------------------------


def scene_source(part: str) -> Path | None:
    """The part's drawn scene, else its older plate, else None (a vector scene)."""
    drawn = SCENES / f"{part}.jpg"
    if drawn.is_file():
        return drawn
    stem = PLATES.get(part)
    plate = ASSETS / f"{stem}.jpg" if stem else None
    return plate if plate is not None and plate.is_file() else None


def plate(
    src: Path, out_dir: Path, w_mm: float, h_mm: float, *, focus: float = 0.5, band: float | None = None
) -> Path:
    """`src` cropped to w × h mm and resampled to 300 DPI at that size (cached by content). A full cover keeps
    the picture's bottom when it must lose height (the child's spot) and its middle when it loses width.
    `band` (0–1): crop a horizontal strip centered at that height of the picture instead (the back's band)."""
    digest = hashlib.sha256(src.read_bytes()).hexdigest()[:12]
    tag = (f"b{band:g}" if band is not None else f"f{focus:g}") + f"-g{GRADE[0]:g}"
    out = out_dir / f"scene-{digest}-{w_mm:g}x{h_mm:g}-{tag}.jpg"
    if out.exists():
        return out
    target = (round(w_mm / 25.4 * DPI), round(h_mm / 25.4 * DPI))
    with Image.open(src) as img:
        rgb = img.convert("RGB")
    ratio = target[0] / target[1]
    w, h = rgb.size
    if w / h > ratio:  # wider than the box: crop the sides around `focus`
        keep = round(h * ratio)
        left = min(max(0, round(w * focus - keep / 2)), w - keep)
        rgb = rgb.crop((left, 0, left + keep, h))
    else:
        keep = round(w / ratio)
        # keep the bottom (the scene's spot and props), or the band around `band`
        top = h - keep if band is None else min(max(0, round(h * band - keep / 2)), h - keep)
        rgb = rgb.crop((0, top, w, top + keep))
    rgb = rgb.resize(target, Image.Resampling.LANCZOS)
    rgb = ImageEnhance.Contrast(ImageEnhance.Color(rgb).enhance(GRADE[0])).enhance(GRADE[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    rgb.save(out, format="JPEG", quality=90, dpi=(DPI, DPI))
    return out


def uri(path: Path | None) -> str:
    return path.resolve().as_uri() if path is not None else ""


# ---- the box a cover panel fills ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Box:
    """A cover panel on its page (mm): where it starts, its size with the bleed on its outer sides, and the
    distance from each of its edges to where text may go (the safe area, or the spine's hinge)."""

    x: float
    w: float
    h: float
    left: float
    right: float
    top: float
    bottom: float

    @classmethod
    def page(cls, g: Geometry) -> Box:
        return cls(0.0, g.page_w, g.page_h, g.inset, g.inset, g.inset, g.inset)

    @property
    def inner_w(self) -> float:
        return self.w - self.left - self.right

    @property
    def cx(self) -> float:
        return self.left + self.inner_w / 2

    def style(self) -> str:
        return f"left: {self.x:.2f}mm; width: {self.w:.2f}mm; height: {self.h:.2f}mm;"


# ---- lettering ---------------------------------------------------------------------------------------------

_MARKS = re.compile("[\\u0610-\\u061a\\u064b-\\u065f\\u0670\\u06d6-\\u06ed\\u0640]")


def letters(text: str) -> int:
    return len(_MARKS.sub("", text).replace(" ", ""))


def printed_name(title: str, name: str) -> str:
    """The child's name as `title` prints it: as typed, or in its case when the title inflects it
    («مُغامَراتُ أبي بكر» for «أبو بكر», `qamra_pdf.arabic_names.case_forms`)."""
    return next((form for form in case_forms(name) if form in title), name)


def title_lines(title: str, keep: str = "", one_line_max: int = 14) -> list[str]:
    """One line up to `one_line_max` letters, else two balanced lines that never break a word, keep the
    words of `keep` (the child's name) together and prefer a second line that starts with «و»."""
    words = title.split()
    if letters(title) <= one_line_max or len(words) < 2:
        return [title]
    best, best_cost = [title], math.inf
    name = keep.split()
    for cut in range(1, len(words)):
        a, b = words[:cut], words[cut:]
        if (
            name
            and len(name) > 1
            and any(a[-k:] == name[:k] and b[: len(name) - k] == name[k:] for k in range(1, len(name)))
        ):
            continue  # the name would be split
        cost = max(letters(" ".join(a)), letters(" ".join(b))) * 10.0
        if _MARKS.sub("", b[0]).startswith("و"):
            cost -= 15
        if cost < best_cost:
            best, best_cost = [" ".join(a), " ".join(b)], cost
    return best


def _ring(radius: float, n: int) -> list[tuple[float, float]]:
    return [
        (round(radius * math.cos(2 * math.pi * i / n), 3), round(radius * math.sin(2 * math.pi * i / n), 3))
        for i in range(n)
    ]


# The sticker effect follows the title's fitted size: full from FULL_EFFECT_MM (every front reaches it), in
# proportion below, and under SMALL_TITLE_MM (the backs) only a hint of the extrusion and the soft shadow.
FULL_EFFECT_MM = 18.0
SMALL_TITLE_MM = 10.0


def title_svg(
    lines: Sequence[str],
    look: Look,
    *,
    width: float,
    height: float,
    uid: str,
    name: str = "",
    keyline: float = 1.5,
    outline: float = 0.75,
    depth: float = 1.6,
    cap: float = 0.0,
    full: float = FULL_EFFECT_MM,
) -> Markup:
    """The title as sticker letters (mm units): each word in its own gradient, a white keyline, a dark outline
    and a toy-block extrusion below. Font sizes and line positions are set in the browser
    (`COVER_FIT_JS`): each line as wide as the box allows, the stack fitted to its height. `cap` limits the
    font size (mm; 0 = none). Words equal to `name` take the look's name colors.

    `keyline`, `outline` and `depth` (mm) are the effect at a font size of `full` mm or more; a smaller title
    gets them in proportion to its size (thin lines at print size, never a smudge), and below
    `SMALL_TITLE_MM` only a hint of the extrusion and the soft shadow. An honorific sign (ﷺ, ﷻ…) is set apart
    (`qamra_pdf.lettering.HONORIFIC`): smaller, in Naskh, solid, raised, outside every outline layer."""
    defs, color_texts, base_ids = [], [], []
    gradients: dict[tuple[str, str], str] = {}

    def gradient(pair: tuple[str, str]) -> str:
        if pair not in gradients:
            gid = f"{uid}-g{len(gradients)}"
            gradients[pair] = gid
            defs.append(
                f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{pair[0]}"/><stop offset="0.18" stop-color="{pair[0]}"/>'
                f'<stop offset="0.62" stop-color="{_mix(pair[0], pair[1], 0.72)}"/>'
                f'<stop offset="1" stop-color="{pair[1]}"/></linearGradient>'
            )
        return gradients[pair]

    k = 0
    plain_name = _MARKS.sub("", name)
    for i, line in enumerate(lines):
        base_id = f"{uid}-l{i}"
        base_ids.append(base_id)
        # the copies (outline, keyline, extrusion, shadow) never draw an honorific sign: fill="none"
        defs.append(
            f'<text id="{base_id}" class="cvt-line cvt-l{i}" direction="rtl" text-anchor="middle" '
            f'x="{width / 2:.2f}" y="{height / 2:.2f}" font-family="{look.font}" font-weight="800" '
            f'font-size="10">{with_honorifics(line, "none")}</text>'
        )
        spans = ""  # the same characters as the base text, each word in its colors
        pair = look.words[k % len(look.words)]
        for j, word in enumerate(line.split()):
            runs = honorific_runs(word)
            lone = len(runs) == 1 and runs[0][1]  # a sign after a space takes the space at its own size
            if plain_name and _MARKS.sub("", word) == plain_name:
                pair = look.name_word
            elif not lone:
                pair = look.words[k % len(look.words)]
                k += 1
            if j and not lone:
                spans += " "
            for run, sign in runs:
                if sign:
                    spans += str(honorific_tspan((" " if lone and j else "") + run, look.outline))
                else:
                    spans += f'<tspan fill="url(#{gradient(pair)})">{escape(run)}</tspan>'
        color_texts.append(
            f'<text class="cvt-line cvt-l{i}" direction="rtl" text-anchor="middle" x="{width / 2:.2f}" '
            f'y="{height / 2:.2f}" font-family="{look.font}" font-weight="800" font-size="10">'
            f"{spans}</text>"
        )

    def copies(offsets: Iterable[tuple[float, float, float]]) -> str:
        """A `<use>` per line and offset: (dx, dy) of the outline's ring, `d` of the depth below (`data-d`,
        so the fit can scale the two apart)."""
        out = []
        for b in base_ids:
            for dx, dy, d in offsets:
                below = f' data-d="{d}"' if d else ""
                out.append(f'<use href="#{b}" x="{dx}" y="{round(dy + d, 3)}"{below}/>')
        return "".join(out)

    ring = keyline + outline
    outer = [(dx, dy, 0.0) for dx, dy in _ring(ring, 28) + _ring(ring * 0.6, 14)]
    inner = [(dx, dy, 0.0) for dx, dy in _ring(keyline, 24) + _ring(keyline * 0.55, 12)]
    steps = [round(depth * (j + 1) / 4, 3) for j in range(4)]
    extrusion = [(dx, dy, s) for s in steps for dx, dy in _ring(ring, 20)]
    shadow = [(dx, dy, round(depth + 1.4, 3)) for dx, dy in _ring(ring, 12)]
    layers = [
        f'<g class="cvt-soft" fill="{look.outline}" opacity=".22" filter="url(#{uid}-soft)">'
        f"{copies(shadow)}</g>",
        f'<g fill="{look.outline}">{copies(extrusion)}</g>',
        f'<g fill="{look.outline}">{copies(outer)}</g>',
        f'<g fill="{look.keyline}">{copies(inner)}</g>',
        *color_texts,
    ]
    defs.append(
        f'<filter id="{uid}-soft" x="-10%" y="-30%" width="120%" height="160%">'
        '<feGaussianBlur stdDeviation="1.1"/></filter>'
    )
    pad = ring + 1.5
    return Markup(  # nosec B704 (the only text is escaped above)
        f'<svg class="cvt" viewBox="0 0 {width:.2f} {height:.2f}" width="{width:.2f}mm" '
        f'height="{height:.2f}mm" data-pad="{pad:.2f}" data-depth="{depth + 1.2:.2f}" data-cap="{cap:.2f}" '
        f'data-ring="{ring:.2f}" data-full="{full:.2f}" data-small="{SMALL_TITLE_MM:.2f}" '
        f'data-marks="{1 if any(_MARKS.search(line) for line in lines) else 0}" '
        f'role="img" aria-label="{escape(" ".join(lines))}"><defs>{"".join(defs)}</defs>'
        f"{''.join(layers)}</svg>"
    )


# Fits every `svg.cvt` (each line as wide as the box allows, lines within 1.25× of each other, the stack
# fitted to the height with room for the extrusion). The outline, keyline and extrusion follow the fitted
# size: full at `data-full` mm and above, in proportion below it, and below `data-small` the extrusion and the
# soft shadow shrink to a hint (the copies' offsets are scaled, then the box is fitted again with the room
# the thinner effect needs). Then, in every cover box (`[data-box]`) that overflows, hides its optional pieces
# (`[data-drop]`, lowest number first: the blurb's later lines, the pages, the series' books, the care note)
# until it fits, and lists the boxes that still overflow: a cover never prints with text cut off, and a long
# name or an organization's logo never stops an order.
COVER_FIT_JS = """
() => {
  for (const svg of document.querySelectorAll('svg.cvt')) {
    const vb = svg.viewBox.baseVal, W = vb.width, H = vb.height;
    const pad0 = parseFloat(svg.dataset.pad || '3'), depth0 = parseFloat(svg.dataset.depth || '2');
    const cap = parseFloat(svg.dataset.cap || '0');
    const ring = parseFloat(svg.dataset.ring || '0');
    const full = parseFloat(svg.dataset.full || '0'), small = parseFloat(svg.dataset.small || '0');
    const n = svg.querySelectorAll('defs text.cvt-line').length;
    const lines = [...Array(n).keys()].map(i => [...svg.querySelectorAll('text.cvt-l' + i)]);
    const marks = svg.dataset.marks === '1';  // tashkeel rises above the letters and hangs below them
    const lh = v => v * (marks ? 1.42 : n > 1 ? 1.16 : 1.0);
    const rise = marks ? 1.06 : 0.80;  // the first baseline below the line's top
    const widths = lines.map(texts => {
      texts.forEach(t => t.setAttribute('font-size', 10));
      return texts[0].getComputedTextLength() || 1;
    });
    const fit = (pad, depth) => {
      let s = widths.map(len => 10 * (W - 2 * pad) / len).map(v => cap > 0 ? Math.min(v, cap) : v);
      const smallest = Math.min(...s);
      s = s.map(v => Math.min(v, smallest * 1.25));
      const room = H - 2 * pad - depth;
      const total = s.reduce((a, v) => a + lh(v), 0);
      if (total > room) { const k = room / total; s = s.map(v => v * k); }
      return s;
    };
    let pad = pad0, depth = depth0, s = fit(pad, depth), kr = 1, kd = 1;
    if (full > 0 && Math.min(...s) < full) {
      let f = Math.min(...s);
      for (let i = 0; i < 4; i++) {  // a thinner effect needs less room, so the text grows a little: settle
        kr = Math.min(1, f / full);
        kd = f < small ? kr * 0.35 : kr;
        pad = pad0 - ring * (1 - kr);
        depth = depth0 * kd;
        s = fit(pad, depth);
        f = Math.min(...s);
      }
      for (const u of svg.querySelectorAll('use')) {
        if (u.dataset.x === undefined) {  // the offsets at full size, kept so a second fit starts from them
          u.dataset.x = u.getAttribute('x') || '0';
          u.dataset.y = u.getAttribute('y') || '0';
        }
        const d = parseFloat(u.dataset.d || '0');
        u.setAttribute('x', (parseFloat(u.dataset.x) * kr).toFixed(3));
        u.setAttribute('y', ((parseFloat(u.dataset.y) - d) * kr + d * kd).toFixed(3));
      }
      const soft = svg.querySelector('.cvt-soft');
      if (soft && kd < kr) soft.setAttribute('opacity', '.12');
      const blur = svg.querySelector('feGaussianBlur');
      if (blur) blur.setAttribute('stdDeviation', (1.1 * Math.max(kr, 0.3)).toFixed(2));
    }
    const room = H - 2 * pad - depth;
    const total = s.reduce((a, v) => a + lh(v), 0);
    let y = pad + (room - total) / 2;
    lines.forEach((texts, i) => {
      const base = y + s[i] * rise;
      texts.forEach(t => {
        t.setAttribute('font-size', s[i].toFixed(2));
        t.setAttribute('y', base.toFixed(2));
      });
      y += lh(s[i]);
    });
    svg.dataset.fs = Math.min(...s).toFixed(2);  // the fitted size (mm), for tests and reviews
  }
  const out = [];
  for (const box of document.querySelectorAll('[data-box]')) {
    const over = () => box.scrollHeight > box.clientHeight + 2
      || (box.hasAttribute('data-box-x') && box.scrollWidth > box.clientWidth + 2);
    const drops = [...box.querySelectorAll('[data-drop]')].sort((a, b) => a.dataset.drop - b.dataset.drop);
    for (const el of drops) {  // optional content goes first (an organization's logo, a very long name…)
      if (!over()) break;
      el.style.display = 'none';
      const list = el.classList.contains('cvk-thumbs') && el.parentElement.querySelector('ul');
      if (list) list.className = 'cols-2';  // without the pages beside it, the list takes two columns
    }
    if (over()) {
      const page = box.closest('[data-page]');
      out.push((page ? page.dataset.page : '?') + ': the cover\\'s ' + box.dataset.box + ' overflows');
    }
  }
  return out;
}
"""


# ---- panels, ribbons, blocks ------------------------------------------------------------------------------


def panel_svg(look: Look, w: float, h: float, uid: str) -> Markup:
    """The title's panel (mm), drawn with its offset card shadow (`panel_edge`) and the series' shape: a
    spiral-notebook page, a trail sign with a dashed path, a house with a roof, or an arch."""
    e = 2.6  # the offset shadow
    r = 7.0
    body: list[str] = []
    shape = look.panel_shape
    if shape == "house":
        roof = min(17.0, h * 0.22)
        eave = min(52.0, w * 0.28)
        d = (
            f"M{r} {roof} L{w / 2 - eave} {roof} L{w / 2 - 3} 0.8 Q{w / 2} -0.6 {w / 2 + 3} 0.8 "
            f"L{w / 2 + eave} {roof} L{w - r} {roof} "
            f"Q{w} {roof} {w} {roof + r} L{w} {h - r} Q{w} {h} {w - r} {h} L{r} {h} Q0 {h} 0 {h - r} "
            f"L0 {roof + r} Q0 {roof} {r} {roof} Z"
        )
    elif shape == "arch":  # a pointed arch, like a window of the old city
        top = min(20.0, h * 0.26)
        d = (
            f"M0 {top} C0 {top * 0.42} {w * 0.3} {top * 0.16} {w / 2 - 2} 1 L{w / 2} -1.4 L{w / 2 + 2} 1 "
            f"C{w * 0.7} {top * 0.16} {w} {top * 0.42} {w} {top} "
            f"L{w} {h - r} Q{w} {h} {w - r} {h} L{r} {h} Q0 {h} 0 {h - r} Z"
        )
    else:
        d = (
            f"M{r} 0 L{w - r} 0 Q{w} 0 {w} {r} L{w} {h - r} Q{w} {h} {w - r} {h} L{r} {h} Q0 {h} 0 {h - r} "
            f"L0 {r} Q0 0 {r} 0 Z"
        )
    body.append(
        draw.el("path", d=d, fill=look.outline, opacity=0.16, transform=f"translate({e * 0.4} {e + 1.6})")
    )
    body.append(draw.el("path", d=d, fill=look.panel_edge, transform=f"translate(0 {e})"))
    body.append(draw.el("path", d=d, fill=look.panel))
    if shape == "notebook":  # spiral rings along the top edge
        n = 13
        for j in range(n):
            x = w * 0.08 + (w * 0.84) * j / (n - 1)
            body.append(draw.el("ellipse", cx=x, cy=4.2, rx=1.5, ry=1.5, fill="#E7DCC8"))
            body.append(
                draw.el(
                    "path",
                    d=f"M{x - 1.1} 4.4 C{x - 1.3} -1.8 {x + 1.3} -1.8 {x + 1.1} 4.4",
                    fill="none",
                    stroke="#8A8FA8",
                    stroke_width=0.9,
                    stroke_linecap="round",
                )
            )
    elif shape == "trail":  # a dashed path inside the edge and a little flag
        inset = 3.2
        body.append(
            draw.el(
                "rect",
                x=inset,
                y=inset,
                width=w - 2 * inset,
                height=h - 2 * inset,
                rx=r - 2,
                fill="none",
                stroke=look.panel_edge,
                stroke_width=0.7,
                stroke_dasharray="2.4 2",
                opacity=0.55,
            )
        )
    elif shape == "arch":  # a gold double line inside the arch
        body.append(
            draw.el(
                "path",
                d=d,
                fill="none",
                stroke=look.panel_edge,
                stroke_width=0.8,
                transform=f"translate({w * 0.02} {h * 0.03}) scale(0.96 0.94)",
                opacity=0.9,
            )
        )
    elif shape == "house":
        body.append(draw.el("path", d=draw.star_points(w / 2, 8.2, 2.4, 1.0), fill=look.panel_edge))
    return Markup(  # nosec B704 (numbers and colors only)
        f'<svg class="cvp-svg" viewBox="-1 -2 {w + 7:.2f} {h + 10:.2f}" width="{w + 7:.2f}mm" '
        f'height="{h + 10:.2f}mm" aria-hidden="true">{"".join(body)}</svg>'
    )


def ribbon_svg(look: Look, w: float, h: float, uid: str) -> Markup:
    """A ribbon banner (mm): a band with folded tails behind both ends."""
    tail, fold = 11.0, 3.2
    grad = f"{uid}-rb"
    body = [
        f'<defs><linearGradient id="{grad}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" '
        f'stop-color="{look.ribbon[0]}"/><stop offset="1" stop-color="{look.ribbon[1]}"/>'
        "</linearGradient></defs>",
        # tails: behind the band, lower, with a V cut
        draw.el(
            "path",
            d=f"M{tail + 2} {fold} L0 {fold} L{tail * 0.45} {fold + (h - fold) / 2} L0 {h + fold} "
            f"L{tail + 2} {h + fold} Z",
            fill=look.ribbon[1],
        ),
        draw.el(
            "path",
            d=f"M{w - tail - 2} {fold} L{w} {fold} L{w - tail * 0.45} {fold + (h - fold) / 2} "
            f"L{w} {h + fold} L{w - tail - 2} {h + fold} Z",
            fill=look.ribbon[1],
        ),
        draw.el("path", d=f"M{tail} {h} L{tail + 3.2} {h + fold} L{tail + 3.2} {h} Z", fill=look.ribbon_fold),
        draw.el(
            "path",
            d=f"M{w - tail} {h} L{w - tail - 3.2} {h + fold} L{w - tail - 3.2} {h} Z",
            fill=look.ribbon_fold,
        ),
        draw.el("rect", x=tail, y=0, width=w - 2 * tail, height=h, rx=1.4, fill=f"url(#{grad})"),
        draw.el(
            "rect",
            x=tail + 1.6,
            y=1.4,
            width=w - 2 * tail - 3.2,
            height=h - 2.8,
            rx=1,
            fill="none",
            stroke="#FFFFFF",
            stroke_width=0.45,
            stroke_dasharray="1.6 1.2",
            opacity=0.55,
        ),
    ]
    return Markup(  # nosec B704 (numbers and colors only)
        f'<svg class="cvr-svg" viewBox="0 0 {w:.2f} {h + fold:.2f}" width="{w:.2f}mm" '
        f'height="{h + fold:.2f}mm" aria-hidden="true">{"".join(body)}</svg>'
    )


def _mix(a: str, b: str, t: float) -> str:
    """The color `t` of the way from `a` to `b`."""
    ca = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#{:02X}{:02X}{:02X}".format(*(round(x + (y - x) * t) for x, y in zip(ca, cb, strict=True)))


def _shade(color: str, k: float) -> str:
    """`color` mixed with black (k < 0) or white (k > 0)."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    t = 255 if k > 0 else 0
    a = abs(k)
    return "#{:02X}{:02X}{:02X}".format(*(round(c + (t - c) * a) for c in (r, g, b)))


SHAPES = {"circle", "triangle", "square", "star", "heart"}


def block_svg(face: str, color: str, size: float, look: Look, *, tilt: float = 0.0) -> Markup:
    """A toy block (mm): a rounded cube seen a little from above and the right, with a letter, a number or a
    shape on its front. The glyph is vector text in the title font; a shape is drawn."""
    s, d = size, size * 0.28
    top, side = _shade(color, 0.32), _shade(color, -0.22)
    gid = "cvb-" + hashlib.sha256(f"{face}{color}{size}".encode()).hexdigest()[:8]
    w, h = s + d, s + d
    parts = [
        # soft contact shadow
        draw.el("ellipse", cx=s * 0.55, cy=h - 0.6, rx=s * 0.62, ry=1.6, fill="#000000", opacity=0.18),
        draw.el(
            "path", d=f"M0 {d} L{d} 0 L{s + d} 0 L{s} {d} Z", fill=top, stroke=look.outline, stroke_width=0.0
        ),
        draw.el("path", d=f"M{s} {d} L{s + d} 0 L{s + d} {s} L{s} {s + d} Z", fill=side),
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" '
        f'stop-color="{_shade(color, 0.2)}"/><stop offset="1" stop-color="{_shade(color, -0.12)}"/>'
        "</linearGradient></defs>",
        draw.el("rect", x=0, y=d, width=s, height=s, rx=s * 0.12, fill=color),
        draw.el(
            "rect",
            x=s * 0.08,
            y=d + s * 0.08,
            width=s * 0.84,
            height=s * 0.84,
            rx=s * 0.1,
            fill=f"url(#{gid})",
        ),
        draw.el(
            "path",
            d=f"M{s * 0.14} {d + s * 0.2} Q{s * 0.16} {d + s * 0.12} {s * 0.3} {d + s * 0.11}",
            fill="none",
            stroke="#FFFFFF",
            stroke_width=s * 0.035,
            stroke_linecap="round",
            opacity=0.75,
        ),
    ]
    cx, cy = s / 2, d + s / 2
    if face in SHAPES:
        r = s * 0.27
        ink = "#FFFFFF"
        if face == "circle":
            parts.append(draw.el("circle", cx=cx, cy=cy, r=r, fill=ink))
        elif face == "square":
            parts.append(
                draw.el(
                    "rect",
                    x=cx - r * 0.9,
                    y=cy - r * 0.9,
                    width=r * 1.8,
                    height=r * 1.8,
                    rx=r * 0.2,
                    fill=ink,
                )
            )
        elif face == "triangle":
            parts.append(
                draw.el(
                    "path",
                    d=f"M{cx} {cy - r} L{cx + r * 1.05} {cy + r * 0.8} L{cx - r * 1.05} {cy + r * 0.8} Z",
                    fill=ink,
                    stroke=ink,
                    stroke_width=r * 0.25,
                    stroke_linejoin="round",
                )
            )
        else:
            parts.append(draw.el("path", d=draw.star_points(cx, cy, r * 1.15, r * 0.5), fill=ink))
    else:
        fs = s * (0.72 if len(face) == 1 else 0.56 if len(face) == 2 else 0.44)
        y = cy + fs * (0.34 if _is_arabic(face) else 0.36)
        ring = "".join(
            f'<text x="{cx + dx:.2f}" y="{y + dy:.2f}" font-size="{fs:.2f}">{escape(face)}</text>'
            for dx, dy in _ring(s * 0.035, 12)
        )
        parts.append(
            f'<g font-family="{look.font}" font-weight="800" text-anchor="middle" direction="rtl" '
            f'fill="{_shade(color, -0.45)}">{ring}</g>'
        )
        parts.append(
            f'<text x="{cx:.2f}" y="{y:.2f}" font-size="{fs:.2f}" font-family="{look.font}" '
            'font-weight="800" '
            f'text-anchor="middle" direction="rtl" fill="#FFFFFF">{escape(face)}</text>'
        )
    turn = f' style="transform: rotate({tilt:g}deg)"' if tilt else ""
    return Markup(  # nosec B704 (the glyph is escaped)
        f'<svg class="cvb" viewBox="0 0 {w:.2f} {h:.2f}" width="{w:.2f}mm" height="{h:.2f}mm"{turn} '
        f'aria-hidden="true">{"".join(parts)}</svg>'
    )


def _is_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in text)


def blocks_layout(
    faces: Sequence[str], look: Look, box: Box, feet: float, hero_w: float, size: float, numerals: Numerals
) -> list[dict[str, Any]]:
    """Two little piles of blocks (the first half of `faces` on the right of the child, the rest on the left),
    each a pyramid: two blocks on the floor and one on top. Positions in mm within the box."""
    if not faces:
        return []
    shown = [f if f in SHAPES or _is_arabic(f) else format_number(f, numerals) for f in faces]
    half = (len(shown) + 1) // 2
    piles = [shown[:half], shown[half:]]
    out = []
    d = size * 0.28
    gap = 1.2
    for side, pile in enumerate(piles):
        if not pile:
            continue
        # floor row: the pile's first two blocks; then one on top
        # right of the child (the RTL start) from its right edge outwards, else left of it
        x0 = box.cx + hero_w / 2 + 2 if side == 0 else box.cx - hero_w / 2 - 2 - (2 * size + gap + d)
        spots = [(x0, feet - size - d), (x0 + size + gap, feet - size - d)]
        spots.append((x0 + (size + gap) / 2, feet - 2 * size - d + 1.2))
        # a pile reads right to left: its first block is the rightmost one on the floor, its last on top
        order = [1, 0, 2]
        for k, face in enumerate(pile[:3]):
            x, y = spots[order[k]]
            tilt = (-5, 4, -2)[k] if side == 0 else (4, -4, 3)[k]
            color = look.blocks[(side * 3 + k) % len(look.blocks)]
            out.append({"svg": block_svg(face, color, size, look, tilt=tilt), "x": x, "y": y})
    return out


def badge(icon: str, text: str, color: str) -> dict[str, Any]:
    return {"icon": art.icon(icon, "ico"), "text": text, "color": color}


# ---- page thumbnails for the back --------------------------------------------------------------------------


def pick_pages(
    book: BookSpec, prefer: Sequence[Sequence[str]], allow: Any = None, count: int = 3
) -> list[int]:
    """Indexes (in `book.pages`) of `count` pages for the back: for each slot of `prefer`, the first page of
    the first type it lists that the book has; then pages spread evenly through the book. Never a page
    `allow` refuses."""
    pages = list(book.pages)
    ok = [i for i, p in enumerate(pages) if allow is None or allow(p)]
    chosen: list[int] = []
    for kinds in prefer:
        for kind in kinds:
            found = next((i for i in ok if pages[i].type == kind and i not in chosen), None)
            if found is not None:
                chosen.append(found)
                break
        if len(chosen) == count:
            return chosen
    rest = [i for i in ok if i not in chosen and i > 4]  # past the front pages
    step = max(1, len(rest) // (count + 1))
    for i in rest[step::step]:
        if len(chosen) == count:
            break
        chosen.append(i)
    return chosen[:count]


def render_thumbs(
    pdf: Path, indexes: Sequence[int], out_dir: Path, g: Geometry, width_mm: float
) -> list[Path]:
    """Pages of a rendered interior as JPEGs cut to the trim, at 300 DPI for `width_mm` (cached by the PDF's
    content and the page)."""
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()[:12]
    out_dir.mkdir(parents=True, exist_ok=True)
    target_w = round(width_mm / 25.4 * DPI)
    target_h = round(target_w * g.trim_h / g.trim_w)
    paths = []
    doc = pdfium.PdfDocument(pdf)
    try:
        for i in indexes:
            out = out_dir / f"page-{digest}-{i}-{width_mm:g}.jpg"
            if not out.exists():
                scale = 2 * target_w / (g.trim_w / 25.4 * 72)  # twice the size, then down: smooth small text
                image = doc[i].render(scale=scale).to_pil().convert("RGB")
                b = round(g.bleed / 25.4 * 72 * scale)
                image = image.crop((b, b, image.width - b, image.height - b))
                image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
                image.save(out, format="JPEG", quality=90, dpi=(DPI, DPI))
            paths.append(out)
    finally:
        doc.close()
    return paths


THUMB_MM = 44.0  # a page's width on the back (_cover.css.j2 .cvk-thumbs img)
# The pages lean a few degrees, and the preflight measures an image by its upright bounding box, which a tilt
# enlarges by up to 15%: render them a quarter larger than they print, so they stay ≥ 300 DPI by that measure.
THUMB_OVERSIZE = 1.25


def with_thumbs(
    cover: BookSpec,
    interior: BookSpec,
    pdf: Path,
    out_dir: Path,
    prefer: Sequence[Sequence[str]],
    allow: Any = None,
) -> BookSpec:
    """The cover with three real pages of `interior` (rendered at `pdf`) on its back."""
    import dataclasses

    if len(interior.pages) < 3 or not pdf.is_file():
        return cover
    width = THUMB_MM * THUMB_OVERSIZE
    indexes = pick_pages(interior, prefer, allow)
    thumbs = [str(p) for p in render_thumbs(pdf, indexes, out_dir, interior.geometry, width)]
    pages = tuple(
        dataclasses.replace(p, params={**p.params, "thumbs": thumbs})
        if p.type.endswith("cover-back") or p.type.endswith("cover-wrap") or p.type == "cover-back"
        else p
        for p in cover.pages
    )
    return dataclasses.replace(cover, pages=pages)


# ---- the spine (perfect-bound) -----------------------------------------------------------------------------


def spine_mm(pages: int) -> float:
    """The spine of a perfect-bound book with `pages` interior pages: paper × leaves + the cover's share."""
    leaves = math.ceil(max(0, pages) / 2)
    return round(leaves * SOFTCOVER_LEAF_MM + SOFTCOVER_COVER_MM, 1)


def wrap_geometry(g: Geometry, spine: float) -> Geometry:
    """A wrap's page: front and back side by side with the spine between them, the bleed around it all."""
    return Geometry(trim_w=2 * g.trim_w + spine, trim_h=g.trim_h, bleed=g.bleed, safe=g.safe, dpi=g.dpi)


def wrap_boxes(g: Geometry, spine: float) -> tuple[Box, tuple[float, float], Box]:
    """(front, spine (x, width), back) on a right-bound wrap: [front | spine | back] from left to right."""
    front_w = g.bleed + g.trim_w
    front = Box(0.0, front_w, g.page_h, g.inset, SPINE_HINGE_MM, g.inset, g.inset)
    back = Box(front_w + spine, front_w, g.page_h, SPINE_HINGE_MM, g.inset, g.inset, g.inset)
    return front, (front_w, spine), back


# ---- the child on the cover --------------------------------------------------------------------------------

HERO_FRONT = 0.5  # the child's height on the front, as a share of the page height (at most)
BAND = {"islamic": 0.2, "family": 0.22}  # the back's scene band (share of the height; default 0.27)
HERO_BACK = 0.24


def hero(ctx: PageContext, height_mm: float, *, waving: bool = False) -> tuple[str, float]:
    """The child's cut-out at 300 DPI for `height_mm` (and its width / height), or ("", 0.47)."""
    sheet = ctx.book.child.character_sheet
    base = ctx.assets.wave if waving and ctx.assets.wave else ctx.assets.character
    if sheet is None or base is None:
        return uri(base), ctx.assets.character_aspect
    index = 1 if waving and ctx.assets.wave else 0
    try:
        path = pose(sheet, base.parent, index, max_print_mm=math.ceil(height_mm) + 2)
    except ValueError:
        path = base
    with Image.open(path) as img:
        return uri(path), img.width / img.height


# ---- the cover's data (shared by the four series' page builders) -------------------------------------------


@dataclass(frozen=True)
class Front:
    """What a series puts on its front."""

    series: Series
    part: str
    title: str  # the big lettering (may hold the child's name)
    ribbon: str  # on the ribbon (personalized)
    subtitle: str = ""  # under the title, inside the panel
    pills: tuple[tuple[str, str], ...] = ()  # (text, "main" or "alt")
    age: str = ""
    badges: tuple[tuple[str, str], ...] = ()  # (icon, text), personalized
    blocks: tuple[str, ...] = ()
    # the family book: draws the child among the family in a w × h mm box → (the SVG, its name tags)
    group: Callable[[float, float], tuple[Markup, list[dict[str, Any]]]] | None = None
    one_line_max: int = 14


def front_data(ctx: PageContext, f: Front, box: Box | None = None) -> dict[str, Any]:
    """The front's layout (mm, within `box`, default the whole page) and its pieces."""
    g = ctx.book.geometry
    box = box or Box.page(g)
    look = LOOKS[f.series]
    h = box.h
    scale = h / 303.0
    uid = f"cv-{ctx.page.id}"
    # the scene
    src = scene_source(f.part)
    out_dir = ctx.assets.character.parent if ctx.assets.character else REPO / "out" / "covers" / "assets"
    scene = uri(plate(src, out_dir, box.w, box.h)) if src else ""
    # the brand row, then the title panel
    brand_top = box.top
    panel_top = brand_top + 13
    name = printed_name(f.title, ctx.book.child.name)  # «مُغامَراتُ أبي بكر»: kept whole, in its colors
    lines = title_lines(f.title, name, f.one_line_max)
    marked = bool(_MARKS.search(f.title))  # tashkeel needs room above and below each line
    title_h = (36.0 if len(lines) == 1 else 54.0) * scale + (5.0 if marked else 0.0)
    if marked and len(lines) > 1:
        title_h += 12.0
    panel_w = min(box.inner_w + 4, 192.0)
    shape_top = {"notebook": 7.0, "trail": 4.0, "house": 15.0, "arch": 12.0}[look.panel_shape]
    pills_top = shape_top
    pad_top = shape_top + (11.0 if f.pills else 0.0) + 1.0
    sub_h = 0.0
    if f.subtitle:
        sub_h = 13.0 if letters(f.subtitle) > 44 else 8.0
    panel_h = pad_top + title_h + sub_h + 11.0
    panel_x = box.cx - panel_w / 2
    ribbon_w = min(150.0, box.inner_w - 16)
    ribbon_h = 15.0 * min(1.0, scale + 0.05)
    ribbon_top = panel_top + panel_h - 8.0
    # the child and the toy blocks, standing on the scene's floor; the badges below them
    badges_top = h - box.bottom - 11.0  # the pills are 9.5 mm; vowel marks hang below their line
    feet = badges_top - (13.0 if f.group is not None else 4.0)  # the family's name tags stand under them
    hero_top = ribbon_top + ribbon_h + 5.0
    hero_h = min(HERO_FRONT * h, feet - hero_top)
    group: Markup | None = None
    tags: list[dict[str, Any]] = []
    group_box: dict[str, float] = {}
    if f.group is not None:
        hero_h = 0.0
        gw, gh = box.inner_w + 10, feet + 11 - hero_top
        group, tags = f.group(gw, gh)
        group_box = {"x": box.cx - gw / 2, "y": hero_top, "w": gw, "h": gh}
    child, aspect = hero(ctx, hero_h) if hero_h else ("", 0.47)
    hero_w = hero_h * aspect
    block = round(23.0 * scale, 1)
    blocks = blocks_layout(f.blocks, look, box, feet, hero_w, block, ctx.book.numerals)
    title = title_svg(lines, look, width=panel_w - 14, height=title_h, uid=uid, name=name)
    return {
        "series": f.series,
        "box": box,
        "scene": scene,
        "uid": uid,
        "brand_top": brand_top,
        "panel": {
            "x": panel_x,
            "y": panel_top,
            "w": panel_w,
            "h": panel_h,
            "svg": panel_svg(look, panel_w, panel_h, uid),
            "pad_top": pad_top,
            "pills_top": pills_top,
        },
        "pills": [{"text": t, "kind": k} for t, k in f.pills],
        "title": title,
        "title_h": title_h,
        "subtitle": f.subtitle,
        "sub_h": sub_h,
        "ribbon": {
            "text": f.ribbon,
            "x": box.cx - ribbon_w / 2,
            "y": ribbon_top,
            "w": ribbon_w,
            "h": ribbon_h,
            "svg": ribbon_svg(look, ribbon_w, ribbon_h, uid),
            "long": len(f.ribbon) > 18,
        },
        "age": f.age,
        "hero": {"src": child, "h": hero_h, "w": hero_w, "x": box.cx - hero_w / 2, "y": feet - hero_h},
        "feet": feet,
        "blocks": blocks,
        "group": group,
        "tags": tags,
        "group_box": group_box,
        "badges": [
            badge(icon, text, look.blocks[i % len(look.blocks)]) for i, (icon, text) in enumerate(f.badges)
        ],
        "badges_top": badges_top,
        "look": look,
    }


@dataclass(frozen=True)
class Back:
    """What a series puts on its back."""

    series: Series
    part: str
    title: str
    pills: tuple[tuple[str, str], ...] = ()
    blurb: tuple[str, ...] = ()
    inside: tuple[tuple[str, str, str], ...] = ()  # (icon or Markup glyph, text, color)
    inside_title: str = "في هذا الجزء"
    comes: tuple[tuple[str, str], ...] = ()  # (icon, text)
    comes_title: str = "يأتي مع الكتاب"
    facts: tuple[str, ...] = ()  # ages, pages, binding
    made_for: str = ""
    domain: str = "qamra.app"
    extra: dict[str, Any] | None = None  # a series' own lines (the Islamic books list and care note)
    cols: int = 0  # columns of «في هذا الجزء» (0: two for a long list or without pages beside it)
    org: dict[str, Any] | None = None  # an organization's logo slot (the family book)


def back_data(ctx: PageContext, b: Back, box: Box | None = None) -> dict[str, Any]:
    g = ctx.book.geometry
    box = box or Box.page(g)
    look = LOOKS[b.series]
    h = box.h
    uid = f"cvb-{ctx.page.id}"
    band_h = round(BAND.get(b.series, 0.27) * h, 1)
    src = scene_source(b.part)
    out_dir = ctx.assets.character.parent if ctx.assets.character else REPO / "out" / "covers" / "assets"
    band = uri(plate(src, out_dir, box.w, band_h, band=0.66)) if src else ""
    hero_h = round(HERO_BACK * h, 1)
    child, aspect = hero(ctx, hero_h, waving=True)
    thumb_files = [Path(p) for p in ctx.page.params.get("thumbs", [])][:3]
    thumbs = [uri(p) for p in thumb_files]
    thumb_ratio = g.trim_h / g.trim_w
    if thumb_files:
        with Image.open(thumb_files[0]) as first:
            thumb_ratio = first.height / first.width
    name = printed_name(b.title, ctx.book.child.name)
    lines = title_lines(b.title, name, 28)  # small on the back: one line when it can
    title_w = box.inner_w - hero_h * aspect - 6
    title = title_svg(
        lines,
        look,
        width=min(title_w, 120.0),
        height=17.0 if len(lines) == 1 else 26.0,
        uid=uid,
        name=name,
    )  # small: the outline and the extrusion follow its size (COVER_FIT_JS)
    inside = []
    for i, (icon, text, color) in enumerate(b.inside):
        mark = icon if isinstance(icon, Markup) else art.icon(icon, "ico")
        inside.append({"icon": mark, "text": text, "color": color or look.blocks[i % len(look.blocks)]})
    return {
        "series": b.series,
        "box": box,
        "uid": uid,
        "band": band,
        "band_h": band_h,
        "hero": {"src": child, "h": hero_h, "w": hero_h * aspect},
        "title": title,
        "pills": [{"text": t, "kind": k} for t, k in b.pills],
        "blurb": list(b.blurb),
        "inside_title": b.inside_title,
        "inside": inside,
        "cols": b.cols or (2 if len(inside) > 6 or not thumbs else 1),
        "thumbs": thumbs,
        "thumbs_h": round(THUMB_MM * thumb_ratio + 12, 1),
        "comes_title": b.comes_title,
        "comes": [
            badge(icon, text, look.blocks[i % len(look.blocks)]) for i, (icon, text) in enumerate(b.comes)
        ],
        "facts": list(b.facts),
        "made_for": b.made_for,
        "domain": b.domain,
        "extra": b.extra or {},
        "org": b.org or {},
        "look": look,
    }


def spine_data(ctx: PageContext, look: Look, x: float, width: float, lines: Sequence[str]) -> dict[str, Any]:
    return {
        "x": x,
        "w": width,
        "color": look.spine,
        "text": width >= SPINE_TEXT_MIN_MM,
        "lines": list(lines),
        "font_pt": round(min(11.0, max(6.0, width * 0.62 / 0.3528 * 0.62)), 1),
    }


def pages_phrase(n: int, *, vowelized: bool = False) -> str:
    """«١٢٠ صفحة ملوّنة» (or vowelized «١٢٠ صَفْحَةً مُلَوَّنَةً»): noun and adjective agree with the number."""
    if not vowelized:
        return f"{counted(n, 'صفحة', 'صفحات')} ملوّنة"
    rest = n % 100
    if 3 <= rest <= 10:
        return f"{n} صَفَحَاتٍ مُلَوَّنَةٍ"
    if rest >= 11:
        return f"{n} صَفْحَةً مُلَوَّنَةً"
    return f"{n} صَفْحَةٍ مُلَوَّنَةٍ"


def fill(ctx: PageContext, text: str, **values: Any) -> str:
    """A cover line as printed: `{pages}`/`{units}`… filled in, personalized, in the book's numerals. «لـ»
    before a name that starts with «ال» joins it as «لل» («للمعتصم», never «لـالمعتصم»). A genitive slot,
    «لِـ{child:gen}», is joined when it is filled (`qamra_pdf.arabic_names`: «لِلمعتصم», «لِأبي بكر»); the rule
    here keeps unmarked text right."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return re.sub(r"لِ?ـال", "لل", ctx.text(text))


# What the backs show of each series' pages: a slot per page, its preferred types in order.
THUMBS: dict[str, tuple[tuple[str, ...], ...]] = {
    "foundation": (
        ("letter-intro",),
        ("count-and-circle", "picture-add", "number-intro", "teen-quantity-match"),
        ("spot-difference", "maze", "kg1-trace-path", "trace-path", "hidden-pictures"),
    ),
    "family": (
        ("passport",),
        ("recipe-steps", "shopping-list"),
        ("nature-bingo", "scavenger-hunt"),
    ),
    "islamic": (  # only pages that never carry sacred text (islamic_volume.no_sacred_text)
        ("muslim-passport",),
        ("islamic-coloring", "islamic-draw"),
        ("islamic-maze", "islamic-coloring", "islamic-cut-paste", "islamic-home-challenge"),
    ),
    "journey": (
        ("journey-map",),
        ("color-journey", "journey-letter-trace", "shape-journey"),
        ("maze", "spot-difference", "shortest-path", "journey-picture-sum"),
    ),
}
