"""Text-panel checks (Addendum 3 §4): never set text over busy art, and keep contrast high.

The panel is cream at 88% opacity by default. Over busy or dark art it goes to 96% and the page is flagged
when the area is still busy (the image prompt asked for calm space there; QA also scores it).
"""

from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

from qamra_pdf.spec import Panel, PanelArea

INK = (0x1C, 0x21, 0x40)
CREAM = (0xFF, 0xFD, 0xF8)
BASE_OPACITY = 0.88
SOLID_OPACITY = 0.96
MIN_CONTRAST = 7.0  # WCAG AAA for body text
BUSY_EDGES = 0.075  # mean edge strength (0..1) above which the area is "busy"

# Where the panel sits, as fractions of the page image (x0, y0, x1, y1). Matches _base.css.j2.
AREAS: dict[PanelArea, tuple[float, float, float, float]] = {
    "top": (0.06, 0.06, 0.94, 0.40),
    "bottom": (0.06, 0.52, 0.94, 0.86),
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


def panel_for(image: Path, area: PanelArea) -> Panel:
    mean, edges = area_stats(image, area)
    busy = edges > BUSY_EDGES
    opacity = BASE_OPACITY
    c = contrast(INK, blend(CREAM, mean, opacity))
    if busy or c < MIN_CONTRAST:
        opacity = SOLID_OPACITY
        c = contrast(INK, blend(CREAM, mean, opacity))
    return Panel(area=area, opacity=opacity, busy=busy, contrast=round(c, 2))
