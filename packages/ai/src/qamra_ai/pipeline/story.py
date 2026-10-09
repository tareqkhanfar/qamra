"""Story: theme template → Claude (Sonnet) adapts it to the child → Haiku safety review.

Addendum 3: ≤ 35 words per page for ages 3–5, a «للأهل» page (lesson + 2 questions) and a back-cover
blurb in the same call, and prompt caching for the fixed part (rules + theme bible) so class batches of
the same theme reuse it.
"""

import json
from collections.abc import Collection
from dataclasses import dataclass, field

from qamra_ai import prompts
from qamra_ai.errors import ContentBlocked, InvalidOutput
from qamra_ai.pipeline.companion import type_label
from qamra_ai.pipeline.models import Child, CompanionSpec, Lang, SafetyVerdict, StoryOut
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import Theme, max_words_for, render_template, word_count
from qamra_ai.text.base import SystemPart
from qamra_pdf.arabic_names import accusative, fix_vocatives

VOWELIZE_MAX_AGE = 7
PARENT_MESSAGE_MAX = 120  # Addendum 3 §4: optional dedication message from the parent


@dataclass
class Story:
    out: StoryOut
    long_pages: list[int] = field(default_factory=list)  # pages over the word limit (flag for review)


def base_pages(theme: Theme, child: Child, lang: Lang, companion_name: str) -> list[dict[str, object]]:
    return [
        {
            "index": p.index,
            "beat": p.beat,
            "text": theme.base_text(p, lang, child.gender, child.name, companion_name),
            **({"wordless": True} if p.wordless else {}),  # a silent picture page: its text stays empty
        }
        for p in theme.pages
    ]


def theme_bible(theme: Theme, lang: Lang) -> str:
    """The fixed part of the story prompt for this theme: identical for every child (cacheable)."""
    title = theme.title_ar if lang == "ar" else theme.title_en
    lines = [f"Title template: {title}", f"Ages: {theme.age_range[0]}–{theme.age_range[1]}", "Beats:"]
    lines += [f"{p.index}. {p.beat}" for p in theme.pages]
    if theme.for_parents:
        lesson = theme.for_parents.lesson_ar if lang == "ar" else theme.for_parents.lesson_en
        lines.append(f"Lesson: {lesson}")
    return "\n".join(lines)


def validate_story(story: StoryOut, n_pages: int, wordless: Collection[int] = ()) -> StoryOut:
    """Pages 1..n, text on every page except the theme's wordless ones (Addendum 11 §4.4), which are
    emptied, and the two questions for parents."""
    indices = [p.index for p in story.pages]
    if indices != list(range(1, n_pages + 1)):
        raise InvalidOutput(f"story must have pages 1..{n_pages}, got {indices}")
    empty = [p.index for p in story.pages if p.index not in wordless and not p.text.strip()]
    if empty:
        raise InvalidOutput(f"story pages without text: {empty}")
    if len(story.parents_questions) != 2:
        raise InvalidOutput("story must have exactly 2 questions for parents")
    if any(p.index in wordless and p.text for p in story.pages):
        pages = [p.model_copy(update={"text": ""}) if p.index in wordless else p for p in story.pages]
        story = story.model_copy(update={"pages": pages})
    return story


def fix_name_case(story: StoryOut, name: str) -> StoryOut:
    """The model's text with «يا أبو بكر» → «يا أبا بكر» on the child's own name (Fusha: the vocative of
    «أبو …» is «أبا …»; `qamra_pdf.arabic_names.fix_vocatives`). The prompt asks the model to inflect the name
    in every case; a vocative it misses is fixed here, the same way every time. Other names stay untouched."""
    if accusative(name) == name:
        return story

    def fix(text: str) -> str:
        return fix_vocatives(text, name)

    return story.model_copy(
        update={
            "title": fix(story.title),
            "dedication": fix(story.dedication),
            "pages": [p.model_copy(update={"text": fix(p.text)}) for p in story.pages],
            "parents_lesson": fix(story.parents_lesson),
            "parents_questions": [fix(q) for q in story.parents_questions],
            "blurb": fix(story.blurb),
        }
    )


def wordless_pages(theme: Theme) -> set[int]:
    return {p.index for p in theme.pages if p.wordless}


def missing_text(theme: Theme, story: StoryOut) -> list[int]:
    """Story pages the theme expects text on that have none: the book must not be drawn or printed."""
    texts = {p.index: p.text for p in story.pages}
    return [p.index for p in theme.pages if not p.wordless and not texts.get(p.index, "").strip()]


def clean_parent_message(message: str | None) -> str | None:
    if not message:
        return None
    text = " ".join(message.split())
    if len(text) > PARENT_MESSAGE_MAX:
        raise InvalidOutput(f"parent message longer than {PARENT_MESSAGE_MAX} characters")
    return text or None


async def write_story(
    rt: Runtime,
    theme: Theme,
    child: Child,
    lang: Lang,
    companion: CompanionSpec | None,
    parent_message: str | None = None,
) -> Story:
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
    fp = theme.for_parents

    def render(template: str) -> str:
        return render_template(template, child.gender, child.name, comp_name)

    system = [
        SystemPart(
            prompts.render(
                "story_adapt",
                version=2,
                brand_name_en=s.brand_name_en,
                brand_name_ar=s.brand_name_ar,
                lang=lang,
                theme_bible=theme_bible(theme, lang),
            ),
            cache=True,
        )
    ]
    max_words = max_words_for(child.age)
    user = prompts.render(
        "story_adapt_user",
        version=2,
        child=child,
        lang=lang,
        companion=comp_ctx,
        max_words=max_words,
        vowelize=lang == "ar" and child.age <= VOWELIZE_MAX_AGE,
        theme_title=theme.title(lang, child.gender, child.name),
        pages_json=json.dumps(base_pages(theme, child, lang, comp_name), ensure_ascii=False, indent=1),
        lesson=render(fp.lesson_ar if lang == "ar" else fp.lesson_en) if fp else "",
        questions=[render(q) for q in ((fp.questions_ar if lang == "ar" else fp.questions_en) if fp else [])],
        blurb=render((theme.blurb_ar if lang == "ar" else theme.blurb_en) or ""),
    )
    out = validate_story(
        await rt.ask(
            step="story",
            system=system,
            user=[user],
            schema=StoryOut,
            kind="story",
            effort=s.story_effort,
            max_tokens=16000,
        ),
        len(theme.pages),
        wordless_pages(theme),
    )
    out = fix_name_case(out, child.name)
    message = clean_parent_message(parent_message)
    review = out.model_dump()
    if message:
        review["parent_message"] = message
    verdict = await rt.ask(
        step="story:safety",
        system=prompts.render("story_safety", version=2, gender=child.gender),
        user=[json.dumps(review, ensure_ascii=False)],
        schema=SafetyVerdict,
        fast=True,
        kind="safety",
    )
    if not verdict.safe:
        raise ContentBlocked("story failed safety review: " + "; ".join(verdict.reasons))
    long_pages = [p.index for p in out.pages if word_count(p.text) > round(max_words * 1.15)]
    return Story(out=out, long_pages=long_pages)
