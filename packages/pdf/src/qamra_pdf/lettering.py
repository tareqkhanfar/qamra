"""Cover title lettering in code (Addendum 11 §2.3): never drawn by the image model.

The title is an inline SVG: each line is one `<text>` on a gently arched `<textPath>`, drawn several times
with `<use>` (glow, drop shadow, thick dark outline, a light rim, then the gradient fill on top). The outline
is a ring of filled copies, not an SVG stroke: Chromium prints stroked text as Type 3 fonts, while filled
copies stay embedded TrueType. Only the soft glow is a blur filter (rasterized at 300 DPI, which is fine for
a glow); every letter stays vector.

Line breaks are decided here (2–3 lines max, never inside a word); the font size of each line is fitted in
the browser (`TITLE_FIT_JS`), so a long title shrinks instead of overflowing.
"""

import math
import re
from dataclasses import dataclass
from typing import Literal

from markupsafe import Markup, escape

TitleStyle = Literal["gold-magic", "candy-bright", "night-glow", "nature-fresh", "heritage-tatreez"]
TITLE_STYLES: tuple[TitleStyle, ...] = (
    "gold-magic",
    "candy-bright",
    "night-glow",
    "nature-fresh",
    "heritage-tatreez",
)
DEFAULT_TITLE_STYLE: TitleStyle = "gold-magic"

_MARKS = re.compile("[\\u0610-\\u061a\\u064b-\\u065f\\u0670\\u06d6-\\u06ed\\u0640]")


@dataclass(frozen=True)
class Treatment:
    """One reusable title treatment: lettering, ribbon, and the colors the rest of the book borrows."""

    slug: TitleStyle
    font: str  # CSS family of the title
    fill: tuple[tuple[float, str], ...]  # vertical gradient stops, top → bottom
    outline: str
    outline_mm: float
    rim: str  # thin light edge above the fill (gloss)
    glow: str
    glow_mm: float
    shadow: str
    shadow_mm: float  # drop distance
    bend: float  # arc height as a fraction of the line width (+ = arches up)
    tilt: float  # degrees, + = rises toward the start of an RTL line
    shade: str  # CSS gradient over the top of the art, behind the title
    ribbon: tuple[str, str]  # ribbon gradient
    ribbon_edge: str
    ribbon_label: str
    ribbon_name: str
    ribbon_name_outline: str
    accent: str  # the child's name in the story text, page badges, ornaments
    ink: str  # dark tone for the spine and the back cover tint
    soft: str  # light tint for paper pages (color blocks, washes)


TREATMENTS: dict[TitleStyle, Treatment] = {
    "gold-magic": Treatment(
        slug="gold-magic",
        font="Lalezar",
        fill=((0.0, "#FFFBEA"), (0.42, "#FFD75E"), (0.78, "#F2A61F"), (1.0, "#D9770F")),
        outline="#3A1D08",
        outline_mm=1.5,
        rim="#FFF8DC",
        glow="#FFE6A0",
        glow_mm=3.4,
        shadow="#1B0D03",
        shadow_mm=1.7,
        bend=0.075,
        tilt=-2.5,
        shade="linear-gradient(to bottom, rgba(14,21,48,.55), rgba(14,21,48,.22) 26%, rgba(14,21,48,0) 44%)",
        ribbon=("#24337A", "#16204A"),
        ribbon_edge="#F2B33D",
        ribbon_label="#FCEFD2",
        ribbon_name="#FFD75E",
        ribbon_name_outline="#0E1530",
        accent="#A8560A",
        ink="#16204A",
        soft="#FCEFD2",
    ),
    "candy-bright": Treatment(
        slug="candy-bright",
        font="Marhey",
        fill=((0.0, "#FFFFFF"), (0.4, "#FFD3EA"), (0.75, "#FF77B4"), (1.0, "#E8458F")),
        outline="#4E0F3E",
        outline_mm=1.5,
        rim="#FFFFFF",
        glow="#FFFFFF",
        glow_mm=3.0,
        shadow="#2C0723",
        shadow_mm=1.6,
        bend=0.06,
        tilt=-4.0,
        shade="linear-gradient(to bottom, rgba(78,15,62,.38), rgba(78,15,62,.14) 26%, rgba(78,15,62,0) 44%)",
        ribbon=("#19B3C6", "#0E8C9E"),
        ribbon_edge="#FFFFFF",
        ribbon_label="#FFFFFF",
        ribbon_name="#FFE45C",
        ribbon_name_outline="#0B4F5A",
        accent="#C2306F",
        ink="#4E0F3E",
        soft="#FFE3F0",
    ),
    "night-glow": Treatment(
        slug="night-glow",
        font="Lalezar",
        fill=((0.0, "#FFFFFF"), (0.45, "#DDF0FF"), (0.8, "#8CC4FF"), (1.0, "#5E9CF0")),
        outline="#0A1238",
        outline_mm=1.5,
        rim="#FFFFFF",
        glow="#9ED3FF",
        glow_mm=4.0,
        shadow="#040820",
        shadow_mm=1.5,
        bend=0.05,
        tilt=0.0,
        shade="linear-gradient(to bottom, rgba(6,10,36,.62), rgba(6,10,36,.26) 28%, rgba(6,10,36,0) 46%)",
        ribbon=("#F6C14E", "#E39A1E"),
        ribbon_edge="#FFF3CF",
        ribbon_label="#16204A",
        ribbon_name="#FFFFFF",
        ribbon_name_outline="#16204A",
        accent="#2B4BA8",
        ink="#0E1530",
        soft="#E3EEFF",
    ),
    "nature-fresh": Treatment(
        slug="nature-fresh",
        font="Marhey",
        fill=((0.0, "#FFFEE6"), (0.42, "#E4F58A"), (0.78, "#8ACB45"), (1.0, "#4F9A2C")),
        outline="#183A10",
        outline_mm=1.5,
        rim="#FFFFF0",
        glow="#FFF6C4",
        glow_mm=3.0,
        shadow="#0C1F07",
        shadow_mm=1.6,
        bend=0.07,
        tilt=2.5,
        shade="linear-gradient(to bottom, rgba(16,40,12,.42), rgba(16,40,12,.16) 26%, rgba(16,40,12,0) 44%)",
        ribbon=("#F58A3C", "#DD6420"),
        ribbon_edge="#FFF1D6",
        ribbon_label="#FFFFFF",
        ribbon_name="#FFF6B0",
        ribbon_name_outline="#6B2A07",
        accent="#3F7F1F",
        ink="#183A10",
        soft="#EAF5D3",
    ),
    "heritage-tatreez": Treatment(
        slug="heritage-tatreez",
        font="Aref Ruqaa",
        fill=((0.0, "#FFF4E2"), (0.4, "#FFD9B0"), (0.75, "#E8664F"), (1.0, "#B3262F")),
        outline="#2A0A0D",
        outline_mm=1.5,
        rim="#FFF6EA",
        glow="#FFE3C4",
        glow_mm=3.0,
        shadow="#160406",
        shadow_mm=1.6,
        bend=0.0,
        tilt=0.0,
        shade="linear-gradient(to bottom, rgba(42,10,13,.5), rgba(42,10,13,.2) 26%, rgba(42,10,13,0) 44%)",
        ribbon=("#2F2A26", "#1D1916"),
        ribbon_edge="#C8343C",
        ribbon_label="#F6E7D0",
        ribbon_name="#F2B33D",
        ribbon_name_outline="#1D1916",
        accent="#A8232D",
        ink="#2A0A0D",
        soft="#F8E6DA",
    ),
}


def treatment(style: str | None) -> Treatment:
    for slug, t in TREATMENTS.items():
        if slug == style:
            return t
    return TREATMENTS[DEFAULT_TITLE_STYLE]


def _length(text: str) -> int:
    return len(_MARKS.sub("", text))


def split_lines(title: str, max_lines: int = 3, keep: str | None = None) -> list[str]:
    """Balanced lines, never breaking a word: 1 line up to 13 letters, 2 up to 28, else 3. The words of
    `keep` (the child's name, e.g. «عبد الرحمن») stay on one line, and a line that is exactly the name is
    preferred (it reads as a big name line)."""
    words = title.split()
    name = keep.split() if keep else []
    units: list[str] = []
    i = 0
    while i < len(words):
        if len(name) > 1 and [_MARKS.sub("", w) for w in words[i : i + len(name)]] == [
            _MARKS.sub("", w) for w in name
        ]:
            units.append(" ".join(words[i : i + len(name)]))
            i += len(name)
        else:
            units.append(words[i])
            i += 1
    n = _length(title)
    lines_wanted = 1 if n <= 13 else 2 if n <= 28 else max_lines
    lines_wanted = max(1, min(lines_wanted, len(units), max_lines))
    if lines_wanted == 1:
        return [" ".join(units)]
    plain_name = _MARKS.sub("", keep or "").strip()

    def cuts(start: int, left: int) -> list[list[int]]:
        if left == 1:
            return [[len(units)]]
        out: list[list[int]] = []
        for end in range(start + 1, len(units) - left + 2):
            out += [[end, *rest] for rest in cuts(end, left - 1)]
        return out

    best: list[str] = [" ".join(units)]
    best_cost = math.inf
    for ends in cuts(0, lines_wanted):  # titles are short: every cut is cheap to score
        lines, start = [], 0
        for end in ends:
            lines.append(" ".join(units[start:end]))
            start = end
        lengths = [_length(line) for line in lines]
        # the longest line decides the font size; prefer a slightly longer last line (reads as a base)
        cost = max(lengths) * 10 + (lengths[0] - lengths[-1] if lengths[0] > lengths[-1] else 0)
        if plain_name and any(_MARKS.sub("", line).strip() == plain_name for line in lines):
            cost -= 25
        if cost < best_cost:
            best, best_cost = lines, cost
    return best


def _ring(radius: float, n: int) -> list[tuple[float, float]]:
    return [
        (round(radius * math.cos(2 * math.pi * i / n), 3), round(radius * math.sin(2 * math.pi * i / n), 3))
        for i in range(n)
    ]


def title_svg(
    title: str,
    style: str | None,
    *,
    width_mm: float,
    height_mm: float,
    uid: str = "t",
    rtl: bool = True,
    keep: str | None = None,
) -> Markup:
    """The layered title as inline SVG (mm units). Sizes and line positions are set by `TITLE_FIT_JS`."""
    t = treatment(style)
    lines = split_lines(title, keep=keep)
    w, h = width_mm, height_mm
    stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in t.fill)
    defs = [
        f'<linearGradient id="{uid}-fill" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>',
        f'<filter id="{uid}-blur" x="-10%" y="-40%" width="120%" height="180%">'
        f'<feGaussianBlur stdDeviation="{t.glow_mm * 0.55:.2f}"/></filter>',
    ]
    direction = "rtl" if rtl else "ltr"
    for i, line in enumerate(lines):
        defs.append(f'<path id="{uid}-arc{i}" d="M 0 {h / 2} L {w} {h / 2}"/>')
        defs.append(
            f'<text id="{uid}-l{i}" class="tl" direction="{direction}" text-anchor="middle" '
            f'font-family="{t.font}" font-size="10"><textPath href="#{uid}-arc{i}" startOffset="50%">'
            f"{escape(line)}</textPath></text>"
        )
    ids = [f"{uid}-l{i}" for i in range(len(lines))]

    def copies(offsets: list[tuple[float, float]]) -> str:
        return "".join(f'<use href="#{i}" x="{dx}" y="{dy}"/>' for i in ids for dx, dy in offsets)

    outline = copies(_ring(t.outline_mm, 24) + _ring(t.outline_mm * 0.55, 12))
    glow = copies(_ring(t.glow_mm, 24))
    layers = [
        f'<g fill="{t.glow}" filter="url(#{uid}-blur)" opacity=".9">{glow}</g>',
        f'<g fill="{t.glow}" opacity=".28">{glow}</g>',
        f'<g fill="{t.shadow}" opacity=".6" transform="translate(0 {t.shadow_mm})">{outline}</g>',
        f'<g fill="{t.outline}">{outline}</g>',
        f'<g fill="{t.rim}">{copies([(0, -0.45)])}</g>',
        f'<g fill="url(#{uid}-fill)">{copies([(0, 0)])}</g>',
    ]
    return Markup(  # nosec B704 (the only text is escaped above)
        f'<svg class="title-art" viewBox="0 0 {w} {h}" data-bend="{t.bend}" data-tilt="{t.tilt}" '
        f'data-rtl="{1 if rtl else 0}" '
        f'data-pad="{t.glow_mm + t.outline_mm + 3:.2f}" aria-label="{escape(title)}" role="img">'
        f"<defs>{''.join(defs)}</defs>{''.join(layers)}</svg>"
    )


# Fits every `.title-art` SVG: each line as large as its width allows (lines stay within 1.3× of each
# other), the stack scaled down to the box height, then each line's arc (and tilt) set on its text path.
# The tilt lives in the path, not in a rotated group: a rotated blur layer would print at a lower DPI.
TITLE_FIT_JS = """
() => {
  const out = [];
  for (const svg of document.querySelectorAll('svg.title-art')) {
    const vb = svg.viewBox.baseVal, W = vb.width, H = vb.height;
    const pad = parseFloat(svg.dataset.pad || '4'), bend = parseFloat(svg.dataset.bend || '0');
    const tilt = parseFloat(svg.dataset.tilt || '0') * Math.PI / 180;
    const rtl = svg.dataset.rtl !== '0';
    const texts = [...svg.querySelectorAll('text.tl')];
    const avail = (W - 2 * pad) / Math.cos(tilt);
    const sizes = texts.map(t => {
      t.setAttribute('font-size', 10);
      const len = t.getComputedTextLength() || 1;
      return 10 * avail / len;
    });
    const multi = texts.length > 1;
    const cap = H * (multi ? 0.5 : 0.62);
    let s = sizes.map(v => Math.min(v, cap));
    const smallest = Math.min(...s);
    s = s.map(v => Math.min(v, smallest * 1.3));
    const lineH = v => v * (multi ? 1.04 : 1.15);
    const bendK = multi ? 0.45 : 1;  // stacked lines arch less, so they do not collide
    // vertical budget: the glow may spill outside the box (overflow visible), the arcs and tilt may not
    const vpad = 1.5;
    const slope = Math.abs(Math.tan(tilt)) * (W / 2 - pad);
    const rises = s.map(v => bend * bendK * 2 * Math.min(W / 2 - pad / 2, avail / 2));
    let total = s.reduce((a, v) => a + lineH(v), 0) + 2 * vpad + slope + Math.max(...rises) * 0.5;
    if (total > H) {
      const fixed = 2 * vpad + slope + Math.max(...rises) * 0.5;
      const k = (H - fixed) / (total - fixed); s = s.map(v => v * k);
    }
    total = s.reduce((a, v) => a + lineH(v), 0);
    let y = (H - total) / 2;
    texts.forEach((t, i) => {
      t.setAttribute('font-size', s[i].toFixed(2));
      const base = y + s[i] * 0.98;
      const half = W / 2 - pad / 2;
      const x0 = W / 2 - half, x1 = W / 2 + half;
      const rise = bend * bendK * 2 * Math.min(half, t.getComputedTextLength() / 2 + s[i]);
      const lift = Math.tan(tilt) * half * (rtl ? 1 : -1);  // + raises the right end
      const y0 = base + rise * 0.5 + lift, y1 = base + rise * 0.5 - lift;
      const arc = svg.querySelector('#' + t.querySelector('textPath').getAttribute('href').slice(1));
      const f = v => v.toFixed(2);
      arc.setAttribute('d', `M ${f(x0)} ${f(y0)} Q ${f(W / 2)} ${f(base - rise * 1.5)} ${f(x1)} ${f(y1)}`);
      y += lineH(s[i]);
    });
    out.push({sizes: s.map(v => Math.round(v / 0.3528 * 10) / 10), lines: texts.length});
  }
  return out;
}
"""
