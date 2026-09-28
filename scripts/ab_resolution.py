"""Resolution A/B locally (keys in .env): photo → character sheet → cover → pages at 1K + upscale and 2K.

  uv run scripts/ab_resolution.py --photo kid.jpg --name "سلمى" --gender f --age 5 --beats 1,6,13

On the server, run the same comparison on an existing book instead (keys stay in the admin settings):
  docker compose exec worker python -m qamra_worker.ab BOOK_ID --beats 1,6,13 --out /tmp/ab
"""

import argparse
import asyncio
import time
from pathlib import Path

from qamra_ai.config import Settings
from qamra_ai.image import make_image_provider, make_upscaler
from qamra_ai.pipeline.ab import run_ab
from qamra_ai.pipeline.book import choose_outfits, default_companion, new_seed
from qamra_ai.pipeline.character import generate_character_sheet
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.pages import BookContext, generate_beat
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import load_style, load_theme
from qamra_ai.text import make_text_provider

ROOT = Path(__file__).resolve().parents[1]


def runtime(settings: Settings) -> Runtime:
    return Runtime(
        settings=settings,
        text=make_text_provider(settings),
        image=make_image_provider(settings),
        upscaler=make_upscaler(settings),
    )


async def main(args: argparse.Namespace) -> None:
    base = Settings()
    child = Child(name=args.name, gender=args.gender, age=args.age, hijab=args.hijab)
    theme, style = load_theme(args.theme), load_style("watercolor")
    rt = runtime(base.model_copy(update={"final_mode": "1k_upscale"}))
    sheet = await generate_character_sheet(rt, child, [args.photo.read_bytes()], style)
    seed = new_seed()
    ctx = BookContext(
        child=child,
        lang="ar",
        theme=theme,
        style=style,
        house=house_style(),
        plan=plan_book(theme, "ar", companion_page=False),
        character_sheet=sheet.data,
        outfits=choose_outfits(theme, child, seed),
        seed=seed,
        mode="preview",
        companion=default_companion(theme, "ar"),
    )
    cover = await generate_beat(rt, ctx, 0)
    if cover.image is None:
        raise SystemExit("cover failed")
    ctx.cover = cover.image.data
    rt_2k = runtime(base.model_copy(update={"final_mode": "2k_upscale"}))
    out = args.out / f"{time.strftime('%Y%m%d-%H%M%S')}-ab"
    report = await run_ab(rt, rt_2k, ctx, [int(b) for b in args.beats.split(",")], out)
    print(f"→ {out}\n{report['per_page_usd']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--photo", type=Path, required=True)
    p.add_argument("--name", default="سلمى")
    p.add_argument("--gender", choices=["m", "f"], default="f")
    p.add_argument("--age", type=int, default=5)
    p.add_argument("--hijab", action="store_true")
    p.add_argument("--theme", default="first-day")
    p.add_argument("--beats", default="1,6,13")
    p.add_argument("--out", type=Path, default=ROOT / "out")
    asyncio.run(main(p.parse_args()))
