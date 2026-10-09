"""Retouch the AI-made site photos so they show our real products and stop looking machine-made.

    uv run python scripts/retouch_site_photos.py            # all → apps/web/public/photos/<name>.jpg
    uv run python scripts/retouch_site_photos.py --only hero-reading --out /tmp/x

The fal photos (scripts/design_images.py, 2026-10-03) were drawn with blank books: their pages and covers
were blurred smears, the phone screen empty. That is the strongest "AI placeholder" tell in the set, and it
hides the very thing we sell. This script lays our real art onto those surfaces, lit by the photo itself:

- hero-reading: the front of «يوم تخرّج ليان» + a navy back cover with the Qamra mark;
- family-book-table: two real pages of «مغامراتي مع عائلتي» (عائلتي, صيد الدوائر);
- journey-qr: two real pages of «رحلتي الأولى للتعلّم» (the maze and the audio-QR page) + an audio player on
  the father's phone;
- kindergarten-teacher: the class-on-stage spread of «يوم تخرّج ليان»;
- gift-box: the front of «يوم تخرّج ليان» in the gift box;
- books-stack: three workbooks fanned out (دوسية التأسيس, رحلتي الأولى للتعلّم, مغامرات مع عائلتي) on a newer
  photo (2026-10-09, no people), mirrored so the wire binding sits on the right as on our Arabic books.

Each surface is a grid of homographies (art → photo quad); the photo's own light on the blank paper is fitted
with a smooth polynomial (linear light) and multiplied in; hands, crayons and tissue lying over the book are
masked out by polygons traced on the photo (px of the 2400/2048 px originals). Then every photo (retouched or
not) gets one fine film grain, which breaks the over-smooth "AI sheen" and makes the set consistent.

Inputs: the untouched originals (--originals; restore them with
`git show 244d81f:apps/web/public/photos/<name>.jpg`; books-stack.jpg is the fal photo
out/design-images/samples/books-stack-2.png saved as JPEG; graduation-class.jpg has its thrown caps redrawn
by a fal edit on 2026-10-09, blended in only where the caps are, the older file kept as
graduation-class-2026-10-03.jpg), the film's cover art in out/video/ (scripts/build_film.py) and the public
workbook previews. No paid API.
"""

from __future__ import annotations

import argparse
import io
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import numpy.typing as npt
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT / "apps/web/public/photos"
WORKBOOKS = ROOT / "apps/web/public/workbooks"
FILM = ROOT / "out/video"
FONTS = ROOT / "packages/pdf/src/qamra_pdf/fonts"
NAMES = [
    "hero-reading",
    "first-day",
    "graduation-class",
    "family-book-table",
    "workbook-tracing",
    "journey-qr",
    "grandma-voice",
    "gift-box",
    "books-stack",
    "kindergarten-teacher",
]
MAX_BYTES = 1_000_000  # public/photos/README.md: under 1 MB each

Img = npt.NDArray[np.float32]
Pt = tuple[float, float]
Poly = list[Pt]


# ---------------------------------------------------------------------------------------------- pixels


def load(path: Path) -> Img:
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0


def to_pil(img: Img) -> Image.Image:
    return Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8))


def lin(x: Img) -> Img:
    x = np.clip(x, 0, None)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def srgb(x: Img) -> Img:
    x = np.clip(x, 0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


def poly_mask(shape: tuple[int, int], polys: list[Poly]) -> Img:
    """Anti-aliased coverage (0..1) of polygons given in image px."""
    m = np.zeros(shape, np.uint8)
    for p in polys:
        pts = np.round(np.array(p, np.float64) * 8).astype(np.int32)
        cv2.fillPoly(m, [pts], 255, lineType=cv2.LINE_AA, shift=3)
    return m.astype(np.float32) / 255.0


def feather(m: Img, sigma: float) -> Img:
    return m if sigma <= 0 else np.asarray(cv2.GaussianBlur(m, (0, 0), sigma), np.float32)


def shrink(m: Img, px: float) -> Img:
    if px <= 0:
        return m
    k = int(np.ceil(px)) * 2 + 1
    return np.asarray(cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))), np.float32)


def grain(shape: tuple[int, int], std: float, seed: int, size: float = 0.7, chroma: float = 0.25) -> Img:
    """Gaussian film grain: mostly luminance, a little colour, slightly soft (size = blur sigma)."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, shape).astype(np.float32)
    c = rng.normal(0, 1, (*shape, 3)).astype(np.float32)
    if size > 0:
        n = np.asarray(cv2.GaussianBlur(n, (0, 0), size), np.float32)
        n /= n.std() + 1e-6
        c = np.asarray(cv2.GaussianBlur(c, (0, 0), size), np.float32)
        c /= c.std() + 1e-6
    return ((n[..., None] * (1 - chroma) + c * chroma) * std).astype(np.float32)


# ---------------------------------------------------------------------------------------------- warping


def quad_grid(tl: Pt, tr: Pt, br: Pt, bl: Pt, rows: int = 2, cols: int = 2) -> npt.NDArray[np.float64]:
    """A rows×cols grid of points inside a quad (bilinear), corners in the art's TL, TR, BR, BL order."""
    g = np.zeros((rows + 1, cols + 1, 2), np.float64)
    q = [np.array(p, np.float64) for p in (tl, tr, br, bl)]
    for r in range(rows + 1):
        t = r / rows
        for c in range(cols + 1):
            s = c / cols
            top = q[0] * (1 - s) + q[1] * s
            bot = q[3] * (1 - s) + q[2] * s
            g[r, c] = top * (1 - t) + bot * t
    return g


def prescale(art: Img, grid: npt.NDArray[np.float64], factor: float = 1.5) -> Img:
    """Area-downscale the art per axis to ~factor × its size in the photo (so the warp can't alias)."""

    def length(pts: npt.NDArray[np.float64]) -> float:
        return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))

    w_on = max(length(grid[0]), length(grid[-1]))
    h_on = max(length(grid[:, 0]), length(grid[:, -1]))
    ah, aw = art.shape[:2]
    tw, th = min(aw, max(8, round(w_on * factor))), min(ah, max(8, round(h_on * factor)))
    if (tw, th) == (aw, ah):
        return art
    return np.asarray(cv2.resize(art, (tw, th), interpolation=cv2.INTER_AREA), np.float32)


def grid_warp(art: Img, grid: npt.NDArray[np.float64], shape: tuple[int, int]) -> tuple[Img, Img]:
    """Warp the art cell by cell onto the grid; returns (warped art, coverage)."""
    rows, cols = grid.shape[0] - 1, grid.shape[1] - 1
    h, w = shape
    ah, aw = art.shape[:2]
    out = np.zeros((h, w, 3), np.float32)
    cov = np.zeros((h, w), np.float32)
    for r in range(rows):
        for c in range(cols):
            x0, x1, y0, y1 = aw * c / cols, aw * (c + 1) / cols, ah * r / rows, ah * (r + 1) / rows
            src = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)
            dst = np.array([grid[r, c], grid[r, c + 1], grid[r + 1, c + 1], grid[r + 1, c]], np.float32)
            m = cv2.getPerspectiveTransform(src, dst)
            wa = cv2.warpPerspective(art, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            cm = poly_mask((h, w), [[(float(x), float(y)) for x, y in dst]])
            take = cm > cov
            out[take] = wa[take]
            cov = np.maximum(cov, cm)
    return out, cov


def fit_light(img: Img, sample: npt.NDArray[np.bool_]) -> Img:
    """The photo's light on the blank paper: a plane per channel (linear light), fitted on `sample`."""
    h, w = sample.shape
    ys, xs = np.nonzero(sample)
    if len(xs) > 40000:
        idx = np.random.default_rng(1).choice(len(xs), 40000, replace=False)
        ys, xs = ys[idx], xs[idx]
    sc = max(w, h) / 2

    def basis(x: npt.NDArray[Any], y: npt.NDArray[Any]) -> npt.NDArray[np.float64]:
        return np.stack([np.ones_like(x), (x - w / 2) / sc, (y - h / 2) / sc], -1).astype(np.float64)

    a = basis(xs.astype(np.float64), ys.astype(np.float64))
    lum = lin(img[ys, xs]).astype(np.float64)
    keep = np.ones(len(xs), bool)
    coef = np.zeros((3, 3))
    for _ in range(4):  # drop outliers (the blurred blobs, stray objects) and refit
        coef = np.linalg.lstsq(a[keep], lum[keep], rcond=None)[0]
        res = np.abs(a @ coef - lum).mean(-1)
        keep = res < np.percentile(res[keep], 80) * 2.2 + 1e-4
    yy, xx = np.mgrid[0:h, 0:w]
    return np.clip(basis(xx.astype(np.float64), yy.astype(np.float64)) @ coef, 1e-4, None).astype(np.float32)


def lay(
    img: Img,
    art: Img,
    grid: npt.NDArray[np.float64],
    *,
    reflect: tuple[float, float, float],
    occluders: list[Poly] | None = None,
    exclude: list[Poly] | None = None,
    light: Img | None = None,
    blur: float = 0.8,
    edge_inset: float = 1.2,
    sat: float = 0.9,
    haze: float = 0.04,
    seed: int = 3,
    grain_std: float = 0.004,
) -> tuple[Img, Img]:
    """Lay `art` on the blank surface `grid` of `img` (paper of reflectance `reflect`), lit like the photo."""
    h, w = img.shape[:2]
    warped, cov = grid_warp(prescale(art, grid), grid, (h, w))
    if light is None:
        sample = shrink(cov, 4) > 0.99
        for polys in (exclude, occluders):
            if polys:
                sample &= poly_mask((h, w), polys) < 0.5
        light = fit_light(img, sample)
    g = warped.mean(-1, keepdims=True)
    warped = np.clip(g + (warped - g) * sat, 0, 1)  # a matte print is a little less saturated than the screen
    refl = lin(np.array(reflect, np.float32))
    lum = lin(warped) * (1 - haze) + refl * haze * 0.35  # ambient light lifts the blacks a little
    rend = srgb(lum * light / refl)
    if blur > 0:
        rend = np.asarray(cv2.GaussianBlur(rend, (0, 0), blur), np.float32)
    rend = rend + grain((h, w), grain_std, seed=seed)
    m = feather(shrink(cov, edge_inset), 0.6)
    if occluders:
        m = m * (1 - feather(poly_mask((h, w), occluders), 1.2))
    m3 = np.clip(m, 0, 1)[..., None]
    return (img * (1 - m3) + np.clip(rend, 0, 1) * m3).astype(np.float32), m


def gutter(art: Img, side: str, width: float = 0.10, depth: float = 0.28) -> Img:
    """Shade a page half toward its binding (`side` is where the binding is)."""
    w = art.shape[1]
    x = np.arange(w, dtype=np.float32) / w
    d = x if side == "left" else 1 - x
    shade = 1 - depth * np.exp(-((d / width) ** 2) * 2.2) - 0.06 * np.exp(-((d / (width * 0.25)) ** 2))
    out: Img = np.clip(art * shade[None, :, None], 0, 1).astype(np.float32)
    return out


# ---------------------------------------------------------------------------------------------- art


def hinge(im: Image.Image, side: str) -> Image.Image:
    """The groove of a hardcover next to its spine (a dark line and a soft highlight)."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    w = a.shape[1]
    x = np.arange(w, dtype=np.float32)
    d = (w - 1 - x) if side == "right" else x
    g = 0.045 * w
    shade = 1 - 0.30 * np.exp(-(((d - g) / (0.010 * w)) ** 2)) - 0.18 * np.exp(-((d / (0.012 * w)) ** 2))
    shade += 0.06 * np.exp(-(((d - g * 1.45) / (0.012 * w)) ** 2))
    return Image.fromarray(np.clip(a * shade[None, :, None], 0, 255).astype(np.uint8))


def front_cover() -> Img:
    """The front of «يوم تخرّج ليان» (the film's lettered cover), spine on the right."""
    return load_pil(hinge(Image.open(FILM / "front-lettered.png"), "right"))


def back_cover() -> Img:
    """A back cover: the night sky of the same scene (no child) fading into navy, the Qamra mark below."""
    src = Image.open(FILM / "cover-nohijab.png").convert("RGB")
    size = 1500
    sky_h = int(size * 0.42 * src.height / src.width)
    sky = src.crop((0, 0, src.width, int(src.height * 0.42))).resize((size, sky_h), Image.Resampling.LANCZOS)
    back = Image.new("RGB", (size, size), (22, 32, 74))
    back.paste(sky.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (0, 0))
    a = np.asarray(back).astype(np.float32)
    y = np.arange(size, dtype=np.float32)[:, None]
    t = np.clip((y - sky_h * 0.40) / (sky_h * 0.62), 0, 1)[..., None]
    t = t * t * (3 - 2 * t)
    k = np.clip((y - size * 0.5) / (size * 0.5), 0, 1)[..., None]
    grad = np.array([22, 32, 74], np.float32) * (1 - k) + np.array([14, 21, 48], np.float32) * k
    back = Image.fromarray(np.clip(a * (1 - t) + grad * t, 0, 255).astype(np.uint8))
    cx, cy, r = size // 2, int(size * 0.80), 70
    moon = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(moon)
    md.ellipse((cx - r, cy - r - 60, cx + r, cy + r - 60), fill=255)
    md.ellipse((cx - r + 42, cy - r - 86, cx + r + 42, cy + r - 86), fill=0)
    back.paste(
        Image.new("RGB", (size, size), (242, 179, 61)), (0, 0), moon.filter(ImageFilter.GaussianBlur(0.8))
    )
    d = ImageDraw.Draw(back)
    word = ImageFont.truetype(str(FONTS / "BalooBhaijaan2-ExtraBold.ttf"), 110)
    d.text(
        (cx, cy + 95), "قمرة", font=word, fill=(255, 253, 248), anchor="mm", direction="rtl", language="ar"
    )
    domain = ImageFont.truetype(str(FONTS / "IBMPlexSansArabic-SemiBold.ttf"), 44)
    d.text((cx, cy + 190), "qamra.app", font=domain, fill=(245, 196, 101), anchor="mm")
    return load_pil(hinge(back, "left"))


def phone_player() -> Img:
    """The audio player a parent sees after scanning a page's QR (portrait phone screen, brand colours)."""
    w, h = 600, 1300
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        top, bottom = (34, 48, 106), (14, 21, 48)
        d.line(
            [(0, y), (w, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(top, bottom, strict=True))
        )
    cover = Image.open(WORKBOOKS / "learning-journey/1/cover.webp").convert("RGB")
    im.paste(cover.resize((300, 424), Image.Resampling.LANCZOS), (150, 170))
    d.rounded_rectangle((150, 170, 450, 594), radius=18, outline=(255, 253, 248), width=4)
    title = ImageFont.truetype(str(FONTS / "BalooBhaijaan2-ExtraBold.ttf"), 46)
    label = ImageFont.truetype(str(FONTS / "IBMPlexSansArabic-SemiBold.ttf"), 30)
    d.text((w / 2, 665), "مَن يُصدِر هذا الصوت؟", font=title, fill=(255, 253, 248), anchor="mm", direction="rtl")
    d.text(
        (w / 2, 725), "رحلتي الأولى للتعلّم", font=label, fill=(245, 196, 101), anchor="mm", direction="rtl"
    )
    d.rounded_rectangle((70, 800, 530, 812), radius=6, fill=(58, 72, 130))
    d.rounded_rectangle((300, 800, 530, 812), radius=6, fill=(242, 179, 61))
    d.ellipse((288, 794, 312, 818), fill=(255, 253, 248))
    cx, cy, r = w / 2, 960, 92
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(242, 179, 61))
    d.polygon([(cx - 30, cy - 44), (cx - 30, cy + 44), (cx + 46, cy)], fill=(14, 21, 48))
    rnd = random.Random(4)
    for i in range(23):
        bar = rnd.randint(16, 90)
        x = 80 + i * 19.5
        d.rounded_rectangle((x, 1140 - bar / 2, x + 9, 1140 + bar / 2), radius=4, fill=(245, 196, 101))
    return load_pil(im)


def load_pil(im: Image.Image) -> Img:
    return np.asarray(im.convert("RGB")).astype(np.float32) / 255.0


# ---------------------------------------------------------------------------------------------- photos

KNEE: Poly = [
    (1095, 1300),
    (1100, 1236),
    (1112, 1223),
    (1150, 1213),
    (1201, 1208),
    (1240, 1214),
    (1280, 1227),
    (1320, 1230),
    (1357, 1230),
    (1362, 1240),
    (1380, 1300),
]


def hero_reading(img: Img) -> Img:
    """The girl reads «يوم تخرّج ليان»: its front faces the camera, the back cover is the right panel."""
    paper = (0.86, 0.80, 0.70)
    fingers: Poly = [
        (958, 1086),
        (972, 1087),
        (985, 1093),
        (994, 1102),
        (1002, 1115),
        (1011, 1124),
        (1014, 1136),
        (1011, 1147),
        (1001, 1151),
        (985, 1155),
        (972, 1160),
        (958, 1160),
    ]
    img, _ = lay(
        img,
        front_cover(),
        quad_grid((972, 927), (1396, 1020), (1352, 1270), (972, 1186)),
        reflect=paper,
        occluders=[fingers, KNEE],
        exclude=[[(995, 960), (1335, 990), (1335, 1215), (995, 1205)]],
        blur=0.75,
        edge_inset=1.0,
        sat=0.86,
        haze=0.06,
    )
    fingers_r: Poly = [
        (1706, 1038),
        (1691, 1057),
        (1677, 1083),
        (1661, 1091),
        (1652, 1108),
        (1655, 1119),
        (1674, 1123),
        (1689, 1131),
        (1716, 1131),
        (1716, 1038),
    ]
    img, _ = lay(
        img,
        back_cover(),
        quad_grid((1401, 1019), (1750, 898), (1667, 1154), (1361, 1231)),
        reflect=paper,
        occluders=[fingers_r, KNEE],
        blur=0.75,
        edge_inset=1.0,
        sat=0.86,
        haze=0.06,
        seed=5,
    )
    return img


def family_book_table(img: Img) -> Img:
    """The spread on the table: «صيد الدوائر» on the left, «عائلتي» (being coloured) on the right."""
    paper = (0.93, 0.91, 0.87)
    book = WORKBOOKS / "family-adventures/book"
    crayon: Poly = [
        (1260, 1144),
        (1290, 1149),
        (1307, 1160),
        (1324, 1176),
        (1324, 1184),
        (1313, 1185),
        (1295, 1173),
        (1277, 1164),
        (1262, 1155),
    ]
    fingers: Poly = [
        (1488, 1128),
        (1500, 1146),
        (1514, 1163),
        (1532, 1161),
        (1562, 1168),
        (1588, 1175),
        (1605, 1150),
        (1605, 1120),
    ]
    img, _ = lay(
        img,
        load(book / "03.webp"),
        quad_grid((836, 1175), (1146, 1152), (1295, 1289), (871, 1335)),
        reflect=paper,
        exclude=[[(885, 1183), (1150, 1162), (1200, 1270), (905, 1300)]],
        blur=0.9,
        edge_inset=1.5,
        haze=0.03,
    )
    img, _ = lay(
        img,
        load(book / "02.webp"),
        quad_grid((1199, 1151), (1480, 1140), (1689, 1274), (1337, 1289)),
        reflect=paper,
        occluders=[crayon, fingers],
        exclude=[[(1280, 1158), (1530, 1150), (1580, 1262), (1330, 1272)]],
        blur=0.9,
        edge_inset=1.5,
        haze=0.03,
        seed=9,
    )
    return img


def journey_qr(img: Img) -> Img:
    """The maze page and the audio-QR page of «رحلتي الأولى للتعلّم»; the father's phone plays the sound."""
    h, w = img.shape[:2]
    paper = (0.93, 0.92, 0.90)
    stage = WORKBOOKS / "learning-journey/1"
    girl: Poly = [(720, 1080), (840, 1080), (846, 1128), (822, 1150), (790, 1153), (720, 1150)]
    img, _ = lay(
        img,
        load(stage / "03.webp"),
        quad_grid((864, 1111), (1131, 1142), (877, 1321), (538, 1277)),
        reflect=paper,
        occluders=[girl],
        exclude=[[(760, 1128), (1100, 1150), (890, 1300), (600, 1268)]],
        edge_inset=1.5,
        haze=0.03,
    )
    img, _ = lay(
        img,
        load(stage / "04.webp"),
        quad_grid((1172, 1148), (1488, 1198), (1352, 1445), (917, 1331)),
        reflect=paper,
        exclude=[[(1175, 1205), (1350, 1232), (1295, 1328), (1105, 1295)]],
        edge_inset=1.5,
        haze=0.03,
        seed=11,
    )
    # the screen glows on its own (no scene light); it faces the father, so we see it upside down
    pts = np.array([(1247, 1100), (1112, 1077), (1229, 1022), (1334, 1040)], np.float64)
    c = pts.mean(0)
    pts = c + (pts - c) * (1 + 3.0 / np.linalg.norm(pts - c, axis=1))[:, None]
    corners = [(float(x), float(y)) for x, y in pts]
    thumb: Poly = [
        (1294, 1074),
        (1302, 1060),
        (1318, 1051),
        (1337, 1039),
        (1352, 1039),
        (1352, 1092),
        (1296, 1092),
    ]
    glass = (0.9, 0.9, 0.9)
    flat = np.ones((h, w, 3), np.float32) * lin(np.array(glass, np.float32)) * 0.80
    img, m = lay(
        img,
        phone_player(),
        quad_grid(corners[0], corners[1], corners[2], corners[3], rows=1, cols=1),
        reflect=glass,
        occluders=[thumb],
        light=flat,
        blur=0.7,
        edge_inset=0.6,
        sat=0.85,
        haze=0.10,
        seed=13,
        grain_std=0.003,
    )
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sheen = np.clip(1 - np.abs((xx - 1190) * 0.55 + (yy - 1045)) / 70, 0, 1) * 0.22 + 0.05
    out: Img = (img + (m * sheen)[..., None] * (1 - img)).astype(np.float32)
    return out


def kindergarten_teacher(img: Img) -> Img:
    """The teacher shows the class on stage, the spread of «يوم تخرّج ليان»."""
    paper = (0.92, 0.91, 0.90)
    spread = load(FILM / "spread-nohijab.png")
    half = spread.shape[1] // 2
    lhand: Poly = [
        (1146, 777),
        (1151, 766),
        (1164, 761),
        (1178, 753),
        (1188, 748),
        (1203, 746),
        (1212, 751),
        (1216, 758),
        (1219, 770),
        (1222, 778),
        (1235, 798),
        (1235, 806),
        (1146, 806),
    ]
    rhand: Poly = [
        (1319, 709),
        (1314, 723),
        (1313, 734),
        (1317.5, 748),
        (1330, 755.5),
        (1358, 759),
        (1381, 763),
        (1381, 691),
        (1344, 693),
        (1330, 700),
    ]
    img, _ = lay(
        img,
        gutter(spread[:, :half], "right"),
        quad_grid((1015, 597), (1176, 600), (1187, 777), (1018, 782)),
        reflect=paper,
        occluders=[lhand],
        exclude=[[(1040, 615), (1160, 615), (1165, 760), (1040, 765)]],
        blur=1.0,
        sat=0.84,
        haze=0.08,
    )
    img, _ = lay(
        img,
        gutter(spread[:, half:], "left"),
        quad_grid((1178, 599), (1335, 569), (1359, 763), (1188, 777)),
        reflect=paper,
        occluders=[lhand, rhand],
        exclude=[[(1200, 610), (1320, 590), (1335, 745), (1200, 760)]],
        blur=1.0,
        sat=0.84,
        haze=0.08,
        seed=17,
    )
    return img


def gift_box(img: Img) -> Img:
    """«يوم تخرّج ليان» in the gift box (the card and a fold of tissue lie over its corners)."""
    tissue: Poly = [(690, 1140), (712, 1149), (722, 1147), (733, 1144), (731, 1160), (712, 1170), (690, 1170)]
    card: Poly = [(1290, 1060), (1480, 1060), (1480, 1290), (1382, 1240), (1300, 1132)]
    img, _ = lay(
        img,
        front_cover(),
        quad_grid((725, 1153), (1154, 1031), (1427, 1300), (930, 1468)),
        reflect=(0.88, 0.84, 0.76),
        occluders=[tissue, card],
        blur=0.7,
        edge_inset=2.0,
        haze=0.05,
    )
    return img


def _unit(v: npt.ArrayLike) -> npt.NDArray[np.float64]:
    a = np.asarray(v, np.float64)
    out: npt.NDArray[np.float64] = a / np.linalg.norm(a)
    return out


# A wire-bound workbook lying cover up, traced on the mirrored photo: L, T, R, B are its cover's top-left,
# top-right, bottom-right and bottom-left corners (the wire runs along T-R, the right edge, as on our books).
Book = dict[str, Pt]


def _rear_book(front: Book, t: Pt, r: Pt, on_top_edge: Pt) -> Book:
    """A book half hidden under another: its binding (T-R) is seen whole and its top edge runs through
    `on_top_edge`; the hidden corners follow the front book's shape (an affine map of it)."""
    scale = float(np.linalg.norm(np.subtract(r, t)) / np.linalg.norm(np.subtract(front["R"], front["T"])))
    width = float(np.linalg.norm(np.subtract(front["L"], front["T"])))
    left = np.asarray(t, np.float64) + _unit(np.subtract(on_top_edge, t)) * width * scale
    src = np.array([front["T"], front["R"], front["L"]], np.float32)
    dst = np.array([t, r, (float(left[0]), float(left[1]))], np.float32)
    m = np.asarray(cv2.getAffineTransform(src, dst), np.float64)
    b = m @ np.array([*front["B"], 1.0])
    return {"L": (float(left[0]), float(left[1])), "T": t, "R": r, "B": (float(b[0]), float(b[1]))}


def _wire_side(book: Book) -> npt.NDArray[np.float64]:
    """The outward normal of the binding edge."""
    d = _unit(np.subtract(book["R"], book["T"]))
    return np.array([d[1], -d[0]])


def _under_wire(book: Book, px: float) -> Book:
    """The traced cover stops where the wire starts; the cover itself runs on under it to the binding edge."""
    n = _wire_side(book) * px
    t, r = np.asarray(book["T"]) + n, np.asarray(book["R"]) + n
    return {**book, "T": (float(t[0]), float(t[1])), "R": (float(r[0]), float(r[1]))}


def _book_body(book: Book) -> list[Poly]:
    """What of a book lies on the books under it: the cover, the wire beyond the binding edge, the page block
    under the lower edges and a hair along the top edge (bands of 34, 44, 30 and 6 px)."""
    pts = [np.asarray(book[k], np.float64) for k in ("L", "T", "R", "B")]
    c = np.mean(pts, axis=0)
    polys: list[Poly] = [[(float(p[0]), float(p[1])) for p in pts]]
    for i, margin in enumerate((6, 34, 44, 30)):  # edges L-T, T-R, R-B, B-L
        a, b = pts[i], pts[(i + 1) % 4]
        d = _unit(b - a)
        n = np.array([d[1], -d[0]])
        if np.dot(n, (a + b) / 2 - c) < 0:
            n = -n
        band = [a, b, b + n * margin, a + n * margin]
        polys.append([(float(p[0]), float(p[1])) for p in band])
    return polys


def _a4(art: Img) -> Img:
    """A 21 × 28 cover on an A4 book: the middle strip at A4 proportions."""
    h, w = art.shape[:2]
    keep = min(w, round(h / 2**0.5))
    x0 = (w - keep) // 2
    return art[:, x0 : x0 + keep]


def books_stack(img: Img) -> Img:
    """Three of our wire-bound workbooks fanned out on the table, the binding on the right (Arabic books).

    The 2026-10-09 photo (fal, `samples:books-stack` in the ledger) has the wire on the left, so it is
    mirrored first. The covers are the site's current ones (public/workbooks/*/cover.webp): run this again
    when the covers change. A book underneath gets its cover only where the photo shows blank paper, and the
    wire of every book is kept from the photo.
    """
    img = np.ascontiguousarray(img[:, ::-1])
    photo = img.copy()
    front: Book = {"L": (244, 1477), "T": (773, 1313), "R": (1297, 1576), "B": (765, 1852)}
    middle = _rear_book(front, (1087, 1228), (1530, 1525), on_top_edge=(829, 1299))
    back = _rear_book(front, (1435, 1200), (1774, 1524), on_top_edge=(1150, 1236))
    books = [
        (_under_wire(back, 14), _a4(load(WORKBOOKS / "family-adventures/book/cover.webp"))),
        (_under_wire(middle, 14), load(WORKBOOKS / "learning-journey/1/cover.webp")),
        (_under_wire(front, 14), load(WORKBOOKS / "foundation-workbook/kg2-1/cover.webp")),
    ]
    hsv = cv2.cvtColor((photo * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    white = ((hsv[..., 2] > 185) & (hsv[..., 1] < 45)).astype(np.uint8)
    blank = cv2.morphologyEx(white, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    paper = feather(np.asarray(cv2.dilate(blank, np.ones((5, 5), np.uint8)), np.float32), 1.0)[..., None]
    for i, (book, art) in enumerate(books):
        lying_on = [p for above, _ in books[i + 1 :] for p in _book_body(above)]
        before = img
        img, _ = lay(
            img,
            art,
            quad_grid(book["L"], book["T"], book["R"], book["B"], rows=4, cols=4),
            reflect=(0.93, 0.93, 0.93),
            occluders=lying_on or None,
            blur=0.8,
            sat=0.92,
            haze=0.03,
            seed=21 + i,
        )
        if lying_on:
            img = (before + (img - before) * paper).astype(np.float32)
    # the wire: wherever the photo is darker than its paper along a binding edge
    lum = photo.mean(-1)
    around = np.asarray(cv2.GaussianBlur(lum, (0, 0), 25), np.float32)
    wire = np.zeros(lum.shape, np.float32)
    for book, _ in books:
        n = _wire_side(book)
        t, r = np.asarray(book["T"]), np.asarray(book["R"])
        band = [tuple(t - n * 40), tuple(r - n * 40), tuple(r + n * 8), tuple(t + n * 8)]
        strip = poly_mask(lum.shape, [[(float(x), float(y)) for x, y in band]])
        wire = np.maximum(wire, strip * np.clip((around - lum - 0.03) / 0.06, 0, 1))
    w3 = feather(wire, 0.7)[..., None]
    out: Img = (img * (1 - w3) + photo * w3).astype(np.float32)
    return out


RETOUCH = {
    "hero-reading": hero_reading,
    "family-book-table": family_book_table,
    "journey-qr": journey_qr,
    "kindergarten-teacher": kindergarten_teacher,
    "gift-box": gift_box,
    "books-stack": books_stack,
}


def film_grain(img: Img, seed: int) -> Img:
    """One fine grain over the whole photo, weaker in deep shadows and highlights (as on film)."""
    lum = img.mean(-1, keepdims=True)
    weight = np.clip(4 * lum * (1 - lum), 0.35, 1.0)
    noise = grain(img.shape[:2], 0.0085, seed=seed, size=0.75, chroma=0.18)
    out: Img = np.clip(img + noise * weight, 0, 1).astype(np.float32)
    return out


def save(img: Img, path: Path) -> tuple[int, int]:
    """Progressive JPEG under MAX_BYTES: the best quality that fits."""
    im = to_pil(img)
    buf = io.BytesIO()
    q = 88
    for q in (88, 86, 84, 82, 80):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0 if q >= 86 else 2)
        if buf.tell() <= MAX_BYTES:
            break
    path.write_bytes(buf.getvalue())
    return q, buf.tell()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--originals", default=str(ROOT / "out/design-audit/originals/site-photos"))
    parser.add_argument("--out", default=str(PHOTOS))
    parser.add_argument("--only", action="append", default=[], help="photo name (repeatable)")
    args = parser.parse_args()
    originals, out = Path(args.originals), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(NAMES):
        if args.only and name not in args.only:
            continue
        src = originals / f"{name}.jpg"
        if not src.exists():
            raise SystemExit(f"{src} is missing (git show 244d81f:apps/web/public/photos/{name}.jpg > {src})")
        img = load(src)
        if name in RETOUCH:
            img = RETOUCH[name](img)
        q, size = save(film_grain(img, seed=100 + i), out / f"{name}.jpg")
        print(
            f"  {out / name}.jpg  {'retouched' if name in RETOUCH else 'grain only'}  q{q}  {size // 1024} KB"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
