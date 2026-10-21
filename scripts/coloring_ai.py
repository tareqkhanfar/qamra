r"""Coloring-book scenes from a cheap image model, cleaned into print line art (candidates a human picks).

A few coloring scenes are too complex to draw well in code (the Dome of the Rock, Jaffa from the sea, a souk,
an iftar table). For those the owner allows a near-zero-cost model; `qamra_workbook.coloring.lineart` turns
its picture into the house line art (2.6 mm black outlines, closed shapes, no grey, no specks).

    uv run python scripts/coloring_ai.py --book palestine --ids aqsa-dome,souk --candidates 3 --dry-run
    uv run python scripts/coloring_ai.py --book palestine --ids aqsa-dome --candidates 3 --max-usd 0.10

Scene prompts: content/coloring/ai-prompts.yaml (`<book>: {<id>: "scene"}`), wrapped in the fixed style
prompt (packages/ai/src/qamra_ai/prompts/style/coloring.md + the line-art rules below).

Writes, per candidate n (out/ is git-ignored):
    out/coloring/ai/<book>/<id>-<n>.png          the model's picture
    out/coloring/ai/<book>/<id>-<n>.svg          the cleaned line art (186 × 232 mm)
    out/coloring/ai/<book>/<id>-<n>.clean.png    the cleaned SVG rendered by Chromium (`coloring.snap`)
    out/coloring/ai/<book>/<id>-<tag>compare.png every candidate of a round: picture above, cleaned below
A chosen candidate goes to the book with `lineart.save(png, book, id)` (content/coloring/art/<book>/<id>.svg).

Money: fal bills FLUX by the megapixel, rounded up per image (1024 × 1024 = 1 MP). Each call makes one
832 × 1040 picture (0.83 MP → billed as 1 MP; the box's 4:5 ratio). Before every call the run's spend plus the
call's price must stay within `--max-usd` (`--count-ledger` also counts earlier `coloring:` ledger lines); a
balance error ("Exhausted balance", "locked", HTTP 402/403 about credits) stops the run at once. Every call,
paid or failed, is one JSON line in the shared fal ledger (/home/tareq/kids/out/design-images/ledger.jsonl).
The key is FAL_KEY from the environment or /home/tareq/kids/.env; it is passed to the client only, never
printed or written.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw
from qamra_workbook.coloring import lineart
from qamra_workbook.coloring.ink import svg
from qamra_workbook.coloring.snap import snap

REPO = Path(__file__).resolve().parents[1]
MAIN_CHECKOUT = Path("/home/tareq/kids")  # the key and the shared ledger live in the main checkout
ENV_FILES = (MAIN_CHECKOUT / ".env", REPO / ".env")
LEDGER = MAIN_CHECKOUT / "out" / "design-images" / "ledger.jsonl"
PROMPTS = REPO / "content" / "coloring" / "ai-prompts.yaml"
STYLE = REPO / "packages" / "ai" / "src" / "qamra_ai" / "prompts" / "style" / "coloring.md"
OUT = REPO / "out" / "coloring" / "ai"
WIDTH, HEIGHT = 832, 1040  # 4:5 ≈ the scene box 186 × 232 mm; 0.83 MP → billed as 1 MP
SEED = 1000


@dataclass(frozen=True)
class Model:
    endpoint: str
    usd_per_mp: float  # fal's price per megapixel (https://fal.ai/models/<endpoint>, https://fal.ai/pricing)
    steps: int
    guidance: float | None = None


MODELS = {
    "schnell": Model("fal-ai/flux/schnell", 0.003, 4),
    "dev": Model("fal-ai/flux/dev", 0.025, 28, 3.5),
}

# v2 (after the first trial: v1 pictures were adult-coloring-book busy, perspective streets, thin lines)
RULES = (
    "A very simple coloring page for toddlers, ages 3 to 6. Bold thick black outlines drawn with a fat "
    "marker, every line the same thickness, on a plain white background. Only a few big, simple, rounded "
    "shapes with large empty white spaces between the lines; minimal details, nothing tiny, every shape "
    "closed. Flat front view, simple cartoon style like a picture book for small children. No shading, no "
    "grey, no hatching, no texture, no patterns, no solid black fills, no color. No text, no letters, no "
    "numbers, no writing, no signature, no watermark, no border. Any people have big simple friendly "
    "cartoon faces with dot eyes and a small smile. Portrait composition filling the page."
)


def style_prompt() -> str:
    """The `## Look` paragraph of the coloring style guide (the same words the book pipeline uses)."""
    text = STYLE.read_text(encoding="utf-8")
    look = " ".join(text.split("## Look", 1)[1].split("##", 1)[0].split())
    # the guide's face sentence is about the book's hero (a child's likeness); here people stay simple
    return ". ".join(s for s in look.split(". ") if "hero" not in s and "Faces" not in s)


def prompt_for(scene: str) -> str:
    return f"{RULES} Scene: {' '.join(scene.split())} Style: {style_prompt()}"


def price(model: Model, width: int = WIDTH, height: int = HEIGHT) -> float:
    """One picture's price: megapixels (1024² px each) rounded up, times the model's rate."""
    return round(math.ceil(width * height / (1024 * 1024)) * model.usd_per_mp, 6)


def fal_key() -> str:
    key = os.environ.get("FAL_KEY", "")
    for env in ENV_FILES:
        if key:
            break
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("FAL_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        sys.exit("FAL_KEY is not set (environment or .env)")
    return key


def ledger_row(row: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ledger_spent(prefix: str = "coloring:") -> float:
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if str(row.get("id", "")).startswith(prefix):
                total += float(row.get("usd", 0.0))
    return total


def exhausted(e: Exception) -> bool:
    text = str(e).lower()
    status = getattr(getattr(e, "response", None), "status_code", None)
    money = any(w in text for w in ("exhausted", "locked", "balance", "credit", "billing", "payment"))
    return money or status == 402 or (status == 403 and money)


def call(client: Any, model: Model, prompt: str, seed: int) -> dict[str, Any]:
    args: dict[str, Any] = {
        "prompt": prompt,
        "image_size": {"width": WIDTH, "height": HEIGHT},
        "num_inference_steps": model.steps,
        "num_images": 1,
        "seed": seed,
        "enable_safety_checker": True,
        "output_format": "png",
    }
    if model.guidance is not None:
        args["guidance_scale"] = model.guidance
    result: dict[str, Any] = client.subscribe(model.endpoint, arguments=args)
    return result


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r:
        path.write_bytes(r.read())


def clean_candidate(png: Path) -> Path:
    """The cleaned SVG beside the picture, and its Chromium render (`<stem>.clean.png`)."""
    body = lineart.clean(png)
    out = png.with_suffix(".svg")
    out.write_text(svg(lineart.BOX_W, lineart.BOX_H, body) + "\n", encoding="utf-8")
    snap({f"{png.stem}.clean": svg(lineart.BOX_W, lineart.BOX_H, body)}, png.parent, dpi=72)
    return out


def candidates(book_dir: Path, scene_id: str, tag: str) -> list[Path]:
    """The model's pictures of one scene and round: <id>-<tag><n>.png."""
    name = re.compile(re.escape(f"{scene_id}-{tag}") + r"\d+")
    return sorted(p for p in book_dir.glob(f"{scene_id}-{tag}*.png") if name.fullmatch(p.stem))


def compare(book_dir: Path, scene_id: str, tag: str = "") -> Path | None:
    """All candidates of a scene on one sheet: the model's picture above, the cleaned line art below."""
    raws = candidates(book_dir, scene_id, tag)
    pairs = [(r, r.with_name(f"{r.stem}.clean.png")) for r in raws]
    pairs = [(r, c) for r, c in pairs if c.exists()]
    if not pairs:
        return None
    tw, th, gap = 372, 464, 12
    sheet = Image.new("RGB", (len(pairs) * (tw + gap) + gap, 2 * (th + gap) + gap + 18), "#DDDDDD")
    draw = ImageDraw.Draw(sheet)
    for i, (raw, cleaned) in enumerate(pairs):
        x = gap + i * (tw + gap)
        for row, path in enumerate((raw, cleaned)):
            with Image.open(path) as img:
                sheet.paste(
                    img.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS), (x, gap + row * (th + gap))
                )
        draw.text((x, 2 * (th + gap) + 2), raw.stem, fill="#000000")
    out = book_dir / f"{scene_id}-{tag}compare.png"
    sheet.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", required=True, choices=("palestine", "ramadan"))
    ap.add_argument("--ids", required=True, help="comma-separated scene ids from ai-prompts.yaml")
    ap.add_argument("--candidates", type=int, default=3)
    ap.add_argument("--model", choices=sorted(MODELS), default="schnell")
    ap.add_argument("--max-usd", type=float, default=0.10, help="this run's spending cap")
    ap.add_argument("--count-ledger", action="store_true", help="count earlier coloring: ledger lines too")
    ap.add_argument(
        "--tag", default="", help="a name part for this round's files (e.g. v2 → <id>-v2-<n>.png)"
    )
    ap.add_argument("--dry-run", action="store_true", help="print pages and prices, make no call")
    ap.add_argument("--clean-only", action="store_true", help="re-clean the pictures already in out/")
    args = ap.parse_args()

    scenes: dict[str, str] = (yaml.safe_load(PROMPTS.read_text(encoding="utf-8")) or {}).get(args.book, {})
    ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    missing = [s for s in ids if s not in scenes]
    if missing:
        sys.exit(f"no prompt in {PROMPTS.name} for {args.book}: {', '.join(missing)}")
    model = MODELS[args.model]
    each = price(model)
    book_dir = OUT / args.book
    tag = "".join(f"{t}-" for t in (args.tag, "" if args.model == "schnell" else args.model) if t)
    jobs = [(sid, n) for sid in ids for n in range(1, args.candidates + 1)]

    if args.clean_only:
        for sid in ids:
            for raw in candidates(book_dir, sid, tag):
                print("cleaned", clean_candidate(raw))
            print("compare", compare(book_dir, sid, tag))
        return

    if args.dry_run:
        for sid, n in jobs:
            print(f"{args.book}/{sid}-{tag}{n}  {model.endpoint}  {WIDTH}x{HEIGHT}  ${each:.4f}")
        print(f"\nprompt ({args.book}/{ids[0]}):\n{prompt_for(scenes[ids[0]])}\n")
        print(f"{len(jobs)} calls × ${each:.4f} = ${each * len(jobs):.4f} (cap ${args.max_usd:.2f})")
        return

    import fal_client

    client = fal_client.SyncClient(key=fal_key())
    spent = ledger_spent() if args.count_ledger else 0.0
    for sid, n in jobs:
        if (book_dir / f"{sid}-{tag}{n}.png").exists():
            continue  # made in an earlier run: never pay twice (delete the file to remake it)
        if spent + each > args.max_usd + 1e-9:
            print(
                f"stop: ${spent:.4f} spent, the next call (${each:.4f}) "
                f"would pass the cap ${args.max_usd:.2f}"
            )
            break
        raw = book_dir / f"{sid}-{tag}{n}.png"
        row: dict[str, Any] = {"id": f"coloring:{args.book}/{sid}-{tag}{n}", "model": model.endpoint}
        t0 = time.monotonic()
        try:
            result = call(client, model, prompt_for(scenes[sid]), SEED + n)
        except Exception as e:
            secs = round(time.monotonic() - t0, 1)
            error = "fal_exhausted" if exhausted(e) else type(e).__name__
            ledger_row(
                {**row, "usd": 0.0, "res": f"{WIDTH}x{HEIGHT}", "file": str(raw), "s": secs, "error": error}
            )
            print(f"{sid}-{n}: failed ({type(e).__name__}: {str(e)[:160]})")
            if exhausted(e):
                print("stop: fal balance error")
                break
            continue
        spent += each  # the picture is made (and billed) even if the download below fails
        image = (result.get("images") or [{}])[0]
        res = f"{image.get('width', WIDTH)}x{image.get('height', HEIGHT)}"
        try:
            download(str(image["url"]), raw)
        except Exception as e:
            ledger_row(
                {
                    **row,
                    "usd": each,
                    "res": res,
                    "file": str(raw),
                    "s": round(time.monotonic() - t0, 1),
                    "error": f"download: {type(e).__name__}",
                }
            )
            print(f"{sid}-{n}: made but not downloaded ({type(e).__name__})")
            continue
        ledger_row({**row, "usd": each, "res": res, "file": str(raw), "s": round(time.monotonic() - t0, 1)})
        flagged = any(result.get("has_nsfw_concepts") or [])
        print(
            f"{sid}-{n}: {raw.relative_to(REPO)} {res} ${each:.4f}{'  (safety-flagged)' if flagged else ''}"
        )
        clean_candidate(raw)
    for sid in ids:
        sheet = compare(book_dir, sid, tag)
        if sheet:
            print("compare", sheet.relative_to(REPO))
    print(f"spent: ${spent:.4f}" + (" (with earlier coloring: ledger lines)" if args.count_ledger else ""))


if __name__ == "__main__":
    main()
