"""Audit the child's cut-out on many character sheets: shoes, hems, shadow remnants, halos.

    uv run python scripts/cutout_audit.py OUT_DIR SHEET_OR_DIR... [--views 0,1] [--colour]

Each sheet's figures (front view and waving pose by default) are cut exactly as the workbooks cut them
(`render.character`: the figure's box, padded with paper, `qamra_pdf.cutout`), and checked:

- `model`   the segmentation model's matte was used (not the colour fallback);
- `feet`    `feet_problem` is quiet (the drawing does not run off the sheet, nothing drawn is left under
            the feet);
- `shadow`  little of the cut's floor band is floor shadow the model does not see as the figure (paper hue,
            darker than the paper, soft): remnants at the heels show as brown smudges inside the sticker edge;
- `eaten`   little of what the model is sure is the figure on the floor (a shoe, a hem: drawn) is left out;
- `halo`    little of the cut's outer rim is plain paper (a cream halo around the figure).

Writes `OUT_DIR/audit.csv`, `OUT_DIR/audit.md` (a pass/fail table) and `OUT_DIR/contact.png` (every cut on a
blue card, the feet enlarged beside it). Free and local: no image model API is called.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from qamra_workbook.render.character import PAD, SHEET_EDGE_PX, figure_box, paper_color

from qamra_pdf import cutout as C
from qamra_pdf.matte import figure_matte

SHADOW_MAX_SHARE = 0.005  # of the floor band's cut (a remnant at the heels: 1–3 %)
EATEN_MAX_SHARE = 0.01  # drawn pixels left out, as a share of the floor band's cut
HALO_MAX_SHARE = 0.15  # of the cut's outer rim
CARD = (52, 110, 190)
TILE_H = 300


@dataclass
class Result:
    sheet: str
    view: int
    method: str
    feet: str
    shadow: float
    eaten: float
    halo: float
    pieces: int
    tile: Image.Image

    @property
    def problems(self) -> list[str]:
        out = []
        if self.method != "model":
            out.append("colour fallback")
        if self.feet:
            out.append(f"feet: {self.feet}")
        if self.shadow > SHADOW_MAX_SHARE:
            out.append(f"shadow {self.shadow:.1%}")
        if self.eaten > EATEN_MAX_SHARE:
            out.append(f"eaten {self.eaten:.1%}")
        if self.halo > HALO_MAX_SHARE:
            out.append(f"halo {self.halo:.0%}")
        if self.pieces > 1:
            out.append(f"{self.pieces} figures in one view")
        return out


def _floor(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    rows = np.flatnonzero(mask.any(1))
    band = np.zeros((h, w), bool)
    if rows.size:
        top, bottom = int(rows[0]), int(rows[-1])
        band[max(0, round(bottom - 0.12 * (bottom - top))) : bottom + 1] = True
    return band


def audit(sheet_path: Path, view: int, use_model: bool) -> Result | None:
    with Image.open(sheet_path) as src:
        img = src.convert("RGB")
    paper = paper_color(img)
    try:
        box = figure_box(img, paper, view)
    except ValueError:
        return None
    crop = img.crop(box)
    padded = Image.new("RGB", (crop.width + 2 * PAD, crop.height + 2 * PAD), paper)
    padded.paste(crop, (PAD, PAD))
    p = C._measure(padded, paper)
    mask, method = C._mask(p, padded, use_model)
    feet = C.feet_problem(p, mask, PAD)
    rows = np.flatnonzero(mask.any(1))
    if (
        box[3] >= img.height - SHEET_EDGE_PX
        and rows.size
        and rows[-1] >= PAD + crop.height - 1 - SHEET_EDGE_PX
    ):
        feet = "the drawing runs off the sheet's bottom edge"
    floor = _floor(mask)
    # the floor shadow kept: soft paper-hued pixels darker than the paper that the model does not see as the
    # figure (brown remnants at the heels inside the sticker edge)
    rgb, field = p.rgb, p.field
    chroma = rgb / (rgb.sum(-1, keepdims=True) + 1.0)
    paper_chroma = field / (field.sum(-1, keepdims=True) + 1.0)
    darker = 1.0 - (rgb / np.maximum(field, 1.0)).mean(-1)
    cand = (
        floor
        & (np.abs(chroma - paper_chroma).max(-1) < C.SHADOW_HUE)
        & (darker > 0.04)
        & (p.edges <= max(C.SHADOW_EDGE, p.edge))
    )
    matte = figure_matte(padded)
    model_says = matte > 0.5 if matte is not None else C._figure(p)
    in_floor = mask & floor
    light = C._light_object(p, cand)
    loose = in_floor & cand & ~model_says & ~light
    # only what reaches the cut's edge (a remnant hangs on the outside; a white shoe's top is inside its
    # outline)
    rim = mask & ~C._shrink(mask, 5)
    labels, sizes = C._components(loose)
    touching = np.unique(labels[rim & loose])
    shadow_px = np.isin(labels, touching[touching > 0])
    shadow = float(shadow_px.sum() / max(1, in_floor.sum()))
    # a shoe or hem eaten: on the floor, what the model is sure is the figure (and is drawn, not a soft
    # wash) that the cut leaves out
    sure = matte > 0.9 if matte is not None else C._figure(p)
    eaten_px = (
        sure & floor & ~mask & C._near(p.edges > C.SHADOW_EDGE, 2) & ~C._grow(mask, 3) & ~(cand & ~light)
    )
    eaten = float(eaten_px.sum() / max(1, in_floor.sum()))
    # a halo: plain paper on the cut's outermost 2 px, more than 2 px from anything drawn
    rim = mask & ~C._shrink(mask, 5)
    far = ~C._near(p.residual > p.peel, 2)
    halo = float(((p.residual <= p.threshold) & far & rim).sum() / max(1, rim.sum()))
    tile = _tile(padded, mask, Path(sheet_path).stem, view, eaten_px, shadow_px)
    _, sizes = C._components(mask)
    sizes[0] = 0
    pieces = int((sizes >= 0.3 * sizes.max()).sum()) if sizes.max() else 0
    return Result(str(sheet_path), view, method, feet, shadow, eaten, halo, pieces, tile)


def _tile(
    padded: Image.Image, mask: np.ndarray, name: str, view: int, eaten: np.ndarray, shadow: np.ndarray
) -> Image.Image:
    """The cut on a blue card with its white sticker edge (as printed), and the feet enlarged beside it (what
    the checks flag marked: left-out drawing red, shadow kept magenta)."""
    alpha = Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))
    fig = padded.convert("RGBA")
    fig.putalpha(alpha)
    edge_w = max(4, fig.height // 90)
    grown = alpha.filter(ImageFilter.GaussianBlur(edge_w / 2)).point(lambda v: 255 if v > 8 else 0)
    sticker = Image.new("RGBA", fig.size, (255, 255, 255, 0))
    sticker.putalpha(grown.filter(ImageFilter.GaussianBlur(1.2)))
    fig = Image.alpha_composite(sticker, fig)
    card = Image.new("RGBA", fig.size, (*CARD, 255))
    card.alpha_composite(fig)
    whole = card.convert("RGB")
    marked = np.asarray(whole).copy()
    marked[eaten] = (230, 30, 30)
    marked[shadow] = (230, 0, 230)
    rows = np.flatnonzero(mask.any(1))
    bottom = int(rows[-1]) if rows.size else whole.height
    top = max(0, bottom - round(0.2 * (bottom - (int(rows[0]) if rows.size else 0))))
    feet = Image.fromarray(marked).crop((0, top, whole.width, min(whole.height, bottom + 2 * edge_w + 8)))
    small = whole.resize((max(1, round(whole.width * TILE_H / whole.height)), TILE_H))
    feet = feet.resize((max(1, round(feet.width * TILE_H / feet.height)), TILE_H))
    if feet.width > 3 * TILE_H:
        feet = feet.resize((3 * TILE_H, round(feet.height * 3 * TILE_H / feet.width)))
    tile = Image.new("RGB", (small.width + feet.width + 12, TILE_H + 18), "white")
    tile.paste(small, (0, 18))
    tile.paste(feet, (small.width + 12, 18))
    ImageDraw.Draw(tile).text((2, 2), f"{name[:48]} #{view}", fill="black", font=ImageFont.load_default())
    return tile


def contact(results: list[Result], out: Path, columns: int = 4) -> None:
    tiles = []
    for r in results:
        t = r.tile.copy()
        d = ImageDraw.Draw(t)
        ok = not r.problems
        d.rectangle(
            (0, 0, t.width - 1, t.height - 1), outline=(30, 150, 60) if ok else (210, 40, 40), width=3
        )
        if not ok:
            d.text((4, t.height - 14), "; ".join(r.problems)[:70], fill=(210, 40, 40))
        tiles.append(t)
    if not tiles:
        return
    cell_w, cell_h = max(t.width for t in tiles) + 10, max(t.height for t in tiles) + 10
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (235, 235, 235))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % columns) * cell_w, (k // columns) * cell_h))
    sheet.save(out)


def sheets(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found += sorted(
                q for q in path.rglob("*") if q.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            )
        else:
            found.append(path)
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", type=Path)
    ap.add_argument("sheets", nargs="+")
    ap.add_argument("--views", default="0,1")
    ap.add_argument("--colour", action="store_true", help="the colour cut alone (no model), to compare")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    views = [int(v) for v in args.views.split(",")]
    results: list[Result] = []
    for sheet in sheets(args.sheets):
        for view in views:
            r = audit(sheet, view, not args.colour)
            if r is None:
                continue
            results.append(r)
            verdict = "PASS" if not r.problems else "FAIL " + "; ".join(r.problems)
            print(f"{sheet.name} #{view}: {verdict}", flush=True)
    with (args.out / "audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sheet", "view", "method", "feet", "shadow", "eaten", "halo", "verdict"])
        for r in results:
            w.writerow(
                [
                    r.sheet,
                    r.view,
                    r.method,
                    r.feet,
                    f"{r.shadow:.4f}",
                    f"{r.eaten:.4f}",
                    f"{r.halo:.4f}",
                    "pass" if not r.problems else "; ".join(r.problems),
                ]
            )
    lines = ["| sheet | view | shadow | eaten | halo | verdict |", "|---|---|---|---|---|---|"]
    for r in results:
        verdict = "pass" if not r.problems else "**FAIL**: " + "; ".join(r.problems)
        lines.append(
            f"| {Path(r.sheet).name} | {r.view} | {r.shadow:.1%} | {r.eaten:.1%} | {r.halo:.0%} | {verdict} |"
        )
    passed = sum(not r.problems for r in results)
    lines.append(f"\n{passed} of {len(results)} cut-outs pass.")
    (args.out / "audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    contact(results, args.out / "contact.png")
    print(f"{passed} of {len(results)} pass")


if __name__ == "__main__":
    main()
