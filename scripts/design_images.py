r"""Draw the design images of docs/image-prompts.md on fal (Nano Banana 2), within a hard budget.

    uv run python scripts/design_images.py --budget 9 [--only C1 C2] [--section D] [--dry-run]

Every `### <id> · \`<file>\`` block of the prompts file is one image: its ratio comes from the block, its
reference images from "استعمل C1 مرجعًا" notes (drawn first). Images land in design/incoming/<file>
(gitignored staging; `scripts/install_design_images.py` copies the chosen ones into the product). An image
that already exists is skipped, so a run can be repeated after a failure. Every paid call is appended to
out/design-images/ledger.jsonl and the run stops before a call that would pass the budget (all runs count).

The fal key comes from FAL_KEY (environment or the repo's .env); it is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from qamra_ai.image.base import ImageRequest, RefImage
from qamra_ai.image.fal import FalImageProvider

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "docs" / "image-prompts.md"
OUT = ROOT / "design" / "incoming"
LEDGER = ROOT / "out" / "design-images" / "ledger.jsonl"
MODEL = "fal-ai/nano-banana-2"
PRICE = {"1K": 0.08, "2K": 0.12}  # packages/ai/src/qamra_ai/pricing.yaml (Nano Banana 2, per image)
# Print and hero images at 2K; character sheets and small scenes at 1K (upscaled later when printed).
HIGH = ("A", "B", "D", "E", "G")
HIGH_IDS = {"F5", "F6", "F7", "F8", "F9", "F10"}  # the Islamic volume covers
FAMILY_SCENES = {f"F{n}" for n in (*range(11, 19), 24, 25, 26)}
_BLOCK = re.compile(r"^### (?P<id>[A-G]\d+) · `(?P<file>[^`]+)`\n(?P<body>.*?)(?=^### |^## |\Z)", re.M | re.S)
_RATIO = re.compile(r"\b(\d+:\d+)\b")
_REF = re.compile(r"استعمل ((?:[A-G]\d+(?:–[A-G]\d+)?)(?:\s*و\s*[A-G]\d+)*) مرجعًا")


@dataclass
class Item:
    id: str
    file: str
    ratio: str
    prompt: str
    refs: list[str] = field(default_factory=list)

    @property
    def resolution(self) -> str:
        return "2K" if self.id[0] in HIGH or self.id in HIGH_IDS else "1K"

    @property
    def price(self) -> float:
        return PRICE[self.resolution]


def _expand(ref: str) -> list[str]:
    if "–" not in ref:
        return [ref]
    a, b = ref.split("–")
    return [f"{a[0]}{n}" for n in range(int(a[1:]), int(b[1:]) + 1)]


def parse(text: str) -> list[Item]:
    items = []
    for m in _BLOCK.finditer(text):
        body = m.group("body")
        ratio = _RATIO.search(body.split("```")[0])
        prompt = body.split("```text\n", 1)[1].split("\n```", 1)[0].strip()
        refs: list[str] = []
        for r in _REF.finditer(body.split("```")[0]):
            for part in re.split(r"\s*و\s*", r.group(1)):
                refs += _expand(part.strip())
        if m.group("id") in FAMILY_SCENES:  # the Islamic scenes with Reem, Salem, Sitti Huda and Naanaa
            refs = ["F1", "F2", "F3", "F4"]
        items.append(Item(m.group("id"), m.group("file"), ratio.group(1) if ratio else "1:1", prompt, refs))
    return items


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


def spent() -> float:
    if not LEDGER.exists():
        return 0.0
    return float(sum(json.loads(line)["usd"] for line in LEDGER.read_text().splitlines() if line.strip()))


class Budget:
    def __init__(self, cap: float) -> None:
        self.cap, self.used, self.lock = cap, spent(), asyncio.Lock()

    async def reserve(self, usd: float) -> bool:
        async with self.lock:
            if self.used + usd > self.cap:
                return False
            self.used += usd
            return True


async def draw(provider: FalImageProvider, item: Item, budget: Budget, sem: asyncio.Semaphore) -> str:
    out = OUT / item.file
    if out.exists():
        return f"{item.id}: exists"
    refs = []
    for r in item.refs:
        path = next(OUT.glob(f"{r}-*.png"), None)
        if path is None:
            return f"{item.id}: waiting for reference {r}"
        refs.append(
            RefImage(path.read_bytes(), "image/png", f"the approved design of the same character ({r})")
        )
    if not await budget.reserve(item.price):
        return f"{item.id}: SKIPPED, budget (${budget.used:.2f} of ${budget.cap:.2f} used)"
    async with sem:
        t = time.time()
        req = ImageRequest(
            step=f"design:{item.id}",
            prompt=item.prompt,
            refs=refs,
            aspect=item.ratio,  # type: ignore[arg-type]  # fal takes any of its ratios (verified 2026-10-02)
            resolution=item.resolution,  # type: ignore[arg-type]
        )
        try:
            image = await provider.generate(req)
        except Exception as e:  # one failure never stops the run; the ledger keeps the reserved price honest
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER.open("a") as f:
                f.write(json.dumps({"id": item.id, "usd": 0.0, "error": type(e).__name__}) + "\n")
            budget.used -= item.price
            return f"{item.id}: FAILED {type(e).__name__}: {str(e)[:160]}"
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_bytes(image.data)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        row = {
            "id": item.id,
            "file": item.file,
            "usd": image.cost.usd,
            "res": item.resolution,
            "s": time.time() - t,
        }
        f.write(json.dumps(row) + "\n")
    budget.used += image.cost.usd - item.price  # the real price replaces the reservation
    return f"{item.id}: ok ${image.cost.usd:.3f} ({time.time() - t:.0f}s)"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, required=True, help="cap for all runs together (USD)")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--section", nargs="*", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    items = parse(PROMPTS.read_text(encoding="utf-8"))
    if a.only:
        items = [i for i in items if i.id in a.only]
    if a.section:
        items = [i for i in items if i.id[0] in a.section]
    todo = [i for i in items if not (OUT / i.file).exists()]
    print(
        f"{len(items)} images, {len(todo)} to draw, about ${sum(i.price for i in todo):.2f};"
        f" spent so far ${spent():.2f}"
    )
    if a.dry_run:
        for i in items:
            print(f"  {i.id} {i.ratio} {i.resolution} refs={i.refs} {i.file}")
        return
    provider = FalImageProvider(fal_key(), MODEL)
    budget, sem = Budget(a.budget), asyncio.Semaphore(a.concurrency)
    first = [i for i in todo if not i.refs]  # references before the images that use them
    for wave in (first, [i for i in todo if i.refs]):
        for line in await asyncio.gather(*(draw(provider, i, budget, sem) for i in wave)):
            print(line, flush=True)
    print(f"spent in total: ${spent():.2f} of ${a.budget:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
