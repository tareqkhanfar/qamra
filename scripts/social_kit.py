"""Qamra social-media kit: HTML/CSS templates rendered to PNG with Playwright (Chromium).

    uv run python scripts/social_kit.py                     # all → out/social/<name>.png + contact sheet
    uv run python scripts/social_kit.py --only ad-a-launch  # one design (repeatable; prefix match)
    uv run python scripts/social_kit.py --incoming DIR      # look for delivered photos in DIR

Everything lives in content/marketing/social/: copy.yaml (all words), captions.yaml (post captions),
images.yaml (photo/mockup slots), templates/ (Jinja2). Art is drawn in code; the only bitmaps are pages
already public on the site (apps/web/public/workbooks/**) and, once Tareq delivers them, files in
design/incoming/. After each render a layout check (templates/qa.js) reports text that leaves its box or the
safe zone, headline lines that wrap, and paragraphs that end with a lone word.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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


# ---------------------------------------------------------------------------------------------- images


def public(rel: str) -> str:
    """A file URI for an image that is already public on the website (apps/web/public/...)."""
    path = PUBLIC / rel
    if not path.exists():
        raise FileNotFoundError(f"public image missing: {path}")
    return path.as_uri()


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
            path = self.incoming / fname
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
                {"slide": slide, "index": i, "total": len(copy["carousel"]["slides"])},
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
    return designs


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


async def render(designs: list[Design], copy: dict[str, Any], slots: Slots, out: Path) -> list[str]:
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
            await page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": d.width, "height": d.height})
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
    }
    row_h = {"profile": 420, "facebook": 420, "highlights": 560, "feed": 520, "carousel": 520, "stories": 640}
    order = ["profile", "facebook", "feed", "carousel", "stories", "highlights"]
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
            im = Image.open(out / f"{d.name}.png").convert("RGB")
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
    args = parser.parse_args()

    copy = glue(load_yaml("copy.yaml"))
    with Path(args.images).open(encoding="utf-8") as fh:
        slots = Slots(yaml.safe_load(fh), Path(args.incoming))
    out = Path(args.out).resolve()
    designs = build_designs(copy)
    chosen = [d for d in designs if not args.only or any(d.name.startswith(p) for p in args.only)]
    if not chosen:
        print("no design matches --only", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    print(f"rendering {len(chosen)} designs → {out}/")
    problems = asyncio.run(render(chosen, copy, slots, out))
    if not args.only and not args.no_sheet:
        print(f"  {contact_sheet(designs, out)}")
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
