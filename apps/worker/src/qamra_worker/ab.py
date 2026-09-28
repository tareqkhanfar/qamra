"""Resolution A/B on an existing book, inside the worker container (keys stay in the admin settings):

  docker compose exec worker python -m qamra_worker.ab BOOK_ID --beats 1,6,13 --out /tmp/ab

Draws the chosen pages at 1K + upscale and at 2K with the book's own references, seed and outfits, then
writes print JPEGs, 100% crops side by side and ab-report.json. The spend is written to generation_costs
against the child (steps `ab:*`), not the book, so the book's own cost and the dashboard stay clean.
"""

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from qamra_ai.pipeline.ab import run_ab
from qamra_ai.pipeline.book import default_companion
from qamra_ai.pipeline.pages import BookContext
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import load_style
from qamra_core.db.models import Book, BookPage, Character, Companion
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_runtime
from qamra_worker.jobs.books import (
    CostSink,
    _companion,
    _setup,
    ai_child,
    book_lang,
    resolved_settings,
)
from qamra_worker.settings import get_settings


async def main(book_id: str, beats: list[int], out: Path) -> None:
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        book = db.get(Book, book_id)
        if book is None:
            raise SystemExit("book not found")
        job = await _setup(db, storage, book)
        character = db.get(Character, book.character_id) if book.character_id else None
        if character is None or not character.sheet_image_key:
            raise SystemExit("the book has no character sheet yet")
        sheet = storage.get(character.sheet_image_key)
        cover_row = db.query(BookPage).filter(BookPage.book_id == book.id, BookPage.index == 0).one_or_none()
        cover = storage.get(cover_row.image_key) if cover_row and cover_row.image_key else None
        companion = default_companion(job.theme, book_lang(book))
        companion_sheet = None
        comp_row = db.get(Companion, book.companion_id) if book.companion_id else None
        if comp_row is not None:
            companion, companion_sheet, _ = await _companion(db, storage, job.rt, comp_row, book.art_style)
        ctx = BookContext(
            child=ai_child(job.child),
            lang=book_lang(book),
            theme=job.theme,
            style=load_style(book.art_style),
            house=house_style(),
            plan=job.plan,
            character_sheet=sheet,
            outfits=dict(book.generation["outfits"]),
            seed=int(book.generation["seed"]),
            mode="final",
            companion=companion,
            companion_sheet=companion_sheet,
            cover=cover,
        )
        resolved = resolved_settings(db)
        base = ai_settings(resolved, get_settings())
        rt_1k = make_runtime(base.model_copy(update={"final_mode": "1k_upscale"}))
        rt_2k = make_runtime(base.model_copy(update={"final_mode": "2k_upscale"}))
        sink = CostSink(db, None, job.child.id)  # experiment spend: not part of the book's cost
        for rt, arm in ((rt_1k, "1k"), (rt_2k, "2k")):
            rt.on_cost = lambda e, arm=arm: sink(replace(e, step=f"ab:{arm}:{e.step}"))
        report = await run_ab(rt_1k, rt_2k, ctx, beats, out)
        print(report)


def cli() -> None:
    p = argparse.ArgumentParser(prog="qamra_worker.ab")
    p.add_argument("book_id")
    p.add_argument("--beats", default="1,6,13")
    p.add_argument("--out", type=Path, default=Path("/tmp/ab"))
    args = p.parse_args()
    asyncio.run(main(args.book_id, [int(b) for b in args.beats.split(",")], args.out))


if __name__ == "__main__":
    cli()
