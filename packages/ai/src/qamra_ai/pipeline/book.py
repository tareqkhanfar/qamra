"""Whole-book orchestration used by the prototype script (and later by the worker)."""

import asyncio
from dataclasses import dataclass

from qamra_ai.image.base import GeneratedImage
from qamra_ai.pipeline.character import generate_character_sheet
from qamra_ai.pipeline.companion import CompanionOptions, generate_companion_options, score_fidelity
from qamra_ai.pipeline.models import Child, CompanionFidelity, CompanionSpec, Lang, StoryOut
from qamra_ai.pipeline.pages import Cast, PageResult, generate_pages
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import write_story
from qamra_ai.pipeline.theme import ArtStyle, Theme


@dataclass
class BookRequest:
    child: Child
    lang: Lang
    theme: Theme
    style: ArtStyle
    photos: list[bytes]
    cleaned_drawing: bytes | None = None
    companion: CompanionSpec | None = None  # name/type from the parent; None → theme default
    companion_pick: int = 1  # which of the 2 options the "parent" picks (prototype: flag)


@dataclass
class BookArtifacts:
    character_sheet: GeneratedImage
    companion: CompanionSpec | None
    companion_options: CompanionOptions | None
    companion_sheet: GeneratedImage | None
    companion_fidelity: CompanionFidelity | None
    story: StoryOut
    cover: PageResult
    pages: list[PageResult]

    @property
    def recognizable_ratio(self) -> float:
        judged = [p for p in self.pages if p.review is not None]
        if not judged:
            return 0.0
        return sum(p.review.hero_recognizable for p in judged if p.review) / len(self.pages)

    @property
    def first_attempt_recognizable_ratio(self) -> float:
        return sum(bool(p.first_attempt_recognizable) for p in self.pages) / len(self.pages)


def default_companion(theme: Theme, lang: Lang) -> CompanionSpec | None:
    d = theme.default_companion
    if not theme.companion_slot or d is None:
        return None
    return CompanionSpec(
        name=d.name_ar if lang == "ar" else d.name_en,
        type_hint="creature",
        description_en=d.description_en,
    )


async def generate_book(rt: Runtime, req: BookRequest) -> BookArtifacts:
    use_drawing = req.theme.companion_slot and req.cleaned_drawing is not None and req.companion
    character_task = generate_character_sheet(rt, req.child, req.photos, req.style)
    if use_drawing and req.cleaned_drawing is not None and req.companion is not None:
        character_sheet, options = await asyncio.gather(
            character_task,
            generate_companion_options(rt, req.cleaned_drawing, req.companion, req.style),
        )
        companion: CompanionSpec | None = options.spec
        companion_sheet: GeneratedImage | None = options.options[req.companion_pick - 1]
    else:
        character_sheet, options = await character_task, None
        companion, companion_sheet = default_companion(req.theme, req.lang), None

    cast = Cast(req.child, req.style, character_sheet, companion, companion_sheet)
    fidelity_task = (
        score_fidelity(rt, req.cleaned_drawing, companion_sheet)
        if use_drawing and req.cleaned_drawing and companion_sheet
        else None
    )
    story, (cover, pages), fidelity = await asyncio.gather(
        write_story(rt, req.theme, req.child, req.lang, companion),
        generate_pages(rt, cast, req.theme),
        fidelity_task if fidelity_task else asyncio.sleep(0, result=None),
    )
    return BookArtifacts(character_sheet, companion, options, companion_sheet, fidelity, story, cover, pages)
