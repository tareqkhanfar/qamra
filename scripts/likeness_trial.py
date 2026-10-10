r"""Likeness trial: does the child on the character sheet look like the child in the photo? (2026-10-10)

Live sheets from a real photo came out as a generic, younger, rounder child in every style. On the production
prompt path (the request builders the worker uses, the house style merged per style, the photo prepared
exactly like an upload), for each style asked:

    N1  the trial's one step: the sheet on Nano Banana Pro edit at 2K with `character_sheet.v5`
    N2  the trial's portrait first: `character_portrait.v1` (Pro, 1K), then the v5 sheet from photo + portrait
    P   production, portrait first: `character_portrait.v2` then `character_sheet.v6`, on the models and
        resolutions of the settings (`character_*_model`, `character_*_resolution`), plus, for the styles in
        `--page-styles`, one story page on the page model with the sheet and the portrait as references, and
        the activity books' cut-out of the sheet (local, free)

The photo goes through what an upload goes through: `qamra_api.uploads.clean_image`, then the create flow's
framing (`qamra_ai.pipeline.photo_crop.frame_photo`: the photo check, a head-and-shoulders framing around the
face, or the whole photo when the framing fails, as for a close-up), then `crop_photo`, which is what the
worker sends. The photo is a CLI argument only; nothing here is written into the repo (outputs go under out/,
which git ignores, or to `--compare-dir`).

    uv run python scripts/likeness_trial.py --photo PATH --gender m --age 5 --approaches P   # dry run
    uv run python scripts/likeness_trial.py --photo PATH --gender m --age 5 --approaches P \
        --prefix likeness-v6 --run --max-usd 1.60 --live 3d=PATH --compare-dir DIR

Prices: fal's published prices (Nano Banana Pro edit $0.15 at 1K and 2K; Nano Banana 2 edit $0.08 at 1K,
checked 2026-10-10), never below pricing.yaml. The cap covers every run with the same `--prefix` (its ledger
rows) plus this run's reservations. A failed call is logged at full price; fal's "exhausted" or "locked"
stops the run (nothing was billed). Finished images are reused. One comparison image per style: face
close-ups on top, the whole pictures below.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from qamra_workbook.render.character import front_view, is_fallback

from qamra_ai.config import Settings
from qamra_ai.cost import fal_cost
from qamra_ai.image.base import ImageRequest, Resolution
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.image.fal import FalImageProvider
from qamra_ai.pipeline.character import LIKENESS_SHEET_VERSION, character_request, portrait_request
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.pages import BookContext, page_request
from qamra_ai.pipeline.photo_check import PhotoCheck, detect_faces
from qamra_ai.pipeline.photo_crop import crop_photo, frame_photo
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import load_style, load_theme
from qamra_api.uploads import clean_image

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "out" / "design-images" / "ledger.jsonl"
PRO, NB2 = "fal-ai/nano-banana-pro", "fal-ai/nano-banana-2"
REAL_USD: dict[tuple[str, str], float] = {
    (f"{PRO}/edit", "1K"): 0.15,
    (f"{PRO}/edit", "2K"): 0.15,
    (f"{NB2}/edit", "1K"): 0.08,
}
SETTINGS = Settings(_env_file=None)  # type: ignore[call-arg]  # the production defaults
TRIAL_SHEET_RES: Resolution = "2K"
TRIAL_PORTRAIT_RES: Resolution = "1K"
PAGE_RES: Resolution = "1K"
THEME, BEAT, SEED = "new-sibling", 13, 7  # the site's «smile» page, as in the semi-realistic grid
STYLES = ("3d", "semi-realistic", "cartoon", "watercolor")
Approach = Literal["N1", "N2", "P"]
Item = Literal["portrait", "sheet", "page"]


@dataclass(frozen=True)
class Step:
    style: str
    approach: Approach
    item: Item

    def id(self, prefix: str) -> str:
        return f"{prefix}:{self.style}:{self.approach}:{self.item}"

    def file(self, out: Path) -> Path:
        return out / f"{self.style}-{self.approach}-{self.item}.png"

    @property
    def model(self) -> str:
        if self.approach != "P":
            return PRO
        if self.item == "page":
            return SETTINGS.fal_image_model
        model = (
            SETTINGS.character_portrait_model if self.item == "portrait" else SETTINGS.character_sheet_model
        )
        return model.removesuffix("/edit")


def steps(styles: list[str], approaches: list[Approach], page_styles: list[str]) -> list[Step]:
    out: list[Step] = []
    for style in styles:
        if "N1" in approaches:
            out.append(Step(style, "N1", "sheet"))
        if "N2" in approaches:
            out += [Step(style, "N2", "portrait"), Step(style, "N2", "sheet")]
        if "P" in approaches:
            out += [Step(style, "P", "portrait"), Step(style, "P", "sheet")]
            if style in page_styles:
                out.append(Step(style, "P", "page"))
    return out


def price(endpoint: str, resolution: str) -> float:
    real = REAL_USD.get((endpoint, resolution))
    if real is None:
        raise SystemExit(f"no checked price for {endpoint} at {resolution}: check fal's page first")
    listed = fal_cost(endpoint, resolution=resolution) or 0.0
    return math.ceil(max(real, listed) * 100 - 1e-9) / 100


# ---- the photo, as an order sends it ------------------------------------------------------------------


def prepare_photo(raw: bytes) -> tuple[bytes, PhotoCheck, bool]:
    """Upload → `clean_image` → the create flow's check and framing → what the worker sends (`crop_photo`):
    (photo, check on it, framed or whole)."""
    stored = clean_image(raw)
    check, framing = frame_photo(stored)
    if not check.ok:
        raise SystemExit(
            f"the photo fails the upload check: {[i.code for i in check.issues]} {check.metrics}"
        )
    return crop_photo(stored, framing), check, framing is not None


# ---- requests -----------------------------------------------------------------------------------------


def _rt() -> Runtime:
    settings = SETTINGS.model_copy(update={"preview_resolution": PAGE_RES})
    return Runtime(settings=settings, text=None, image=FakeImageProvider())  # type: ignore[arg-type]


def page_req(step: Step, child: Child, sheet: bytes, portrait: bytes) -> ImageRequest:
    theme = load_theme(THEME)
    ctx = BookContext(
        child=child,
        lang="ar",
        theme=theme,
        style=load_style(step.style),
        house=house_style(),
        plan=plan_book(theme, "ar", companion_page=False),
        character_sheet=sheet,
        outfits={},
        seed=SEED,
        mode="preview",  # 1K here (`_rt`)
        companion=None,  # the hero alone next to the baby: no companion sheet to draw
        portrait=portrait,
    )
    return page_request(_rt(), ctx, BEAT, 1)


def request(
    step: Step, child: Child, photo: bytes, portrait: bytes | None, sheet: bytes | None
) -> ImageRequest:
    style = load_style(step.style)
    if step.approach == "P":  # production: the builders' own versions and the settings' resolutions
        if step.item == "portrait":
            return portrait_request(child, [photo], style, resolution=SETTINGS.character_portrait_resolution)
        if step.item == "sheet":
            assert portrait is not None  # nosec B101
            return character_request(
                child, [photo], style, resolution=SETTINGS.character_sheet_resolution, portrait=portrait
            )
        assert portrait is not None and sheet is not None  # nosec B101
        return page_req(step, child, sheet, portrait)
    if step.item == "portrait":
        return portrait_request(child, [photo], style, resolution=TRIAL_PORTRAIT_RES, version=1)
    return character_request(
        child,
        [photo],
        style,
        resolution=TRIAL_SHEET_RES,
        version=LIKENESS_SHEET_VERSION,
        portrait=portrait if step.approach == "N2" else None,
    )


class _NoNetwork:
    async def subscribe(self, application: str, arguments: dict[str, Any], **_: Any) -> Any:
        raise RuntimeError("dry run: no network")


def provider(model: str, key: str | None) -> FalImageProvider:
    return FalImageProvider(key, model) if key else FalImageProvider(None, model, client=_NoNetwork())


def describe(req: ImageRequest, model: str) -> tuple[str, str, float]:
    endpoint, args, _ = provider(model, None).build(req)
    res = str(args.get("resolution", req.resolution))
    return endpoint, res, price(endpoint, res)


def inputs(step: Step, out: Path, photo: bytes) -> tuple[bytes | None, bytes | None]:
    """(portrait, sheet) this step is drawn from, when drawn already; in a dry run the photo stands in."""
    portrait_file = Step(step.style, step.approach, "portrait").file(out)
    sheet_file = Step(step.style, step.approach, "sheet").file(out)
    portrait = portrait_file.read_bytes() if portrait_file.exists() else None
    sheet = sheet_file.read_bytes() if sheet_file.exists() else None
    return portrait, sheet


# ---- the ledger and the cap -----------------------------------------------------------------------------


def logged(ledger: Path, prefix: str) -> float:
    if not ledger.exists():
        return 0.0
    rows = (json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip())
    return float(sum(r.get("usd", 0.0) for r in rows if str(r.get("id", "")).startswith(f"{prefix}:")))


def ledger_row(ledger: Path, row: dict[str, Any]) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def exhausted(e: Exception) -> bool:
    text = str(e).lower()
    return "exhausted" in text or "locked" in text


def fal_key() -> str:
    """FAL_KEY from the environment or the repo's .env; never printed."""
    key = os.environ.get("FAL_KEY", "")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("FAL_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit("FAL_KEY is not set (environment or .env)")
    return key


class Budget:
    def __init__(self, cap: float, spent: float) -> None:
        self.cap, self.spent, self.lock, self.stopped = cap, spent, asyncio.Lock(), False

    async def reserve(self, usd: float) -> bool:
        async with self.lock:
            if self.stopped or self.spent + usd > self.cap + 1e-9:
                return False
            self.spent += usd
            return True


@dataclass
class Run:
    child: Child
    photo: bytes
    out: Path
    key: str
    budget: Budget
    ledger: Path
    prefix: str


async def run_style(style: str, todo: list[Step], run: Run) -> list[str]:
    """One style's steps in order (a sheet needs its portrait, a page its sheet)."""
    lines: list[str] = []
    for step in (s for s in todo if s.style == style):
        target, sid = step.file(run.out), step.id(run.prefix)
        if target.exists():
            lines.append(f"= {sid}: reused")
            continue
        portrait, sheet = inputs(step, run.out, run.photo)
        needs_portrait = step.item != "portrait" and step.approach in ("N2", "P")
        if (needs_portrait and portrait is None) or (step.item == "page" and sheet is None):
            lines.append(f"✗ {sid}: SKIPPED, what it is drawn from is missing")
            continue
        req = request(step, run.child, run.photo, portrait, sheet)
        endpoint, res, usd = describe(req, step.model)
        if not await run.budget.reserve(usd):
            lines.append(f"✗ {sid}: SKIPPED (cap ${run.budget.cap:.2f}, or the run stopped)")
            continue
        t = time.time()
        base = {"id": sid, "model": endpoint, "usd": usd, "res": res}
        fal = provider(step.model, run.key)
        try:
            image = await fal.generate(req)
        except Exception as e:  # logged at full price, except an empty account (nothing billed: stop)
            if exhausted(e):
                run.budget.stopped = True
                run.budget.spent -= usd
                ledger_row(run.ledger, {**base, "usd": 0.0, "error": "fal_exhausted"})
                lines.append(f"✗ {sid}: fal says exhausted or locked: STOPPED")
                break
            ledger_row(run.ledger, {**base, "error": type(e).__name__, "s": round(time.time() - t, 1)})
            lines.append(f"✗ {sid}: {type(e).__name__}: {str(e)[:160]}")
            continue
        finally:
            close = getattr(fal, "aclose", None)
            if close is not None:
                await close()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image.data)
        ledger_row(run.ledger, {**base, "file": str(target), "s": round(time.time() - t, 1)})
        lines.append(f"✓ {sid}: ${usd:.2f} ({time.time() - t:.0f}s)")
    return lines


# ---- the comparison -------------------------------------------------------------------------------------


def _faces(img: Image.Image) -> list[tuple[int, int, int, int, float]]:
    """(x, y, w, h, score) of the faces YuNet finds, left to right."""
    rgb = np.asarray(img.convert("RGB"))[:, :, ::-1].copy()
    scale = min(1.0, 1600 / max(img.size))
    small = np.ascontiguousarray(rgb[:: max(1, round(1 / scale)), :: max(1, round(1 / scale))])
    step = rgb.shape[1] / small.shape[1]
    found = detect_faces(small)
    faces = [
        (int(f[0] * step), int(f[1] * step), int(f[2] * step), int(f[3] * step), float(f[-1])) for f in found
    ]
    return sorted(faces, key=lambda f: f[0])


BACKGROUND = (246, 241, 230)


def face_crop(
    path: Path, side: int, *, pick: Literal["left", "best", "largest"], face: tuple[int, int, int, int] | None
) -> Image.Image:
    """The face, squared with room for the hair and chin: `face` when given (the photo check's own box), else
    on a sheet the leftmost (the front view), on a portrait the surest one, on a page the largest. Past the
    picture's edge the crop is the comparison's background (never black)."""
    with Image.open(path) as im:
        rgba = ImageOps.exif_transpose(im).convert("RGBA")  # a cut-out is transparent around the figure
    img = Image.new("RGB", rgba.size, BACKGROUND)
    img.paste(rgba, (0, 0), rgba)
    faces = [(*face, 1.0)] if face else _faces(img)
    if faces:
        chosen = {
            "left": faces[0],
            "best": max(faces, key=lambda f: f[4]),
            "largest": max(faces, key=lambda f: f[2] * f[3]),
        }[pick]
        x, y, w, h, _ = chosen
        cx, cy, half = x + w / 2, y + h * 0.42, max(w, h) * 1.05
    else:  # no face found: the top of the leftmost third (a sheet's front view), or the middle
        third = img.width / 3 if img.width > img.height * 1.2 else img.width
        cx, cy, half = third / 2, img.height * 0.2, min(third, img.height) * 0.22
    left, top = round(cx - half), round(cy - half)
    size = round(2 * half)
    inside = (max(0, left), max(0, top), min(img.width, left + size), min(img.height, top + size))
    crop = Image.new("RGB", (size, size), BACKGROUND)
    crop.paste(img.crop(inside), (inside[0] - left, inside[1] - top))
    return crop.resize((side, side), Image.Resampling.LANCZOS)


def cutouts(styles: list[str], out: Path) -> dict[str, Path]:
    """The activity books' figure (the front view cut out of each production sheet), as the books make it."""
    found: dict[str, Path] = {}
    for style in styles:
        sheet = Step(style, "P", "sheet").file(out)
        if sheet.exists():
            path = front_view(sheet, out / "figures")
            found[style] = path
            print(
                f"  {style} cut-out: {'FRAMED PORTRAIT (cut-out failed)' if is_fallback(path) else 'cut out'}"
            )
    return found


def compare(
    style: str,
    photo: bytes,
    face: tuple[int, int, int, int] | None,
    live: Path | None,
    out: Path,
    dest: Path,
    figure: Path | None,
) -> Path:
    side, gap, label_h = 340, 12, 34
    columns: list[tuple[str, Path | None, Literal["left", "best", "largest"]]] = [
        ("photo (as sent)", out / "photo-as-sent.jpg", "best"),
        ("live sheet (NB2 1K, v3)", live, "left"),
        ("N1 sheet (Pro 2K, v5)", Step(style, "N1", "sheet").file(out), "left"),
        ("N2 portrait (Pro, v1)", Step(style, "N2", "portrait").file(out), "best"),
        ("N2 sheet (Pro, v5)", Step(style, "N2", "sheet").file(out), "left"),
        ("NEW portrait (Pro 1K, v2)", Step(style, "P", "portrait").file(out), "best"),
        ("NEW sheet (Pro 2K, v6)", Step(style, "P", "sheet").file(out), "left"),
        ("NEW page (NB2 1K)", Step(style, "P", "page").file(out), "largest"),
        ("NEW activity cut-out", figure, "best"),
    ]
    (out / "photo-as-sent.jpg").write_bytes(photo)
    width = gap + len(columns) * (side + gap)
    height = gap + label_h + side + gap + side + gap
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=15)
    pen.text((gap, 4), style, fill=(20, 20, 40), font=ImageFont.load_default(size=20))
    for i, (label, src, pick) in enumerate(columns):
        x = gap + i * (side + gap)
        pen.text((x, label_h - 8), label, fill=(30, 30, 50), font=font)
        y = gap + label_h
        if src is None or not src.exists():
            pen.rectangle((x, y, x + side, y + side), outline=(180, 170, 150))
            pen.text((x + 12, y + 12), "none", fill=(120, 110, 100), font=font)
            continue
        canvas.paste(face_crop(src, side, pick=pick, face=face if i == 0 else None), (x, y))
        with Image.open(src) as im:
            whole = im.convert("RGBA")
        whole.thumbnail((side, side), Image.Resampling.LANCZOS)
        tile = Image.new("RGBA", (side, side), (*BACKGROUND, 255))
        tile.alpha_composite(whole, ((side - whole.width) // 2, (side - whole.height) // 2))
        canvas.paste(tile.convert("RGB"), (x, y + side + gap))
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"likeness-{style}.jpg"
    canvas.save(path, quality=90)
    return path


# ---- main -----------------------------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--photo", type=Path, required=True, help="the child's photo (never stored in the repo)")
    p.add_argument("--gender", choices=["m", "f"], required=True)
    p.add_argument("--age", type=int, required=True)
    p.add_argument("--hijab", action="store_true")
    p.add_argument("--glasses", action="store_true")
    p.add_argument("--styles", default=",".join(STYLES))
    p.add_argument("--approaches", default="N1,N2", help="any of N1, N2, P (production)")
    p.add_argument("--page-styles", default="3d,semi-realistic", help="P: the styles that get a story page")
    p.add_argument("--live", action="append", default=[], help="STYLE=PATH: the live sheet to compare")
    p.add_argument("--out", type=Path, help="default: out/likeness-trial/<photo name>")
    p.add_argument("--compare-dir", type=Path, help="where the comparison images go (default: --out)")
    p.add_argument("--ledger", type=Path, default=LEDGER, help="the shared spend ledger")
    p.add_argument("--prefix", default="likeness", help="ledger id prefix; the cap counts this prefix's rows")
    p.add_argument("--run", action="store_true", help="draw on fal (without it: a dry run)")
    p.add_argument("--max-usd", type=float, help="hard cap for every run with this prefix together")
    p.add_argument("--compare-only", action="store_true", help="only (re)build the comparison images")
    args = p.parse_args(argv)
    if args.run and args.max_usd is None:
        p.error("--run needs --max-usd")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    styles = [s.strip() for s in args.styles.split(",") if s.strip()]
    approaches: list[Approach] = [a for a in ("N1", "N2", "P") if a in args.approaches.split(",")]
    page_styles = [s.strip() for s in args.page_styles.split(",") if s.strip()]
    out: Path = args.out or ROOT / "out" / "likeness-trial" / args.photo.stem
    out.mkdir(parents=True, exist_ok=True)
    child = Child(name="child", gender=args.gender, age=args.age, hijab=args.hijab, glasses=args.glasses)
    photo, check, framed = prepare_photo(args.photo.read_bytes())
    m = check.metrics
    print(
        f"photo: {'framed (head and shoulders)' if framed else 'whole (the framing failed the check)'} → "
        f"{int(m['width'])}×{int(m['height'])}, {int(m['faces'])} face (score {m['face_score']}, "
        f"{m['face_ratio']:.0%} of the width), sharpness {m['sharpness']}"
    )
    todo = steps(styles, approaches, page_styles)
    earlier = logged(args.ledger, args.prefix)
    total = 0.0
    for s in todo:
        portrait, sheet = inputs(s, out, photo)
        req = request(s, child, photo, portrait or photo, sheet or photo)  # a stand-in: same prompt and price
        endpoint, res, usd = describe(req, s.model)
        reused = s.file(out).exists()
        total += 0.0 if reused else usd
        cost = "reused" if reused else f"{usd:.2f}"
        print(f"{s.id(args.prefix):<42} {endpoint:<28} {res:<3} {len(req.refs)} refs {cost:>6} {total:>6.2f}")
    print(f"{len(todo)} calls, ${total:.2f} to spend; earlier runs with this prefix logged ${earlier:.2f}")
    live = dict(item.split("=", 1) for item in args.live)
    if args.run and not args.compare_only:
        run = Run(child, photo, out, fal_key(), Budget(args.max_usd, earlier), args.ledger, args.prefix)

        async def go() -> list[list[str]]:
            return await asyncio.gather(*(run_style(s, todo, run) for s in styles))

        for lines in asyncio.run(go()):
            print("\n".join(lines))
        print(
            f"spend with this prefix (ledger): ${logged(args.ledger, args.prefix):.2f} of ${args.max_usd:.2f}"
        )
    elif not args.run and not args.compare_only:
        print("dry run: nothing was sent (add --run --max-usd X to draw)")
        return 0
    figures = cutouts(styles, out) if "P" in approaches else {}
    dest: Path = args.compare_dir or out
    for style in styles:
        live_sheet = Path(live[style]) if style in live else None
        path = compare(style, photo, check.face_box, live_sheet, out, dest, figures.get(style))
        print(f"comparison: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
