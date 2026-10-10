r"""Likeness trial: does the child on the character sheet look like the child in the photo? (2026-10-10)

Live sheets from a real photo came out as a generic, younger, rounder child in every style. Two candidates,
both on the production prompt path (`character_request` / `portrait_request`, the house style merged per
style, the photo prepared like an upload), for each style asked:

    N1  one step: the sheet on Nano Banana Pro edit at 2K with the likeness-tuned `character_sheet.v5`
    N2  portrait first: a large head-and-shoulders portrait in the style (`character_portrait.v1`, Pro edit,
        1K), then the sheet from [photo + portrait] (`character_sheet.v5`, Pro edit, 2K)

The photo goes through what an upload goes through: `qamra_api.uploads.clean_image`, the photo check, then a
head-and-shoulders framing around the face found (the constants of the create flow's auto-framing: the face
box takes 42% of a 358 × 340 frame's height, centred at 45%), re-encoded as the image model gets it. The photo
is a CLI argument only; nothing here is written into the repo (outputs go under out/, which git ignores, or
to `--compare-dir`).

    uv run python scripts/likeness_trial.py --photo PATH --gender m --age 5     # dry run: calls, prices
    uv run python scripts/likeness_trial.py --photo PATH --gender m --age 5 --run --max-usd 2.00 \
        --live 3d=PATH --live watercolor=PATH --compare-dir DIR

Prices: fal's published prices (Nano Banana Pro edit $0.15 at 1K and 2K, checked 2026-10-10), never below
pricing.yaml. The cap covers every run of this script (`likeness:` rows of the ledger) plus this run's
reservations. A failed call is logged at full price; fal's "exhausted" or "locked" stops the run (nothing was
billed). Finished images are reused. One comparison image per style: the photo's face | the live sheet (if
given) | N1 | N2's portrait | N2's sheet, face close-ups on top and the whole pictures below.
"""

from __future__ import annotations

import argparse
import asyncio
import io
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

from qamra_ai.cost import fal_cost
from qamra_ai.image.base import ImageRequest, Resolution
from qamra_ai.image.fal import FalImageProvider
from qamra_ai.pipeline.character import LIKENESS_SHEET_VERSION, character_request, portrait_request
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.photo_check import PhotoCheck, check_photo, detect_faces
from qamra_ai.pipeline.theme import load_style
from qamra_api.uploads import clean_image

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "out" / "design-images" / "ledger.jsonl"
PREFIX = "likeness"
PRO = "fal-ai/nano-banana-pro"
REAL_USD: dict[tuple[str, str], float] = {(f"{PRO}/edit", "1K"): 0.15, (f"{PRO}/edit", "2K"): 0.15}
SHEET_RES: Resolution = "2K"
PORTRAIT_RES: Resolution = "1K"
STYLES = ("3d", "semi-realistic", "cartoon", "watercolor")
# the create flow's auto-framing (photo step, 2026-10-10): the face's share of the frame height, its centre
FRAME_ASPECT, FACE_HEIGHT, FACE_CENTER, MIN_CROP = 358 / 340, 0.42, (0.5, 0.45), 400
Approach = Literal["N1", "N2"]
Item = Literal["sheet", "portrait"]


@dataclass(frozen=True)
class Step:
    style: str
    approach: Approach
    item: Item

    @property
    def id(self) -> str:
        return f"{PREFIX}:{self.style}:{self.approach}:{self.item}"

    def file(self, out: Path) -> Path:
        return out / f"{self.style}-{self.approach}-{self.item}.png"


def steps(styles: list[str], approaches: list[Approach]) -> list[Step]:
    out: list[Step] = []
    for style in styles:
        if "N1" in approaches:
            out.append(Step(style, "N1", "sheet"))
        if "N2" in approaches:
            out += [Step(style, "N2", "portrait"), Step(style, "N2", "sheet")]
    return out


def price(endpoint: str, resolution: str) -> float:
    real = REAL_USD.get((endpoint, resolution))
    if real is None:
        raise SystemExit(f"no checked price for {endpoint} at {resolution}: check fal's page first")
    listed = fal_cost(endpoint, resolution=resolution) or 0.0
    return math.ceil(max(real, listed) * 100 - 1e-9) / 100


# ---- the photo, as an order sends it ------------------------------------------------------------------


def frame_box(width: int, height: int, face: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Head and shoulders around the face found (the create flow's auto-framing), inside the photo."""
    fx, fy, fw, fh = face
    ch = max(fh / FACE_HEIGHT, MIN_CROP)
    cw = ch * FRAME_ASPECT
    fit = min(1.0, width / cw, height / ch)
    cw, ch = cw * fit, ch * fit
    left = min(max(0.0, fx + fw / 2 - FACE_CENTER[0] * cw), width - cw)
    top = min(max(0.0, fy + fh / 2 - FACE_CENTER[1] * ch), height - ch)
    return round(left), round(top), round(left + cw), round(top + ch)


def prepare_photo(raw: bytes) -> tuple[bytes, PhotoCheck, tuple[int, int, int, int] | None]:
    """Upload → `clean_image` → photo check → framed head and shoulders (JPEG, as the model gets it). As in
    the create flow, a framing that fails the check (a close-up photo: the frame can't zoom out past the
    photo's edges) is dropped and the whole photo is used, when the whole photo passed."""
    stored = clean_image(raw)
    whole = check_photo(stored)
    if whole.face_box is None or any(i.code not in ("face_small",) for i in whole.issues):
        raise SystemExit(
            f"the photo fails the upload check: {[i.code for i in whole.issues]} {whole.metrics}"
        )
    with Image.open(io.BytesIO(stored)) as im:
        img = im.convert("RGB")
    box = frame_box(img.width, img.height, whole.face_box)
    buf = io.BytesIO()
    img.crop(box).save(buf, format="JPEG", quality=92)
    framed = buf.getvalue()
    check = check_photo(framed)
    if check.ok:
        return framed, check, box
    if whole.ok:
        print(f"framing {box} fails the check ({[i.code for i in check.issues]}): the whole photo is used")
        return stored, whole, None
    raise SystemExit(f"the framed photo fails the check: {[i.code for i in check.issues]} {check.metrics}")


# ---- requests -----------------------------------------------------------------------------------------


def request(step: Step, child: Child, photo: bytes, portrait: bytes | None) -> ImageRequest:
    style = load_style(step.style)
    if step.item == "portrait":
        return portrait_request(child, [photo], style, resolution=PORTRAIT_RES)
    return character_request(
        child,
        [photo],
        style,
        resolution=SHEET_RES,
        version=LIKENESS_SHEET_VERSION,
        portrait=portrait if step.approach == "N2" else None,
    )


class _NoNetwork:
    async def subscribe(self, application: str, arguments: dict[str, Any], **_: Any) -> Any:
        raise RuntimeError("dry run: no network")


def provider(key: str | None) -> FalImageProvider:
    return FalImageProvider(key, PRO) if key else FalImageProvider(None, PRO, client=_NoNetwork())


def describe(req: ImageRequest) -> tuple[str, str, float]:
    endpoint, args, _ = provider(None).build(req)
    res = str(args.get("resolution", req.resolution))
    return endpoint, res, price(endpoint, res)


# ---- the ledger and the cap -----------------------------------------------------------------------------


def logged(ledger: Path) -> float:
    if not ledger.exists():
        return 0.0
    rows = (json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip())
    return float(sum(r.get("usd", 0.0) for r in rows if str(r.get("id", "")).startswith(f"{PREFIX}:")))


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


async def run_style(
    style: str,
    todo: list[Step],
    child: Child,
    photo: bytes,
    out: Path,
    fal: FalImageProvider,
    budget: Budget,
    ledger: Path,
) -> list[str]:
    """One style's steps in order (N2's sheet needs its portrait)."""
    lines: list[str] = []
    for step in (s for s in todo if s.style == style):
        target = step.file(out)
        if target.exists():
            lines.append(f"= {step.id}: reused")
            continue
        portrait_file = Step(style, "N2", "portrait").file(out)
        if step.approach == "N2" and step.item == "sheet" and not portrait_file.exists():
            lines.append(f"✗ {step.id}: SKIPPED, no portrait")
            continue
        portrait = portrait_file.read_bytes() if portrait_file.exists() else None
        req = request(step, child, photo, portrait)
        endpoint, res, usd = describe(req)
        if not await budget.reserve(usd):
            lines.append(f"✗ {step.id}: SKIPPED (cap ${budget.cap:.2f}, or the run stopped)")
            continue
        t = time.time()
        base = {"id": step.id, "model": endpoint, "usd": usd, "res": res}
        try:
            image = await fal.generate(req)
        except Exception as e:  # logged at full price, except an empty account (nothing billed: stop)
            if exhausted(e):
                budget.stopped = True
                budget.spent -= usd
                ledger_row(ledger, {**base, "usd": 0.0, "error": "fal_exhausted"})
                lines.append(f"✗ {step.id}: fal says exhausted or locked: STOPPED")
                break
            ledger_row(ledger, {**base, "error": type(e).__name__, "s": round(time.time() - t, 1)})
            lines.append(f"✗ {step.id}: {type(e).__name__}: {str(e)[:160]}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image.data)
        ledger_row(ledger, {**base, "file": str(target), "s": round(time.time() - t, 1)})
        lines.append(f"✓ {step.id}: ${usd:.2f} ({time.time() - t:.0f}s)")
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


def face_crop(
    path: Path, side: int, *, leftmost: bool, face: tuple[int, int, int, int] | None = None
) -> Image.Image:
    """The face, squared with room for the hair and chin: `face` when given (the photo check's own box),
    else on a sheet the leftmost (the front view), on a portrait the surest one. Past the picture's edge the
    crop is the background colour."""
    with Image.open(path) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    faces = [(*face, 1.0)] if face else _faces(img)
    if faces:
        x, y, w, h, _ = faces[0] if leftmost else max(faces, key=lambda f: f[4])
        cx, cy, half = x + w / 2, y + h * 0.42, max(w, h) * 1.05
    else:  # no face found: the top of the leftmost third (a sheet's front view), or the middle
        third = img.width / 3 if img.width > img.height * 1.2 else img.width
        cx, cy, half = third / 2, img.height * 0.2, min(third, img.height) * 0.22
    left, top = round(cx - half), round(cy - half)
    size = round(2 * half)
    inside = (max(0, left), max(0, top), min(img.width, left + size), min(img.height, top + size))
    crop = Image.new("RGB", (size, size), img.getpixel((0, 0)))
    crop.paste(img.crop(inside), (inside[0] - left, inside[1] - top))
    return crop.resize((side, side), Image.Resampling.LANCZOS)


def compare(
    style: str, photo: bytes, face: tuple[int, int, int, int] | None, live: Path | None, out: Path, dest: Path
) -> Path:
    side, gap, label_h = 420, 14, 34
    columns: list[tuple[str, Path | None]] = [
        ("photo (as sent)", None),
        ("live sheet (NB2 1K, v3)", live),
        ("N1 sheet (Pro 2K, v5)", Step(style, "N1", "sheet").file(out)),
        ("N2 portrait (Pro 1K)", Step(style, "N2", "portrait").file(out)),
        ("N2 sheet (Pro 2K, v5 + portrait)", Step(style, "N2", "sheet").file(out)),
    ]
    photo_path = out / "photo-as-sent.jpg"
    photo_path.write_bytes(photo)
    width = gap + len(columns) * (side + gap)
    height = gap + label_h + side + gap + side + gap
    canvas = Image.new("RGB", (width, height), (246, 241, 230))
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=17)
    pen.text((gap, 6), f"{style}", fill=(20, 20, 40), font=ImageFont.load_default(size=20))
    for i, (label, path) in enumerate(columns):
        x = gap + i * (side + gap)
        src = photo_path if i == 0 else path
        pen.text((x, label_h - 6), label, fill=(30, 30, 50), font=font)
        y = gap + label_h
        if src is None or not src.exists():
            pen.rectangle((x, y, x + side, y + side), outline=(180, 170, 150))
            pen.text((x + 12, y + 12), "none", fill=(120, 110, 100), font=font)
            continue
        canvas.paste(face_crop(src, side, leftmost="sheet" in label, face=face if i == 0 else None), (x, y))
        with Image.open(src) as im:
            whole = im.convert("RGB")
        whole.thumbnail((side, side), Image.Resampling.LANCZOS)
        canvas.paste(whole, (x + (side - whole.width) // 2, y + side + gap + (side - whole.height) // 2))
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
    p.add_argument("--approaches", default="N1,N2")
    p.add_argument("--live", action="append", default=[], help="STYLE=PATH: the live sheet to compare")
    p.add_argument("--out", type=Path, help="default: out/likeness-trial/<photo name>")
    p.add_argument("--compare-dir", type=Path, help="where the comparison images go (default: --out)")
    p.add_argument("--ledger", type=Path, default=LEDGER, help="the shared spend ledger")
    p.add_argument("--run", action="store_true", help="draw on fal (without it: a dry run)")
    p.add_argument("--max-usd", type=float, help="hard cap for every run of this script together")
    p.add_argument("--compare-only", action="store_true", help="only (re)build the comparison images")
    args = p.parse_args(argv)
    if args.run and args.max_usd is None:
        p.error("--run needs --max-usd")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    styles = [s.strip() for s in args.styles.split(",") if s.strip()]
    approaches: list[Approach] = [a for a in ("N1", "N2") if a in args.approaches.split(",")]
    out: Path = args.out or ROOT / "out" / "likeness-trial" / args.photo.stem
    out.mkdir(parents=True, exist_ok=True)
    child = Child(name="child", gender=args.gender, age=args.age, hijab=args.hijab, glasses=args.glasses)
    photo, check, box = prepare_photo(args.photo.read_bytes())
    m = check.metrics
    print(
        f"photo: {f'framed {box}' if box else 'whole'} → {int(m['width'])}×{int(m['height'])}, "
        f"{int(m['faces'])} face "
        f"(score {m['face_score']}, {m['face_ratio']:.0%} of the width), sharpness {m['sharpness']}"
    )
    todo = steps(styles, approaches)
    earlier = logged(args.ledger)
    total = 0.0
    for s in todo:
        portrait = photo if s.approach == "N2" and s.item == "sheet" else None  # a stand-in: same price
        endpoint, res, usd = describe(request(s, child, photo, portrait))
        reused = s.file(out).exists()
        total += 0.0 if reused else usd
        cost = "reused" if reused else f"{usd:.2f}"
        print(f"{s.id:<36} {endpoint:<28} {res:<3} {cost:>6} {total:>6.2f}")
    print(f"{len(todo)} calls, ${total:.2f} to spend; this script's earlier runs logged ${earlier:.2f}")
    live = dict(item.split("=", 1) for item in args.live)
    if args.run and not args.compare_only:
        fal = provider(fal_key())
        budget = Budget(args.max_usd, earlier)

        async def go() -> list[list[str]]:
            try:
                return await asyncio.gather(
                    *(run_style(s, todo, child, photo, out, fal, budget, args.ledger) for s in styles)
                )
            finally:
                close = getattr(fal, "aclose", None)
                if close is not None:
                    await close()

        for lines in asyncio.run(go()):
            print("\n".join(lines))
        print(f"this script's spend (ledger): ${logged(args.ledger):.2f} of the ${args.max_usd:.2f} cap")
    elif not args.run and not args.compare_only:
        print("dry run: nothing was sent (add --run --max-usd X to draw)")
        return 0
    dest: Path = args.compare_dir or out
    for style in styles:
        path = compare(style, photo, check.face_box, Path(live[style]) if style in live else None, out, dest)
        print(f"comparison: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
