"""Domain inputs and the structured outputs we ask Claude for."""

from typing import Literal

from pydantic import BaseModel, Field

Gender = Literal["m", "f"]
Lang = Literal["ar", "en"]
CompanionType = Literal["creature", "animal", "robot", "other"]


class Child(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    gender: Gender
    age: int = Field(ge=2, le=12)
    interests: list[str] = Field(default_factory=list)
    hijab: bool = False  # chosen by the parent; never inferred from the photo
    glasses: bool = False


class CompanionSpec(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    type_hint: CompanionType = "creature"
    type_other: str | None = Field(default=None, max_length=30)
    traits: str | None = Field(default=None, max_length=120)
    description_en: str = ""  # visual description the image + story prompts rely on
    from_drawing: bool = False


# ---- Claude structured outputs -------------------------------------------------------------


class StoryPageOut(BaseModel):
    index: int
    text: str


class StoryOut(BaseModel):
    title: str
    dedication: str
    pages: list[StoryPageOut]
    parents_lesson: str = ""
    parents_questions: list[str] = []
    blurb: str = ""


class SafetyVerdict(BaseModel):
    safe: bool
    reasons: list[str]
    # words that misgender the hero (story_safety.v3): a hint for the text review, never a reason to block
    gender_issues: list[str] = []


class DrawingReview(BaseModel):
    safe: bool
    is_drawing: bool
    description_en: str
    key_features: list[str]
    reasons: list[str]


class PageQA(BaseModel):
    """Haiku vision check of one page (Addendum 3 §2.3, Addendum 11 §4.5). Scoring lives in `pipeline.qa`."""

    # First on purpose: listing every child before the counts is what catches a duplicated hero
    # (a look-alike pair hugging passed a plain "how many heroes?" question).
    children: list[str]
    likeness: int  # 0–10 vs the character sheet
    hero_count: int
    people_count_ok: bool
    # Characters cut by the picture's edge or inside the trimmed border: "hero", "companion" or a short name.
    cropped: list[str]
    anatomy_ok: bool
    text_in_image: bool
    outfit_ok: bool  # the outfit of this page's scene group (cover, or the group's first accepted page)
    hijab_ok: bool  # the book's one head covering (or none), in its locked color
    text_space_ok: bool  # the text area is calm and free of busy detail
    companion_ok: bool  # once, and the same shape and colors as its sheet
    style_ok: bool
    safe: bool
    notes: str


class CompanionFidelity(BaseModel):
    score: int  # 1..5, 5 = unmistakably the child's drawing
    preserved_features: list[str]
    lost_features: list[str]
    safe: bool
