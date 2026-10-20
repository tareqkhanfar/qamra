r"""Outfit trial (owner, 2026-10-20: «ماذا يلبس؟»): does the sheet wear the chosen outfit, likeness kept?

The invented sample child تالا (never a real child's photo): the reference is a head-and-shoulders crop of her
published watercolor sheet (`semireal_compare.tala_reference`), as for the site's samples. For each
`STYLE=OUTFIT` item the production request builders draw her character sheet (`character_sheet.v8`) in
that outfit on the settings' sheet model; `--portrait STYLE` first draws that style's portrait
(`character_portrait.v4`, the outfit's top) and paints the sheet from it, as an order does. Each sheet is
set next to her earlier sheet in the same style (the default outfit) and the outfit's swatch, in
`--compare-dir`.

    uv run python scripts/outfit_trial.py --tala-sheet PATH --old 3d=PATH ... \
        --items watercolor=rose-dress,3d=tatreez,cartoon=yellow-cardigan --portrait 3d            # dry run
    ... --run --max-usd 0.90 --ledger LEDGER --env ENV --compare-dir DIR --swatches DIR

Prices and the cap work as in `likeness_trial.py` (its helpers): every run with the same `--prefix` together,
checked before anything is sent; a failed call is logged at full price; fal's "exhausted" stops the run.
Finished images are reused.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from likeness_trial import describe, exhausted, ledger_row, logged, provider
from semireal_compare import tala_reference

from qamra_ai.config import Settings
from qamra_ai.image.base import ImageRequest
from qamra_ai.pipeline.character import character_request, portrait_request
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.outfits import load_outfits
from qamra_ai.pipeline.theme import load_style

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = Settings(_env_file=None)  # type: ignore[call-arg]  # the production defaults
TALA = Child(name="تالا", gender="f", age=5)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def fal_key(env: Path) -> str:
    """FAL_KEY from the environment or `env`; never printed."""
    key = os.environ.get("FAL_KEY", "")
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("FAL_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit("FAL_KEY is not set (environment or --env)")
    return key


def requests(
    items: dict[str, str], portraits: set[str], out: Path
) -> list[tuple[str, str, ImageRequest | None, str]]:
    """(style, item, request or None when it waits for its portrait, model) in drawing order."""
    ref = tala_reference(ARGS.tala_sheet)
    rows: list[tuple[str, str, ImageRequest | None, str]] = []
    for style, outfit in items.items():
        child = TALA.model_copy(update={"outfit": outfit})
        art = load_style(style)
        if style in portraits:
            rows.append(
                (
                    style,
                    "portrait",
                    portrait_request(child, [ref], art, resolution=SETTINGS.character_portrait_resolution),
                    SETTINGS.character_portrait_model,
                )
            )
        portrait_file = out / f"{style}-{outfit}-portrait.png"
        portrait = portrait_file.read_bytes() if portrait_file.exists() else None
        sheet = character_request(
            child,
            [ref],
            art,
            resolution=SETTINGS.character_sheet_resolution,
            portrait=portrait if style in portraits else None,
        )
        rows.append((style, "sheet", sheet, SETTINGS.character_sheet_model))
    return rows


def label(img: Image.Image, text: str, size: int = 34) -> Image.Image:
    font = ImageFont.truetype(FONT, size)
    band = Image.new("RGB", (img.width, size + 24), (251, 246, 236))
    ImageDraw.Draw(band).text((16, 10), text, fill=(22, 32, 74), font=font)
    out = Image.new("RGB", (img.width, img.height + band.height), (251, 246, 236))
    out.paste(band, (0, 0))
    out.paste(img, (0, band.height))
    return out


def compare(style: str, outfit: str, old: Path, new: Path, swatch: Path | None, dest: Path) -> None:
    h = 900
    cells: list[Image.Image] = []
    for path, text in ((old, f"before: {style}, default outfit"), (new, f"{style} + {outfit}")):
        with Image.open(path) as im:
            img = im.convert("RGB")
        img = img.resize((round(img.width * h / img.height), h))
        cells.append(label(img, text))
    if swatch and swatch.exists():
        with Image.open(swatch) as im:
            sw = im.convert("RGB")
        sw = sw.resize((round(sw.width * h / sw.height), h))
        cells.append(label(sw, "swatch"))
    w = sum(c.width for c in cells) + 24 * (len(cells) + 1)
    sheet = Image.new("RGB", (w, cells[0].height + 48), (251, 246, 236))
    x = 24
    for c in cells:
        sheet.paste(c, (x, 24))
        x += c.width + 24
    sheet.save(dest)


async def run(args: argparse.Namespace) -> int:
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    items = dict(i.split("=", 1) for i in args.items.split(","))
    catalog = load_outfits()
    for outfit in items.values():
        o = catalog.get(outfit)
        if o is None or "f" not in o.looks:
            raise SystemExit(f"{outfit}: not a girls' outfit")
    portraits = set(filter(None, args.portrait.split(",")))
    planned = requests(items, portraits, out)
    todo: list[tuple[str, str, str, float]] = []
    for style, item, req, model in planned:
        assert req is not None
        endpoint, res, usd = describe(req, model)
        todo.append((style, item, endpoint, usd))
        print(f"{style:12} {item:8} {endpoint} {res} ${usd:.2f}  ({len(req.refs)} refs)")
    spent = logged(args.ledger, args.prefix)
    files = {(s, i): out / f"{s}-{items[s]}-{i}.png" for s, i, _, _ in todo}
    cost = sum(usd for s, i, _, usd in todo if not files[(s, i)].exists())
    print(f"logged under {args.prefix}: ${spent:.2f}; this run: ${cost:.2f}; cap ${args.max_usd:.2f}")
    if spent + cost > args.max_usd + 1e-9:
        raise SystemExit("over the cap: nothing sent")
    if not args.run:
        return 0
    key = fal_key(args.env)
    for style, item in [(s, i) for s, i, _, _ in todo]:
        dest = files[(style, item)]
        if dest.exists():
            continue
        # rebuilt now: a sheet is painted from the portrait drawn a moment ago
        req = next(r for s, i, r, _ in requests(items, portraits, out) if (s, i) == (style, item))
        model = next(m for s, i, _, m in planned if (s, i) == (style, item))
        assert req is not None
        endpoint, res, usd = describe(req, model)
        row_id = f"{args.prefix}:{style}-{items[style]}-{item}"
        t0 = time.monotonic()
        try:
            image = await provider(model, key).generate(req)
        except Exception as e:  # logged at full price, then stop
            ledger_row(
                args.ledger, {"id": row_id, "model": endpoint, "usd": usd, "res": res, "error": str(e)[:200]}
            )
            print(f"{row_id}: failed ({type(e).__name__})")
            if exhausted(e):
                print("fal balance exhausted: stopping")
            return 1
        dest.write_bytes(image.data)
        took = round(time.monotonic() - t0, 1)
        ledger_row(
            args.ledger,
            {"id": row_id, "model": endpoint, "usd": usd, "res": res, "file": str(dest), "s": took},
        )
        print(f"{row_id}: done in {took}s")
    if args.compare_dir:
        args.compare_dir.mkdir(parents=True, exist_ok=True)
        olds = dict(o.split("=", 1) for o in args.old)
        for style, outfit in items.items():
            new = files[(style, "sheet")]
            if style in olds and new.exists():
                swatch = args.swatches / f"f-{outfit}.png" if args.swatches else None
                compare(
                    style, outfit, Path(olds[style]), new, swatch, args.compare_dir / f"{style}-{outfit}.png"
                )
                for item in ("sheet", "portrait"):
                    if files.get((style, item)) and files[(style, item)].exists():
                        target = args.compare_dir / f"tala-{style}-{outfit}-{item}.png"
                        target.write_bytes(files[(style, item)].read_bytes())
        (args.compare_dir / "run.json").write_text(
            json.dumps(
                {"items": items, "portraits": sorted(portraits), "prompt": "character_sheet.v8"}, indent=2
            )
        )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tala-sheet", type=Path, required=True)
    p.add_argument("--items", default="watercolor=rose-dress,3d=tatreez,cartoon=yellow-cardigan")
    p.add_argument("--portrait", default="3d", help="styles whose portrait is drawn first (comma separated)")
    p.add_argument("--old", action="append", default=[], help="STYLE=PATH: her earlier sheet in that style")
    p.add_argument("--out", type=Path, default=ROOT / "out" / "outfit-trial")
    p.add_argument("--prefix", default="outfit-trial")
    p.add_argument("--ledger", type=Path, default=ROOT / "out" / "design-images" / "ledger.jsonl")
    p.add_argument("--env", type=Path, default=ROOT / ".env")
    p.add_argument("--max-usd", type=float, default=0.90)
    p.add_argument("--compare-dir", type=Path)
    p.add_argument("--swatches", type=Path, help="a folder of f-<outfit>.png swatches")
    p.add_argument("--run", action="store_true")
    return p.parse_args(argv)


ARGS: argparse.Namespace


def main(argv: list[str] | None = None) -> int:
    global ARGS
    ARGS = parse_args(argv)
    return asyncio.run(run(ARGS))


if __name__ == "__main__":
    raise SystemExit(main())
