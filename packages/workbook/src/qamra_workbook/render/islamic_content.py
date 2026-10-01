"""The content of the sample pages of «قلبي يعرف الله» (content/islamic/samples.yaml) as typed models, and
the engine
page specs built from them. A page never holds a verse, hadith or dhikr: a block names a source id and the
builder
asks the resolver (`islamic_sources`) for the wording. Strict models (`extra="forbid"`): a typo in the file
fails
loudly, naming the page.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from qamra_workbook.islamic_sources import SAMPLES, Resolver
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.spec import PageSpec


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Marker(_M):
    start: str
    end: str


class Claim(_M):
    """A short text of the page: the drafter's simple explanation of a source (marked AI-drafted) or a plain
    line."""

    text: str
    sources: list[str] = Field(default_factory=list)
    ai_drafted: bool = False


class Choice(_M):
    """An answer to tick. Plain options are typed (`t`); an option that IS religious wording (a dhikr, a
    verse) names a
    source instead, and the page prints what the register gives (marked while unapproved, a placeholder if
    missing)."""

    t: str = ""
    ok: bool = False
    feedback: str = ""
    source: str = ""
    span: Marker | None = None

    @model_validator(mode="after")
    def _typed_or_sourced(self) -> Choice:
        if bool(self.t) == bool(self.source):
            raise ValueError("a choice has either typed text `t` or a `source`, not both and not neither")
        if self.span is not None and not self.source:
            raise ValueError("`span` needs a `source`")
        return self


class Quote(_M):
    """A block that prints a source's wording (a verse, a quotation, a dhikr): by source id, never by text."""

    source: str
    label: str = ""
    span: Marker | None = None
    frame: str = ""


class Ask(_M):
    text: str
    choices: list[Choice]
    sources: list[str] = Field(default_factory=list)


class Scene(_M):
    art: str
    text: str = ""
    sources: list[str] = Field(default_factory=list)
    ai_drafted: bool = False
    figures: list[str] = Field(default_factory=list)


class Narrator(_M):
    figures: list[str]
    intro: str


class Base(_M):
    id: str
    title: str
    unit: str = ""
    volume: str = ""
    engine_type: str = ""
    instruction: str = ""
    tags: list[str] = Field(default_factory=list)
    sacred_text: str = ""
    flags: list[str] = Field(default_factory=list)


class ProphetStory(Base):
    type: Literal["prophet-story"]
    narrator: Narrator
    scenes: list[Scene]
    verse: Quote
    lesson: Claim
    question: Ask


class Step(_M):
    n: int
    t: str
    art: str = ""
    times: int | None = None
    sources: list[str] = Field(default_factory=list)
    scholar_decision: bool = False
    dua: str = ""


class OrderSteps(Base):
    type: Literal["order-steps"]
    steps: list[Step]
    scholar_points: list[str] = Field(default_factory=list)
    parent_line: str = ""


class Dhikr(Base):
    type: Literal["dhikr"]
    when: str
    dhikr: Quote
    why: Claim
    manner: Claim
    scene: Scene
    home: str
    audio: dict[str, str] = Field(default_factory=dict)


class Wwyd(Base):
    type: Literal["wwyd"]
    scenario: str
    scene: Scene
    choices: list[Choice]
    quote: Quote
    sources: list[str] = Field(default_factory=list)
    role_play: str = ""


class Wdif(Base):
    type: Literal["wdif"]
    intro: Claim
    steps: list[Step]
    quote: Quote
    meaning: Claim
    tracker: str


class Coloring(Base):
    type: Literal["coloring"]
    art: str


class Hunt(Base):
    type: Literal["blessings-hunt"]
    art: str
    find: list[str]
    closing: Claim
    draw_box: str


class TrueFalse(_M):
    t: str
    ok: bool
    sources: list[str] = Field(default_factory=list)


class UnitReview(Base):
    type: Literal["unit-review"]
    subtitle: str = ""
    true_false: list[TrueFalse]
    choose: Ask
    stars: str


class ParentGuide(Base):
    type: Literal["parent-guide"]
    lang: str = "modern-standard"
    learned: Claim
    explain: Claim
    ask: str
    together: str
    habit: Claim
    care_note: str


class Passport(Base):
    type: Literal["passport"]
    gendered_title: str = ""
    photo_slot: str = "reader"
    stamps_from: str = "units.yaml"
    challenge_stars: int = 8


class Certificate(Base):
    type: Literal["certificate"]
    statement: str
    fields: list[str]
    reviewed_by_line: bool = False


class Tracker(_M):
    ayahs: int
    days: int


class Surah(Base):
    type: Literal["surah"]
    verse: Quote
    meaning: Claim
    audio_qr: dict[str, str] = Field(default_factory=dict)
    tracker: Tracker
    care_note: str


# ---- the thin page types (no sample page yet): a prayer's steps, true or false, a pillar, a day, a
# unit's endings,
# the final assessment


class TrueFalsePage(Base):
    type: Literal["true-false"]
    statements: list[TrueFalse]


class PillarCard(Base):
    type: Literal["pillar-card"]
    pillar: str
    idea: Claim
    question: Ask
    art: str = ""


class Moment(_M):
    when: str
    t: str
    picture: str = "star"
    sources: list[str] = Field(default_factory=list)


class DayWithAllah(Base):
    type: Literal["my-day-with-allah"]
    moments: list[Moment]


class UnitClosing(Base):
    type: Literal["unit-closing"]
    learned: list[str]
    apply: str
    dhikr: Quote
    challenge: str


class Skill(_M):
    skill: str
    t: str
    sources: list[str] = Field(default_factory=list)


class FinalAssessment(Base):
    type: Literal["final-assessment"]
    skills: list[Skill]
    note: str = ""


class PrayerSteps(Base):
    type: Literal["prayer-steps"]
    steps: list[Step]
    scholar_points: list[str] = Field(default_factory=list)
    parent_line: str = ""


Page = Annotated[
    ProphetStory
    | OrderSteps
    | Dhikr
    | Wwyd
    | Wdif
    | Coloring
    | Hunt
    | UnitReview
    | ParentGuide
    | Passport
    | Certificate
    | Surah
    | TrueFalsePage
    | PillarCard
    | DayWithAllah
    | UnitClosing
    | FinalAssessment
    | PrayerSteps,
    Field(discriminator="type"),
]
_PAGES: TypeAdapter[Page] = TypeAdapter(Page)

# the plan's page type → the engine's page type name (a lead's `engine_type` wins)
ENGINE_NAMES: dict[str, str] = {
    "prophet-story": "prophet-story",
    "order-steps": "wudu-steps",
    "dhikr": "dhikr-situation",
    "wwyd": "what-would-you-do",
    "wdif": "what-do-i-do-if",
    "coloring": "islamic-coloring",
    "blessings-hunt": "blessings-hunt",
    "unit-review": "islamic-unit-review",
    "parent-guide": "parent-guide",
    "passport": "muslim-passport",
    "certificate": "muslim-certificate",
    "surah": "surah-page",
    "true-false": "true-false",
    "pillar-card": "pillar-card",
    "my-day-with-allah": "my-day-with-allah",
    "unit-closing": "unit-closing",
    "final-assessment": "final-assessment",
    "prayer-steps": "prayer-steps",
}
AUDIO_TYPES = frozenset({"dhikr", "surah"})  # pages with a QR to a recorded voice (never TTS for sacred text)
FINALE = "finale"  # the section of the passport and the certificate: they belong to no unit


def parse_page(raw: dict[str, Any]) -> Page:
    try:
        return _PAGES.validate_python(raw)
    except ValidationError as err:
        first = err.errors()[0]
        loc = ".".join(str(p) for p in first["loc"][1:])
        raise ValueError(f"page {raw.get('id', '?')}: {loc}: {first['msg']}") from None


def load_pages(path: Path = SAMPLES) -> list[Page]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [parse_page(p) for p in raw["pages"]]


@dataclass(frozen=True)
class IslamicContext:
    """What the series' page builders need besides the page: the resolver for the wording, the build mode and
    the cast."""

    resolver: Resolver
    kit: Kit
    mode: Literal["preview", "print"] = "preview"
    date: dt.date = dt.date(2026, 10, 1)
    review_marks: bool = False


def page_spec(page: Page, number: int, context: IslamicContext) -> PageSpec:
    """The engine's page for a sample page: the model and the context ride in `params`."""
    section = page.unit or FINALE
    title = getattr(page, "gendered_title", "") or page.title
    return PageSpec(
        id=page.id,
        type=page.engine_type or ENGINE_NAMES[page.type],
        number=number,
        section=section,
        title=title,
        instruction=page.instruction,
        audio=page.type in AUDIO_TYPES,
        params={"page": page, "islamic": context},
    )
