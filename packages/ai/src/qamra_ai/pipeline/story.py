"""Story: theme template → Claude adapts to the child (gender, age, interests, companion) → safety review."""

import json

from qamra_ai import prompts
from qamra_ai.errors import ContentBlocked, InvalidOutput
from qamra_ai.pipeline.companion import type_label
from qamra_ai.pipeline.models import Child, CompanionSpec, Lang, SafetyVerdict, StoryOut
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import Theme

MAX_CHARS_PER_PAGE = 180  # design: 180-char soft limit per page
VOWELIZE_MAX_AGE = 7


def base_pages(theme: Theme, child: Child, lang: Lang, companion_name: str) -> list[dict[str, object]]:
    return [
        {
            "index": p.index,
            "beat": p.beat,
            "text": theme.base_text(p, lang, child.gender, child.name, companion_name),
        }
        for p in theme.pages
    ]


def validate_story(story: StoryOut, n_pages: int) -> StoryOut:
    indices = [p.index for p in story.pages]
    if indices != list(range(1, n_pages + 1)):
        raise InvalidOutput(f"story must have pages 1..{n_pages}, got {indices}")
    if any(not p.text.strip() for p in story.pages):
        raise InvalidOutput("story has an empty page")
    return story


async def write_story(
    rt: Runtime, theme: Theme, child: Child, lang: Lang, companion: CompanionSpec | None
) -> StoryOut:
    comp_name = companion.name if companion else ""
    comp_ctx = None
    if companion:
        comp_ctx = {
            "name": companion.name,
            "type_label": type_label(companion),
            "traits": companion.traits,
            "description_en": companion.description_en,
        }
    s = rt.settings
    system = prompts.render(
        "story_adapt",
        brand_name_en=s.brand_name_en,
        brand_name_ar=s.brand_name_ar,
        n_pages=len(theme.pages),
        lang=lang,
        gender=child.gender,
        age=child.age,
        vowelize=lang == "ar" and child.age <= VOWELIZE_MAX_AGE,
        max_chars=MAX_CHARS_PER_PAGE,
        companion=comp_ctx,
    )
    user = prompts.render(
        "story_adapt_user",
        child=child,
        companion=comp_ctx,
        theme_title=theme.title(lang, child.gender, child.name),
        pages_json=json.dumps(base_pages(theme, child, lang, comp_name), ensure_ascii=False, indent=1),
    )
    story = validate_story(
        await rt.ask(step="story", system=system, user=[user], schema=StoryOut), len(theme.pages)
    )
    verdict = await rt.ask(
        step="story:safety",
        system=prompts.render("story_safety", gender=child.gender),
        user=[story.model_dump_json()],
        schema=SafetyVerdict,
        fast=True,
    )
    if not verdict.safe:
        raise ContentBlocked("story failed safety review: " + "; ".join(verdict.reasons))
    return story
