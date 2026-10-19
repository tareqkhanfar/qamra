"""Text-area checks (Addendum 3 §4, Addendum 11 §3): never set text over busy art, and keep contrast high.

Layouts that set text on the art (cloud, fade, panorama, big moment, dialogue) back it with cream at 88%
opacity by default. Over busy or low-contrast art it goes to 96% and the page is flagged when the area is
still busy (the image prompt asked for calm space there; QA also scores it). Dark text areas (night scenes)
get `tone="dark"`, so a fade can turn deep blue with light text instead of a cream fog.

`AREAS` are the text areas the planner (`qamra_ai.pipeline.layout`) names and the image prompt keeps calm:
every layout of the library sets its text inside one of them.
"""

import colorsys
from pathlib import Path
from typing import Literal

from PIL import Image, ImageFilter, ImageStat

from qamra_pdf.spec import Panel, PanelArea

INK = (0x1C, 0x21, 0x40)
CREAM = (0xFF, 0xFD, 0xF8)
BASE_OPACITY = 0.88
SOLID_OPACITY = 0.96
MIN_CONTRAST = 7.0  # WCAG AAA for body text
WASH_THINNEST = 0.8  # the painted wash's mottling (shapes.SHAPES_JS) never thins below 80% of its opacity
BUSY_EDGES = 0.075  # mean edge strength (0..1) above which the area is "busy"
DARK_LUMINANCE = 0.16  # relative luminance below which the text area counts as dark

# Where the panel sits, as fractions of the page image (x0, y0, x1, y1). Matches _base.css.j2 and the layout
# library (packages/pdf/layouts): a bottom text box ends 191 mm down a 216 mm page.
AREAS: dict[PanelArea, tuple[float, float, float, float]] = {
    "top": (0.06, 0.06, 0.94, 0.40),
    "bottom": (0.06, 0.52, 0.94, 0.89),
    "left": (0.06, 0.06, 0.46, 0.86),
    "right": (0.54, 0.06, 0.94, 0.86),
}


def _luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def blend(
    top: tuple[int, int, int], bottom: tuple[float, float, float], alpha: float
) -> tuple[float, float, float]:
    return (
        alpha * top[0] + (1 - alpha) * bottom[0],
        alpha * top[1] + (1 - alpha) * bottom[1],
        alpha * top[2] + (1 - alpha) * bottom[2],
    )


def area_stats(image: Path, area: PanelArea) -> tuple[tuple[float, float, float], float]:
    """(mean color, edge strength 0..1) of the panel area."""
    with Image.open(image) as src:
        im = src.convert("RGB")
        im.thumbnail((600, 600))
        w, h = im.size
        x0, y0, x1, y1 = AREAS[area]
        region = im.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
        mean = tuple(ImageStat.Stat(region).mean[:3])
        edges = ImageStat.Stat(region.convert("L").filter(ImageFilter.FIND_EDGES)).mean[0] / 255
    return (mean[0], mean[1], mean[2]), edges


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def _from_hls(h: float, light: float, sat: float) -> tuple[float, float, float]:
    r, g, b = colorsys.hls_to_rgb(h, light, sat)
    return (r * 255, g * 255, b * 255)


def picture_hue(image: Path) -> tuple[float, float]:
    """(hue, saturation) of the picture's own color: the largest clearly colored region (a few dominant
    colors; greys, near-whites and near-blacks don't count)."""
    with Image.open(image) as src:
        im = src.convert("RGB")
        im.thumbnail((240, 240))
        q = im.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette() or []
    best, score = (0.08, 0.35), 0.0  # a warm brown when nothing is colored
    for count, idx in q.getcolors() or []:
        i = int(idx)  # type: ignore[arg-type]  # a palette index ("P" image)
        r, g, b = palette[i * 3 : i * 3 + 3]
        h, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if not 0.15 < light < 0.82 or sat < 0.12:
            continue
        if count * sat > score:
            best, score = (h, sat), count * sat
    return best


def palette_for(
    image: Path, area: PanelArea, opacity: float = BASE_OPACITY
) -> tuple[str, str, str, str, float]:
    """(wash, ink, deep, backdrop, contrast) for text set on the picture.

    - wash: a pale tint (lightness 0.93) of the art's own color around the text, so the painted shape reads
      as part of the picture, not a white sticker;
    - ink: the picture's own hue, deep (lightness ≤ 0.2), darkened until it reaches 7:1 on the wash as
      printed (the wash at `opacity` over the art);
    - deep: a mid tone of the same hue for ornaments and flourishes;
    - backdrop: what the words actually sit on where the wash is thinnest (the contrast is measured there).
    """
    mean, _ = area_stats(image, area)
    hue, sat = picture_hue(image)
    h0, _, s0 = colorsys.rgb_to_hls(*(c / 255 for c in mean))
    # a pale tint of the art's own color around the text (the picture's hue when that area is grey)
    wash = _from_hls(h0, 0.93, min(0.6, max(0.32, s0 * 1.4))) if s0 >= 0.12 else _from_hls(hue, 0.93, 0.4)
    while _luminance(wash) < 0.8:
        wash = blend(CREAM, wash, 0.7)
    # the words' background where the painted wash is thinnest (its mottling goes down to 80% of `opacity`)
    under = blend((round(wash[0]), round(wash[1]), round(wash[2])), mean, opacity * WASH_THINNEST)
    light = 0.2
    ink = _from_hls(hue, light, min(0.55, max(0.3, sat)))
    while contrast(ink, under) < MIN_CONTRAST and light > 0.06:
        light -= 0.02
        ink = _from_hls(hue, light, min(0.55, max(0.3, sat)))
    if contrast(ink, under) < MIN_CONTRAST:
        ink = INK
    deep = _from_hls(hue, 0.4, min(0.6, max(0.35, sat)))
    return _hex(wash), _hex(ink), _hex(deep), _hex(under), round(contrast(ink, under), 2)


def readable(color: str, background: str, minimum: float = 4.5) -> str:
    """`color`, darkened in small steps until it reaches `minimum` contrast on `background` (hex colors)."""

    def rgb(c: str) -> tuple[float, float, float]:
        c = c.lstrip("#")
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

    fg, bg = rgb(color), rgb(background)
    h, light, sat = colorsys.rgb_to_hls(*(c / 255 for c in fg))
    while contrast(fg, bg) < minimum and light > 0.05:
        light -= 0.03
        fg = _from_hls(h, light, sat)
    return _hex(fg)


def panel_for(image: Path, area: PanelArea) -> Panel:
    mean, edges = area_stats(image, area)
    busy = edges > BUSY_EDGES
    opacity = BASE_OPACITY
    c = contrast(INK, blend(CREAM, mean, opacity))
    if busy or c < MIN_CONTRAST:
        opacity = SOLID_OPACITY
    tone: Literal["light", "dark"] = "dark" if _luminance(mean) < DARK_LUMINANCE else "light"
    wash, ink, deep, backdrop, c = palette_for(image, area, opacity)
    return Panel(
        area=area,
        opacity=opacity,
        busy=busy,
        contrast=c,
        tone=tone,
        wash=wash,
        ink=ink,
        deep=deep,
        backdrop=backdrop,
    )


def paper_panel(image: Path, area: PanelArea) -> Panel:
    """Text on the cream page beside a framed or vignetted picture: the ink and ornaments still come from
    the picture's hue, on the page's own paper color."""
    hue, sat = picture_hue(image)
    paper = (0xFB, 0xF6, 0xEC)
    light = 0.2
    ink = _from_hls(hue, light, min(0.55, max(0.3, sat)))
    while contrast(ink, paper) < MIN_CONTRAST and light > 0.06:
        light -= 0.02
        ink = _from_hls(hue, light, min(0.55, max(0.3, sat)))
    deep = _from_hls(hue, 0.4, min(0.6, max(0.35, sat)))
    return Panel(
        area=area,
        opacity=1.0,
        contrast=round(contrast(ink, paper), 2),
        wash=_hex(paper),
        ink=_hex(ink),
        deep=_hex(deep),
        backdrop=_hex(paper),
    )
