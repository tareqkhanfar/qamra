"""Images the templates derive from the book's own pictures, and the optional decor set (Addendum 11 §5).

- The back cover continues the front art: the cover picture mirrored (its edge meets the front at the spine)
  and blurred, at print resolution, so no CSS filter has to rasterize it.
- Cut-outs: a character on a plain sheet background becomes a transparent PNG (the companion peeking on the
  drawing page).
- Decor (E1–E5 in docs/image-prompts.md): finished PNGs listed in `packages/pdf/layouts/decor/manifest.json`
  are used when present (cropped, white keyed out); otherwise the templates draw their SVG fallbacks.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

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


def cutout(src: Path, dest: Path, *, threshold: int = 30, feather: float = 1.6) -> Path:
    """A figure on a plain background (character/companion sheets) as a transparent PNG, trimmed."""
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as original:
        im = original.convert("RGB")
        w, h = im.size
        corners = [
            im.getpixel((2, 2)),
            im.getpixel((w - 3, 2)),
            im.getpixel((2, h - 3)),
            im.getpixel((w - 3, h - 3)),
        ]
        bg = tuple(sorted(c[i] for c in corners)[1] for i in range(3))  # type: ignore[index]
        diff = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L")
        mask = diff.point(lambda v: 255 if v > threshold else 0).filter(ImageFilter.MaxFilter(3))
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
        out = im.convert("RGBA")
        out.putalpha(mask)
        box = mask.point(lambda v: 255 if v > 40 else 0).getbbox()
        if box:
            out = out.crop(box)
        out.save(dest, format="PNG", optimize=True)
    return dest


@dataclass
class Assets:
    """What a render adds to the book's own images: derived pictures and the decor found on disk."""

    back: Path | None = None
    companion: Path | None = None
    decor: dict[str, Path] = field(default_factory=dict)


def prepare(front: Path | None, companion: Path | None, out_dir: Path) -> Assets:
    work = out_dir / "derived"
    return Assets(
        back=back_background(front, work / "back.jpg") if front and front.is_file() else None,
        companion=cutout(companion, work / "companion.png") if companion and companion.is_file() else None,
        decor=prepare_decor(work / "decor"),
    )
