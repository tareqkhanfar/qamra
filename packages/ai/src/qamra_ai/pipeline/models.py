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


class SafetyVerdict(BaseModel):
    safe: bool
    reasons: list[str]


class DrawingReview(BaseModel):
    safe: bool
    is_drawing: bool
    description_en: str
    key_features: list[str]
    reasons: list[str]


class PageReview(BaseModel):
    safe: bool
    hero_recognizable: bool
    companion_present: bool
    has_text_artifacts: bool
    notes: str


class CompanionFidelity(BaseModel):
    score: int  # 1..5, 5 = unmistakably the child's drawing
    preserved_features: list[str]
    lost_features: list[str]
    safe: bool
