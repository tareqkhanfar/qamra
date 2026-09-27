"""Page illustrations: prompt from style + scene + references; bounded parallelism; review; auto-redraw."""

import asyncio
from dataclasses import dataclass, field
from typing import Literal

from qamra_ai import prompts
from qamra_ai.errors import ContentBlocked
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage
from qamra_ai.pipeline.models import Child, CompanionSpec, PageReview
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import ArtStyle, Theme, ThemeScene
from qamra_ai.text.base import ImagePart

PageStatus = Literal["ok", "needs_regeneration", "blocked"]


@dataclass
class PageResult:
    index: int  # 0 = cover
    image: GeneratedImage | None
    review: PageReview | None
    status: PageStatus
    attempts: int
    first_attempt_recognizable: bool | None = None
    history: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Cast:
    """Who appears on every page, with the reference images the model gets."""

    child: Child
    style: ArtStyle
    character_sheet: GeneratedImage
    companion: CompanionSpec | None = None
    companion_sheet: GeneratedImage | None = None

    def refs(self) -> list[RefImage]:
        refs = [
            RefImage(
                self.character_sheet.data,
                self.character_sheet.mime,
                "THE HERO — character reference sheet of the child",
            )
        ]
        if self.companion and self.companion_sheet:
            refs.append(
                RefImage(
                    self.companion_sheet.data,
                    self.companion_sheet.mime,
                    f"THE COMPANION — character sheet of {self.companion.name}",
                )
            )
        return refs

    def companion_ctx(self) -> dict[str, object] | None:
        if not self.companion:
            return None
        return {
            "name": self.companion.name,
            "description_en": self.companion.description_en,
            "has_ref": self.companion_sheet is not None,
        }


def page_request(cast: Cast, scene: ThemeScene, index: int, total: int, attempt: int) -> ImageRequest:
    is_cover = index == 0
    prompt = prompts.render(
        "page_image",
        is_cover=is_cover,
        index=index,
        total=total,
        scene=scene.scene,
        companion=cast.companion_ctx(),
        companion_action=scene.companion_action,
        gender=cast.child.gender,
        age=cast.child.age,
        style_guide=cast.style.guide,
    )
    step = "cover" if is_cover else f"page:{index}"
    return ImageRequest(
        step=f"{step}:a{attempt}",
        prompt=prompt,
        refs=cast.refs(),
        aspect="1:1",
        seed=index * 100 + attempt,
    )


async def review_page(
    rt: Runtime, cast: Cast, scene: ThemeScene, index: int, image: GeneratedImage
) -> PageReview:
    parts: list[str | ImagePart] = [ImagePart(cast.character_sheet.data, cast.character_sheet.mime)]
    if cast.companion_sheet:
        parts.append(ImagePart(cast.companion_sheet.data, cast.companion_sheet.mime))
    parts += [ImagePart(image.data, image.mime), "The last image is the page to review."]
    system = prompts.render(
        "page_review",
        step_label="cover" if index == 0 else str(index),
        scene=scene.scene,
        companion_ref=cast.companion_sheet is not None,
        companion_desc=cast.companion.description_en if cast.companion else "",
    )
    step = "review:cover" if index == 0 else f"review:{index}"
    return await rt.ask(step=step, system=system, user=parts, schema=PageReview, fast=True)


def passes(review: PageReview) -> bool:
    return (
        review.safe
        and review.hero_recognizable
        and review.companion_present
        and not review.has_text_artifacts
    )


async def generate_page(rt: Runtime, cast: Cast, scene: ThemeScene, index: int, total: int) -> PageResult:
    result = PageResult(index=index, image=None, review=None, status="blocked", attempts=0)
    for attempt in range(1, rt.settings.page_max_regenerations + 2):
        result.attempts = attempt
        try:
            image = await rt.draw(page_request(cast, scene, index, total, attempt))
        except ContentBlocked as e:
            result.history.append(f"a{attempt}: blocked by provider ({e})")
            continue
        review = await review_page(rt, cast, scene, index, image)
        if attempt == 1:
            result.first_attempt_recognizable = review.hero_recognizable
        result.history.append(f"a{attempt}: {review.model_dump_json()}")
        if review.safe and (result.image is None or passes(review)):
            result.image, result.review = image, review
        if passes(review):
            result.status = "ok"
            return result
        if result.image is not None:
            result.status = "needs_regeneration"
    return result


async def generate_pages(rt: Runtime, cast: Cast, theme: Theme) -> tuple[PageResult, list[PageResult]]:
    """Cover + every theme page, at most `image_concurrency` in flight."""
    sem = asyncio.Semaphore(rt.settings.image_concurrency)
    total = len(theme.pages)

    async def one(scene: ThemeScene, index: int) -> PageResult:
        async with sem:
            return await generate_page(rt, cast, scene, index, total)

    results = await asyncio.gather(one(theme.cover, 0), *(one(p, p.index) for p in theme.pages))
    return results[0], list(results[1:])
