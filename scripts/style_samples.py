"""Example pages per art style for the website (`apps/web/src/lib/styleSamples.ts`).

Four steps, each repeatable:

  # 1. download the published example books (watermarked web copies) from a running site, no cost:
  uv run scripts/style_samples.py fetch --base http://62.84.179.155:3300

  # 2. lay out pictures that already exist (an example's pages, `p<beat>-*.jpg`) as real book pages with
  #    the theme's own text and the current layouts: no AI, no cost.
  uv run scripts/style_samples.py reuse --theme new-sibling --style watercolor --name "تالا" --gender f \
      --age 5 --images out/style-samples/ref/new-sibling-girl --beats 0,1,7,11,13,16 \
      --out-name watercolor-new-sibling-tala

  # 3. draw the missing pages of a story in one style for an invented sample child (fal, hard budget; every
  #    paid call is appended to out/design-images/ledger.jsonl). `--ref` is a picture of the invented sample
  #    child (e.g. a published example's character sheet), never a real child's photo. `--provider sketch`
  #    is a free dry run. About $0.08 per picture (Nano Banana 2, 1K): sheet + cover + N pages.
  uv run scripts/style_samples.py draw --theme first-day --style cartoon --name "آدم" --gender m --age 4 \
      --ref out/style-samples/ref/first-day-boy/character.jpg --beats 9,11 --budget 0.32

  # 4. export SAMPLES (below) to apps/web/public/samples/<style>/:
  #    <name>.webp (900 px) and <name>-sm.webp (480 px)
  uv run scripts/style_samples.py export

Steps 2 and 3 write `<out>/<run>/proof.pdf` (the cover, then the drawn pages with the front and back matter)
and small renders of its pages in `<out>/<run>/pages/` to pick the PDF page numbers from.
"""

import argparse
import asyncio
import json
import subprocess  # nosec B404: pdftoppm with fixed arguments
import sys
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path

from PIL import Image

from qamra_ai.config import Settings
from qamra_ai.cost import CostEntry
from qamra_ai.image import make_image_provider, make_upscaler
from qamra_ai.image.base import GeneratedImage
from qamra_ai.pipeline.assemble import AssemblyInputs, assemble_book
from qamra_ai.pipeline.book import BookInputs, BookRun, default_companion, run_book
from qamra_ai.pipeline.budget import Budget
from qamra_ai.pipeline.character import generate_character_sheet
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.pages import PageResult
from qamra_ai.pipeline.plates import DirPlateStore
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_style, load_theme
from qamra_ai.text import make_text_provider
from qamra_pdf import Brand

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "style-samples"
LEDGER = ROOT / "out" / "design-images" / "ledger.jsonl"
PUBLIC = ROOT / "apps" / "web" / "public" / "samples"
SIZES = {"": 900, "-sm": 480}  # the lightbox and the carousel

GRAD_3D = "out/redesign/proof/20261003-112823-fal-graduation/proof.pdf"  # Addendum 11 §6 proof, ليان
GRAD_WC = "out/redesign/proof/20261003-110907-fal-graduation/proof.pdf"
FIRST_ADAM = "out/style-samples/watercolor-first-day-adam/proof.pdf"  # published examples, laid out (step 2)
FIRST_LAYLA = "out/style-samples/watercolor-first-day-layla/proof.pdf"
SIBLING_TALA = "out/style-samples/watercolor-new-sibling-tala/proof.pdf"
# drawn on 2026-10-09 (step 3), then laid out with `reuse` from out/style-samples/src/<run>/ (step 2)
CARTOON_ADAM = "out/style-samples/cartoon-first-day-adam/proof.pdf"
CARTOON_TALA = "out/style-samples/cartoon-new-sibling-tala/proof.pdf"
ADAM_3D = "out/style-samples/3d-first-day-adam/proof.pdf"
TALA_3D = "out/style-samples/3d-new-sibling-tala/proof.pdf"  # p1 is a rejected cover, never exported

# What the site shows: style/name ← (a proof PDF and its 1-based page) or a picture file. The alt texts and
# the order live in styleSamples.ts; this list only makes the files.
SAMPLES: list[tuple[str, str, str, int | None]] = [
    ("3d", "first-day-cover", ADAM_3D, 1),
    ("3d", "first-day-blocks", ADAM_3D, 3),
    ("3d", "first-day-yard", ADAM_3D, 4),
    ("3d", "new-sibling-bassinet", TALA_3D, 3),
    ("3d", "new-sibling-smile", TALA_3D, 4),
    ("3d", "graduation-cover", GRAD_3D, 1),
    ("3d", "graduation-mirror", GRAD_3D, 3),
    ("3d", "graduation-album", GRAD_3D, 4),
    ("3d", "graduation-teacher", GRAD_3D, 9),
    ("3d", "graduation-stage", GRAD_3D, 15),
    ("3d", "graduation-caps", GRAD_3D, 17),
    ("3d", "graduation-sunset", GRAD_3D, 19),
    ("3d", "companion", "content/cast/qamour-3d.jpg", None),
    ("watercolor", "graduation-cover", GRAD_WC, 1),
    ("watercolor", "graduation-mirror", GRAD_WC, 3),
    ("watercolor", "graduation-teacher", GRAD_WC, 9),
    ("watercolor", "graduation-stage", GRAD_WC, 15),
    ("watercolor", "graduation-caps", GRAD_WC, 17),
    ("watercolor", "graduation-sunset", GRAD_WC, 19),
    ("watercolor", "first-day-cover", FIRST_ADAM, 1),
    ("watercolor", "first-day-gate", FIRST_ADAM, 3),
    ("watercolor", "first-day-blocks", FIRST_ADAM, 5),
    ("watercolor", "first-day-yard", FIRST_ADAM, 6),
    ("watercolor", "first-day-cover-girl", FIRST_LAYLA, 1),
    ("watercolor", "first-day-walk", FIRST_LAYLA, 3),
    ("watercolor", "first-day-easel", FIRST_LAYLA, 5),
    ("watercolor", "new-sibling-cover", SIBLING_TALA, 1),
    ("watercolor", "new-sibling-news", SIBLING_TALA, 3),
    ("watercolor", "new-sibling-bassinet", SIBLING_TALA, 4),
    ("watercolor", "new-sibling-hug", SIBLING_TALA, 5),
    ("watercolor", "new-sibling-smile", SIBLING_TALA, 6),
    ("watercolor", "companion", "content/cast/qamour-watercolor.jpg", None),
    ("cartoon", "first-day-cover", CARTOON_ADAM, 1),
    ("cartoon", "first-day-blocks", CARTOON_ADAM, 3),
    ("cartoon", "first-day-yard", CARTOON_ADAM, 4),
    ("cartoon", "new-sibling-cover", CARTOON_TALA, 1),
    ("cartoon", "new-sibling-bassinet", CARTOON_TALA, 3),
    ("cartoon", "new-sibling-smile", CARTOON_TALA, 4),
    ("cartoon", "companion", "content/cast/qamour-cartoon.jpg", None),
]


def _ledger_row(entry: CostEntry, tag: str) -> None:
    if entry.provider in ("fake", "sketch"):  # offline dry runs cost nothing
        return
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"id": f"samples:{tag}:{entry.step}", "model": entry.model, "usd": round(entry.usd, 4)}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _child(args: argparse.Namespace) -> Child:
    return Child(name=args.name, gender=args.gender, age=args.age, hijab=args.hijab, glasses=args.glasses)


async def _assemble(settings: Settings, run: BookRun, child: Child, sheet: bytes, out: Path) -> None:
    assert run.story is not None  # nosec B101
    s = settings
    await assemble_book(
        AssemblyInputs(
            run=run,
            story=run.story.out,
            child=child,
            lang="ar",
            brand=Brand(
                s.brand_name_ar, s.brand_name_en, s.brand_domain, s.brand_tagline_ar, s.brand_tagline_en
            ),
            character_sheet=sheet,
            made_on=date.today(),
            watermark=False,
        ),
        out,
        print_files=False,
    )
    # a preview proof leaves out the pages not drawn: look at the pages to pick the PDF page numbers
    (out / "pages").mkdir(exist_ok=True)
    subprocess.run(  # nosec B603 B607
        ["pdftoppm", "-jpeg", "-scale-to", "450", str(out / "proof.pdf"), str(out / "pages" / "pg")],
        check=True,
    )
    print(f"✓ {out / 'proof.pdf'} · pages to look at: {out / 'pages'}")


async def draw(args: argparse.Namespace) -> int:
    settings = Settings().model_copy(
        update={
            "image_provider": args.provider,
            "text_provider": "fake",  # the theme's own text; no Claude key here, no QA calls
            "preview_resolution": "1K",  # web samples: 1K, no upscale, no watermark
            "page_max_regenerations": 0,  # a bad page is redrawn by hand, inside the same budget
            "image_concurrency": 2,
        }
    )
    if args.provider == "fal" and settings.fal_key is None:
        print("FAL_KEY is not set")
        return 2
    theme, style, child = load_theme(args.theme), load_style(args.style), _child(args)
    tag = f"{args.style}:{args.theme}"
    image = make_image_provider(settings)
    rt = Runtime(
        settings=settings,
        text=make_text_provider(settings),
        image=image,
        upscaler=make_upscaler(settings),
        budget=Budget(cap_usd=args.budget),
        on_cost=lambda e: _ledger_row(e, tag),
    )
    out = OUT / f"{time.strftime('%Y%m%d-%H%M%S')}-{args.style}-{args.theme}"
    out.mkdir(parents=True, exist_ok=True)
    print(f"→ {out} (budget ${args.budget:.2f})")
    try:
        if args.sheet:
            sheet = args.sheet.read_bytes()
        else:
            sheet = (await generate_character_sheet(rt, child, [args.ref.read_bytes()], style)).data
            (out / "character-sheet.png").write_bytes(sheet)
        inputs = BookInputs(
            child=child,
            lang="ar",
            theme=theme,
            style=style,
            character_sheet=sheet,
            companion=default_companion(theme, "ar"),
            seed=args.seed,
            cover=args.cover.read_bytes() if args.cover else None,  # an earlier run's cover: no new cover
            plates=DirPlateStore(OUT / "plate-cache"),
        )
        beats = sorted(set(args.beats) if args.cover else {0, *args.beats})
        run = await run_book(rt, inputs, mode="preview", beats=beats)
        if args.cover:  # lay out the earlier cover too
            cost = CostEntry("reuse:cover", "file", args.cover.name, {}, 0.0)
            run.pages[0] = PageResult(
                0, "ok", image=GeneratedImage(args.cover.read_bytes(), "image/png", cost)
            )
        for beat, res in sorted(run.pages.items()):
            if res.image is not None:
                (out / f"beat-{beat:02d}.png").write_bytes(res.image.data)
            print(f"  beat {beat}: {res.status} {', '.join(res.flags)}")
        await _assemble(settings, run, child, sheet, out)
    finally:
        close = getattr(image.primary, "aclose", None)
        if close:
            await close()
    (out / "cost.json").write_text(
        json.dumps(rt.ledger.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"spent ${rt.ledger.total_usd:.3f}")
    return 0


async def reuse(args: argparse.Namespace) -> int:
    settings = Settings().model_copy(update={"image_provider": "fake", "text_provider": "fake"})
    theme, style, child = load_theme(args.theme), load_style(args.style), _child(args)
    rt = Runtime(settings=settings, text=make_text_provider(settings), image=make_image_provider(settings))
    # the pictures come from books drawn with the theme's companion: its lines stay in the text (as in `draw`)
    inputs = BookInputs(
        child=child,
        lang="ar",
        theme=theme,
        style=style,
        character_sheet=b"",
        companion=default_companion(theme, "ar"),
        seed=1,
    )
    run = await run_book(rt, inputs, mode="preview", beats=[])
    for beat in args.beats:
        found = sorted(p for p in args.images.glob(f"p{beat:02d}-*") if p.suffix in (".jpg", ".png"))
        if not found:
            print(f"✗ no picture for beat {beat} in {args.images}")
            return 2
        data = found[0].read_bytes()
        mime = "image/png" if found[0].suffix == ".png" else "image/jpeg"
        cost = CostEntry(f"reuse:{beat}", "file", found[0].name, {}, 0.0)
        run.pages[beat] = PageResult(beat, "ok", image=GeneratedImage(data, mime, cost))
    sheet = next(iter(args.images.glob("character.*")), None)
    out = OUT / (args.out_name or f"{time.strftime('%Y%m%d-%H%M%S')}-reuse-{args.style}-{args.theme}")
    out.mkdir(parents=True, exist_ok=True)
    await _assemble(settings, run, child, sheet.read_bytes() if sheet else b"", out)
    return 0


def fetch(args: argparse.Namespace) -> int:
    """The published examples' pages and character sheets into out/style-samples/ref/<theme>-<look>/."""
    with urllib.request.urlopen(f"{args.base}/api/examples?lang=ar", timeout=30) as r:  # nosec B310
        examples = json.load(r)
    for e in examples:
        folder = OUT / "ref" / f"{e['theme']}-{e['variant']}"
        folder.mkdir(parents=True, exist_ok=True)
        files = [(p["image"], f"p{p['beat']:02d}-{p['layout']}.jpg") for p in e["pages"]]
        if e.get("character"):
            files.append((e["character"], "character.jpg"))
        for url, name in files:
            urllib.request.urlretrieve(args.base + url, folder / name)  # nosec B310
        print(f"{folder.relative_to(ROOT)}: {e['child_name']}, {e['style']}, {len(files)} files")
    return 0


def _picture(source: str, page: int | None, tmp: Path) -> Image.Image:
    if page is None:
        return Image.open(ROOT / source).convert("RGB")
    stem = tmp / "page"
    subprocess.run(  # nosec B603 B607
        [
            "pdftoppm",
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            "-png",
            "-scale-to",
            str(max(SIZES.values())),
            str(ROOT / source),
            str(stem),
        ],
        check=True,
    )
    return Image.open(f"{stem}.png").convert("RGB")


def export(args: argparse.Namespace) -> int:
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for style, name, source, page in SAMPLES:
            im = _picture(source, page, Path(tmp))
            for suffix, width in SIZES.items():
                target = PUBLIC / style / f"{name}{suffix}.webp"
                target.parent.mkdir(parents=True, exist_ok=True)
                copy = im.copy()
                copy.thumbnail((width, width), Image.Resampling.LANCZOS)
                copy.save(target, "WEBP", quality=args.quality, method=6)
                total += target.stat().st_size
            where = source if page is None else f"{source} p{page}"
            print(f"{style}/{name}: {im.size[0]}×{im.size[1]} from {where}")
    print(f"{len(SAMPLES)} samples, {total / 1e6:.1f} MB")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("draw", "reuse"):
        s = sub.add_parser(name)
        s.add_argument("--theme", required=True)
        s.add_argument("--style", required=True)
        s.add_argument("--name", required=True)
        s.add_argument("--gender", choices=["m", "f"], required=True)
        s.add_argument("--age", type=int, default=5)
        s.add_argument("--hijab", action="store_true")
        s.add_argument("--glasses", action="store_true")
        s.add_argument("--beats", type=lambda v: [int(x) for x in v.split(",") if x], required=True)
        if name == "draw":
            s.add_argument("--ref", type=Path, help="reference picture of the invented sample child")
            s.add_argument(
                "--sheet", type=Path, help="an existing character sheet in this style (no sheet call)"
            )
            s.add_argument("--budget", type=float, required=True, help="hard cap in USD for this run")
            s.add_argument(
                "--provider", choices=["fal", "sketch"], default="fal", help="sketch: offline dry run"
            )
            s.add_argument("--seed", type=int, default=7, help="same seed = same outfits as an earlier run")
            s.add_argument("--cover", type=Path, help="an earlier run's cover (beat-00.png): no cover call")
        else:
            s.add_argument("--images", type=Path, required=True)
            s.add_argument("--out-name", help="folder name under out/style-samples (default: a time stamp)")
    f = sub.add_parser("fetch")
    f.add_argument("--base", default="http://62.84.179.155:3300", help="a running site (it serves /api)")
    e = sub.add_parser("export")
    e.add_argument("--quality", type=int, default=80)
    args = p.parse_args(argv)
    if args.cmd == "draw" and not (args.ref or args.sheet):
        p.error("draw needs --ref or --sheet")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.cmd in ("export", "fetch"):
        return export(args) if args.cmd == "export" else fetch(args)
    return asyncio.run(draw(args) if args.cmd == "draw" else reuse(args))


if __name__ == "__main__":
    sys.exit(main())
