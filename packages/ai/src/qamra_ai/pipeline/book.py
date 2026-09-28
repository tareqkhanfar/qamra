"""Whole-book orchestration: story → plan → outfit lock → cover → pages (preview or final).

Shared by the scripts and the worker. Per-child steps (character sheet, companion) run before this and
are reused across books. Everything that must stay stable when a book is resumed or re-rendered (seed,
outfits, story, cover, previews) can be passed back in.
"""

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field

from qamra_ai.pipeline.budget import BudgetExceeded
from qamra_ai.pipeline.layout import BookPlan, PrintSpec, plan_book
from qamra_ai.pipeline.models import Child, CompanionSpec, Lang, StoryOut
from qamra_ai.pipeline.pages import BookContext, Mode, PageResult, beats_for, generate_pages
from qamra_ai.pipeline.plates import PlateStore
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import Story, write_story
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import ArtStyle, Theme


def default_companion(theme: Theme, lang: Lang) -> CompanionSpec | None:
    d = theme.default_companion
    if not theme.companion_slot or d is None:
        return None
    return CompanionSpec(
        name=d.name_ar if lang == "ar" else d.name_en,
        type_hint="creature",
        description_en=d.description_en,
    )


def choose_outfits(theme: Theme, child: Child, seed: int) -> dict[str, str]:
    """Pick one option per outfit key, once per book (Addendum 3 §3 outfit lock)."""
    out: dict[str, str] = {}
    for key, options in sorted(theme.outfits.items()):
        option = options[(seed + sum(map(ord, key))) % len(options)]
        out[key] = option.describe(child.gender, child.hijab)
    return out


def new_seed() -> int:
    return secrets.randbelow(2_000_000_000)


@dataclass
class BookInputs:
    child: Child
    lang: Lang
    theme: Theme
    style: ArtStyle
    character_sheet: bytes
    companion: CompanionSpec | None = None
    companion_sheet: bytes | None = None
    has_drawing: bool = False  # adds the «وهكذا وُلد صاحبي» page
    parent_message: str | None = None
    seed: int | None = None
    outfits: dict[str, str] | None = None
    story: StoryOut | None = None
    cover: bytes | None = None
    previews: dict[int, bytes] = field(default_factory=dict)
    plates: PlateStore | None = None
    spec: PrintSpec | None = None


@dataclass
class BookRun:
    plan: BookPlan
    seed: int
    outfits: dict[str, str]
    story: Story | None
    pages: dict[int, PageResult]
    flags: list[str] = field(default_factory=list)

    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in self.pages.values():
            counts[p.status] = counts.get(p.status, 0) + 1
        return counts


async def run_book(
    rt: Runtime,
    inp: BookInputs,
    *,
    mode: Mode,
    beats: list[int] | None = None,
    on_page: Callable[[PageResult], None] | None = None,
) -> BookRun:
    seed = inp.seed if inp.seed is not None else new_seed()
    outfits = inp.outfits or choose_outfits(inp.theme, inp.child, seed)
    plan = plan_book(
        inp.theme, inp.lang, companion_page=inp.has_drawing and inp.companion is not None, spec=inp.spec
    )
    run = BookRun(plan=plan, seed=seed, outfits=outfits, story=None, pages={})
    try:
        run.story = (
            Story(out=inp.story)
            if inp.story is not None
            else await write_story(rt, inp.theme, inp.child, inp.lang, inp.companion, inp.parent_message)
        )
    except BudgetExceeded:
        run.flags.append("budget_exceeded")
        return run
    if run.story.long_pages:
        run.flags.append("long_text")
    ctx = BookContext(
        child=inp.child,
        lang=inp.lang,
        theme=inp.theme,
        style=inp.style,
        house=house_style(),
        plan=plan,
        character_sheet=inp.character_sheet,
        outfits=outfits,
        seed=seed,
        mode=mode,
        companion=inp.companion,
        companion_sheet=inp.companion_sheet,
        cover=inp.cover,
        previews=dict(inp.previews),
        plates=inp.plates,
        on_page=on_page,
    )
    wanted = beats if beats is not None else beats_for(ctx, rt.settings.preview_pages)
    run.pages = await generate_pages(rt, ctx, wanted)
    if rt.budget is not None and rt.budget.exceeded:
        run.flags.append("budget_exceeded")
    if any(p.status in ("needs_review", "failed") for p in run.pages.values()):
        run.flags.append("pages_need_review")
    return run
