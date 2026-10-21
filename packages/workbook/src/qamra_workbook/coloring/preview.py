"""Look at a book's scenes while drawing them (no PDF, no captions: the drawing in its frame).

    uv run python -m qamra_workbook.coloring.preview --book palestine [--only olive-harvest,sea-of-jaffa]
                                                     [--mode line|color|both] [--dpi 90] [--out DIR]

Writes DIR/<id>.<mode>.png per scene and DIR/contact-<mode>.png (all scenes on one sheet), and prints the
line-art problems of each scene (`coloring.checks`). Default DIR: out/coloring/preview/<book>.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from qamra_workbook.coloring.checks import line_problems
from qamra_workbook.coloring.scenes import SCENES, framed
from qamra_workbook.coloring.snap import snap


def contact(pngs: list[Path], out: Path, columns: int = 5, thumb_w: int = 260) -> Path:
    with Image.open(pngs[0]) as first:
        thumb_h = round(first.height * thumb_w / first.width)
    rows = (len(pngs) + columns - 1) // columns
    gap, label = 16, 22
    sheet = Image.new(
        "RGB", (columns * (thumb_w + gap) + gap, rows * (thumb_h + label + gap) + gap), "#EDEDED"
    )
    draw = ImageDraw.Draw(sheet)
    for i, png in enumerate(pngs):
        x = gap + (i % columns) * (thumb_w + gap)
        y = gap + (i // columns) * (thumb_h + label + gap)
        with Image.open(png) as img:
            sheet.paste(img.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS), (x, y))
        draw.text((x, y + thumb_h + 4), png.stem, fill="#000000")
    sheet.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--book", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--mode", default="line", choices=["line", "color", "both"])
    ap.add_argument("--dpi", type=int, default=90)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    out = args.out or Path("out/coloring/preview") / args.book
    only = {s for s in args.only.split(",") if s}
    scenes = [s for s in SCENES.values() if s.book == args.book and (not only or s.id in only)]
    if not scenes:
        raise SystemExit(f"no scenes for {args.book} {sorted(only) or ''}")
    modes = ["line", "color"] if args.mode == "both" else [args.mode]
    for mode in modes:
        drawings = {f"{s.id}.{mode}": framed(s, mode) for s in scenes}  # type: ignore[arg-type]
        if mode == "line":
            for name, markup in drawings.items():
                for problem in line_problems(markup):
                    print(f"{name}: {problem}")
        pngs = snap(drawings, out, args.dpi)
        if len(pngs) > 1:
            print(contact(pngs, out / f"contact-{mode}.png"))
        else:
            print(pngs[0])


if __name__ == "__main__":
    main()
