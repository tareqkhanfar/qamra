"""Resolution A/B (Addendum 3 §2.1): "1K + upscale" vs "2K native" on the same pages, same seeds.

Arm A draws at 1K and upscales with the configured upscaler (SeedVR by default). Arm B draws at 2K and only
needs a small Lanczos step (×1.25) to reach 2551 px. Both end as print JPEGs at exactly the print size.
The report has the cost of each arm and side-by-side crops at 100% print scale (what a 300 DPI proof
shows), so a person can judge sharpness on screen before ordering a physical proof.
"""

import io
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image

from qamra_ai.image.upscale import LocalUpscaler
from qamra_ai.pipeline.pages import BookContext, page_request
from qamra_ai.pipeline.printimg import fit_exact
from qamra_ai.pipeline.runtime import Runtime

ARMS = ("1k_upscale", "2k_native")
CROP = 800  # px at 300 DPI ≈ 68 mm: a face-sized window at print scale


@dataclass
class ArmResult:
    arm: str
    beats: list[int] = field(default_factory=list)
    usd: float = 0.0
    files: list[str] = field(default_factory=list)


def _crop(data: bytes, box: tuple[int, int, int, int]) -> Image.Image:
    with Image.open(io.BytesIO(data)) as im:
        return im.convert("RGB").crop(box)


async def run_ab(
    rt_1k: Runtime, rt_2k: Runtime, ctx: BookContext, beats: list[int], out: Path
) -> dict[str, object]:
    """`rt_1k` has final_mode 1k_upscale; `rt_2k` has final_mode 2k_upscale (2K draw, then Lanczos only)."""
    out.mkdir(parents=True, exist_ok=True)
    results = {arm: ArmResult(arm) for arm in ARMS}
    ctx.mode = "final"
    pairs: list[tuple[int, bytes, bytes]] = []
    for beat in beats:
        plan = ctx.plan.beats[beat]
        prints: dict[str, bytes] = {}
        for arm, rt in (("1k_upscale", rt_1k), ("2k_native", rt_2k)):
            before = rt.ledger.total_usd
            req = page_request(rt, ctx, beat, 90)  # same attempt number → same seed in both arms
            image = await rt.draw(req)
            if arm == "1k_upscale":
                up = await rt.upscale(image.data, step=f"upscale:page:{beat}", target=plan.print_px)
                data = up.data
            else:
                data = (await LocalUpscaler().upscale(image.data, step="lanczos", target=plan.print_px)).data
            prints[arm] = fit_exact(data, plan.print_px, dpi=ctx.plan.spec.dpi)
            path = out / f"p{beat:02d}-{arm}.jpg"
            path.write_bytes(prints[arm])
            results[arm].beats.append(beat)
            results[arm].files.append(path.name)
            results[arm].usd += rt.ledger.total_usd - before
        pairs.append((beat, prints["1k_upscale"], prints["2k_native"]))

    # side-by-side crops at 100% print scale, from the upper-middle (where faces usually are)
    for beat, a, b in pairs:
        w, h = Image.open(io.BytesIO(a)).size
        x0, y0 = (w - CROP) // 2, max(0, h // 3 - CROP // 2)
        box = (x0, y0, x0 + CROP, y0 + CROP)
        sheet = Image.new("RGB", (CROP * 2 + 20, CROP), "white")
        sheet.paste(_crop(a, box), (0, 0))
        sheet.paste(_crop(b, box), (CROP + 20, 0))
        sheet.save(out / f"p{beat:02d}-crops-1k-left-2k-right.png")
    report = {
        "arms": {arm: asdict(r) for arm, r in results.items()},
        "per_page_usd": {arm: round(r.usd / max(1, len(r.beats)), 4) for arm, r in results.items()},
        "note": "Crops are 800×800 px at 300 DPI (≈ 68 mm): left = 1K + upscale, right = 2K + Lanczos.",
    }
    (out / "ab-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
