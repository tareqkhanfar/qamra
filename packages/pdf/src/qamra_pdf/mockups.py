"""Product mockups from the real print files (Addendum 11 §2.7): no AI, no paid service.

- `hardcover.png` (1600 × 1600): the closed hardcover lying on cream linen at a slight angle, with board
  thickness, the rounded spine on the binding side (right for Arabic books, left for English), page-block
  edges and a soft contact shadow.
- `spread.png` (2000 × 1250): the book open flat on two facing pages (gutter shadow, slight page curve), with
  the closed book lying behind it.

Both are HTML/CSS 3D scenes screenshotted with Chromium, like the rest of this package. The textures come
from the cover wrap (front, spine, back) and two facing interior pages, rasterized from the PDFs with pdfium.

Photo mode: when a real product photo with a blank white cover exists (`design/assets/B1-mockup-hardcover-
angle.*`, `B2-mockup-open-spread.*`, docs/image-prompts.md §B), the blank quadrilateral is found (largest
near-white region that is clearly a quadrilateral) and the art is warped onto it in perspective, multiplied by
the photo's own shading. When the detection is unsure the CSS scene is used.
"""

import asyncio
import math
import tempfile
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from playwright.async_api import async_playwright

from qamra_pdf.spec import PageSpec

Lang = Literal["ar", "en"]
Side = Literal["left", "right"]
Edge = Literal["top", "bottom", "left", "right"]

HARDCOVER_PX = (1600, 1600)
SPREAD_PX = (2000, 1250)
_HERE = Path(__file__).resolve().parents
# the repo's design assets (docs/image-prompts.md §B); an installed package simply has none
PHOTOS_DIR: Path | None = _HERE[4] / "design" / "assets" if len(_HERE) > 4 else None
PHOTO_NAMES = {"hardcover": "B1-mockup-hardcover-angle", "spread": "B2-mockup-open-spread"}
TRIM_MM = 210.0
BOARD_MM = 2.6  # hardcover board thickness
SQUARE_MM = 3.0  # the boards overhang the page block by this much
MIN_THICKNESS_MM = 8.0
SUPERSAMPLE = 2  # screenshot at 2× and downsample: clean edges on the 3D faces
PANORAMA = frozenset({"spread-panorama", "spread"})


def spine_side(lang: str) -> Side:
    """Arabic books are bound on the right, English on the left."""
    return "right" if lang == "ar" else "left"


@dataclass(frozen=True)
class BookArt:
    """Textures for the scenes, cut to the trim (no bleed)."""

    front: Image.Image
    lang: Lang
    spine: Image.Image | None = None
    back: Image.Image | None = None
    pages: tuple[Image.Image, Image.Image] | None = None  # (left, right) as they lie in the open book
    thickness_mm: float = MIN_THICKNESS_MM


@dataclass(frozen=True)
class Mockups:
    hardcover: Path
    spread: Path | None
    modes: dict[str, str]  # mockup → "css" | "photo"


# ---- textures from the PDFs ------------------------------------------------------------------------------


def _render(page: pdfium.PdfPage, x0: float, x1: float, inset: float, px: int) -> Image.Image:
    """Region [x0, x1] × [inset, h − inset] (points) of a page, `px` wide."""
    w, _ = page.get_size()
    scale = px / max(1.0, x1 - x0)
    im: Image.Image = page.render(scale=scale, crop=(x0, inset, max(0.0, w - x1), inset)).to_pil()
    return im.convert("RGB")


def _bleed_pt(page: pdfium.PdfPage) -> float:
    left, bottom, _, _ = page.get_trimbox()
    return max(0.0, min(float(left), float(bottom)))


@dataclass(frozen=True)
class WrapArt:
    front: Image.Image
    spine: Image.Image | None
    back: Image.Image | None
    spine_mm: float


def cover_art(cover_pdf: Path, lang: Lang, *, px: int = 1500) -> WrapArt:
    """Front, spine and back from the cover wrap's first page. The wrap is laid out as the printer sees the
    flat sheet: Arabic [front | spine | back], English [back | spine | front]. A square page is a front."""
    doc = pdfium.PdfDocument(str(cover_pdf))
    try:
        page = doc[0]
        w, h = page.get_size()
        b = _bleed_pt(page)
        trim = h - 2 * b
        spine = w - 2 * b - 2 * trim
        if spine < -1:  # not a wrap: the whole trim is the front
            return WrapArt(_render(page, b, w - b, b, px), None, None, 0.0)
        spine = max(0.0, spine)
        front_x0 = b if lang == "ar" else b + trim + spine
        back_x0 = b + trim + spine if lang == "ar" else b
        strip = None
        if spine > 1:
            strip = _render(page, b + trim, b + trim + spine, b, max(8, round(px * spine / trim)))
        return WrapArt(
            _render(page, front_x0, front_x0 + trim, b, px),
            strip,
            _render(page, back_x0, back_x0 + trim, b, 300),
            spine * 25.4 / 72,
        )
    finally:
        doc.close()


def interior_pages(interior_pdf: Path) -> list[int]:
    """Indexes of the square (interior) pages: a combined proof file starts with the wide cover wrap."""
    doc = pdfium.PdfDocument(str(interior_pdf))
    try:
        return [i for i in range(len(doc)) if abs(doc[i].get_size()[0] - doc[i].get_size()[1]) < 2]
    finally:
        doc.close()


def page_art(interior_pdf: Path, numbers: Sequence[int], *, px: int = 1100) -> list[Image.Image]:
    """Physical pages (1-based among the square pages), cut to the trim."""
    square = interior_pages(interior_pdf)
    doc = pdfium.PdfDocument(str(interior_pdf))
    try:
        out = []
        for n in numbers:
            page = doc[square[n - 1]]
            w, _ = page.get_size()
            b = _bleed_pt(page)
            out.append(_render(page, b, w - b, b, px))
        return out
    finally:
        doc.close()


def facing(n: int, lang: str) -> tuple[int, int]:
    """(left, right) physical page numbers of the open spread whose first page is the even page `n`.
    Arabic: page 1 is a left-hand page, so even pages are on the right; English mirrors that."""
    return (n + 1, n) if lang == "ar" else (n, n + 1)


def spread_from_pages(pages: Sequence[PageSpec], lang: str) -> tuple[int, int] | None:
    """The spread to show: a panorama (one picture across both pages) if there is one, else the middle pair
    of facing story pages with pictures."""
    by_number = {p.number: p for p in pages}
    candidates: list[tuple[int, int]] = []
    for p in pages:
        q = by_number.get(p.number + 1)
        if p.number % 2 or q is None or not (p.kind == q.kind == "story" and p.image and q.image):
            continue
        if p.layout in PANORAMA and q.layout in PANORAMA:
            return facing(p.number, lang)
        candidates.append(facing(p.number, lang))
    return candidates[len(candidates) // 2] if candidates else None


def pick_spread(interior_pdf: Path, lang: str) -> tuple[int, int] | None:
    """Without a page plan: the facing pair whose picture runs on across the gutter (a panorama), weighted by
    how much picture the two pages hold. Page 1 and the last pages (activities, memories) are never picked."""
    count = len(interior_pages(interior_pdf))
    evens = list(range(2, count - 3, 2))
    if not evens:
        return None
    numbers = sorted({m for n in evens for m in (n, n + 1)})
    small = dict(zip(numbers, page_art(interior_pdf, numbers, px=64), strict=True))
    best, best_score = None, -math.inf
    for n in evens:
        left_no, right_no = facing(n, lang)
        a = np.asarray(small[left_no], dtype=np.float32)
        c = np.asarray(small[right_no], dtype=np.float32)
        seam = float(np.abs(a[:, -2:, :].mean(axis=1) - c[:, :2, :].mean(axis=1)).mean())
        score = float(a.std() + c.std()) - 2.5 * seam
        if score > best_score:
            best, best_score = (left_no, right_no), score
    return best


# ---- the CSS scenes ---------------------------------------------------------------------------------------

_LINEN_H = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512'><filter id='f'>"
    "<feTurbulence type='fractalNoise' baseFrequency='0.012 0.55' numOctaves='3' seed='4' "
    "stitchTiles='stitch'/>"
    "<feColorMatrix values='0 0 0 0 0.42 0 0 0 0 0.33 0 0 0 0 0.22 0 0 0 -1.1 0.62'/></filter>"
    "<rect width='100%' height='100%' filter='url(#f)'/></svg>"
)
_LINEN_V = _LINEN_H.replace("0.012 0.55", "0.55 0.012").replace("seed='4'", "seed='9'")
_GRAIN = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256'><filter id='g'>"
    "<feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='2' stitchTiles='stitch'/>"
    "<feColorMatrix values='0 0 0 0 0.35 0 0 0 0 0.28 0 0 0 0 0.2 0 0 0 -0.9 0.55'/></filter>"
    "<rect width='100%' height='100%' filter='url(#g)'/></svg>"
)


def _svg_url(svg: str) -> str:
    return 'url("data:image/svg+xml;utf8,' + svg.replace("#", "%23") + '")'


_LINEN = (
    f"background-color:#ECE2D0;background-image:{_svg_url(_GRAIN)},{_svg_url(_LINEN_H)},{_svg_url(_LINEN_V)};"
    "background-size:256px 256px,512px 512px,512px 512px;"
)

_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{w}px;height:{h}px;overflow:hidden;background:#E9DFCC}}
.scene{{position:absolute;inset:0;perspective:{persp}px;perspective-origin:{po}}}
.table{{position:absolute;left:{cx}px;top:{cy}px;width:0;height:0;transform-style:preserve-3d;
  transform:rotateX({tilt}deg)}}
.surface{{position:absolute;left:-3000px;top:-3000px;width:6000px;height:6000px;transform:translateZ(-2px);
  {linen}}}
.obj{{position:absolute;left:0;top:0;width:0;height:0;transform-style:preserve-3d}}
.f{{position:absolute;left:0;top:0;transform-origin:0 0;backface-visibility:hidden}}
.sh{{position:absolute;left:0;top:0;transform-origin:0 0}}
.light{{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 75% 70% at 36% 30%,rgba(255,248,232,.30),rgba(255,248,232,0) 60%),
  radial-gradient(ellipse 95% 90% at 50% 46%,rgba(0,0,0,0) 55%,rgba(70,48,24,.24) 100%)}}
</style></head><body><div class="scene"><div class="table"><div class="surface"></div>
{body}
</div></div><div class="light"></div></body></html>"""


@dataclass(frozen=True)
class _Light:
    """Light from the upper left, above the table (table coordinates: x right, y toward the camera, z up)."""

    x: float = -0.45
    y: float = -0.55
    z: float = 0.85

    def shade(self, nx: float, ny: float, nz: float, rz_deg: float) -> float:
        """Black overlay alpha for a face whose book-local normal is (nx, ny, nz), the book turned by rz."""
        r = math.radians(rz_deg)
        wx, wy = nx * math.cos(r) - ny * math.sin(r), nx * math.sin(r) + ny * math.cos(r)
        dot = (wx * self.x + wy * self.y + nz * self.z) / math.sqrt(self.x**2 + self.y**2 + self.z**2)
        return round(max(0.0, min(0.62, 0.36 - 0.36 * dot)), 3)


_LIGHT = _Light()
_PAPER = "#F7F2E8"


def _dim(a: float) -> str:
    return f"linear-gradient(rgba(20,12,4,{a}),rgba(20,12,4,{a}))"


def _face(w: float, h: float, transform: str, background: str, extra: str = "") -> str:
    return (
        f'<div class="f" style="width:{w:.2f}px;height:{h:.2f}px;transform:{transform};'
        f'background:{background};{extra}"></div>'
    )


def _shadows(x: float, y: float, w: float, h: float, scale: float) -> str:
    """Contact shadow (tight, dark) and two soft ones falling away from the light, on the table under an
    object whose footprint is (x, y, w, h)."""
    out = []
    for blur, grow, dx, dy, a in ((3, 2, 3, 4, 0.62), (16, 9, 18, 26, 0.42), (60, 30, 62, 88, 0.3)):
        b, g, ox, oy = blur * scale, grow * scale, dx * scale, dy * scale
        out.append(
            f'<div class="sh" style="left:{x - g + ox:.1f}px;top:{y - g + oy:.1f}px;width:{w + 2 * g:.1f}px;'
            f"height:{h + 2 * g:.1f}px;transform:translateZ(-1px);background:rgba(58,38,18,{a});"
            f'border-radius:{g + 4:.0f}px;filter:blur({b:.1f}px)"></div>'
        )
    return "".join(out)


def _mean_color(im: Image.Image, edge: Edge) -> str:
    w, h = im.size
    d = max(2, min(w, h) // 60)
    box = {"bottom": (0, h - d, w, h), "top": (0, 0, w, d), "left": (0, 0, d, h), "right": (w - d, 0, w, h)}
    r, g, b = (int(v) for v in np.asarray(im.crop(box[edge]), dtype=np.float32).reshape(-1, 3).mean(axis=0))
    return f"rgb({r},{g},{b})"


def _edge_strip(im: Image.Image, edge: Edge) -> Image.Image:
    """The art next to an edge, mirrored so the edge row/column comes first: what the cover cloth shows as
    it wraps around the board's edge (the top of a horizontal edge face, the start of a vertical one)."""
    w, h = im.size
    d = max(3, min(w, h) // 70)
    if edge == "bottom":
        return ImageOps.flip(im.crop((0, h - d, w, h)))
    if edge == "top":
        return ImageOps.mirror(im.crop((0, 0, w, d)))
    if edge == "left":
        return ImageOps.mirror(im.crop((0, 0, d, h)))
    return ImageOps.mirror(im.crop((w - d, 0, w, h)))


@dataclass(frozen=True)
class _Tex:
    """Texture files for one scene (URIs), plus solid colors for the small faces."""

    front: str
    spine: str | None
    spine_color: str
    edges: dict[str, str]  # front board edge strips: top / bottom / fore
    back_colors: dict[str, str]  # back board edges: top / bottom / fore
    board_color: str  # the rim of the open book's boards
    pages: tuple[str, str] | None


def _textures(art: BookArt, work: Path) -> _Tex:
    def save(im: Image.Image, name: str, fmt: str = "JPEG") -> str:
        path = work / name
        im.convert("RGB").save(path, fmt, **({"quality": 93} if fmt == "JPEG" else {}))
        return path.as_uri()

    fore: Edge = "left" if spine_side(art.lang) == "right" else "right"
    back_fore: Edge = "right" if fore == "left" else "left"  # the back panel is mirrored on the wrap
    back = art.back or art.front
    pages = None
    if art.pages is not None:
        pages = (save(art.pages[0], "left.jpg"), save(art.pages[1], "right.jpg"))
    return _Tex(
        front=save(art.front, "front.jpg"),
        spine=save(art.spine, "spine.png", "PNG") if art.spine is not None else None,
        spine_color=_mean_color(art.spine, "left") if art.spine is not None else _mean_color(art.front, fore),
        edges={e: save(_edge_strip(art.front, e), f"edge-{e}.png", "PNG") for e in ("top", "bottom")}
        | {"fore": save(_edge_strip(art.front, fore), "edge-fore.png", "PNG")},
        back_colors={"top": _mean_color(back, "top"), "bottom": _mean_color(back, "bottom")}
        | {"fore": _mean_color(back, back_fore)},
        board_color=_mean_color(back, "bottom"),
        pages=pages,
    )


def _page_lines(direction: str, a: float) -> str:
    a = round(a * 0.4, 3)  # paper is bright: edges in shade still read as white paper
    return (
        f"{_dim(a)},repeating-linear-gradient({direction},rgba(150,128,96,.16) 0 1px,rgba(255,255,255,0) 1px "
        f"2.4px,rgba(170,146,110,.08) 2.4px 3.3px),{_PAPER}"
    )


def _closed_book(art: BookArt, tex: _Tex, size: float, rz: float, *, spine_steps: int = 14) -> str:
    """A closed hardcover lying on the table, front up, centred on the object origin. Book-local axes:
    x right, y down the cover, z up out of the table."""
    k = size / TRIM_MM
    s = size
    t = max(art.thickness_mm, MIN_THICKNESS_MM) * k
    tb = BOARD_MM * k
    q = SQUARE_MM * k
    bulge = 0.32 * t
    side = spine_side(art.lang)
    sx = s if side == "right" else 0.0  # spine x
    fore = 0.0 if side == "right" else s  # fore-edge x
    fdir = -1 if side == "right" else 1  # the fore-edge faces −x (Arabic) or +x (English)
    L = _LIGHT
    parts = [_shadows(0.0 if side == "right" else -bulge, 0.0, s + bulge, s, k / 4.95)]

    # front cover: a matte sheen, the hinge groove beside the spine, softened board edges
    gw = 4.5 * k
    gx = s - 11 * k if side == "right" else 11 * k - gw
    gdir = "to right" if side == "right" else "to left"
    groove = (
        f"linear-gradient({gdir},rgba(0,0,0,0) 0,rgba(30,18,6,.13) 30%,rgba(30,18,6,.05) 55%,"
        f"rgba(255,250,240,.07) 75%,rgba(255,255,255,0) 100%) {gx:.1f}px 0/{gw:.1f}px 100% no-repeat"
    )
    sheen = (
        "linear-gradient(128deg,rgba(255,252,244,.16) 0%,rgba(255,252,244,0) 38%,rgba(0,0,0,0) 62%,"
        "rgba(20,12,4,.10) 100%)"
    )
    parts.append(
        _face(
            s,
            s,
            f"translate3d(0,0,{t:.2f}px)",
            f"{sheen},{groove},url('{tex.front}') 0 0/100% 100%",
            "box-shadow:inset 0 0 2px rgba(0,0,0,.3)",
        )
    )

    def near(x0: float, w: float, y: float, z: float, h: float, bg: str) -> None:  # facing +y
        parts.append(_face(w, h, f"translate3d({x0:.2f}px,{y:.2f}px,{z:.2f}px) rotateX(-90deg)", bg))

    def far(x0: float, w: float, y: float, z: float, h: float, bg: str) -> None:  # facing −y
        tf = f"translate3d({x0 + w:.2f}px,{y:.2f}px,{z:.2f}px) rotateZ(180deg) rotateX(-90deg)"
        parts.append(_face(w, h, tf, bg))

    def side_face(x: float, y0: float, h: float, z_top: float, d: float, bg: str) -> None:
        # local x runs from the top of the face (z_top) down the thickness d
        if fdir < 0:
            tf = f"translate3d({x:.2f}px,{y0:.2f}px,{z_top - d:.2f}px) rotateY(-90deg)"
        else:
            tf = f"translate3d({x:.2f}px,{y0:.2f}px,{z_top:.2f}px) rotateY(90deg)"
        parts.append(_face(d, h, tf, bg))

    a_near, a_far, a_fore = L.shade(0, 1, 0, rz), L.shade(0, -1, 0, rz), L.shade(fdir, 0, 0, rz)
    lip = "linear-gradient(rgba(255,250,240,.22),rgba(255,250,240,0) 35%)"  # the rounded edge catches light
    near(0, s, s, t, tb, f"{lip},{_dim(a_near)},url('{tex.edges['bottom']}') 0 0/100% 100%")
    far(0, s, 0, t, tb, f"{lip},{_dim(a_far)},url('{tex.edges['top']}') 0 0/100% 100%")
    fore_strip = f"url('{tex.edges['fore']}') 0 0/100% 100%"
    lip_side = "linear-gradient(to left,rgba(255,250,240,.2),rgba(255,250,240,0) 35%)"
    side_face(
        fore,
        0,
        s,
        t,
        tb,
        f"{lip_side if fdir < 0 else lip_side.replace('to left', 'to right')},{_dim(a_fore)},{fore_strip}",
    )
    near(0, s, s, tb, tb, f"{_dim(a_near)},{tex.back_colors['bottom']}")
    far(0, s, 0, tb, tb, f"{_dim(a_far)},{tex.back_colors['top']}")
    side_face(fore, 0, s, tb, tb, f"{_dim(a_fore)},{tex.back_colors['fore']}")
    # the page block, set back by the squares, with a shadow line under the front board
    under = "linear-gradient(rgba(40,26,10,.35),rgba(40,26,10,0) 40%)"
    under_side = under.replace("(", "(to right," if fdir > 0 else "(to left,", 1)
    block_x0 = q if side == "right" else 0.0
    block_h = t - 2 * tb
    near(block_x0, s - q, s - q, t - tb, block_h, f"{under},{_page_lines('to bottom', a_near)}")
    far(block_x0, s - q, q, t - tb, block_h, f"{under},{_page_lines('to bottom', a_far)}")
    side_face(
        fore - fdir * q,
        q,
        s - 2 * q,
        t - tb,
        block_h,
        f"{under_side},{_page_lines('to right', a_fore)}",
    )

    # the rounded spine: strips around a half-ellipse from the front board down to the back board, traversed
    # so each strip faces outward; the wrap's spine image runs front → back (Arabic) or back → front (English)
    # from left to right, which is the strips' order either way.
    pts: list[tuple[float, float]] = []
    for i in range(spine_steps + 1):
        phi = math.pi / 2 - math.pi * i / spine_steps  # +90° (top) → −90° (table)
        pts.append((sx - fdir * bulge * math.cos(phi), t / 2 + (t / 2) * math.sin(phi)))
    if side == "left":
        pts.reverse()
    lengths = [math.dist(pts[i], pts[i + 1]) for i in range(spine_steps)]
    total, pos = sum(lengths), 0.0
    for i in range(spine_steps):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        ang = math.atan2(-(z1 - z0), x1 - x0)
        nx, nz = math.sin(ang), math.cos(ang)
        tint = f"{_dim(L.shade(nx, 0, nz, rz))}"
        hi = max(0.0, nz) * 0.10
        body = (
            f"url('{tex.spine}') {-pos:.2f}px 0/{total:.2f}px {s:.2f}px no-repeat"
            if tex.spine
            else tex.spine_color
        )
        bg = f"{tint},linear-gradient(rgba(255,250,240,{hi:.3f}),rgba(255,250,240,{hi:.3f})),{body}"
        tf = f"translate3d({x0:.2f}px,0,{z0:.2f}px) rotateY({math.degrees(ang):.3f}deg)"
        parts.append(_face(lengths[i] + 0.8, s, tf, bg))
        pos += lengths[i]
    # head and tail of the spine: half-ellipse caps (the hollow behind the rounded spine)
    clip = "ellipse(100% 50% at 0% 50%)" if side == "right" else "ellipse(100% 50% at 100% 50%)"
    cap_x = sx if side == "right" else sx - bulge
    cap_bg = f"{_dim(0.62)},{tex.spine_color}"
    parts.append(
        _face(
            bulge,
            t,
            f"translate3d({cap_x:.2f}px,{s:.2f}px,{t:.2f}px) rotateX(-90deg)",
            cap_bg,
            f"clip-path:{clip}",
        )
    )
    return (
        f'<div class="obj" style="transform:rotateZ({rz}deg) translate({-s / 2:.1f}px,{-s / 2:.1f}px)">'
        + "".join(parts)
        + "</div>"
    )


def _page_curve(p: float, rise: float, steps: int) -> list[tuple[float, float]]:
    """(distance from the gutter, height) along an open page: a steep rise out of the gutter, then a gentle
    dome that settles on the page stack at the outer edge."""
    out = []
    for i in range(steps + 1):
        u = p * (i / steps) ** 1.7
        out.append((u, rise * (1 - math.exp(-u / (0.07 * p))) + 0.008 * p * math.sin(math.pi * u / p)))
    return out


def _gutter(u: float, page: float) -> float:
    """Gutter shadow (black alpha) at distance `u` from the fold."""
    return 0.55 * math.exp(-u / (0.028 * page)) + 0.16 * math.exp(-u / (0.13 * page))


def _open_book(art: BookArt, tex: _Tex, page: float, rz: float, *, steps: int = 30) -> str:
    """The book open flat, centred on the gutter. The cover boards show a few mm around the pages."""
    assert tex.pages is not None
    k = page / TRIM_MM
    tb = BOARD_MM * k
    q = SQUARE_MM * k
    block = (
        max(1.0, (max(art.thickness_mm, MIN_THICKNESS_MM) - 2 * BOARD_MM)) * k / 2
    )  # stack under each side
    rise = block + 6 * k
    L = _LIGHT
    w_all, h_all = 2 * page + 2 * q, page + 2 * q
    x0, y0 = -w_all / 2, -h_all / 2
    parts = [_shadows(x0, y0, w_all, h_all, k / 3.4)]
    # boards: the inside rim around the pages and the edges
    col = tex.board_color
    parts.append(
        _face(
            w_all,
            h_all,
            f"translate3d({x0:.2f}px,{y0:.2f}px,{tb:.2f}px)",
            f"{_dim(0.05)},{col}",
            "box-shadow:inset 0 0 0 1px rgba(0,0,0,.12)",
        )
    )
    parts.append(
        _face(
            w_all,
            tb,
            f"translate3d({x0:.2f}px,{-y0:.2f}px,{tb:.2f}px) rotateX(-90deg)",
            f"{_dim(L.shade(0, 1, 0, rz))},{col}",
        )
    )
    for sgn in (-1, 1):
        x = sgn * w_all / 2
        tf = (
            f"translate3d({x:.2f}px,{y0:.2f}px,0) rotateY(-90deg)"
            if sgn < 0
            else f"translate3d({x:.2f}px,{y0:.2f}px,{tb:.2f}px) rotateY(90deg)"
        )
        parts.append(_face(tb, h_all, tf, f"{_dim(L.shade(sgn, 0, 0, rz))},{col}"))

    curve = _page_curve(page, rise, steps)
    top = -page / 2
    for sgn, uri in ((-1, tex.pages[0]), (1, tex.pages[1])):
        # the page stack's near edge, cut along the curve of the top page
        poly = ",".join(f"{(page - u) if sgn < 0 else u:.1f}px {block + rise - z:.1f}px" for u, z in curve)
        bottom = block + rise
        corners = (
            f"{0 if sgn < 0 else page:.1f}px {bottom:.1f}px,{page if sgn < 0 else 0:.1f}px {bottom:.1f}px"
        )
        parts.append(
            _face(
                page,
                block + rise,
                f"translate3d({-page if sgn < 0 else 0:.2f}px,{page / 2:.2f}px,{tb + bottom:.2f}px) "
                "rotateX(-90deg)",
                _page_lines("to bottom", L.shade(0, 1, 0, rz)),
                f"clip-path:polygon({poly},{corners})",
            )
        )
        # the stack's outer fore-edge
        xo = sgn * page
        h_edge = block + curve[-1][1]
        tf = (
            f"translate3d({xo:.2f}px,{top:.2f}px,{tb:.2f}px) rotateY(-90deg)"
            if sgn < 0
            else f"translate3d({xo:.2f}px,{top:.2f}px,{tb + h_edge:.2f}px) rotateY(90deg)"
        )
        parts.append(_face(h_edge, page, tf, _page_lines("to right", L.shade(sgn, 0, 0, rz))))
        # the top page, in strips from its outer edge to the gutter (left) or from the gutter outward (right)
        seq = list(reversed(curve)) if sgn < 0 else curve
        pts = [(sgn * u, tb + block + z) for u, z in seq]
        angs = [math.atan2(-(pts[i + 1][1] - pts[i][1]), pts[i + 1][0] - pts[i][0]) for i in range(steps)]
        # shading per vertex (normal averaged over the two strips that meet there), blended across each strip
        dark, light = [], []
        for j, (u, _) in enumerate(seq):
            ang = (angs[max(0, j - 1)] + angs[min(steps - 1, j)]) / 2
            slope = L.shade(math.sin(ang), 0, math.cos(ang), rz) - L.shade(0, 0, 1, rz)
            dark.append(max(0.0, _gutter(u, page) + slope))
            light.append(0.10 * math.exp(-(((u / page) - 0.12) ** 2) / 0.004))  # light on the page's crown
        for i in range(steps):
            (xa, za), (xb, zb) = pts[i], pts[i + 1]
            img_x = (page + xa) if sgn < 0 else xa
            bg = (
                f"linear-gradient(to right,rgba(26,16,6,{dark[i]:.3f}),rgba(26,16,6,{dark[i + 1]:.3f})),"
                f"linear-gradient(to right,rgba(255,252,244,{light[i]:.3f}),"
                f"rgba(255,252,244,{light[i + 1]:.3f})),"
                f"url('{uri}') {-img_x:.2f}px 0/{page:.2f}px {page:.2f}px no-repeat"
            )
            tf = f"translate3d({xa:.2f}px,{top:.2f}px,{za:.2f}px) rotateY({math.degrees(angs[i]):.3f}deg)"
            parts.append(_face(math.hypot(xb - xa, zb - za) + 0.9, page, tf, bg))
    return f'<div class="obj" style="transform:rotateZ({rz}deg)">' + "".join(parts) + "</div>"


def hardcover_html(art: BookArt, tex: _Tex) -> str:
    """The closed book turned a little so its spine side faces the camera."""
    w, h = HARDCOVER_PX
    flip = 1 if spine_side(art.lang) == "right" else -1
    book = _closed_book(art, tex, 1040.0, 12.0 * flip)
    return _PAGE.format(
        w=w,
        h=h,
        persp=3600,
        po=f"{50 + 14 * flip}% 18%",
        cx=w / 2 - 12 * flip,
        cy=h / 2 - 34,
        tilt=32,
        linen=_LINEN,
        body=book,
    )


def spread_html(art: BookArt, tex: _Tex) -> str:
    """The open book in front; the closed book lies behind it on the binding side."""
    w, h = SPREAD_PX
    flip = 1 if spine_side(art.lang) == "right" else -1
    closed = _closed_book(art, tex, 470.0, 10.0 * flip)
    opened = _open_book(art, tex, 610.0, -2.0 * flip)
    body = (
        f'<div class="obj" style="transform:translate3d({555 * flip}px,-330px,0)">{closed}</div>'
        f'<div class="obj" style="transform:translate3d({-95 * flip}px,215px,0)">{opened}</div>'
    )
    return _PAGE.format(
        w=w, h=h, persp=3800, po="50% 22%", cx=w / 2, cy=h / 2, tilt=26, linen=_LINEN, body=body
    )


async def _shoot(pages: Sequence[tuple[str, tuple[int, int], Path]], work: Path) -> None:
    """Screenshot each (html, size, out) at 2× in one Chromium session and downsample to a PNG."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            for html, size, out in pages:
                page_file = work / f"{out.stem}.html"
                page_file.write_text(html, encoding="utf-8")
                page = await browser.new_page(
                    viewport={"width": size[0], "height": size[1]}, device_scale_factor=SUPERSAMPLE
                )
                try:
                    await page.goto(page_file.as_uri(), wait_until="load")
                    raw = work / f"{out.stem}@2x.jpg"  # JPEG at 2×: far faster to encode, lossless enough
                    await page.screenshot(path=str(raw), type="jpeg", quality=95)
                finally:
                    await page.close()
                with Image.open(raw) as im:
                    im.convert("RGB").resize(size, Image.Resampling.LANCZOS).save(out)
        finally:
            await browser.close()


# ---- photo mode -------------------------------------------------------------------------------------------


def find_blank_quad(photo: Image.Image, *, aspect: float = 1.0) -> list[tuple[float, float]] | None:
    """Corners (tl, tr, br, bl, full-size pixels) of the largest near-white region when it is clearly a
    quadrilateral of about the expected aspect; None when unsure (the caller then uses the CSS scene)."""
    scale = 480 / max(photo.size)
    small = photo.convert("RGB").resize(
        (max(1, round(photo.width * scale)), max(1, round(photo.height * scale))), Image.Resampling.BILINEAR
    )
    px = np.asarray(small, dtype=np.int16)
    lo, hi = px.min(axis=2), px.max(axis=2)
    white = (lo > max(170.0, float(np.percentile(hi, 99.5)) * 0.8)) & ((hi - lo) < 22)
    cleaned = Image.fromarray(white.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))
    comp = _largest_component(np.asarray(cleaned.filter(ImageFilter.MaxFilter(3))) > 0)
    if comp is None:
        return None
    ys, xs = comp
    if len(xs) < 0.04 * white.size:
        return None
    s, d = xs + ys, xs - ys
    picks = (np.argmin(s), np.argmax(d), np.argmax(s), np.argmin(d))  # tl, tr, br, bl
    quad = [(float(xs[i]), float(ys[i])) for i in picks]
    area = 0.5 * abs(sum(quad[i][0] * quad[i - 3][1] - quad[i - 3][0] * quad[i][1] for i in range(4)))
    sides = [math.dist(quad[i], quad[(i + 1) % 4]) for i in range(4)]
    if area <= 0 or not 0.9 <= len(xs) / area <= 1.08 or min(sides) < 0.12 * min(small.size):
        return None
    ratio = ((sides[0] + sides[2]) / 2) / ((sides[1] + sides[3]) / 2)
    if not 0.65 * aspect <= ratio <= 1.5 * aspect:
        return None
    return [((x + 0.5) / scale, (y + 0.5) / scale) for x, y in quad]


def _largest_component(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """(ys, xs) of the largest 4-connected True region (breadth-first; the mask is small)."""
    h, w = mask.shape
    flat = mask.ravel()
    seen = np.zeros(flat.shape, dtype=bool)
    best: list[int] = []
    for start in np.flatnonzero(flat):
        if seen[start]:
            continue
        seen[start] = True
        queue, members = deque([int(start)]), [int(start)]
        while queue:
            i = queue.popleft()
            y, x = divmod(i, w)
            for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1), (i - w, y > 0), (i + w, y < h - 1)):
                if ok and flat[j] and not seen[j]:
                    seen[j] = True
                    queue.append(j)
                    members.append(j)
        if len(members) > len(best):
            best = members
    if not best:
        return None
    ys, xs = np.divmod(np.asarray(best), w)
    return ys, xs


def _perspective_coeffs(
    dst: Sequence[tuple[float, float]], src: Sequence[tuple[float, float]]
) -> list[float]:
    """PIL PERSPECTIVE coefficients mapping output pixels (dst quad) back to input pixels (src quad)."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        rows += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        rhs += [u, v]
    sol = np.linalg.solve(np.asarray(rows, dtype=np.float64), np.asarray(rhs, dtype=np.float64))
    return [float(c) for c in sol]


def photo_mockup(
    photo_path: Path, art: Image.Image, size: tuple[int, int], out: Path, *, mirror: bool = False
) -> Path | None:
    """Warp `art` onto the photo's blank cover (or blank pages) under the photo's own shading; None when the
    blank area is not found with confidence. `mirror` flips the photo first: the product photos show an
    Arabic book (spine on the right), so an English book uses their mirror image."""
    with Image.open(photo_path) as raw:
        photo = ImageOps.mirror(raw.convert("RGB")) if mirror else raw.convert("RGB")
    quad = find_blank_quad(photo, aspect=art.width / art.height)
    if quad is None:
        return None
    cx, cy = sum(p[0] for p in quad) / 4, sum(p[1] for p in quad) / 4
    quad = [(x + (x - cx) * 0.004, y + (y - cy) * 0.004) for x, y in quad]  # cover the white fringe
    src = [
        (0.0, 0.0),
        (float(art.width), 0.0),
        (float(art.width), float(art.height)),
        (0.0, float(art.height)),
    ]
    warped = art.convert("RGB").transform(
        photo.size, Image.Transform.PERSPECTIVE, _perspective_coeffs(quad, src), Image.Resampling.BICUBIC
    )
    ss = 4  # antialiased mask: draw at 4× and downsample
    big = Image.new("L", (photo.width * ss, photo.height * ss), 0)
    ImageDraw.Draw(big).polygon([(x * ss, y * ss) for x, y in quad], fill=255)
    mask = big.resize(photo.size, Image.Resampling.LANCZOS)
    lum = np.asarray(photo.convert("L"), dtype=np.float32)
    inside = np.asarray(mask) > 128
    white = float(np.percentile(lum[inside], 97)) if inside.any() else 255.0
    shading = np.clip(lum / max(white, 1.0), 0.0, 1.06)[..., None]
    shaded = np.clip(np.asarray(warped, dtype=np.float32) * (0.25 + 0.75 * shading), 0, 255).astype(np.uint8)
    comp = Image.composite(Image.fromarray(shaded), photo, mask)
    ratio = size[0] / size[1]
    if comp.width / comp.height > ratio:
        nw = round(comp.height * ratio)
        comp = comp.crop(((comp.width - nw) // 2, 0, (comp.width - nw) // 2 + nw, comp.height))
    else:
        nh = round(comp.width / ratio)
        comp = comp.crop((0, (comp.height - nh) // 2, comp.width, (comp.height - nh) // 2 + nh))
    comp.resize(size, Image.Resampling.LANCZOS).save(out)
    return out


def _photo(photos: Path | None, which: str) -> Path | None:
    if photos is None:
        return None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = photos / f"{PHOTO_NAMES[which]}{ext}"
        if p.is_file():
            return p
    return None


# ---- entry points -----------------------------------------------------------------------------------------


async def render_mockups(art: BookArt, out_dir: Path, *, photos: Path | None = PHOTOS_DIR) -> Mockups:
    """`hardcover.png` and (with two facing pages) `spread.png` in `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    modes: dict[str, str] = {}
    hard_out, spread_out = out_dir / "hardcover.png", out_dir / "spread.png"
    with tempfile.TemporaryDirectory(prefix="qamra-mockup-") as tmp:
        work = Path(tmp)
        tex = await asyncio.to_thread(_textures, art, work)
        shots: list[tuple[str, tuple[int, int], Path]] = []
        b1 = _photo(photos, "hardcover")
        mirror = spine_side(art.lang) == "left"
        if b1 and await asyncio.to_thread(photo_mockup, b1, art.front, HARDCOVER_PX, hard_out, mirror=mirror):
            modes["hardcover"] = "photo"
        else:
            shots.append((hardcover_html(art, tex), HARDCOVER_PX, hard_out))
            modes["hardcover"] = "css"
        if art.pages is not None:
            left, right = art.pages
            both = Image.new("RGB", (left.width * 2, left.height))
            both.paste(left.convert("RGB"), (0, 0))
            both.paste(right.convert("RGB").resize(left.size), (left.width, 0))
            b2 = _photo(photos, "spread")
            if b2 and await asyncio.to_thread(photo_mockup, b2, both, SPREAD_PX, spread_out):
                modes["spread"] = "photo"
            else:
                shots.append((spread_html(art, tex), SPREAD_PX, spread_out))
                modes["spread"] = "css"
        if shots:
            await _shoot(shots, work)
    return Mockups(hard_out, spread_out if art.pages is not None else None, modes)


async def mockups_from_pdfs(
    cover_pdf: Path,
    interior_pdf: Path | None,
    lang: Lang,
    out_dir: Path,
    *,
    spread: tuple[int, int] | None = None,
    photos: Path | None = PHOTOS_DIR,
) -> Mockups:
    """Mockups of a rendered book: front, spine and back from the cover wrap; the open spread from two facing
    interior pages, `spread` = (left, right) physical page numbers, else picked from the PDF."""
    wrap = await asyncio.to_thread(cover_art, cover_pdf, lang)
    pages = None
    if interior_pdf is not None:
        pair = spread or await asyncio.to_thread(pick_spread, interior_pdf, lang)
        if pair is not None:
            left, right = await asyncio.to_thread(page_art, interior_pdf, pair)
            pages = (left, right)
    art = BookArt(
        front=wrap.front,
        lang=lang,
        spine=wrap.spine,
        back=wrap.back,
        pages=pages,
        thickness_mm=max(wrap.spine_mm, MIN_THICKNESS_MM),
    )
    return await render_mockups(art, out_dir, photos=photos)
