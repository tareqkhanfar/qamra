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
    # Two-tone title: the child's name in its own gradient (the rest of the title in `fill`); () = one tone.
    name_fill: tuple[tuple[float, str], ...] = ()
    side: str = ""  # the 3D side of the letters under the face (extrusion); "" = flat lettering
    depth_mm: float = 1.3  # how deep the extrusion goes
    line_gap: float = 1.1  # stacked lines, × the font size (Ruqaa's deep descenders need more)


TREATMENTS: dict[TitleStyle, Treatment] = {
    "gold-magic": Treatment(
        slug="gold-magic",
        font="Lalezar",
        fill=((0.0, "#FFFFFF"), (0.5, "#FFF4DA"), (1.0, "#FFD993")),
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
        name_fill=((0.0, "#FFF7CC"), (0.4, "#FFD54F"), (0.78, "#F6A623"), (1.0, "#DC7A0E")),
        side="#8C4A12",
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
        name_fill=((0.0, "#FFFFFF"), (0.35, "#FFF4B3"), (0.75, "#FFD43F"), (1.0, "#F5A517")),
        side="#9E2560",
    ),
    "night-glow": Treatment(
        slug="night-glow",
        font="Lalezar",
        fill=((0.0, "#FFFFFF"), (0.5, "#E8F4FF"), (1.0, "#AFD5FF")),
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
        name_fill=((0.0, "#FFF8DA"), (0.45, "#FFD866"), (0.8, "#F4AE2E"), (1.0, "#E08C14")),
        side="#24398A",
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
        name_fill=((0.0, "#FFFBEA"), (0.4, "#FFD36A"), (0.78, "#FFA03A"), (1.0, "#EE7420")),
        side="#2E6A1B",
    ),
    "heritage-tatreez": Treatment(
        slug="heritage-tatreez",
        font="Aref Ruqaa",
        fill=((0.0, "#FFF9F0"), (0.55, "#FFE9D0"), (1.0, "#F7CCA4")),
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
        name_fill=((0.0, "#FFE9D6"), (0.4, "#FF9A7A"), (0.75, "#E0483C"), (1.0, "#B3262F")),
        side="#6E1A20",
        line_gap=1.34,
    ),
}


def treatment(style: str | None) -> Treatment:
    for slug, t in TREATMENTS.items():
        if slug == style:
            return t
    return TREATMENTS[DEFAULT_TITLE_STYLE]


def _length(text: str) -> int:
    return len(_MARKS.sub("", text))


# Display lettering keeps the shadda («تخرّج», «أوّل») and drops the short vowels, the sukun, the tanween and
# the dagger alif (modern print writes «هذا», «الرحمن»): at poster size the full tashkeel crowds the letters
# and collides between lines. The article's own shadda («الّذي») and a sun letter's after «ال» or «لل»
# («بالرّوضة», «للشّمس», «اللّه») go too. The story text inside the book keeps every mark.
_SHORT_VOWELS = re.compile("[\\u064b-\\u0650\\u0652\\u0670]")
_WORD_START = "(?<![\\u0621-\\u064a])"
_ARTICLE_SHADDA = re.compile(_WORD_START + "([وفبك]?ال)\\u0651")
_SUN_SHADDA = re.compile(_WORD_START + "([وفبك]?ال|[وف]?لل)([\\u0621-\\u064a])\\u0651")


def display_text(text: str) -> str:
    plain = _SHORT_VOWELS.sub("", text)
    plain = _SUN_SHADDA.sub(r"\1\2", _ARTICLE_SHADDA.sub(r"\1", plain))
    return " ".join(plain.split())


def _plain(word: str) -> str:
    return _MARKS.sub("", word).strip("،,:!?.«»\"'")


def name_units(title: str, keep: str | None) -> tuple[list[str], int | None]:
    """The title's words with the name's words kept as one unit, and the index of that unit (None when the
    name is not in the title). «Layla's» counts as the name in English titles."""
    words = title.split()
    name = [_plain(w) for w in (keep or "").split()]
    units: list[str] = []
    found: int | None = None
    i = 0
    while i < len(words):
        chunk = [_plain(w) for w in words[i : i + len(name)]]
        last = chunk[-1] if chunk else ""
        possessive = last.endswith(("'s", "’s")) and last[:-2] == (name[-1] if name else None)
        if name and found is None and (chunk == name or (chunk[:-1] == name[:-1] and possessive)):
            units.append(" ".join(words[i : i + len(name)]))
            found = len(units) - 1
            i += len(name)
        else:
            units.append(words[i])
            i += 1
    return units, found


def _balanced(units: list[str], lines_wanted: int, plain_name: str = "") -> list[str]:
    """`units` cut into `lines_wanted` lines whose longest line is as short as possible."""
    lines_wanted = max(1, min(lines_wanted, len(units)))
    if lines_wanted == 1:
        return [" ".join(units)]

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


def split_lines(title: str, max_lines: int = 3, keep: str | None = None) -> list[str]:
    """Balanced lines, never breaking a word: 1 line up to 13 letters, 2 up to 28, else 3. The words of
    `keep` (the child's name, e.g. «عبد الرحمن») stay on one line, and a line that is exactly the name is
    preferred (it reads as a big name line)."""
    units, _ = name_units(title, keep)
    n = _length(title)
    lines_wanted = 1 if n <= 13 else 2 if n <= 28 else max_lines
    return _balanced(units, max(1, min(lines_wanted, max_lines)), _MARKS.sub("", keep or "").strip())


LONG_PART = 26  # characters: a part of a poster title longer than this takes two lines when there is room


def poster_lines(title: str, keep: str | None, max_lines: int = 3) -> tuple[list[str], int | None]:
    """Poster layout: the child's name on a line of its own (it is set larger, in the name's colors), the
    words before and after it on their own lines; a long part takes two balanced lines while the total
    stays within `max_lines`. Returns the lines and the index of the name line (None: no name in the title,
    then the balanced `split_lines`)."""
    units, at = name_units(title, keep)
    if at is None or len(units) == 1:
        return split_lines(title, max_lines, keep), (0 if at is not None else None)
    before, name, after = units[:at], units[at], units[at + 1 :]
    parts = [p for p in (before, after) if p]
    room = max_lines - 1 - len(parts)
    lines: list[str] = []
    name_line = 0
    for part in (before, [name], after):
        if not part:
            continue
        if part == [name]:
            name_line = len(lines)
            lines.append(name)
            continue
        two = room > 0 and len(part) > 1 and _length(" ".join(part)) > LONG_PART
        if two:
            room -= 1
        lines += _balanced(part, 2 if two else 1)
    return lines, name_line


def _ring(radius: float, n: int) -> list[tuple[float, float]]:
    return [
        (round(radius * math.cos(2 * math.pi * i / n), 3), round(radius * math.sin(2 * math.pi * i / n), 3))
        for i in range(n)
    ]


def _line_markup(line: str, keep: str | None, scale: float = 1.0) -> Markup:
    """One title line, the child's name wrapped in a `tspan.nm` (painted in the name's gradient, `scale` × the
    line's size when it shares the line with other words)."""
    if not keep:
        return escape(line)
    units, at = name_units(line, keep)
    if at is None:
        return escape(line)
    size = f' font-size="{scale:g}em"' if scale != 1.0 and len(units) > 1 else ""
    parts = [
        escape(u) if i != at else Markup('<tspan class="nm"%s>%s</tspan>') % (Markup(size), u)
        for i, u in enumerate(units)
    ]
    return Markup(" ").join(parts)


ONE_LINE = 19  # characters (spaces too): a poster title this short stays on one line, the name larger


def poster_layout(title: str, keep: str | None) -> tuple[list[str], int | None]:
    """The lines of a poster title (see `title_svg`)."""
    if _length(title) <= ONE_LINE:
        return [" ".join(title.split())], None
    return poster_lines(title, keep)


def title_svg(
    title: str,
    style: str | None,
    *,
    width_mm: float,
    height_mm: float,
    uid: str = "t",
    rtl: bool = True,
    keep: str | None = None,
    poster: bool = False,
    glow: float = 1.0,
) -> Markup:
    """The layered title as inline SVG (mm units). Sizes and line positions are set by `TITLE_FIT_JS`.

    `keep` is the child's name: its words stay on one line and are painted in the treatment's name colors.
    `poster`: a short title stays on one line with the name set larger; a longer one gives the name a line of
    its own (`poster_lines`). `glow` scales the soft halo (light art needs less of it)."""
    t = treatment(style)
    if poster:
        lines, name_line = poster_layout(title, keep)
    else:
        lines, name_line = split_lines(title, keep=keep), None
    w, h = width_mm, height_mm

    def gradient(gid: str, stops: tuple[tuple[float, str], ...]) -> str:
        body = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        return f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">{body}</linearGradient>'

    two_tone = bool(keep and t.name_fill)
    defs = [
        gradient(f"{uid}-fill", t.fill),
        f'<filter id="{uid}-blur" x="-10%" y="-40%" width="120%" height="180%">'
        f'<feGaussianBlur stdDeviation="{t.glow_mm * 0.55:.2f}"/></filter>',
    ]
    if two_tone:
        defs.append(gradient(f"{uid}-name", t.name_fill))
    direction = "rtl" if rtl else "ltr"
    for i, line in enumerate(lines):
        is_name = name_line is not None and i == name_line
        defs.append(f'<path id="{uid}-arc{i}" d="M 0 {h / 2} L {w} {h / 2}"/>')
        defs.append(
            f'<text id="{uid}-l{i}" class="tl{" tl-name" if is_name else ""}" direction="{direction}" '
            f'text-anchor="middle" font-family="{t.font}" font-size="10" data-w="{1.75 if is_name else 1.3}">'
            f'<textPath href="#{uid}-arc{i}" startOffset="50%">'
            f"{_line_markup(line, keep if two_tone else None, 1.14 if poster else 1.0)}"
            "</textPath></text>"
        )
    ids = [f"{uid}-l{i}" for i in range(len(lines))]

    def copies(offsets: list[tuple[float, float]]) -> str:
        return "".join(f'<use href="#{i}" x="{dx}" y="{dy}"/>' for i in ids for dx, dy in offsets)

    ring = _ring(t.outline_mm, 24) + _ring(t.outline_mm * 0.55, 12)
    depth = t.depth_mm if t.side else 0.0
    steps = [round(depth * k / 4, 3) for k in range(1, 5)] if depth else []
    # the outline wraps the face and its extruded side as one silhouette
    silhouette = ring + [(dx, dy + s) for s in steps for dx, dy in _ring(t.outline_mm, 16)]
    glow_ring = _ring(t.glow_mm, 24)
    layers = []
    if glow > 0:  # only blurred: a sharp ring of copies this wide would show its scallops in print
        layers.append(
            f'<g fill="{t.glow}" filter="url(#{uid}-blur)" opacity="{min(1.0, 1.05 * glow):.2f}">'
            f"{copies(glow_ring)}</g>"
        )
    drop = t.shadow_mm + depth
    layers += [
        f'<g fill="{t.shadow}" opacity=".55" transform="translate(0 {drop})">{copies(ring)}</g>',
        f'<g fill="{t.outline}">{copies(silhouette)}</g>',
    ]
    if steps:
        layers.append(f'<g fill="{t.side}">{copies([(0, s) for s in steps])}</g>')
        layers.append(f'<g fill="{t.outline}">{copies(_ring(0.3, 12))}</g>')  # the face's edge
    layers += [
        f'<g fill="{t.rim}">{copies([(0, -0.45)])}</g>',
        f'<g fill="url(#{uid}-fill)"{f" style=--nf:url(#{uid}-name)" if two_tone else ""}>'
        f"{copies([(0, 0)])}</g>",
    ]
    return Markup(  # nosec B704 (the only text is escaped above)
        f'<svg class="title-art" viewBox="0 0 {w} {h}" data-bend="{t.bend}" data-tilt="{t.tilt}" '
        f'data-rtl="{1 if rtl else 0}" data-depth="{depth}" data-lh="{t.line_gap}" '
        f'data-pad="{t.glow_mm + t.outline_mm + 3:.2f}" aria-label="{escape(title)}" role="img">'
        f"<style>.nm{{fill:var(--nf)}}</style><defs>{''.join(defs)}</defs>{''.join(layers)}</svg>"
    )


# Fits every `.title-art` SVG: each line as large as its width allows (a line stays within `data-w` × the
# smallest line: 1.3, or 1.75 for the child's name line in a poster title, whose other lines step back to a
# smaller cap), the stack scaled down to the box height, then each line's arc (and tilt) set on its text
# path. The tilt lives in the path, not in a rotated group: a rotated blur layer would print at a lower DPI.
TITLE_FIT_JS = """
() => {
  const out = [];
  for (const svg of document.querySelectorAll('svg.title-art')) {
    const vb = svg.viewBox.baseVal, W = vb.width, H = vb.height;
    const pad = parseFloat(svg.dataset.pad || '4'), bend = parseFloat(svg.dataset.bend || '0');
    const depth = parseFloat(svg.dataset.depth || '0');
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
    // poster titles: the name line leads (up to 0.62 of the box), the other lines step back (0.38)
    const poster = texts.some(t => t.classList.contains('tl-name'));
    const named = t => t.classList.contains('tl-name');
    const caps = texts.map(t => H * (!multi || named(t) ? 0.62 : poster ? 0.38 : 0.5));
    let s = sizes.map((v, i) => Math.min(v, caps[i]));
    const smallest = Math.min(...s);
    s = s.map((v, i) => Math.min(v, smallest * parseFloat(texts[i].dataset.w || '1.3')));
    const lineH = v => v * (multi ? parseFloat(svg.dataset.lh || '1.1') : 1.15);
    const bendK = multi ? 0.45 : 1;  // stacked lines arch less, so they do not collide
    // vertical budget: the glow may spill outside the box (overflow visible), the arcs and tilt may not
    const vpad = 1.5 + depth;
    const slope = Math.abs(Math.tan(tilt)) * (W / 2 - pad);
    const rises = s.map(v => bend * bendK * 2 * Math.min(W / 2 - pad / 2, avail / 2));
    let total = s.reduce((a, v) => a + lineH(v), 0) + 2 * vpad + slope + Math.max(...rises) * 0.5;
    if (total > H) {
      const fixed = 2 * vpad + slope + Math.max(...rises) * 0.5;
      const k = (H - fixed) / (total - fixed); s = s.map(v => v * k);
    }
    total = s.reduce((a, v) => a + lineH(v), 0);
    let y = (H - total - depth) / 2;
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
