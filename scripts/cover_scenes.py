r"""Draw and install the cover scenes of docs/plans/cover-scenes.md (one per part of the activity series).

    uv run python scripts/cover_scenes.py --dry-run
    uv run python scripts/cover_scenes.py --budget 5.5 [--only kg1-v1 islamic-r]
    uv run python scripts/cover_scenes.py --budget 5.5 --again kg1-v1
    uv run python scripts/cover_scenes.py --install kg1-v1 [kg1-v1-2.png]

Every `### <id> · <part>` block of the plan is one image: Nano Banana Pro on fal, text to image, 3:4 at 2K.
Drawn images land in design/incoming/cover-scenes/ (gitignored staging): `<id>.png`, then `<id>-2.png`… for
`--again`. `--install` copies the chosen one to content/covers/scenes/<id>.jpg, where the covers read it.

Every paid call is appended to out/design-images/ledger.jsonl with an id that starts with `cover-scenes:`, and
the run stops before a call that would take this work's rows past `--budget` (other work in the ledger has its
own caps). The fal key comes from FAL_KEY (environment or the repo's .env); it is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "plans" / "cover-scenes.md"
OUT = ROOT / "design" / "incoming" / "cover-scenes"
SCENES = ROOT / "content" / "covers" / "scenes"
LEDGER = ROOT / "out" / "design-images" / "ledger.jsonl"
PREFIX = "cover-scenes:"
MODEL = "fal-ai/nano-banana-pro"  # text to image; aspect_ratio + resolution (fal schema checked 2026-10-09)
PRICE = 0.15  # per image at 1K and 2K (fal.ai/models/fal-ai/nano-banana-pro, checked 2026-10-09)
RESOLUTION = "2K"
RATIO = "3:4"
_BLOCK = re.compile(r"^### (?P<id>[a-z0-9-]+) · (?P<part>[^\n]+)\n(?P<body>.*?)(?=^### |\Z)", re.M | re.S)


@dataclass(frozen=True)
class Scene:
    id: str
    part: str
    prompt: str


def parse(text: str) -> list[Scene]:
    scenes = []
    for m in _BLOCK.finditer(text):
        body = m.group("body")
        if "```text\n" not in body:
            continue
        prompt = body.split("```text\n", 1)[1].split("\n```", 1)[0].strip()
        scenes.append(Scene(m.group("id"), m.group("part").strip(), prompt))
    return scenes


def spent() -> float:
    """What this work spent so far (the ledger's `cover-scenes:` rows)."""
    if not LEDGER.exists():
        return 0.0
    rows = [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]
    return float(sum(r.get("usd", 0.0) for r in rows if str(r.get("id", "")).startswith(PREFIX)))


def fal_key() -> str:
    key = os.environ.get("FAL_KEY", "")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("FAL_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        sys.exit("FAL_KEY is not set (environment or .env)")
    return key


def next_file(scene: Scene, again: bool) -> Path | None:
    """Where the next drawing of `scene` goes; None when it exists and no new version is asked for."""
    first = OUT / f"{scene.id}.png"
    if not first.exists():
        return first
    if not again:
        return None
    n = 2
    while (OUT / f"{scene.id}-{n}.png").exists():
        n += 1
    return OUT / f"{scene.id}-{n}.png"


def log(row: dict[str, object]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps(row) + "\n")


class Budget:
    def __init__(self, cap: float) -> None:
        self.cap, self.used, self.lock = cap, spent(), asyncio.Lock()

    async def reserve(self, usd: float) -> bool:
        async with self.lock:
            if self.used + usd > self.cap + 1e-9:
                return False
            self.used += usd
            return True


async def draw(provider: object, scene: Scene, out: Path, budget: Budget, sem: asyncio.Semaphore) -> str:
    from qamra_ai.image.base import ImageRequest

    if not await budget.reserve(PRICE):
        return f"{scene.id}: SKIPPED, the cap (${budget.used:.2f} of ${budget.cap:.2f} used)"
    async with sem:
        t = time.time()
        req = ImageRequest(
            step=f"{PREFIX}{scene.id}",
            prompt=scene.prompt,
            refs=[],
            aspect=RATIO,  # type: ignore[arg-type]
            resolution=RESOLUTION,  # type: ignore[arg-type]
        )
        try:
            image = await provider.generate(req)  # type: ignore[attr-defined]
        except Exception as e:  # one failure never stops the run; a failed call is not billed
            log({"id": f"{PREFIX}{scene.id}", "usd": 0.0, "error": type(e).__name__})
            budget.used -= PRICE
            return f"{scene.id}: FAILED {type(e).__name__}: {str(e)[:160]}"
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_bytes(image.data)
    usd = max(image.cost.usd, PRICE)
    log(
        {
            "id": f"{PREFIX}{scene.id}",
            "file": out.name,
            "usd": usd,
            "model": MODEL,
            "res": RESOLUTION,
            "size": image.params.get("size"),
            "s": round(time.time() - t, 1),
        }
    )
    budget.used += usd - PRICE
    return f"{scene.id}: ok ${usd:.2f} → {out.relative_to(ROOT)} ({time.time() - t:.0f}s)"


def install(scene_id: str, name: str | None) -> Path:
    from PIL import Image

    src = OUT / (name or f"{scene_id}.png")
    if not src.exists():
        sys.exit(f"{src} does not exist")
    SCENES.mkdir(parents=True, exist_ok=True)
    dest = SCENES / f"{scene_id}.jpg"
    with Image.open(src) as img:
        img.convert("RGB").save(dest, format="JPEG", quality=90, optimize=True)
    return dest


async def run(args: argparse.Namespace) -> None:
    scenes = parse(PLAN.read_text(encoding="utf-8"))
    wanted = set(args.only or []) | set(args.again or [])
    if wanted:
        unknown = wanted - {s.id for s in scenes}
        if unknown:
            sys.exit(f"no scene {sorted(unknown)} in {PLAN.name}")
        scenes = [s for s in scenes if s.id in wanted]
    todo = [(s, f) for s in scenes if (f := next_file(s, s.id in (args.again or []))) is not None]
    print(
        f"{len(scenes)} scenes, {len(todo)} to draw, about ${len(todo) * PRICE:.2f}; "
        f"this work spent ${spent():.2f} so far"
    )
    if args.dry_run:
        for s, f in todo:
            print(f"  {s.id} → {f.relative_to(ROOT)} ({len(s.prompt)} chars)")
        return
    if args.budget is None:
        sys.exit("--budget is required to draw")
    from qamra_ai.image.fal import FalImageProvider

    provider = FalImageProvider(fal_key(), MODEL)
    budget, sem = Budget(args.budget), asyncio.Semaphore(args.concurrency)
    for line in await asyncio.gather(*(draw(provider, s, f, budget, sem) for s, f in todo)):
        print(line, flush=True)
    print(f"this work spent ${spent():.2f} of ${args.budget:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--budget", type=float, help="cap for every cover-scenes call together (USD)")
    ap.add_argument("--only", nargs="*", help="these scene ids")
    ap.add_argument("--again", nargs="*", help="draw a new version of these scene ids")
    ap.add_argument("--install", nargs="+", metavar=("ID", "FILE"), help="install a drawn version")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()
    if args.install:
        print(f"wrote {install(args.install[0], args.install[1] if len(args.install) > 1 else None)}")
        return
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
