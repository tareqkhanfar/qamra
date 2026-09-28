"""Canned Claude answers for tests and offline runs (`fake` / `sketch` providers: no network, $0)."""

import json
import re

from pydantic import BaseModel

from qamra_ai.pipeline.models import (
    CompanionFidelity,
    DrawingReview,
    PageQA,
    SafetyVerdict,
    StoryOut,
    StoryPageOut,
)
from qamra_ai.text.base import UserPart
from qamra_ai.text.fake import FakeTextProvider

_PAGES = re.compile(r"<pages_json>\s*(.*?)\s*</pages_json>", re.S)
_TITLE = re.compile(r"^Title template: (.+)$", re.M)
_NAME = re.compile(r"^- name: (.+)$", re.M)
_LESSON = re.compile(r"^Base lesson for parents: (.+)$", re.M)
_QUESTIONS = re.compile(r"^Base questions for parents:\n((?:- .+\n?)+)", re.M)
_BLURB = re.compile(r"^Base back-cover blurb: (.+)$", re.M)


def _text(user: list[UserPart]) -> str:
    return "\n".join(p for p in user if isinstance(p, str))


def fake_story(step: str, system: str, user: list[UserPart]) -> BaseModel:
    """Echo the base story (already gender-rendered) back, as Claude would after adapting it."""
    text = _text(user)
    pages_m, title_m, name_m = _PAGES.search(text), _TITLE.search(text), _NAME.search(text)
    if not (pages_m and title_m and name_m):
        raise ValueError("fake story responder: unexpected prompt shape")
    pages = json.loads(pages_m.group(1))
    name = name_m.group(1).strip()
    arabic = bool(re.search(r"[؀-ۿ]", pages[0]["text"]))
    dedication = (
        f"إلى {name}، نجمِنا الصغير: نحبُّكَ حتّى القمر."
        if arabic
        else f"To {name}, our little star: we love you to the moon."
    )
    lesson = _LESSON.search(text)
    questions = _QUESTIONS.search(text)
    blurb = _BLURB.search(text)
    qs = [q.removeprefix("- ").strip() for q in questions.group(1).strip().splitlines()] if questions else []
    return StoryOut(
        title=title_m.group(1).strip(),
        dedication=dedication,
        pages=[StoryPageOut(index=p["index"], text=p["text"]) for p in pages],
        parents_lesson=lesson.group(1).strip() if lesson else "",
        parents_questions=[*qs, "?", "?"][:2],
        blurb=blurb.group(1).strip() if blurb else "",
    )


def good_page_qa(*_: object) -> PageQA:
    return PageQA(
        children=["the hero, center, smiling"],
        likeness=9,
        hero_count=1,
        people_count_ok=True,
        anatomy_ok=True,
        text_in_image=False,
        outfit_ok=True,
        text_space_ok=True,
        companion_ok=True,
        style_ok=True,
        safe=True,
        notes="ok",
    )


def fake_page_qa(step: str, system: str, user: list[UserPart]) -> BaseModel:
    """A passing verdict; hero_count follows the brief (plates have no hero)."""
    qa = good_page_qa()
    if "Hero expected: no" in _text(user):
        qa.hero_count = 0
    return qa


def default_fake_text_provider() -> FakeTextProvider:
    return FakeTextProvider(
        {
            "StoryOut": fake_story,
            "SafetyVerdict": lambda *_: SafetyVerdict(safe=True, reasons=[]),
            "DrawingReview": lambda *_: DrawingReview(
                safe=True,
                is_drawing=True,
                description_en="a round purple creature with three eyes, two stubby legs and an "
                "orange zigzag tail",
                key_features=[
                    "round purple body",
                    "three eyes",
                    "two stubby legs",
                    "orange zigzag tail",
                ],
                reasons=[],
            ),
            "PageQA": fake_page_qa,
            "CompanionFidelity": lambda *_: CompanionFidelity(
                score=4, preserved_features=["fake"], lost_features=[], safe=True
            ),
        }
    )
