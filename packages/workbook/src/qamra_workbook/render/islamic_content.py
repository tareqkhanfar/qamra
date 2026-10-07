"""The content of «قلبي يعرف الله» pages as typed models (the sample pages of content/islamic/samples.yaml and
the volumes' pages of content/islamic/pages/<volume>.yaml), and the engine page specs built from them.

A page never holds a verse, hadith or dhikr: a block names a source id and the builder asks the resolver
(`islamic_sources`) for the wording. Strict models (`extra="forbid"`): a typo in a file fails loudly, naming
the page. The writers' guide (docs/islamic/content-guide.md) shows one valid example of every type below."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from qamra_workbook.islamic_sources import SAMPLES, Resolver
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.spec import PageSpec

# who may appear on a page: the recurring characters and the reader (the child's own character cut-out)
CastId = Literal["huda", "reem", "salem", "reader", "naanaa"]
LISTENERS: tuple[CastId, ...] = ("huda", "reem", "salem")  # the back page's cast by default
# who may speak a line of a story: the cast, or the narrator (no picture)
Speaker = Literal["huda", "reem", "salem", "reader", "naanaa", "narrator"]


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
    verse) names a source instead, and the page prints what the register gives (marked while unapproved, a
    placeholder if missing)."""

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


class Question(Ask):
    """A question of a «choose» page: like `Ask`, with an optional picture beside it."""

    pic: str = ""


class Scene(_M):
    """A picture: a named scene (`art`, pictures/islamic_scenes.SCENES), or one composed on the page from a
    `backdrop` (pictures/islamic_backdrops.BACKDROPS) with `props` (picture-library ids, or `isl:<icon>`) and
    `figures` (the cast). People appear ONLY as the cast; a prophet's or a sira page shows none."""

    art: str = ""
    backdrop: str = ""
    props: list[str] = Field(default_factory=list, max_length=6)
    text: str = ""
    sources: list[str] = Field(default_factory=list)
    ai_drafted: bool = False
    figures: list[CastId] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _art_or_backdrop(self) -> Scene:
        if bool(self.art) == bool(self.backdrop):
            raise ValueError("a scene names either `art` (a drawn scene) or `backdrop` (a composed one)")
        if self.props and not self.backdrop:
            raise ValueError("`props` go on a composed scene (`backdrop`), not on a drawn `art` scene")
        return self


class Narrator(_M):
    figures: list[str]
    intro: str


class Line(_M):
    """One line of a story or a dialogue: who says it (`narrator`: nobody drawn) and what."""

    who: Speaker
    t: str
    sources: list[str] = Field(default_factory=list)
    ai_drafted: bool = False


class Base(_M):
    id: str
    title: str
    key: str = ""  # the page's place in its volume (content/islamic/pages/<v>.yaml), e.g. u-allah/l1-1
    unit: str = ""
    volume: str = ""
    engine_type: str = ""
    instruction: str = ""
    tags: list[str] = Field(default_factory=list)
    sacred_text: str = ""
    flags: list[str] = Field(default_factory=list)
    ai_drafted: bool = False  # the page was drafted by the AI drafter (every draft is reviewed)


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
    """A page to colour: a line-art scene (`art`), or one to six line-art pictures from the library (`pics`,
    or isl:<icon>) laid out on the page. It never carries a verse, hadith or dhikr (`sacred_text: none`)."""

    type: Literal["coloring"]
    art: str = ""
    pics: list[str] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _art_or_pics(self) -> Coloring:
        if bool(self.art) == bool(self.pics):
            raise ValueError("a colouring page has either `art` (a line-art scene) or `pics` (1–6 pictures)")
        return self


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
    # passport: the identity card, the units' stamps and the challenges' stars; journey-card: the stamps and
    # the stars only, bigger (the volume's back page «بطاقة رحلة الإيمان»)
    layout: Literal["passport", "journey-card"] = "passport"


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


class TrueFalsePage(Base):
    type: Literal["true-false"]
    statements: list[TrueFalse] = Field(min_length=2, max_length=6)


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
    """«يومي مع الله»: the moments of a day in order, each with a picture and a circle the child ticks."""

    type: Literal["day", "my-day-with-allah"]
    moments: list[Moment]
    tick: bool = True
    closing: Claim | None = None


class UnitClosing(Base):
    """The endings of a unit (Addendum 10 §5), over its two closing pages: «ماذا تعلّمت؟» and «ماذا سأطبّق هذا
    الأسبوع؟» on the first, the unit's dhikr (from the register) and «تحدٍّ صغير مع أمي وأبي» on the second. A
    page carries any of the four; the volume check wants all four across the unit's two pages."""

    type: Literal["unit-closing"]
    learned: list[str] = Field(default_factory=list, max_length=4)
    apply: str = ""
    apply_choices: list[str] = Field(default_factory=list, max_length=4)
    dhikr: Quote | None = None
    dhikr_when: str = ""
    challenge: str = ""

    @model_validator(mode="after")
    def _some_ending(self) -> UnitClosing:
        if not (self.learned or self.apply or self.dhikr or self.challenge):
            raise ValueError("a closing page carries at least one ending: learned, apply, dhikr or challenge")
        if self.apply_choices and not self.apply:
            raise ValueError("`apply_choices` go with `apply` (the question they answer)")
        return self


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


# ---- the page types of the volumes (Addendum 10 §5, §7) -----------------------------------------------


class Story(Base):
    """A short story or a dialogue of the cast: one picture, a few lines, and optionally a quotation (by
    source id), a lesson and a question."""

    type: Literal["story"]
    scene: Scene
    lines: list[Line] = Field(min_length=1, max_length=6)
    quote: Quote | None = None
    lesson: Claim | None = None
    question: Ask | None = None


class SiraStory(Base):
    """A moment from the life of our Prophet ﷺ, told by Sitti Huda: scenes of places and objects only (no
    person, no Companion, never the Prophet ﷺ), a quotation by source id, a lesson and a question."""

    type: Literal["sira-story"]
    narrator: Narrator
    scenes: list[Scene] = Field(min_length=1, max_length=4)
    quote: Quote | None = None
    lesson: Claim
    question: Ask


class Role(_M):
    role: str  # the part: «الضَّيْفُ»
    by: str  # who plays it: «{أَنْتَ/أَنْتِ}», «مَامَا»


class Say(_M):
    role: str  # one of the page's roles
    t: str
    sources: list[str] = Field(default_factory=list)


class RolePlay(Base):
    """«تمثيل موقف مع الأهل»: the situation, the parts and who plays them, a short script, a tip for the
    grown-up."""

    type: Literal["role-play"]
    scenario: str
    scene: Scene
    roles: list[Role] = Field(min_length=2, max_length=3)
    script: list[Say] = Field(min_length=2, max_length=6)
    tip: str
    stars: str = ""

    @model_validator(mode="after")
    def _known_roles(self) -> RolePlay:
        names = {r.role for r in self.roles}
        unknown = [s.role for s in self.script if s.role not in names]
        if unknown:
            raise ValueError(f"script lines name roles the page does not list: {unknown}")
        return self


class Thing(_M):
    pic: str  # a picture-library id, or isl:<icon>
    word: str  # its name as the child reads it


class FindObjects(Base):
    """«ابحث عن الأشياء»: the things to find, scattered on a board among `others`; the child rings them and
    ticks each name."""

    type: Literal["find-objects"]
    find: list[Thing] = Field(min_length=2, max_length=8)
    others: list[str] = Field(default_factory=list, max_length=10)
    closing: Claim | None = None


class Side(_M):
    """One end of a match: a picture, a word, both, or the wording of a source (a dhikr) by id."""

    pic: str = ""
    t: str = ""
    source: str = ""
    span: Marker | None = None

    @model_validator(mode="after")
    def _something(self) -> Side:
        if not (self.pic or self.t or self.source):
            raise ValueError("a side shows a picture `pic`, a text `t` or a source's wording `source`")
        if self.t and self.source:
            raise ValueError("a side has either typed text `t` or a `source`, not both")
        if self.span is not None and not self.source:
            raise ValueError("`span` needs a `source`")
        return self


class Pair(_M):
    a: Side  # the right-hand column, in this order
    b: Side  # the left-hand column, shuffled on the page
    sources: list[str] = Field(default_factory=list)


class Match(Base):
    """«صِل»: the child draws a line from each item on the right to its partner on the left."""

    type: Literal["match"]
    pairs: list[Pair] = Field(min_length=3, max_length=5)


class Choose(Base):
    """«اختر الإجابة الصحيحة»: one to four questions, each with exactly one right answer."""

    type: Literal["choose"]
    questions: list[Question] = Field(min_length=1, max_length=4)
    scene: Scene | None = None


class MazePage(Base):
    """A maze: the runner (the reader's character, or a picture) finds the way to the goal, collecting the
    pictures on the right path. No sacred text (it is a page the child draws on)."""

    type: Literal["maze"]
    runner: str = "reader"
    goal: str
    goal_word: str = ""
    size: Literal["small", "medium", "large"] = "medium"
    collect: list[str] = Field(default_factory=list, max_length=4)


class DrawPage(Base):
    """«ارسم»: a prompt, one big box (or two labelled boxes), small pictures as ideas, writing lines."""

    type: Literal["draw"]
    prompt: str
    boxes: list[str] = Field(default_factory=list, max_length=2)
    hints: list[str] = Field(default_factory=list, max_length=4)
    lines: int = Field(0, ge=0, le=3)


class CutPiece(_M):
    pic: str = ""
    t: str = ""

    @model_validator(mode="after")
    def _something(self) -> CutPiece:
        if not (self.pic or self.t):
            raise ValueError("a piece shows a picture `pic`, a word `t` or both")
        return self


class CutPaste(Base):
    """«قصّ والصق»: the pieces, given in the right order, print shuffled on a strip to cut; the board above
    has a slot for each (numbered, or labelled by `slots`). No sacred text: the strip is cut and thrown."""

    type: Literal["cut-paste"]
    pieces: list[CutPiece] = Field(min_length=3, max_length=6)
    slots: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _slots(self) -> CutPaste:
        if self.slots and len(self.slots) != len(self.pieces):
            raise ValueError("`slots` labels one slot per piece")
        return self


class UnitOpener(Base):
    """A unit's first page: its icon, colour and picture, the lessons inside (from the plan), a hello from the
    cast and a question that opens the door."""

    type: Literal["unit-opener"]
    hello: Line | None = None
    question: str = ""
    art: str = ""  # an image of content/assets (its file stem); default: the unit's own when there is one


class FrontTitle(Base):
    type: Literal["front-title"]
    subtitle: str = ""


class Intro(_M):
    who: CastId
    t: str


class FrontCharacters(Base):
    """«أصدقائي في الرحلة»: the cast and the reader, each with a line about them."""

    type: Literal["front-characters"]
    intros: list[Intro] = Field(min_length=3, max_length=5)


class Tip(_M):
    icon: str  # an engine icon (render/art.py): book, pencil, star, family, heart, sticker, speaker…
    t: str


class FrontHowTo(Base):
    """«كيف نستعمل الكتاب؟»: a few steps for the child and the family, and the note on caring for a book with
    the words of Allah in it (Addendum 10 §3.6)."""

    type: Literal["front-how-to-use"]
    steps: list[Tip] = Field(min_length=3, max_length=6)
    care_note: str


class FrontMe(Base):
    """«هذا أنا»: the reader's character, lines to fill in and a box to draw in."""

    type: Literal["front-this-is-me"]
    prompts: list[str] = Field(min_length=2, max_length=5)
    draw_box: str = ""


class BackPage(Base):
    """The last page: a goodbye from the cast and what comes next."""

    type: Literal["back-page"]
    message: str
    figures: list[CastId] = Field(default_factory=lambda: list(LISTENERS), max_length=4)
    next: str = ""


class HomeChallenge(Base):
    """«تحدّي الأسبوع» with the family: the challenge, a few steps, a star for each day. No sacred text."""

    type: Literal["home-challenge"]
    challenge: str
    steps: list[str] = Field(default_factory=list, max_length=4)
    days: int = Field(7, ge=3, le=7)
    reward: str = ""


class Quiz(Base):
    """«اختبر نفسك» / «ماذا أتذكّر؟» (a cumulative review): true or false and questions to tick."""

    type: Literal["self-test", "quiz"]
    subtitle: str = ""
    true_false: list[TrueFalse] = Field(default_factory=list, max_length=5)
    questions: list[Ask] = Field(default_factory=list, max_length=3)
    stars: str = ""

    @model_validator(mode="after")
    def _enough(self) -> Quiz:
        if len(self.true_false) + len(self.questions) < 2:
            raise ValueError("a review asks at least two things (true_false and/or questions)")
        return self


class Situation(_M):
    t: str
    choices: list[Choice] = Field(min_length=2, max_length=3)
    sources: list[str] = Field(default_factory=list)


class Assessment(Base):
    """The final fun assessment (Addendum 10 §6): a game, not an exam: true or false, questions, situations,
    and the parents' observation stars for each skill."""

    type: Literal["assessment"]
    intro: str = ""
    true_false: list[TrueFalse] = Field(default_factory=list, max_length=4)
    questions: list[Ask] = Field(default_factory=list, max_length=3)
    situations: list[Situation] = Field(default_factory=list, max_length=3)
    skills: list[Skill] = Field(default_factory=list, max_length=6)
    note: str = ""

    @model_validator(mode="after")
    def _something(self) -> Assessment:
        if not (self.true_false or self.questions or self.situations or self.skills):
            raise ValueError("an assessment page has true_false, questions, situations or skills")
        return self


class Missing(Base):
    """A placed page whose content is not written yet (preview builds only; a print build refuses)."""

    type: Literal["missing"]
    planned: str  # the plan's page type
    lesson_title: str = ""
    concepts: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


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
    | PrayerSteps
    | Story
    | SiraStory
    | RolePlay
    | FindObjects
    | Match
    | Choose
    | MazePage
    | DrawPage
    | CutPaste
    | UnitOpener
    | FrontTitle
    | FrontCharacters
    | FrontHowTo
    | FrontMe
    | BackPage
    | HomeChallenge
    | Quiz
    | Assessment,
    Field(discriminator="type"),
]
_PAGES: TypeAdapter[Page] = TypeAdapter(Page)
AnyPage = Page | Missing

# the content type → the engine's page type name (a page's `engine_type` wins)
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
    "day": "my-day-with-allah",
    "unit-closing": "unit-closing",
    "final-assessment": "final-assessment",
    "prayer-steps": "prayer-steps",
    "story": "islamic-story",
    "sira-story": "sira-story",
    "role-play": "islamic-role-play",
    "find-objects": "islamic-find-objects",
    "match": "islamic-match",
    "choose": "islamic-choose",
    "maze": "islamic-maze",
    "draw": "islamic-draw",
    "cut-paste": "islamic-cut-paste",
    "unit-opener": "islamic-unit-opener",
    "front-title": "islamic-front-title",
    "front-characters": "islamic-front-characters",
    "front-how-to-use": "islamic-front-how-to-use",
    "front-this-is-me": "islamic-this-is-me",
    "back-page": "islamic-back-page",
    "home-challenge": "islamic-home-challenge",
    "self-test": "islamic-self-test",
    "quiz": "islamic-self-test",
    "assessment": "islamic-assessment",
    "missing": "islamic-missing",
}
# the content types whose name is not a page type of plan.yaml → the plan type they fill (its rules apply)
PLAN_TYPE: dict[str, str] = {
    "my-day-with-allah": "day",
    "prayer-steps": "order-steps",
    "final-assessment": "assessment",
    "front-title": "front",
    "front-characters": "front",
    "front-how-to-use": "front",
    "front-this-is-me": "front",
    "back-page": "front",
}
AUDIO_TYPES = frozenset({"dhikr", "surah"})  # pages with a QR to a recorded voice (never TTS for sacred text)
# The one switch for those QR codes. Off since 2026-10-07: no reciter's or human recording exists yet, so the
# pages print with no QR and no «listen» label (docs/decisions.md). Turn it on once every code plays a real
# recording.
AUDIO_QR = False
FINALE = "finale"  # the section of the pages that belong to no unit (front pages, passport, certificate)


def plan_type(content_type: str) -> str:
    """The plan.yaml page type a content type fills."""
    return PLAN_TYPE.get(content_type, content_type)


def parse_page(raw: Mapping[str, Any]) -> Page:
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
    credit: str = ""  # «راجعه علميًّا: …»: the scholar's name, only when the review export gives one (print)


def page_spec(
    page: AnyPage, number: int, context: IslamicContext, extra: Mapping[str, Any] | None = None
) -> PageSpec:
    """The engine's page: the model and the context ride in `params` (with `extra`: what the volume knows,
    e.g. the unit's lessons for its opener)."""
    section = page.unit or FINALE
    title = getattr(page, "gendered_title", "") or page.title
    return PageSpec(
        id=page.id,
        type=page.engine_type or ENGINE_NAMES[page.type],
        number=number,
        section=section,
        title=title,
        instruction=page.instruction,
        audio=AUDIO_QR and page.type in AUDIO_TYPES,
        params={**(extra or {}), "page": page, "islamic": context},
    )
