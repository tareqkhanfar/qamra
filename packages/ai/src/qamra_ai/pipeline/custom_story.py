"""«حكاية خاصة»: a Magic story written from the family's brief (Addendum 4 §1B, product magic-custom-story).

The brief (occasion, place, 2–3 things the child loves or did, a wish or lesson, optional family names) is
checked twice before any story is written: locally for personal data and plainly unsafe words (the API gives
the parent a friendly error at once), then by the same safety review as every story (Haiku). Claude (Sonnet)
then writes the text *and* the pictures of the base «custom» theme's beats (prompts story_custom.v1), with the
usual page count, word limit and vowelization rules; the result gets the same safety review as a theme story.
The rewritten theme (scenes, places, times, outfits) is what the book's pages are drawn from.
"""

import json
import re
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from qamra_ai import prompts
from qamra_ai.errors import ContentBlocked, InvalidOutput
from qamra_ai.pipeline.companion import type_label
from qamra_ai.pipeline.models import Child, CompanionSpec, Lang, SafetyVerdict, StoryOut, StoryPageOut
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import VOWELIZE_MAX_AGE, Story, clean_parent_message, validate_story
from qamra_ai.pipeline.theme import Theme, TimeOfDay, max_words_for, word_count
from qamra_ai.text.base import SystemPart

CUSTOM_THEME = "custom"  # content/themes/custom: the base beats every custom story is written on
PROMPT_VERSION = 1
MAX_OTHERS = 6


def _squash(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.split()) or None


Short = Annotated[str, Field(min_length=2, max_length=60)]


class FamilyMember(BaseModel):
    """Someone the family wants in the story, in their own word (never assumed: ستّي, خالتو, بابا…)."""

    role: str = Field(min_length=1, max_length=20)
    name: str | None = Field(default=None, max_length=30)

    @field_validator("role", "name", mode="before")
    @classmethod
    def _tidy(cls, v: object) -> object:
        return _squash(v) if isinstance(v, str) else v


class CustomBrief(BaseModel):
    occasion: Short
    place: Short
    loves: list[Short] = Field(min_length=2, max_length=3)
    wish: str = Field(min_length=2, max_length=120)
    family: list[FamilyMember] = Field(default_factory=list, max_length=6)

    @field_validator("occasion", "place", "wish", mode="before")
    @classmethod
    def _tidy(cls, v: object) -> object:
        return _squash(v) or "" if isinstance(v, str) else v

    @field_validator("loves", mode="before")
    @classmethod
    def _tidy_list(cls, v: object) -> object:
        if isinstance(v, list):
            return [s for s in (_squash(x) if isinstance(x, str) else x for x in v) if s]
        return v


# ---- the local screen (instant, before anything costs money) ------------------------------------------

_LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(com|net|org|ps|jo|io|me|info)\b|@\w", re.I)
_DIGITS = re.compile(r"[0-9٠-٩۰-۹]")
_DIACRITICS = re.compile(r"[ً-ْٰـ]")
_PREFIXES = ("وال", "بال", "فال", "لل", "ال", "و", "ب", "ف")
UNSAFE_WORDS = frozenset(
    {
        # a short list of words that never belong in a picture book; the AI review catches the rest
        "قتل", "يقتل", "مقتل", "سلاح", "أسلحة", "اسلحة", "مسدس", "بندقية", "رصاص", "قنبلة", "انفجار",
        "حرب", "دماء", "ذبح", "مخدرات", "kill", "killed", "killing", "gun", "guns", "weapon", "weapons",
        "bomb", "bombs", "blood", "war", "murder", "drugs", "sexy",
    }
)  # fmt: skip


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w؀-ۿ]+", _DIACRITICS.sub("", text.lower()))


def _unsafe_word(token: str) -> bool:
    if token in UNSAFE_WORDS:
        return True
    return any(token.startswith(p) and token[len(p) :] in UNSAFE_WORDS for p in _PREFIXES)


def screen_brief(brief: CustomBrief) -> list[str]:
    """The fields that carry personal data (links, e-mails, phone numbers) or plainly unsafe words."""
    fields: dict[str, list[str]] = {
        "occasion": [brief.occasion],
        "place": [brief.place],
        "loves": list(brief.loves),
        "wish": [brief.wish],
        "family": [f"{m.role} {m.name or ''}" for m in brief.family],
    }
    bad = []
    for field, texts in fields.items():
        for text in texts:
            phone = len(_DIGITS.findall(text)) >= 6
            if _LINK.search(text) or phone or any(_unsafe_word(t) for t in _tokens(text)):
                bad.append(field)
                break
    return bad


class BriefRejected(ContentBlocked):
    user_message_ar = (
        "بعض ما كتبتموه في تفاصيل الحكاية لا يناسب كتاب أطفال. عدّلوه قليلًا ونكتب الحكاية من جديد."
    )
    user_message_en = (
        "Some of the story details don't fit a children's book. Edit them a little and we'll write it again."
    )


# ---- what Claude returns -----------------------------------------------------------------------------------


class CustomScene(BaseModel):
    scene: str
    location: str | None = None
    time: TimeOfDay = "morning"
    outfit: Literal["day", "festive", "sleep"] = "day"
    others: str | None = None
    others_count: int = 0
    companion_action: str | None = None


class CustomPageOut(CustomScene):
    index: int
    text: str


class CustomLocation(BaseModel):
    key: str
    description: str


class CustomStoryOut(BaseModel):
    title: str
    dedication: str
    locations: list[CustomLocation]
    cover: CustomScene
    pages: list[CustomPageOut]
    parents_lesson: str = ""
    parents_questions: list[str] = []
    blurb: str = ""

    def story(self) -> StoryOut:
        return StoryOut(
            title=self.title,
            dedication=self.dedication,
            pages=[StoryPageOut(index=p.index, text=p.text) for p in self.pages],
            parents_lesson=self.parents_lesson,
            parents_questions=self.parents_questions,
            blurb=self.blurb,
        )


# ---- the story and its pictures ------------------------------------------------------


@dataclass
class CustomStory:
    story: Story
    theme: Theme  # the base theme with this story's scenes, places, times and outfits


def page_plan(theme: Theme) -> list[dict[str, object]]:
    return [{"index": p.index, "beat": p.beat, "layout": p.layout} for p in theme.pages]


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")[:32]


def custom_theme(base: Theme, out: CustomStoryOut) -> Theme:
    """The base theme redrawn for this story: every scene and place from the brief, the beats and layouts
    kept (so the page plan, spreads and print layout stay valid). Unknown places fall back to none."""
    locations = {_key(loc.key): " ".join(loc.description.split()) for loc in out.locations[:6]}
    locations = {k: v for k, v in locations.items() if k and v} or dict(base.locations)
    data = base.model_dump(mode="json")

    def scene(shape: dict[str, object], s: CustomScene) -> dict[str, object]:
        where = _key(s.location or "")
        return {
            **shape,
            "scene": " ".join(s.scene.split()) or shape["scene"],
            "location": where if where in locations else None,
            "time": s.time,
            "outfit": s.outfit if s.outfit in base.outfits else shape["outfit"],
            "others": _squash(s.others),
            "others_count": max(0, min(MAX_OTHERS, s.others_count)) if _squash(s.others) else 0,
            "companion_action": _squash(s.companion_action),
        }

    data["locations"] = locations
    data["cover"] = scene(data["cover"], out.cover)
    data["pages"] = [scene(shape, page) for shape, page in zip(data["pages"], out.pages, strict=True)]
    return Theme.model_validate(data)


async def review_brief(rt: Runtime, brief: CustomBrief, child: Child) -> None:
    """The same safety review as every story, on the family's words, before anything is written."""
    verdict = await rt.ask(
        step="story:brief_safety",
        system=prompts.render("story_safety", version=2, gender=child.gender),
        user=[json.dumps({"custom_story_brief": brief.model_dump()}, ensure_ascii=False)],
        schema=SafetyVerdict,
        fast=True,
        kind="safety",
    )
    if not verdict.safe:
        raise BriefRejected("custom story brief failed safety review: " + "; ".join(verdict.reasons))


async def write_custom_story(
    rt: Runtime,
    base: Theme,
    child: Child,
    lang: Lang,
    companion: CompanionSpec | None,
    brief: CustomBrief,
    parent_message: str | None = None,
) -> CustomStory:
    if screen_brief(brief):
        raise BriefRejected("custom story brief failed the local screen")
    await review_brief(rt, brief, child)
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
        "story_custom",
        version=PROMPT_VERSION,
        brand_name_en=s.brand_name_en,
        brand_name_ar=s.brand_name_ar,
        lang=lang,
    )
    max_words = max_words_for(child.age)
    user = prompts.render(
        "story_custom_user",
        version=PROMPT_VERSION,
        child=child,
        lang=lang,
        companion=comp_ctx,
        max_words=max_words,
        vowelize=lang == "ar" and child.age <= VOWELIZE_MAX_AGE,
        theme_title=base.title(lang, child.gender, child.name),
        brief=brief,
        pages_json=json.dumps(page_plan(base), ensure_ascii=False, indent=1),
    )

    out = await rt.ask(
        step="story",
        system=[SystemPart(system, cache=True)],
        user=[user],
        schema=CustomStoryOut,
        kind="story",
        effort=s.story_effort,
        max_tokens=16000,
    )
    story = validate_story(out.story(), len(base.pages))
    if [p.index for p in out.pages] != [p.index for p in base.pages]:
        raise InvalidOutput("custom story pages do not follow the plan")
    review = out.model_dump()
    message = clean_parent_message(parent_message)
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
        raise ContentBlocked("custom story failed safety review: " + "; ".join(verdict.reasons))
    long_pages = [p.index for p in story.pages if word_count(p.text) > round(max_words * 1.15)]
    return CustomStory(story=Story(out=story, long_pages=long_pages), theme=custom_theme(base, out))
