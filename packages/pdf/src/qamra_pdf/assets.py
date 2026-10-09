"""Images the templates derive from the book's own pictures, and the optional decor set (Addendum 11 §5).

- The back cover continues the front art: the cover picture mirrored (its edge meets the front at the spine)
  and blurred, at print resolution, so no CSS filter has to rasterize it.
- Cut-outs: a character on a plain sheet background becomes a transparent PNG (the companion peeking on the
  drawing page).
- Decor (E1–E5 in docs/image-prompts.md): finished PNGs listed in `packages/pdf/layouts/decor/manifest.json`
  are used when present (cropped, white keyed out); otherwise the templates draw their SVG fallbacks.
- The back cover's hero: the child's figure from the character sheet, cut out (only when the cut-out reads as
  a whole figure); and small print copies of a few story pages for the back cover's thumbnails.
"""

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

from qamra_pdf.cutout import VERSION as CUTOUT_VERSION
from qamra_pdf.cutout import cut_out_figure

PKG_DIR = Path(__file__).parent


def _layouts_dir() -> Path:
    packaged = PKG_DIR / "layouts"  # wheel builds (force-include)
    return packaged if packaged.is_dir() else PKG_DIR.parents[1] / "layouts"


LAYOUTS_DIR = _layouts_dir()
MANIFEST = LAYOUTS_DIR / "decor" / "manifest.json"


def decor_dirs() -> list[Path]:
    dirs = [Path(d) for d in os.environ.get("QAMRA_DECOR_DIR", "").split(os.pathsep) if d]
    dirs.append(LAYOUTS_DIR / "decor")
    if len(PKG_DIR.parents) > 3:
        dirs.append(PKG_DIR.parents[3] / "design" / "incoming")  # Tareq drops finished images here
    return dirs


@dataclass(frozen=True)
class DecorItem:
    key: str
    file: str
    crop: tuple[float, float, float, float] | None = None
    key_white: bool = False
    px: int = 1400


def manifest() -> dict[str, DecorItem]:
    try:
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    items: dict[str, DecorItem] = {}
    for key, v in raw.items():
        if key.startswith("_") or not isinstance(v, dict) or "file" not in v:
            continue
        crop = v.get("crop")
        items[key] = DecorItem(
            key=key,
            file=str(v["file"]),
            crop=(float(crop[0]), float(crop[1]), float(crop[2]), float(crop[3])) if crop else None,
            key_white=bool(v.get("key_white", False)),
            px=int(v.get("px", 1400)),
        )
    return items


def find_source(item: DecorItem) -> Path | None:
    for d in decor_dirs():
        p = d / item.file
        if p.is_file():
            return p
    return None


def white_to_alpha(im: Image.Image) -> Image.Image:
    """Un-blend a white background: alpha = how far the darkest channel is from white, colors restored."""
    rgb = im.convert("RGB")
    alpha = ImageOps.invert(_min_channel(rgb))
    alpha = alpha.point(lambda v: 0 if v < 6 else min(255, int(v * 1.04)))
    bands = []
    for band in rgb.split():
        # c = a·c' + (1 − a)·255  →  c' = 255 − (255 − c) / a
        inv = ImageChops.invert(band)
        restored = ImageChops.invert(_divide(inv, alpha))
        bands.append(restored)
    return Image.merge("RGBA", (*bands, alpha))


def _min_channel(rgb: Image.Image) -> Image.Image:
    r, g, b = rgb.split()
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _divide(a: Image.Image, b: Image.Image) -> Image.Image:
    """Per-pixel a / b · 255 (b = 0 → 0), for 8-bit bands."""
    from PIL import ImageMath

    out: Image.Image = ImageMath.lambda_eval(
        lambda e: e["convert"](e["min"](e["float"](e["a"]) * 255 / (e["float"](e["b"]) + 0.5), 255), "L"),
        a=a,
        b=b,
    )
    return out


def prepare_decor(out_dir: Path) -> dict[str, Path]:
    """Processed decor images for this render (only the ones whose source file exists)."""
    found: dict[str, Path] = {}
    for key, item in manifest().items():
        src = find_source(item)
        if src is None:
            continue
        dest = out_dir / f"{key}.png"
        if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
            out_dir.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as original:
                im = (
                    original.convert("RGBA")
                    if original.mode in ("RGBA", "LA", "P")
                    else original.convert("RGB")
                )
                if item.crop:
                    w, h = im.size
                    x0, y0, x1, y1 = item.crop
                    im = im.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
                im.thumbnail((item.px, item.px), Image.Resampling.LANCZOS)
                if item.key_white:
                    im = white_to_alpha(im)
                im.save(dest, format="PNG", optimize=True)
        found[key] = dest
    return found


def back_background(front: Path, dest: Path) -> Path:
    """The front art mirrored (continuous across the spine) and softly blurred, at the source resolution."""
    if dest.exists() and dest.stat().st_mtime >= front.stat().st_mtime:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(front) as original:
        im = ImageOps.mirror(original.convert("RGB"))
        small = im.resize((max(64, im.width // 4), max(64, im.height // 4)), Image.Resampling.BILINEAR)
        small = small.filter(ImageFilter.GaussianBlur(radius=max(4, small.width // 70)))
        blurred = small.resize(im.size, Image.Resampling.BICUBIC)
        dpi = original.info.get("dpi", (300, 300))
        blurred.save(dest, format="JPEG", quality=88, dpi=dpi)
    return dest


def cutout(src: Path, dest: Path) -> Path:
    """A figure on a plain background (character/companion sheets) as a transparent PNG, trimmed.

    The paper and the floor shadow go; light clothes and anything the figure encloses stay (qamra_pdf.cutout).
    """
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as original:
        out = cut_out_figure(original.convert("RGB"))
    box = out.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    if box:
        out = out.crop(box)
    out.save(dest, format="PNG", optimize=True)
    return dest


THUMB_PX = 720  # a back-cover thumbnail is at most 46 mm: 720 px is ≥ 390 DPI
HERO_MIN_HEIGHT = 0.62  # a whole figure fills at least this share of its view's height
# ... and this share of its own box (a cut-out of the whole view, or a sliver, fails)
HERO_COVERAGE = (0.18, 0.85)


def hero_view(sheet: Path, dest: Path) -> Path | None:
    """The middle view of a three-view character sheet (three-quarter, waving: the back cover's hero), cut
    out. None when the picture is not a three-view sheet or the cut-out is not a clean whole figure; the back
    cover then shows the round portrait."""
    if dest.exists() and dest.stat().st_mtime >= sheet.stat().st_mtime:
        return dest
    with Image.open(sheet) as original:
        im = original.convert("RGB")
    w, h = im.size
    if w < 1.3 * h:
        return None
    view = im.crop((w // 3, 0, 2 * w // 3, h))
    figure = cut_out_figure(view)
    alpha = figure.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    box = alpha.getbbox()
    if not box:
        return None
    x0, y0, x1, y1 = box
    area = max(1, (x1 - x0) * (y1 - y0))
    coverage = sum(alpha.crop(box).histogram()[255:]) / area
    if (y1 - y0) < HERO_MIN_HEIGHT * h or not HERO_COVERAGE[0] <= coverage <= HERO_COVERAGE[1]:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    figure.crop(box).save(dest, format="PNG", optimize=True)
    _fit_height(dest)
    return dest


HERO_MAX_PX = 1100  # the back cover's figure is at most ~75 mm tall: 1100 px is ≥ 370 DPI there


def _fit_height(path: Path, px: int = HERO_MAX_PX) -> None:
    """Shrink a cut-out stored far above print resolution (PNG with alpha is stored losslessly)."""
    with Image.open(path) as im:
        if im.height <= px:
            return
        small = im.resize((max(1, round(im.width * px / im.height)), px), Image.Resampling.LANCZOS)
    small.save(path, format="PNG", optimize=True)


def figure_cutout(src: Path, dest: Path) -> Path | None:
    """A single front view on plain paper (a class book's portrait), cut out; None when it is not clean."""
    fresh = not (dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime)
    out = cutout(src, dest)
    if fresh:
        _fit_height(out)
    with Image.open(out) as im:
        alpha = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
        coverage = sum(alpha.histogram()[255:]) / max(1, im.width * im.height)
    return out if HERO_COVERAGE[0] <= coverage <= HERO_COVERAGE[1] else None


def thumb_copy(src: Path, dest: Path, px: int = THUMB_PX) -> Path:
    """A small print copy (center square) of a story page for the back cover."""
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as original:
        im = original.convert("RGB")
        side = min(im.size)
        left, top = (im.width - side) // 2, (im.height - side) // 2
        im = im.crop((left, top, left + side, top + side)).resize((px, px), Image.Resampling.LANCZOS)
        im.save(dest, format="JPEG", quality=88, dpi=(300, 300))
    return dest


@dataclass
class Assets:
    """What a render adds to the book's own images: derived pictures and the decor found on disk."""

    back: Path | None = None
    companion: Path | None = None
    decor: dict[str, Path] = field(default_factory=dict)
    hero: Path | None = None  # the child's cut-out figure for the back cover
    thumbs: list[Path] = field(default_factory=list)  # story pages shown small on the back cover


def prepare(
    front: Path | None,
    companion: Path | None,
    out_dir: Path,
    *,
    hero: Path | None = None,
    hero_is_sheet: bool = True,
    thumbs: Sequence[Path] = (),
) -> Assets:
    work = out_dir / "derived"
    figure: Path | None = None
    if hero and hero.is_file():
        dest = work / f"hero-{hero.stem}-v{CUTOUT_VERSION}.png"
        figure = hero_view(hero, dest) if hero_is_sheet else figure_cutout(hero, dest)
    return Assets(
        back=back_background(front, work / "back.jpg") if front and front.is_file() else None,
        companion=cutout(companion, work / f"companion-v{CUTOUT_VERSION}.png")
        if companion and companion.is_file()
        else None,
        decor=prepare_decor(work / "decor"),
        hero=figure,
        thumbs=[
            thumb_copy(p, work / "thumbs" / f"{i}-{p.stem}.jpg") for i, p in enumerate(thumbs) if p.is_file()
        ],
    )
