"""Canned Claude answers for tests and offline runs (`fake` / `sketch` providers: no network, $0)."""

import json
import re

from pydantic import BaseModel

from qamra_ai.pipeline.classic import ClassicQA, HeroBoxOut, PortraitQA
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


def fake_custom_story(step: str, system: str, user: list[UserPart]) -> BaseModel:
    """A custom story shaped like Claude's (story_custom.v1): the plan's beats with the brief woven in."""
    from qamra_ai.pipeline.custom_story import CustomLocation, CustomPageOut, CustomScene, CustomStoryOut

    text = _text(user)
    pages_m, name_m = _PAGES.search(text), _NAME.search(text)
    place_m, title_m = re.search(r"^- place: (.+)$", text, re.M), re.search(r"^Title idea: (.+)$", text, re.M)
    if not (pages_m and name_m and place_m and title_m):
        raise ValueError("fake custom story responder: unexpected prompt shape")
    name, place = name_m.group(1).strip(), place_m.group(1).strip()
    loves = re.findall(r"^  - (.+)$", text, re.M)
    arabic = "Vowelization:" in text  # only an Arabic request has that line
    comp = re.search(r"^Companion: (.+?) \(", text, re.M)
    with_comp = f" {'مع' if arabic else 'with'} {comp.group(1)}" if comp else ""
    out = []
    for p in json.loads(pages_m.group(1)):
        thing = loves[(p["index"] - 6) % len(loves)] if loves and p["index"] in (6, 7, 11) else ""
        line = f"{name} {'في' if arabic else 'at'} {place}{with_comp}. {thing}"
        out.append(
            CustomPageOut(
                index=p["index"],
                text=line.strip(),
                scene=f"The hero at {place}: {p['beat']}.",
                location="main_place" if p["index"] not in (1, 14) else "home",
                time="night" if p["index"] == 14 else "morning",
                outfit="sleep" if p["index"] == 14 else "festive",
                others="a kind grandmother" if p["index"] == 10 else None,
                others_count=1 if p["index"] == 10 else 0,
                companion_action="walks beside the hero",
            )
        )
    return CustomStoryOut(
        title=title_m.group(1).strip(),
        dedication=f"إلى {name}، بكلّ الحبّ." if arabic else f"To {name}, with all our love.",
        locations=[
            CustomLocation(key="home", description="a cozy limestone family home"),
            CustomLocation(key="main_place", description=f"{place}, bright and welcoming"),
        ],
        cover=CustomScene(scene=f"The hero smiling at {place}.", location="main_place", outfit="festive"),
        pages=out,
        parents_lesson="?",
        parents_questions=["?", "?"],
        blurb=f"{name}!",
    )


def good_page_qa(*_: object) -> PageQA:
    return PageQA(
        children=["the hero, center, smiling"],
        likeness=9,
        hero_count=1,
        people_count_ok=True,
        cropped=[],
        anatomy_ok=True,
        text_in_image=False,
        outfit_ok=True,
        hijab_ok=True,
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


def fake_vowelized(step: str, system: str, user: list[UserPart]) -> BaseModel:
    """The texts back as they came (only diacritics may change; the fake adds none)."""
    from qamra_ai.pipeline.vowelize import VowelizedTexts

    return VowelizedTexts.model_validate(json.loads(_text(user)))


def fake_translation(step: str, system: str, user: list[UserPart]) -> BaseModel:
    """English that says where it came from: one line per page, the placeholders kept."""
    from qamra_ai.pipeline.translate import ThemeTranslation, TranslatedPage

    source = json.loads(_text(user))
    indices = [p["index"] for p in source["pages"]]
    pages = [TranslatedPage(index=i, text_en=f"{{name}} on page {i}.") for i in indices]
    return ThemeTranslation(
        title_en="{name}'s story",
        blurb_en="A story about {name}.",
        lesson_en="Kindness helps.",
        questions_en=[f"Question {i + 1}?" for i in range(len(source["questions_ar"]))],
        pages=pages,
    )


def default_fake_text_provider() -> FakeTextProvider:
    return FakeTextProvider(
        {
            "StoryOut": fake_story,
            "CustomStoryOut": fake_custom_story,
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
            # Classic (Addendum 4 §1A): the hero stands in the middle of every page; edits pass
            "HeroBoxOut": lambda *_: HeroBoxOut(found=True, x=0.3, y=0.3, w=0.35, h=0.6, notes="fake"),
            "ClassicQA": lambda *_: ClassicQA(
                likeness=9,
                same_scene=True,
                seams=False,
                hero_count=1,
                anatomy_ok=True,
                text_in_image=False,
                style_ok=True,
                safe=True,
                notes="ok",
            ),
            "PortraitQA": lambda *_: PortraitQA(likeness=9, safe=True, text_in_image=False, notes="ok"),
            "VowelizedTexts": fake_vowelized,
            "ThemeTranslation": fake_translation,  # the template studio's English draft
        }
    )
