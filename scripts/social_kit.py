"""Qamra social-media kit: HTML/CSS templates rendered to PNG with Playwright (Chromium).

    uv run python scripts/social_kit.py                     # all → out/social/<name>.png + contact sheet
    uv run python scripts/social_kit.py --only ad-a-launch  # one design (repeatable; prefix match)
    uv run python scripts/social_kit.py --incoming DIR      # look for delivered photos in DIR
    uv run python scripts/social_kit.py --videos            # also cut the reels and ad videos (with sound)
    uv run python scripts/social_kit.py --package           # collect everything into out/social/package/

Everything lives in content/marketing/social/: copy.yaml (all words), captions.yaml (post captions),
images.yaml (photo/mockup slots and the `media:` registry), templates/ (Jinja2), ads.md and calendar.md (Meta
ads and the posting plan). Art is drawn in code; the bitmaps are pages and photos already public on the site
(apps/web/public/**), the theme plates and cast sheets (content/), the brand film's stills and mockups
(out/video/, made by scripts/build_film.py) and, once Tareq delivers them, files in design/incoming/. Every
video gets the brand soundtrack (scripts/film_audio.py): a voice version and a music-only one (*-music.mp4).
After each render a layout check (templates/qa.js) reports text that leaves its box or the
safe zone, headline lines that wrap, and paragraphs that end with a lone word.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import film_audio
import yaml
from jinja2 import Environment, FileSystemLoader, Undefined
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "content/marketing/social"
OUT = ROOT / "out/social"
FONTS = ROOT / "packages/pdf/src/qamra_pdf/fonts"
PUBLIC = ROOT / "apps/web/public"

AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


@dataclass
class Design:
    name: str
    template: str
    width: int
    height: int
    group: str
    ctx: dict[str, Any] = field(default_factory=dict)
    # (left, top, right, bottom) in px: every [data-qa] text box must stay inside
    safe: tuple[int, int, int, int] | None = None
    transparent: bool = False  # a video overlay: rendered with an alpha channel


# ---------------------------------------------------------------------------------------------- images


def public(rel: str) -> str:
    """A file URI for an image that is already public on the website (apps/web/public/...). `a|b` lists
    alternatives, the first that exists wins (pages move when a workbook's previews are re-exported)."""
    for alt in rel.split("|"):
        path = PUBLIC / alt
        if path.exists():
            return path.as_uri()
    raise FileNotFoundError(f"public image missing: {PUBLIC / rel.split('|')[0]}")


def homography(src: list[tuple[float, float]], dst: list[tuple[float, float]]) -> list[float]:
    """The 3×3 projective transform (row-major, h33 = 1) that maps four src points onto four dst points."""
    a: list[list[float]] = []
    b: list[float] = []
    for (x, y), (u, v) in zip(src, dst, strict=True):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)
    n = 8
    m = [[*row, b[i]] for i, row in enumerate(a)]
    for col in range(n):  # Gauss-Jordan with partial pivoting
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        for r in range(n):
            if r != col and m[col][col]:
                f = m[r][col] / m[col][col]
                m[r] = [rv - f * cv for rv, cv in zip(m[r], m[col], strict=True)]
    h = [m[i][n] / m[i][i] for i in range(n)]
    return [*h, 1.0]


def matrix3d(w: float, h: float, quad: list[list[float]]) -> str:
    """CSS matrix3d (transform-origin 0 0) that puts a w×h box onto quad = [TL, TR, BR, BL] (image px)."""
    t = homography([(0, 0), (w, 0), (w, h), (0, h)], [(p[0], p[1]) for p in quad])
    a, b, c, d, e, f, g, hh, _ = t
    # CSS matrix3d is column-major 4×4: map (x, y, 0, 1)
    vals = [a, d, 0, g, b, e, 0, hh, 0, 0, 1, 0, c, f, 0, 1]
    return "matrix3d(" + ",".join(f"{v:.10f}" for v in vals) + ")"


class Slots:
    """images.yaml: each slot lists incoming files in priority order; the first usable one wins."""

    def __init__(self, manifest: dict[str, Any], incoming: Path) -> None:
        self.files: dict[str, dict[str, Any]] = manifest.get("files", {})
        self.slots: dict[str, dict[str, Any]] = manifest.get("slots", {})
        self.incoming = incoming
        self.used: dict[str, str] = {}
        self.warnings: list[str] = []

    def get(self, slot: str) -> dict[str, Any] | None:
        spec = self.slots.get(slot)
        if spec is None:
            raise KeyError(f"images.yaml has no slot {slot!r}")
        for fname in spec.get("candidates", []):
            # `public:photos/x.jpg` is a file already public on the site; anything else is in incoming/
            path = PUBLIC / fname[7:] if fname.startswith("public:") else self.incoming / fname
            if not path.exists():
                continue
            meta = dict(self.files.get(fname, {}))
            kind = meta.get("kind", "photo")
            if kind == "mockup" and not meta.get("cover_quad"):
                self.warnings.append(
                    f"{fname} exists but has no cover_quad in images.yaml (its cover is blank): "
                    "code-drawn art kept"
                )
                continue
            with Image.open(path) as im:
                iw, ih = im.size
            info: dict[str, Any] = {
                "file": fname,
                "src": path.resolve().as_uri(),
                "kind": kind,
                "w": iw,
                "h": ih,
                "focus": meta.get("focus", "50% 50%"),
            }
            if kind == "mockup":
                cw, ch = meta.get("cover_size", [600, 600])
                info["cover_w"], info["cover_h"] = cw, ch
                info["cover_transform"] = matrix3d(cw, ch, meta["cover_quad"])
            self.used[slot] = fname
            return info
        return None


class Media:
    """images.yaml `media:`: named bitmaps (site photos, theme plates, the film's stills and mockups)."""

    def __init__(self, manifest: dict[str, Any]) -> None:
        self.items: dict[str, dict[str, Any]] = manifest.get("media", {})
        self.used: set[str] = set()

    def get(self, key: str) -> dict[str, Any]:
        spec = self.items.get(key)
        if spec is None:
            raise KeyError(f"images.yaml has no media {key!r}")
        path = ROOT / spec["src"]
        if not path.exists():
            hint = " (out/video/ is made by scripts/build_film.py)" if spec["src"].startswith("out/") else ""
            raise FileNotFoundError(f"media {key!r} is missing: {path}{hint}")
        self.used.add(key)
        return {"src": path.resolve().as_uri(), "focus": spec.get("focus", "50% 50%"), "path": path}


# ---------------------------------------------------------------------------------------------- sky helpers


def stars(
    seed: int, w: int, h: int, n: int, keep_out: list[tuple[int, int, int, int]] | None = None
) -> list[dict[str, Any]]:
    """Deterministic star field: small dots plus a few four-point sparkles, away from the keep-out boxes."""
    rnd = random.Random(seed)
    out: list[dict[str, Any]] = []
    tries = 0
    while len(out) < n and tries < n * 40:
        tries += 1
        x, y = rnd.uniform(28, w - 28), rnd.uniform(28, h - 28)  # never cut by the canvas edge
        if keep_out and any(
            x0 - 24 <= x <= x1 + 24 and y0 - 24 <= y <= y1 + 24 for x0, y0, x1, y1 in keep_out
        ):
            continue
        if any((x - s["x"]) ** 2 + (y - s["y"]) ** 2 < 70**2 for s in out):
            continue
        sparkle = rnd.random() < 0.18
        out.append(
            {
                "x": round(x, 1),
                "y": round(y, 1),
                "r": round(rnd.uniform(9, 16) if sparkle else rnd.uniform(1.6, 3.4), 1),
                "o": round(rnd.uniform(0.45, 0.95), 2),
                "sparkle": sparkle,
            }
        )
    return out


TATREEZ_MOTIF = [  # a cross-stitch diamond (13 × 13 stitches): X = main colour, o = accent
    "......X......",
    ".....X.X.....",
    "....X.o.X....",
    "...X.o.o.X...",
    "..X.o...o.X..",
    ".X.o..X..o.X.",
    "X.o..XoX..o.X",
    ".X.o..X..o.X.",
    "..X.o...o.X..",
    "...X.o.o.X...",
    "....X.o.X....",
    ".....X.X.....",
    "......X......",
]
TATREEZ_SMALL = ["..X..", ".X.X.", "X.o.X", ".X.X.", "..X.."]


def tatreez(width: int, height: int, main: str = "#A7432D", accent: str = "#22306A") -> str:
    """A band of cross-stitch diamonds (SVG elements) filling width × height, tatreez-inspired."""
    cell = height / 13
    parts: list[str] = []

    def stitch(cx: float, cy: float, color: str) -> None:
        a = cell * 0.36
        parts.append(
            f'<path d="M{cx - a:.1f} {cy - a:.1f}L{cx + a:.1f} {cy + a:.1f}'
            f'M{cx + a:.1f} {cy - a:.1f}L{cx - a:.1f} {cy + a:.1f}" '
            f'stroke="{color}" stroke-width="{cell * 0.3:.2f}" stroke-linecap="round"/>'
        )

    def motif(rows: list[str], x0: float, y0: float) -> None:
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != ".":
                    stitch(x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell, main if ch == "X" else accent)

    unit = 13 * cell + 5 * cell + 4 * cell  # big diamond, small diamond, gaps
    n = int(width // unit) + 2
    start = (width - n * unit) / 2
    for i in range(n):
        x = start + i * unit
        motif(TATREEZ_MOTIF, x, 0)
        motif(TATREEZ_SMALL, x + 15 * cell, 4 * cell)
    return "".join(parts)


# ---------------------------------------------------------------------------------------------- designs


def glue(value: Any) -> Any:
    """`~` in the copy glues two words (no line break between them): it becomes a no-break space."""
    if isinstance(value, str):
        return value.replace("~", "\u00a0")
    if isinstance(value, list):
        return [glue(v) for v in value]
    if isinstance(value, dict):
        return {k: glue(v) for k, v in value.items()}
    return value


def load_yaml(name: str) -> dict[str, Any]:
    with (KIT / name).open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict)
    return data


def build_designs(copy: dict[str, Any]) -> list[Design]:
    designs: list[Design] = [
        Design("profile", "profile.html.j2", 1080, 1080, "profile", {}, (160, 160, 920, 920)),
        # Facebook: phones show only the centre ~1110 px; the profile photo and buttons cover the corners
        Design("fb-cover", "fb_cover.html.j2", 1640, 624, "facebook", {}, (285, 56, 1355, 560)),
    ]
    for i, hl in enumerate(copy["highlights"], start=1):
        designs.append(
            Design(
                f"highlight-{i}-{hl['slug']}",
                "highlight.html.j2",
                1080,
                1920,
                "highlights",
                {"hl": hl},
                (230, 650, 850, 1270),
            )
        )
    for ad in copy["ads"]:
        designs.append(
            Design(
                f"ad-{ad['slug']}",
                "ad.html.j2",
                1080,
                1350,
                "feed",
                {"ad": ad, "fmt": "feed"},
                (80, 80, 1000, 1270),
            )
        )
    for i, slide in enumerate(copy["carousel"]["slides"], start=1):
        designs.append(
            Design(
                f"carousel-{i}-{slide['slug']}",
                "carousel.html.j2",
                1080,
                1350,
                "carousel",
                {"car": copy["carousel"], "slide": slide, "step": i},
                (80, 80, 1000, 1270),
            )
        )
    by_slug = {ad["slug"]: ad for ad in copy["ads"]}
    for slug in copy["stories"]:
        designs.append(
            Design(
                f"story-{slug}",
                "ad.html.j2",
                1080,
                1920,
                "stories",
                {"ad": by_slug[slug], "fmt": "story"},
                (80, 220, 1000, 1670),
            )
        )
    designs += build_month(copy)
    return designs


# The October 2026 set: feed posts, two carousels, the Meta ad sets and the pieces of the videos.
FEED_SAFE = (80, 80, 1000, 1270)
SQUARE_SAFE = (64, 64, 1016, 1016)
# Reels: Instagram covers the top ~220 px (header) and the bottom ~380 px (caption, buttons), so nothing that
# matters goes below 1560; the like/comment column sits on the right edge, outside x 1000.
REEL_SAFE = (80, 220, 1000, 1560)
# Where the film sits in each video format (px). The overlays leave this box clear; videos() uses it too.
VIDEO_BOX: dict[str, dict[str, int]] = {
    "reel-film": {"W": 1080, "H": 1920, "w": 1080, "h": 720, "y": 600},  # the whole 3:2 film
    "reel-cut": {"W": 1080, "H": 1920, "w": 1080, "h": 864, "y": 560},  # one shot, cropped to 5:4
    "feed-film": {"W": 1080, "H": 1350, "w": 1080, "h": 720, "y": 315},  # 4:5 feed
}


def build_month(copy: dict[str, Any]) -> list[Design]:
    out: list[Design] = []
    for i, post in enumerate(copy["posts"], start=1):
        out.append(
            Design(
                f"post-{i:02d}-{post['slug']}",
                "ad.html.j2",
                1080,
                1350,
                "posts",
                {"ad": post, "fmt": "feed"},
                FEED_SAFE,
            )
        )
    for car in copy["carousels"]:
        for i, slide in enumerate(car["slides"], start=1):
            out.append(
                Design(
                    f"carousel-{car['slug']}-{i}",
                    "carousel.html.j2",
                    1080,
                    1350,
                    "carousels",
                    {"car": car, "slide": slide, "step": slide.get("step")},
                    FEED_SAFE,
                )
            )
    for ad in copy["ad_sets"]:
        out.append(
            Design(
                f"meta-{ad['slug']}-1x1",
                "ad.html.j2",
                1080,
                1080,
                "meta",
                {"ad": ad, "fmt": "square"},
                SQUARE_SAFE,
            )
        )
        out.append(
            Design(
                f"meta-{ad['slug']}-4x5",
                "ad.html.j2",
                1080,
                1350,
                "meta",
                {"ad": ad, "fmt": "feed"},
                FEED_SAFE,
            )
        )
    video = copy["video"]
    for card in video["endcards"] + video["frames"]:
        out.append(
            Design(
                f"end-{card['slug']}",
                "ad.html.j2",
                1080,
                1920,
                "video",
                {"ad": card, "fmt": "reel"},
                REEL_SAFE,
            )
        )
    for ov in video["overlays"]:
        box = VIDEO_BOX[ov["box"]]
        safe = REEL_SAFE if box["H"] == 1920 else (60, 60, 1020, 1290)
        out.append(
            Design(
                f"overlay-{ov['slug']}",
                "overlay.html.j2",
                box["W"],
                box["H"],
                "overlays",
                {"ov": ov, "box": box},
                safe,
                transparent=True,
            )
        )
    return out


QA_JS = (KIT / "templates/qa.js").read_text(encoding="utf-8")


class OptionalUndefined(Undefined):
    """Missing keys are False in `{% if %}` (optional copy such as a note), but printing one is an error."""

    def __str__(self) -> str:
        self._fail_with_undefined_error()


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(KIT / "templates"),
        autoescape=True,
        undefined=OptionalUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["ar"] = lambda s: str(s).translate(AR_DIGITS)
    env.globals["public"] = public
    env.globals["stars"] = stars
    env.globals["tatreez"] = tatreez
    env.globals["fonts"] = FONTS.as_uri()
    return env


async def render(
    designs: list[Design], copy: dict[str, Any], slots: Slots, media: Media, out: Path
) -> list[str]:
    env = make_env()
    html_dir = out / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for d in designs:
            ctx = {
                "copy": copy,
                "brand": copy["brand"],
                "W": d.width,
                "H": d.height,
                "slot": slots.get,
                "media": media.get,
                "design": d.name,
                **d.ctx,
            }
            html = env.get_template(d.template).render(**ctx)
            html_path = html_dir / f"{d.name}.html"
            html_path.write_text(html, encoding="utf-8")
            page = await browser.new_page(
                viewport={"width": d.width, "height": d.height}, device_scale_factor=1
            )
            await page.goto(html_path.as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready")
            await page.wait_for_timeout(150)
            missing = await page.evaluate(
                "() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)"
            )
            for src in missing:
                problems.append(f"{d.name}: image did not load: {src}")
            issues = await page.evaluate(QA_JS, list(d.safe) if d.safe else None)
            problems.extend(f"{d.name}: {msg}" for msg in issues)
            png = out / f"{d.name}.png"
            await page.screenshot(
                path=str(png),
                clip={"x": 0, "y": 0, "width": d.width, "height": d.height},
                omit_background=d.transparent,
            )
            await page.close()
            print(f"  {png}  {d.width}×{d.height}")
        await browser.close()
    return problems


def contact_sheet(designs: list[Design], out: Path) -> Path:
    """All renders on one sheet, grouped by format, each labelled with its file name."""
    groups: dict[str, list[Design]] = {}
    for d in designs:
        groups.setdefault(d.group, []).append(d)
    titles = {
        "profile": "Profile 1080×1080",
        "facebook": "Facebook cover 1640×624",
        "highlights": "Instagram highlight covers 1080×1920",
        "feed": "Feed ads 1080×1350",
        "carousel": "How-it-works carousel 1080×1350",
        "stories": "Stories 1080×1920",
        "posts": "October posts 1080×1350",
        "carousels": "October carousels 1080×1350 (5 slides each)",
        "meta": "Meta ad sets: 1080×1080 and 1080×1350",
        "video": "Reel end cards and activity frames 1080×1920",
        "overlays": "Video overlays (transparent, shown on grey)",
    }
    row_h = {
        "profile": 420,
        "facebook": 420,
        "highlights": 560,
        "feed": 520,
        "carousel": 520,
        "stories": 640,
        "posts": 520,
        "carousels": 520,
        "meta": 520,
        "video": 640,
        "overlays": 640,
    }
    order = [
        "profile",
        "facebook",
        "feed",
        "carousel",
        "stories",
        "highlights",
        "posts",
        "carousels",
        "meta",
        "video",
        "overlays",
    ]
    pad, label_h, head_h, sheet_w = 40, 34, 64, 3000
    font_path = FONTS / "IBMPlexSansArabic-SemiBold.ttf"
    font = ImageFont.truetype(str(font_path), 22)
    head_font = ImageFont.truetype(str(font_path), 30)
    rows: list[tuple[str, list[tuple[Image.Image, str]]]] = []
    # merge profile + facebook on one row
    for g in order:
        if g not in groups:
            continue
        items = []
        for d in groups[g]:
            im: Image.Image = Image.open(out / f"{d.name}.png")
            if im.mode == "RGBA":  # an overlay: show it on grey so its scrims and text read
                im = Image.alpha_composite(Image.new("RGBA", im.size, "#7A7F94"), im)
            im = im.convert("RGB")
            h = row_h[g]
            im = im.resize((round(im.width * h / im.height), h), Image.Resampling.LANCZOS)
            items.append((im, d.name))
        rows.append((titles[g], items))
    # wrap rows wider than the sheet
    lines: list[tuple[str, list[tuple[Image.Image, str]]]] = []
    for title, items in rows:
        cur: list[tuple[Image.Image, str]] = []
        width = pad
        for im, name in items:
            if cur and width + im.width + pad > sheet_w:
                lines.append((title, cur))
                title, cur, width = "", [], pad
            cur.append((im, name))
            width += im.width + pad
        lines.append((title, cur))
    total_h = pad + sum(
        (head_h if t else 0) + max(im.height for im, _ in it) + label_h + pad for t, it in lines
    )
    sheet = Image.new("RGB", (sheet_w, total_h), "#EDE6D6")
    draw = ImageDraw.Draw(sheet)
    y = pad
    for title, items in lines:
        if title:
            draw.text((pad, y + 12), title, fill="#16204A", font=head_font)
            y += head_h
        x = pad
        for im, name in items:
            sheet.paste(im, (x, y))
            draw.text((x, y + im.height + 6), name, fill="#585C72", font=font)
            x += im.width + pad
        y += max(im.height for im, _ in items) + label_h + pad
    path = out / "contact-sheet.png"
    sheet.save(path, optimize=True)
    return path


# ---------------------------------------------------------------------------------------------- videos

FILM = ROOT / "out/video"  # the brand film and its shots (scripts/build_film.py)
FPS = 24
XFADE = 0.4  # seconds of cross-fade between two parts
MAX_MB = 8.0
AUDIO_MB_PER_S = 0.021  # the soundtrack (AAC 160 kb/s) that film_audio adds to the picture


@dataclass
class Clip:
    """A shot of the film, fitted into a VIDEO_BOX over a blurred, enlarged copy of itself, + an overlay."""

    src: str  # file in out/video/
    box: str  # VIDEO_BOX key
    overlay: str  # name of the overlay design (transparent PNG)
    cx: float = 0.5  # horizontal centre of the crop, 0–1 of the shot's width


@dataclass
class Still:
    """A kit render (end card or frame) shown for `dur` seconds with a slow push-in."""

    design: str
    dur: float
    zoom: float = 1.035


# Every video: its parts in order. Names are the files in out/social/video/. The stills are long enough for
# the voice line read over them (content/marketing/film-audio/soundtrack.yaml; the cutter warns otherwise).
VIDEOS: dict[str, list[Clip | Still]] = {
    "reel-film-9x16": [Clip("qamra-film.mp4", "reel-film", "overlay-film-reel")],
    "feed-film-4x5": [Clip("qamra-film.mp4", "feed-film", "overlay-film-feed")],
    "cut-1-photo-to-character-9x16": [
        Clip("c2.mp4", "reel-cut", "overlay-cut-photo"),
        Still("end-cut-photo", 3.6),
    ],
    "cut-2-printed-book-9x16": [Clip("c3.mp4", "reel-cut", "overlay-cut-book"), Still("end-cut-book", 3.2)],
    "cut-3-kindergartens-9x16": [Clip("c4.mp4", "reel-cut", "overlay-cut-kg"), Still("end-cut-kg", 2.8)],
    "ad-parents-9x16": [
        Clip("c2.mp4", "reel-cut", "overlay-ad-parents"),
        Clip("c3.mp4", "reel-cut", "overlay-ad-parents"),
        Still("end-ad-parents", 3.4),
    ],
    "ad-kindergartens-9x16": [
        Clip("c4.mp4", "reel-cut", "overlay-cut-kg"),
        Clip("c3.mp4", "reel-cut", "overlay-cut-kg"),
        Still("end-cut-kg", 2.6),
    ],
    "ad-activity-books-9x16": [
        Still("end-frame-journey", 3.9),
        Still("end-frame-foundation", 2.8),
        Still("end-frame-family", 3.9),
        Still("end-ad-activity-books", 3.7),
    ],
    "ad-gifts-9x16": [Clip("c3.mp4", "reel-cut", "overlay-ad-gifts"), Still("end-ad-gifts", 3.2)],
}


def find_ffmpeg(arg: str | None) -> str:
    """--ffmpeg, else $FFMPEG, else ffmpeg on PATH, else the binary that ships with imageio-ffmpeg."""
    for cand in (arg, os.environ.get("FFMPEG"), shutil.which("ffmpeg")):
        if cand:
            return cand
    try:
        import imageio_ffmpeg

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError as exc:
        raise SystemExit("no ffmpeg: pass --ffmpeg PATH or set FFMPEG") from exc


def probe(ff: str, path: Path) -> tuple[float, int, int]:
    """(seconds, width, height) of a video, read from ffmpeg's banner."""
    err = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    import re

    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    v = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5})", err)
    if not d or not v:
        raise RuntimeError(f"cannot read {path}")
    secs = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))
    return secs, int(v.group(1)), int(v.group(2))


def compose(
    ff: str, name: str, parts: list[Clip | Still], rendered: Path, out: Path
) -> tuple[Path, list[float]]:
    """One silent MP4 (H.264): every part is brought to the same size, then the parts cross-fade. Returns the
    file and where each part starts (s), for the soundtrack's cues."""
    first = next((p for p in parts if isinstance(p, Clip)), None)
    W, H = (VIDEO_BOX[first.box]["W"], VIDEO_BOX[first.box]["H"]) if first else (1080, 1920)
    args: list[str] = []
    chains: list[str] = []
    durs: list[float] = []
    n = 0
    for k, part in enumerate(parts):
        if isinstance(part, Clip):
            src = FILM / part.src
            if not src.exists():
                raise FileNotFoundError(f"{src} is missing (made by scripts/build_film.py)")
            dur, sw, sh = probe(ff, src)
            box = VIDEO_BOX[part.box]
            aspect = box["w"] / box["h"]
            cw, ch = (
                (round(sh * aspect / 2) * 2, sh) if aspect < sw / sh else (sw, round(sw / aspect / 2) * 2)
            )
            x0 = round(min(max(part.cx * sw - cw / 2, 0), sw - cw))
            y0 = (sh - ch) // 2
            args += [
                "-i",
                str(src),
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-t",
                f"{dur:.3f}",
                "-i",
                str(rendered / f"{part.overlay}.png"),
            ]
            vi, oi = n, n + 1
            n += 2
            chains.append(
                f"[{vi}:v]fps={FPS},setpts=PTS-STARTPTS,split=2[b{k}][f{k}];"
                f"[b{k}]scale=-2:{H},crop={W}:{H},gblur=sigma=40,eq=brightness=-0.09:saturation=1.08[bb{k}];"
                f"[f{k}]crop={cw}:{ch}:{x0}:{y0},scale={box['w']}:{box['h']}:flags=lanczos[ff{k}];"
                f"[bb{k}][ff{k}]overlay=0:{box['y']}[m{k}];"
                f"[{oi}:v]format=rgba[o{k}];[m{k}][o{k}]overlay=0:0:shortest=1,"
                f"format=yuv420p,setsar=1,settb=AVTB,fps={FPS}[s{k}]"
            )
        else:
            frames = round(part.dur * FPS)
            args += [
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-t",
                f"{part.dur:.3f}",
                "-i",
                str(rendered / f"{part.design}.png"),
            ]
            chains.append(
                f"[{n}:v]scale={W * 2}:{H * 2},zoompan=z='1+({part.zoom}-1)*on/{frames}'"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
                f"format=yuv420p,setsar=1,settb=AVTB,fps={FPS}[s{k}]"
            )
            n += 1
            dur = part.dur
        durs.append(dur)
    last, t, starts = "[s0]", 0.0, [0.0]
    for k in range(1, len(parts)):
        t += durs[k - 1] - XFADE
        starts.append(t)
        chains.append(f"{last}[s{k}]xfade=transition=fade:duration={XFADE}:offset={t:.3f}[x{k}]")
        last = f"[x{k}]"
    path = out / "silent" / f"{name}.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    budget = MAX_MB - AUDIO_MB_PER_S * (sum(durs) - XFADE * (len(durs) - 1))
    for crf in (22, 24, 26, 28, 30):
        subprocess.run(
            [
                ff,
                "-v",
                "error",
                "-y",
                *args,
                "-filter_complex",
                ";".join(chains),
                "-map",
                last,
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                str(crf),
                "-maxrate",
                "3000k",
                "-bufsize",
                "6000k",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(FPS),
                "-movflags",
                "+faststart",
                str(path),
            ],
            check=True,
        )
        if path.stat().st_size <= budget * 1024 * 1024:
            break
    return path, starts


def videos(ff: str, rendered: Path, only: list[str]) -> list[str]:
    """Cut every video in VIDEOS into out/social/video/: <name>.mp4 with the voice and the music,
    <name>-music.mp4 with the music only (soundtrack.yaml has a cue sheet per video); 3 review frames of each
    into video/frames/."""
    out = rendered / "video"
    frames = out / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    for name, parts in VIDEOS.items():
        if only and not any(name.startswith(p) for p in only):
            continue
        silent, starts = compose(ff, name, parts, rendered, out)
        path = out / f"{name}.mp4"
        for voice, dest in ((True, path), (False, out / f"{name}-music.mp4")):
            sound = film_audio.mux(ff, name, silent, dest, starts, voice=voice)
            problems += sound["warnings"] if voice else []
            secs, w, h = probe(ff, dest)
            mb = dest.stat().st_size / 1024 / 1024
            print(f"  {dest}  {w}×{h}  {secs:.1f} s  {mb:.1f} MB  {sound['lufs']:.1f} LUFS")
            if mb > MAX_MB:
                problems.append(f"{dest.name}: {mb:.1f} MB is over {MAX_MB} MB")
        for i, at in enumerate((0.12, 0.5, 0.9), start=1):
            subprocess.run(
                [
                    ff,
                    "-v",
                    "error",
                    "-y",
                    "-ss",
                    f"{secs * at:.2f}",
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "3",
                    str(frames / f"{name}-{i}.jpg"),
                ],
                check=True,
            )
    return problems


# ---------------------------------------------------------------------------------------------- package

AD_FOLDERS = {
    "parents": "1-parents-story-books",
    "kindergartens": "2-kindergartens",
    "activity-books": "3-activity-books",
    "gifts": "4-gifts",
}


def package(copy: dict[str, Any], rendered: Path) -> Path:
    """out/social/package/: what Tareq uploads: posts, reels, ads/<set>, stories, profile, the .md sheets."""
    pkg = rendered / "package"
    if pkg.exists():
        shutil.rmtree(pkg)
    (pkg / "posts").mkdir(parents=True)

    def put(src: Path, dst: Path) -> None:
        if not src.exists():
            raise FileNotFoundError(f"{src} is missing: render it first (and --videos for the MP4s)")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    for i, post in enumerate(copy["posts"], start=1):
        name = f"post-{i:02d}-{post['slug']}"
        put(rendered / f"{name}.png", pkg / "posts" / f"{name}.png")
    for car in copy["carousels"]:
        for i in range(1, len(car["slides"]) + 1):
            put(
                rendered / f"carousel-{car['slug']}-{i}.png",
                pkg / "posts" / f"carousel-{car['slug']}" / f"{i}.png",
            )
    for name in VIDEOS:
        if not name.startswith("ad-"):
            for v in (name, f"{name}-music"):
                put(rendered / "video" / f"{v}.mp4", pkg / "reels" / f"{v}.mp4")
    for slug, folder in AD_FOLDERS.items():
        put(rendered / f"meta-{slug}-1x1.png", pkg / "ads" / folder / f"{slug}-1080x1080.png")
        put(rendered / f"meta-{slug}-4x5.png", pkg / "ads" / folder / f"{slug}-1080x1350.png")
        for end in ("", "-music"):
            put(
                rendered / "video" / f"ad-{slug}-9x16{end}.mp4",
                pkg / "ads" / folder / f"{slug}-1080x1920{end}.mp4",
            )
    for slug in copy["stories"]:
        put(rendered / f"story-{slug}.png", pkg / "stories" / f"story-{slug}.png")
    profile = ["profile", "fb-cover"] + [
        f"highlight-{i}-{h['slug']}" for i, h in enumerate(copy["highlights"], 1)
    ]
    for name in profile:
        put(rendered / f"{name}.png", pkg / "profile" / f"{name}.png")
    for sheet in ("ads.md", "calendar.md"):
        put(KIT / sheet, pkg / sheet)
    (pkg / "captions.md").write_text(captions_md(copy), encoding="utf-8")
    return pkg


def captions_md(copy: dict[str, Any]) -> str:
    """captions.yaml as a sheet to copy from: one section per file, the caption, then its hashtags."""
    caps = load_yaml("captions.yaml")
    lines = [
        "# نصوص المنشورات — قمرة",
        "",
        "انسخوا كل نص مع وسومه كما هو من المربّع تحت اسم الملف. الملفات في مجلدَي `posts/` و`reels/`،"
        " وموعد كل منشور في `calendar.md`.",
        "",
    ]
    keys = [f"post-{i:02d}-{p['slug']}" for i, p in enumerate(copy["posts"], start=1)]
    keys += [f"carousel-{c['slug']}" for c in copy["carousels"]]
    keys += [n for n in VIDEOS if not n.startswith("ad-")]
    for key in keys:
        cap = caps.get(key)
        if cap is None:
            raise KeyError(f"captions.yaml has no caption for {key}")
        files = (
            f"`posts/{key}.png`"
            if key.startswith("post-")
            else (f"`posts/{key}/` (١–٥)" if key.startswith("carousel-") else f"`reels/{key}.mp4`")
        )
        lines += [
            f"## {key}",
            "",
            f"الملف: {files}",
            "",
            "```text",  # a fenced block keeps the line breaks and gets a copy button
            cap["text"].strip(),
            "",
            " ".join("#" + h for h in cap["hashtags"]),
            "```",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--only", action="append", default=[], help="render designs whose name starts with this"
    )
    parser.add_argument(
        "--incoming", default=str(ROOT / "design/incoming"), help="folder of delivered photos"
    )
    parser.add_argument("--no-sheet", action="store_true", help="skip the contact sheet")
    parser.add_argument("--images", default=str(KIT / "images.yaml"), help="image-slot manifest (for tests)")
    parser.add_argument("--out", default=str(OUT), help="output folder")
    parser.add_argument(
        "--videos", action="store_true", help="also cut the videos, with sound (needs ffmpeg and out/video/)"
    )
    parser.add_argument(
        "--ffmpeg", default=None, help="ffmpeg binary (default: $FFMPEG, PATH, imageio-ffmpeg)"
    )
    parser.add_argument("--package", action="store_true", help="collect the deliverables into OUT/package/")
    args = parser.parse_args()

    copy = glue(load_yaml("copy.yaml"))
    with Path(args.images).open(encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    slots = Slots(manifest, Path(args.incoming))
    media = Media(manifest)
    out = Path(args.out).resolve()
    designs = build_designs(copy)
    chosen = [d for d in designs if not args.only or any(d.name.startswith(p) for p in args.only)]
    if not chosen and not (args.videos and any(v.startswith(p) for v in VIDEOS for p in args.only)):
        print("no design matches --only", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    if chosen:  # `--videos --only cut-1` cuts one video from the renders already in OUT
        print(f"rendering {len(chosen)} designs → {out}/")
        problems = asyncio.run(render(chosen, copy, slots, media, out))
    if not args.only and not args.no_sheet:
        print(f"  {contact_sheet(designs, out)}")
    if args.videos:
        print(f"cutting videos → {out}/video/")
        problems += videos(find_ffmpeg(args.ffmpeg), out, args.only)
    if args.package and not problems:
        print(f"package → {package(copy, out)}/")
    if slots.used:
        print("incoming images used: " + json.dumps(slots.used, ensure_ascii=False))
    for w in dict.fromkeys(slots.warnings):
        print(f"note: {w}")
    if problems:
        print("\nlayout check found problems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("layout check: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
