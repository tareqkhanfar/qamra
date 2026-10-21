r"""Face-shape trial (2026-10-21): in cartoon and 3D the child's face came out rounder, wider and younger.

The owner's report after the likeness v2 work: the hair, the eyes and the smile are close now, but in the
cartoon and 3D styles the face is rounder, wider and younger than his child's. This draws portraits of the
same photo with prompt variants on the production path (the upload's framing, the neutral reference, the
request builders the worker uses):

    A  the live prompts (`character_portrait.v4`, `likeness.v3`, style guides v3) with likeness notes
       written to the v2 notes rules (the face's proportions, no default "soft full cheeks", "rounded chin")
    B  `character_portrait.v5` (`likeness.v4`: the FACE SHAPE block, the measured face proportion, the age
       as a face of that age) with the same notes; style guides v3
    C  B with candidate style guides (`--style-dir`: cartoon and 3D v4, no "soft", "simple shapes" or
       "appealing" face; the child a cartoonist's portrait or a 3D likeness of a real child)

and then sheets (`character_sheet.v10`: one direction per view, the whole figure turned that way, both shoes
inside the picture) from a variant's portrait, or from an earlier portrait (`--portrait STYLE=PATH`, variant
`L`: the live style guide with the v10 templates).

Notes come from a JSON file (`--notes`); there is no Anthropic key here, so they are written by hand from the
photo following the notes prompt's rules (the server writes its own). Nothing of the photo goes into the repo:
outputs under out/ (git-ignored) or `--compare-dir`. Prices, the cap, the ledger and the "exhausted" stop work
as in `likeness_trial.py`.

    uv run python scripts/face_shape_trial.py --photo PATH --gender m --age 5 --notes NOTES.json \
        --items cartoon:A:portrait,cartoon:B:portrait,3d:C:portrait                    # dry run
    ... --run --max-usd 1.50 --ledger LEDGER --env ENV --live cartoon=PATH --compare-dir DIR
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from likeness_colour_trial import _tile, env_key, head, model, prepare
from likeness_trial import (
    BACKGROUND,
    LEDGER,
    ROOT,
    SETTINGS,
    describe,
    exhausted,
    fal_key,
    ledger_row,
    logged,
    provider,
)

from qamra_ai.image.base import ImageRequest
from qamra_ai.pipeline.character import character_request, portrait_request
from qamra_ai.pipeline.face_shape import face_shape, measure_face
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.style import parse_style_guide
from qamra_ai.pipeline.theme import ArtStyle, art_style, load_style

Item = Literal["portrait", "sheet"]
# variant → (portrait template, sheet template, measured face shape, candidate style guide)
VARIANTS: dict[str, tuple[int, int, bool, bool]] = {
    "A": (4, 10, False, False),
    "B": (5, 10, True, False),
    "C": (5, 10, True, True),
    "D": (5, 10, True, True),  # C with another candidate guide (`--style-dir D=PATH`)
    "L": (5, 10, True, False),  # a sheet from an earlier portrait (`--portrait`), live style guide
}


@dataclass(frozen=True)
class Job:
    style: str
    variant: str
    item: Item

    @property
    def name(self) -> str:
        return f"{self.style}-{self.variant}-{self.item}"

    def file(self, out: Path) -> Path:
        return out / f"{self.name}.png"


def parse_job(text: str) -> Job:
    parts = text.strip().split(":")
    if len(parts) != 3 or parts[1] not in VARIANTS or parts[2] not in ("portrait", "sheet"):
        raise ValueError(f"not STYLE:VARIANT:portrait|sheet: {text}")
    return Job(parts[0], parts[1], "portrait" if parts[2] == "portrait" else "sheet")


def style_for(job: Job, style_dirs: dict[str, Path]) -> ArtStyle:
    if VARIANTS[job.variant][3]:
        folder = style_dirs.get(job.variant)
        if folder is None or not (folder / f"{job.style}.md").exists():
            raise SystemExit(
                f"variant {job.variant} needs --style-dir {job.variant}=PATH with {job.style}.md"
            )
        return art_style(parse_style_guide((folder / f"{job.style}.md").read_text(encoding="utf-8")))
    return load_style(job.style)


@dataclass
class Run:
    child: Child
    photo: bytes
    notes: dict[str, str]
    shape: str | None
    out: Path
    style_dirs: dict[str, Path]
    portraits: dict[str, Path]
    key: str
    ledger: Path
    prefix: str
    stopped: bool = False


def portrait_for(job: Job, run: Run) -> Path:
    if job.variant == "L":
        return run.portraits[job.style]
    return Job(job.style, job.variant, "portrait").file(run.out)


def request(job: Job, run: Run, portrait: bytes | None) -> ImageRequest:
    pv, sv, measured, _ = VARIANTS[job.variant]
    s = style_for(job, run.style_dirs)
    shape = run.shape if measured else None
    if job.item == "portrait":
        return portrait_request(
            run.child,
            [run.photo],
            s,
            1,
            SETTINGS.character_portrait_resolution,
            version=pv,
            notes=run.notes,
            face_shape=shape,
        )
    return character_request(
        run.child,
        [run.photo],
        s,
        1,
        SETTINGS.character_sheet_resolution,
        version=sv,
        portrait=portrait or run.photo,
        notes=run.notes,
        face_shape=shape,
    )


async def draw_one(job: Job, run: Run) -> str:
    target, sid = job.file(run.out), f"{run.prefix}:{job.name}"
    if target.exists():
        return f"= {sid}: reused"
    portrait = None
    if job.item == "sheet":
        pf = portrait_for(job, run)
        if not pf.exists():
            return f"✗ {sid}: SKIPPED, no portrait"
        portrait = pf.read_bytes()
    req = request(job, run, portrait)
    endpoint, res, usd = describe(req, model(job.item))
    base = {"id": sid, "model": endpoint, "usd": usd, "res": res}
    fal = provider(model(job.item), run.key)
    t = time.time()
    try:
        image = await fal.generate(req)
    except Exception as e:
        if exhausted(e):
            run.stopped = True
            ledger_row(run.ledger, {**base, "usd": 0.0, "error": "fal_exhausted"})
            return f"✗ {sid}: fal says exhausted or locked: STOPPED"
        ledger_row(run.ledger, {**base, "error": type(e).__name__, "s": round(time.time() - t, 1)})
        return f"✗ {sid}: {type(e).__name__}: {str(e)[:160]}"
    finally:
        close = getattr(fal, "aclose", None)
        if close is not None:
            await close()
    target.write_bytes(image.data)
    ledger_row(run.ledger, {**base, "file": str(target), "s": round(time.time() - t, 1)})
    return f"✓ {sid}: ${usd:.2f} ({time.time() - t:.0f}s)"


async def draw(jobs: list[Job], run: Run) -> None:
    for item in ("portrait", "sheet"):
        batch = [j for j in jobs if j.item == item]
        if run.stopped or not batch:
            continue
        for line in await asyncio.gather(*(draw_one(j, run) for j in batch)):
            print(line)


def ratio_label(path: Path) -> str:
    shape = measure_face(path.read_bytes())
    return f" (w/l {shape.ratio:.2f})" if shape else ""


def compare_row(title: str, columns: list[tuple[str, Path | None]], dest: Path, wide: bool) -> Path:
    """One row: labelled pictures side by side (the photo first)."""
    h = 520
    gap, label_h = 14, 64
    widths = [h if i == 0 or not wide else round(h * 1.5) for i in range(len(columns))]
    width = gap + sum(w + gap for w in widths)
    canvas = Image.new("RGB", (width, gap + label_h + h + gap), BACKGROUND)
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=17)
    x = gap
    for (label, path), w in zip(columns, widths, strict=True):
        lines = label.split("\n")
        for i, line in enumerate(lines):
            pen.text((x, 10 + i * 22), line, fill=(30, 30, 50), font=font)
        if path is not None and path.exists():
            img = head(path) if path.suffix == ".jpg" and "photo" in path.name else Image.open(path)
            canvas.paste(_tile(img, w, h), (x, gap + label_h))
        x += w + gap
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"{title}.jpg"
    canvas.save(out, quality=90)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--photo", type=Path, required=True, help="the child's photo (never stored in the repo)")
    p.add_argument("--gender", choices=["m", "f"], required=True)
    p.add_argument("--age", type=int, required=True)
    p.add_argument("--notes", type=Path, required=True, help="likeness notes JSON (field → note)")
    p.add_argument("--items", required=True, help="STYLE:VARIANT:portrait|sheet,…")
    p.add_argument(
        "--style-dir", action="append", default=[], help="VARIANT=PATH: candidate style guides (C, D)"
    )
    p.add_argument(
        "--portrait", action="append", default=[], help="STYLE=PATH: an earlier portrait (variant L)"
    )
    p.add_argument("--live", action="append", default=[], help="STYLE:ITEM=PATH: the live result to compare")
    p.add_argument("--out", type=Path, default=ROOT / "out" / "face-shape")
    p.add_argument("--compare-dir", type=Path)
    p.add_argument("--ledger", type=Path, default=LEDGER)
    p.add_argument("--prefix", default="face-shape")
    p.add_argument("--env", type=Path, help="a .env with FAL_KEY (default: the environment or the repo's)")
    p.add_argument("--run", action="store_true")
    p.add_argument("--max-usd", type=float)
    args = p.parse_args(argv)
    if args.run and args.max_usd is None:
        p.error("--run needs --max-usd")
    try:
        jobs = [parse_job(it) for it in args.items.split(",")]
    except ValueError as e:
        p.error(str(e))
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    child = Child(name="child", gender=args.gender, age=args.age)
    notes = {str(k): str(v) for k, v in json.loads(args.notes.read_text(encoding="utf-8")).items() if v}
    _, now, done = prepare(args.photo.read_bytes())
    (out / "photo-now.jpg").write_bytes(now)
    shape = face_shape([now])
    print(f"colour step: {done}")
    print(f"measured: {shape}")
    portraits = {k: Path(v) for k, v in (x.split("=", 1) for x in args.portrait)}
    style_dirs = {k: Path(v) for k, v in (x.split("=", 1) for x in args.style_dir)}
    run = Run(child, now, notes, shape, out, style_dirs, portraits, "", args.ledger, args.prefix)
    total = 0.0
    for job in jobs:
        req = request(job, run, None)  # same prompt and price as with the portrait
        endpoint, res, usd = describe(req, model(job.item))
        reused = job.file(out).exists()
        total += 0.0 if reused else usd
        print(f"{job.name:<28} {endpoint:<32} {res} {'reused' if reused else f'${usd:.2f}'}")
        (out / f"{job.name}.prompt.txt").write_text(req.prompt, encoding="utf-8")
    spent = logged(args.ledger, args.prefix)
    print(f"${total:.2f} to spend; ${spent:.2f} logged with this prefix")
    if args.run:
        if spent + total > args.max_usd + 1e-9:
            raise SystemExit(
                f"over the cap: ${spent:.2f} spent + ${total:.2f} > ${args.max_usd:.2f}; nothing sent"
            )
        run.key = env_key(args.env) if args.env else fal_key()
        asyncio.run(draw(jobs, run))
        print(f"spent with this prefix: ${logged(args.ledger, args.prefix):.2f} of ${args.max_usd:.2f}")
    if args.compare_dir:
        live = {k: Path(v) for k, v in (x.split("=", 1) for x in args.live)}
        photo = out / "photo-now.jpg"
        for style in dict.fromkeys(j.style for j in jobs):
            for item in ("portrait", "sheet"):
                mine = [j for j in jobs if j.style == style and j.item == item and j.file(out).exists()]
                if not mine:
                    continue
                cols: list[tuple[str, Path | None]] = [(f"{style}: photo{ratio_label(photo)}", photo)]
                lv = live.get(f"{style}:{item}")
                if lv is not None:
                    cols.append((f"live {item}{ratio_label(lv) if item == 'portrait' else ''}", lv))
                for j in mine:
                    pv, sv, _, cand = VARIANTS[j.variant]
                    tmpl = f"portrait v{pv}" if item == "portrait" else f"sheet v{sv}"
                    guide = f"guide v4 (candidate {j.variant})" if cand else "guide v3"
                    r = ratio_label(j.file(out)) if item == "portrait" else ""
                    cols.append((f"{j.variant}: {tmpl}, {guide}{r}", j.file(out)))
                print(
                    f"comparison: {compare_row(f'{style}-{item}', cols, args.compare_dir, item == 'sheet')}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
