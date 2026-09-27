"""Companion fidelity eval (Addendum 1): drawings → clean-up → 2 companion options → Claude fidelity score.

  uv run scripts/companion_eval.py --drawings path/to/drawings/ --provider gemini --style watercolor

The automated score is a proxy; the acceptance test is parents recognizing their child's drawing
(≥ 8 of 10). Use the side-by-side images in the output folder for that check.
"""

import argparse
import asyncio
import time
from pathlib import Path

from qamra_ai.config import get_settings
from qamra_ai.image import make_image_provider
from qamra_ai.pipeline.companion import DrawingRejected, generate_companion_options, score_fidelity
from qamra_ai.pipeline.drawing import clean_drawing
from qamra_ai.pipeline.models import CompanionSpec
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_style
from qamra_ai.text import make_text_provider

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    provider = args.provider or settings.image_provider
    rt = Runtime(
        settings=settings,
        text=make_text_provider(settings, "fake" if provider == "fake" else "anthropic"),
        image=make_image_provider(settings, provider),
    )
    style = load_style(args.style)
    drawings = sorted(p for p in args.drawings.iterdir() if p.suffix.lower() in IMAGE_EXT)
    if not drawings:
        raise SystemExit(f"no images in {args.drawings}")
    out = (args.out / f"companion-eval-{time.strftime('%Y%m%d-%H%M%S')}-{provider}").resolve()
    out.mkdir(parents=True)

    rows = []
    for i, path in enumerate(drawings, start=1):
        d = out / path.stem
        d.mkdir()
        cleaned = clean_drawing(path.read_bytes())
        (d / "cleaned.png").write_bytes(cleaned.png)
        spec = CompanionSpec(name=f"صاحب {i}", type_hint="creature")
        try:
            result = await generate_companion_options(rt, cleaned.png, spec, style)
        except DrawingRejected as e:
            rows.append(f"| {path.name} | {cleaned.paper_found} | rejected: {e} | | |")
            continue
        scores = []
        for n, option in enumerate(result.options, start=1):
            (d / f"option-{n}.png").write_bytes(option.data)
            fid = await score_fidelity(rt, cleaned.png, option)
            scores.append(fid.score)
            (d / f"option-{n}-fidelity.json").write_text(fid.model_dump_json(indent=2), encoding="utf-8")
        rows.append(
            f"| {path.name} | {cleaned.paper_found} | {', '.join(result.review.key_features)} | "
            f"{' / '.join(map(str, scores))} | {max(scores)} |"
        )
        print(f"✓ {path.name}: fidelity {scores}")

    best = [int(r.rsplit("|", 2)[-2]) for r in rows if "rejected" not in r]
    good = sum(s >= 4 for s in best)
    report = [
        f"# Companion fidelity — {rt.image.name}/{rt.image.model}, style {args.style}",
        "",
        f"- drawings: {len(drawings)}; best option scored ≥ 4/5 on **{good}/{len(best)}**",
        f"- cost: ${rt.ledger.total_usd:.3f} (≈ ${rt.ledger.total_usd / len(drawings):.3f} per drawing)",
        "",
        "| drawing | paper found | key features | option scores | best |",
        "|---|---|---|---|---|",
        *rows,
    ]
    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"→ {out / 'report.md'}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--drawings", type=Path, required=True, help="folder with drawing photos")
    p.add_argument("--provider", choices=["gemini", "flux", "openai", "fake"])
    p.add_argument("--style", default="watercolor")
    p.add_argument("--out", type=Path, default=ROOT / "out")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
