"""Canned Claude answers for tests and `--provider fake` dry runs (no network, $0)."""

import json
import re

from pydantic import BaseModel

from qamra_ai.pipeline.models import (
    CompanionFidelity,
    DrawingReview,
    PageReview,
    SafetyVerdict,
    StoryOut,
    StoryPageOut,
)
from qamra_ai.text.base import UserPart
from qamra_ai.text.fake import FakeTextProvider

_PAGES = re.compile(r"<pages_json>\s*(.*?)\s*</pages_json>", re.S)
_THEME = re.compile(r"^Theme: (.+)$", re.M)
_NAME = re.compile(r"^- name: (.+)$", re.M)


def _text(user: list[UserPart]) -> str:
    return "\n".join(p for p in user if isinstance(p, str))


def fake_story(step: str, system: str, user: list[UserPart]) -> BaseModel:
    """Echo the base story (already gender-rendered) back, as Claude would after adapting it."""
    text = _text(user)
    pages_m, theme_m, name_m = _PAGES.search(text), _THEME.search(text), _NAME.search(text)
    if not (pages_m and theme_m and name_m):
        raise ValueError("fake story responder: unexpected prompt shape")
    pages = json.loads(pages_m.group(1))
    name = name_m.group(1).strip()
    arabic = bool(re.search(r"[؀-ۿ]", pages[0]["text"]))
    dedication = (
        f"إلى {name}، نجمِنا الصغير: نحبُّكَ حتّى القمر."
        if arabic
        else (f"To {name}, our little star: we love you to the moon.")
    )
    return StoryOut(
        title=theme_m.group(1).strip(),
        dedication=dedication,
        pages=[StoryPageOut(index=p["index"], text=p["text"]) for p in pages],
    )


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
            "PageReview": lambda *_: PageReview(
                safe=True,
                hero_recognizable=True,
                companion_present=True,
                has_text_artifacts=False,
                notes="fake review",
            ),
            "CompanionFidelity": lambda *_: CompanionFidelity(
                score=4, preserved_features=["fake"], lost_features=[], safe=True
            ),
        }
    )
