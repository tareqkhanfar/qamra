r"""Colour and likeness check after the owner's live test of 2026-10-19 (portrait v3, sheet v7).

A night photo under yellow street light gave a muddy, almost sepia watercolor portrait and sheet, and a
generic cartoon boy. This draws the production path again on the same photo: the upload's framing, then the
reference with its light made neutral (`photo_color.reference_photo`), the portrait (`character_portrait.v3`)
and, when asked, the sheet (`character_sheet.v7`) on the settings' models, with the likeness notes in both
prompts.

The likeness notes come from a JSON file (`--notes`): on the server Claude writes them from the photo
(`likeness_notes.v1`); locally there is no Anthropic key, so the trial's notes are written by hand in the same
shape. Neither the photo nor the notes are written into the repo (outputs go under out/, which git ignores, or
to `--compare-dir`).

    uv run python scripts/likeness_colour_trial.py --photo PATH --gender m --age 5 --notes NOTES.json \
        --items watercolor:portrait,cartoon:portrait                                   # dry run
    ... --run --max-usd 0.55 --live watercolor:portrait=PATH --compare-dir DIR

Prices and the cap work as in `likeness_trial.py` (its helpers): every run with the same `--prefix` together,
checked for the whole batch before anything is sent; a failed call is logged at full price; fal's "exhausted"
stops the run. Portraits are drawn all at once, then sheets all at once. `STYLE:ITEM:2` is a second try (a new
seed); its sheet is painted from the same try's portrait when there is one.
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

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.photo_check import check_photo
from qamra_ai.pipeline.photo_color import neutralize
from qamra_ai.pipeline.photo_crop import crop_photo, frame_photo
from qamra_ai.pipeline.theme import load_style
from qamra_api.uploads import clean_image

Item = Literal["portrait", "sheet"]


def prepare(raw: bytes) -> tuple[bytes, bytes, str]:
    """(as sent before, as sent now, what the colour step did)."""
    stored = clean_image(raw)
    check, framing = frame_photo(stored)
    if not check.ok:
        raise SystemExit(f"the photo fails the upload check: {[i.code for i in check.issues]}")
    before = crop_photo(stored, framing)
    after, fix = neutralize(before)
    gains = ", ".join(f"{g:.3f}" for g in fix.gains)
    done = (
        f"framed={framing is not None} face={fix.face} light={fix.light} skin={fix.skin} gains=({gains}) "
        f"exposure={fix.exposure:.3f} stretch={fix.stretch:.3f} changed={fix.changed}"
    )
    return before, after, done


@dataclass(frozen=True)
class Job:
    """One drawing: a style's portrait or sheet; `attempt` > 1 is another try (another seed)."""

    style: str
    item: Item
    attempt: int = 1

    @property
    def name(self) -> str:
        return f"{self.style}-{self.item}" + (f"-a{self.attempt}" if self.attempt > 1 else "")

    def file(self, out: Path) -> Path:
        return out / f"{self.name}.png"

    def portrait_file(self, out: Path) -> Path:
        """The portrait a sheet is painted from: the same try's, else the first."""
        same = Job(self.style, "portrait", self.attempt).file(out)
        return same if same.exists() else Job(self.style, "portrait").file(out)


def parse_job(text: str) -> Job:
    parts = text.strip().split(":")
    if len(parts) not in (2, 3) or parts[1] not in ("portrait", "sheet"):
        raise ValueError(f"not STYLE:portrait|sheet[:N]: {text}")
    return Job(
        parts[0], "portrait" if parts[1] == "portrait" else "sheet", int(parts[2]) if len(parts) == 3 else 1
    )


def request(
    job: Job, child: Child, photo: bytes, notes: dict[str, str], portrait: bytes | None
) -> ImageRequest:
    s = load_style(job.style)
    if job.item == "portrait":
        return portrait_request(
            child, [photo], s, job.attempt, SETTINGS.character_portrait_resolution, notes=notes
        )
    assert portrait is not None  # nosec B101
    return character_request(
        child, [photo], s, job.attempt, SETTINGS.character_sheet_resolution, portrait=portrait, notes=notes
    )


def env_key(env: Path) -> str:
    """FAL_KEY from another .env (a worktree has none); never printed."""
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("FAL_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit(f"no FAL_KEY in {env}")


def model(item: Item) -> str:
    m = SETTINGS.character_portrait_model if item == "portrait" else SETTINGS.character_sheet_model
    return str(m).removesuffix("/edit")


@dataclass
class Run:
    child: Child
    photo: bytes
    notes: dict[str, str]
    out: Path
    key: str
    ledger: Path
    prefix: str
    stopped: bool = False


async def draw_one(job: Job, run: Run) -> str:
    target, sid = job.file(run.out), f"{run.prefix}:{job.name}"
    if target.exists():
        return f"= {sid}: reused"
    portrait = None
    if job.item == "sheet":
        pf = job.portrait_file(run.out)
        if not pf.exists():
            return f"✗ {sid}: SKIPPED, no portrait"
        portrait = pf.read_bytes()
    req = request(job, run.child, run.photo, run.notes, portrait)
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
    """All portraits at once, then all sheets at once (a sheet needs its portrait). The cap was checked
    for the whole batch before anything was sent."""
    for item in ("portrait", "sheet"):
        batch = [j for j in jobs if j.item == item]
        if run.stopped or not batch:
            continue
        for line in await asyncio.gather(*(draw_one(j, run) for j in batch)):
            print(line)


def _tile(img: Image.Image, w: int, h: int) -> Image.Image:
    img = img.convert("RGBA")
    img.thumbnail((w, h), Image.Resampling.LANCZOS)
    tile = Image.new("RGBA", (w, h), (*BACKGROUND, 255))
    tile.alpha_composite(img, ((w - img.width) // 2, (h - img.height) // 2))
    return tile.convert("RGB")


def head(photo: Path) -> Image.Image:
    """The photo around the face the upload check finds (head and shoulders), else the whole photo."""
    data = photo.read_bytes()
    with Image.open(photo) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    box = check_photo(data).face_box
    if box is None:
        return img
    x, y, w, h = box
    cx, cy, half = x + w / 2, y + h * 0.45, max(w, h) * 1.15
    left, top = max(0, round(cx - half)), max(0, round(cy - half * 1.05))
    return img.crop((left, top, min(img.width, round(cx + half)), min(img.height, round(cy + half * 1.15))))


def compare(job: Job, out: Path, live: Path | None, dest: Path) -> Path | None:
    """photo as sent (head and shoulders) | the live result | the new result, side by side."""
    style, item, new = job.style, job.item, job.file(out)
    if not new.exists():
        return None
    h = 560
    w = h if item == "portrait" else round(h * 1.5)
    gap, label_h = 14, 40
    columns: list[tuple[str, Image.Image | None, int]] = [
        ("photo (as sent to the model)", head(out / "photo-now.jpg"), h),
        (f"live {item} (portrait v2 / sheet v6)", Image.open(live) if live and live.exists() else None, w),
        (f"NEW {item} (portrait v3 / sheet v7, with notes, try {job.attempt})", Image.open(new), w),
    ]
    width = gap + sum(cw + gap for _, _, cw in columns)
    canvas = Image.new("RGB", (width, gap + label_h + h + gap), BACKGROUND)
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    x = gap
    for label, img, cw in columns:
        pen.text(
            (x, 12),
            f"{style}: {label}" if img is not None else f"{label}: none",
            fill=(30, 30, 50),
            font=font,
        )
        if img is not None:
            canvas.paste(_tile(img, cw, h), (x, gap + label_h))
        x += cw + gap
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{job.name}.jpg"
    canvas.save(path, quality=90)
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--photo", type=Path, required=True, help="the child's photo (never stored in the repo)")
    p.add_argument("--gender", choices=["m", "f"], required=True)
    p.add_argument("--age", type=int, required=True)
    p.add_argument("--notes", type=Path, required=True, help="likeness notes JSON (field → note)")
    p.add_argument(
        "--items", default="watercolor:portrait,cartoon:portrait", help="STYLE:portrait|sheet[:TRY],…"
    )
    p.add_argument("--live", action="append", default=[], help="STYLE:ITEM=PATH: the live result to compare")
    p.add_argument("--out", type=Path, default=ROOT / "out" / "likeness-v2")
    p.add_argument("--compare-dir", type=Path)
    p.add_argument("--ledger", type=Path, default=LEDGER)
    p.add_argument("--prefix", default="likeness-v2")
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
    before, now, done = prepare(args.photo.read_bytes())
    (out / "photo-before.jpg").write_bytes(before)
    (out / "photo-now.jpg").write_bytes(now)
    print(f"colour step: {done}")
    total = 0.0
    for job in jobs:
        req = request(
            job, child, now, notes, None if job.item == "portrait" else now
        )  # same prompt and price
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
        key = env_key(args.env) if args.env else fal_key()
        asyncio.run(draw(jobs, Run(child, now, notes, out, key, args.ledger, args.prefix)))
        print(f"spent with this prefix: ${logged(args.ledger, args.prefix):.2f} of ${args.max_usd:.2f}")
    live = {k: Path(v) for k, v in (x.split("=", 1) for x in args.live)}
    for job in jobs:
        path = compare(job, out, live.get(f"{job.style}:{job.item}"), args.compare_dir or out)
        if path:
            print(f"comparison: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
