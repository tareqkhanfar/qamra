"""Install the chosen design images (design/incoming/, drawn by scripts/design_images.py) into the product.

    uv run python scripts/install_design_images.py [--only C1 D1] [--dry-run]

JPEG (quality 90), so the repo stays small; every reader accepts .jpg (the site's photo slots, the fixed
character sheets and cover plates of the story pipeline, docs/decisions.md 2026-10-02). Where each image goes:
- A1–A10 → apps/web/public/photos/<slot>.jpg (public/photos/README.md), 2400 px on the long side
- C-sheets → content/cast/<id>-<style>.jpg (shared by every theme)
- D-plates → content/themes/<theme>/plates/<style>-<n>.jpg
- B, E, F, G → content/assets/<file>.jpg (mockups, page decor, the Islamic series, activity covers), read by
  the social kit, the page decor manifest and the Islamic renderer once they use them
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "design" / "incoming"
CAST = {
    "C1": "qamour-3d", "C2": "qamour-watercolor", "C7": "qamour-cartoon",
    "C3": "teacher-3d", "C4": "teacher-watercolor", "C5": "classmates-3d", "C6": "classmates-watercolor",
    "C8": "mom-3d", "C9": "mom-watercolor", "C10": "dad-3d", "C11": "dad-watercolor",
    "C12": "grandma-3d", "C13": "grandma-watercolor", "C14": "grandpa-3d", "C15": "grandpa-watercolor",
    "C16": "baby-3d", "C17": "baby-watercolor",
}  # fmt: skip
PLATES = {
    "D1": ("graduation", "3d-1"), "D2": ("graduation", "watercolor-1"),
    "D3": ("graduation", "3d-2"), "D4": ("graduation", "watercolor-2"),
    "D5": ("graduation", "3d-3"), "D6": ("graduation", "watercolor-3"),
    "D7": ("first-day", "3d-1"), "D8": ("first-day", "watercolor-1"),
    "D9": ("new-sibling", "3d-1"), "D10": ("new-sibling", "watercolor-1"),
}  # fmt: skip
_ID = re.compile(r"^([A-G]\d+)-(.+)\.png$")


def target(image_id: str, rest: str) -> tuple[Path, int | None]:
    """(destination, long side to resize to or None to keep)."""
    if image_id[0] == "A":
        return ROOT / "apps/web/public/photos" / f"{rest}.jpg", 2400
    if image_id in CAST:
        return ROOT / "content/cast" / f"{CAST[image_id]}.jpg", None
    if image_id in PLATES:
        theme, name = PLATES[image_id]
        return ROOT / "content/themes" / theme / "plates" / f"{name}.jpg", None
    return ROOT / "content/assets" / f"{image_id}-{rest}.jpg", None


def trim_paper_margin(img: Image.Image, limit: float = 0.08) -> Image.Image:
    """Cut the light paper border paintings tend to keep (a cover background is full-bleed): from each edge,
    the rows/columns that are near-white and flat, up to `limit` of the side; the original shape after."""
    import numpy as np

    a = np.asarray(img.convert("L"), dtype=float)
    h, w = a.shape

    def edge(lines: np.ndarray, n: int) -> int:
        k = 0
        while k < int(n * limit) and lines[k].mean() > 215 and lines[k].std() < 22:
            k += 1
        return k + (3 if k else 0)  # and the soft edge of the paint

    top, bottom = edge(a, h), edge(a[::-1], h)
    left, right = edge(a.T, w), edge(a.T[::-1], w)
    if not (top or bottom or left or right):
        return img
    img = img.crop((left, top, w - right, h - bottom))
    cw, ch = img.size  # back to the original shape (square plates, 3:4 covers), centred, then its size
    if cw / ch > w / h:
        nw = round(ch * w / h)
        img = img.crop(((cw - nw) // 2, 0, (cw - nw) // 2 + nw, ch))
    else:
        nh = round(cw * h / w)
        img = img.crop((0, (ch - nh) // 2, cw, (ch - nh) // 2 + nh))
    return img.resize((w, h), Image.Resampling.LANCZOS)


def install(src: Path, dst: Path, long_side: int | None, trim: bool = False) -> None:
    img = Image.open(src).convert("RGB")
    if trim:
        img = trim_paper_margin(img)
    if long_side and max(img.size) > long_side:
        img.thumbnail((long_side, long_side), Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=90, optimize=True, progressive=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for src in sorted(INCOMING.glob("*.png")):
        m = _ID.match(src.name)
        if not m or (a.only and m.group(1) not in a.only):
            continue
        dst, long_side = target(m.group(1), m.group(2))
        print(f"{src.name} → {dst.relative_to(ROOT)}")
        if not a.dry_run:
            install(src, dst, long_side, trim=m.group(1) in PLATES or m.group(1)[0] == "G")


if __name__ == "__main__":
    main()
