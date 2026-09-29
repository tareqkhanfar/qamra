"""«أي كتاب يناسب طفلي؟» (Addendum 9 §1.2–§1.3): the quiz's rules as data.

An ordered list of `age × goal × holds-a-pen → product + alternative`, stored as one JSON row in
`app_settings` (key `quiz_rules`). It is a list, so it lives outside the settings registry and has its own
editor in the admin catalog. `qamra seed-store` seeds it from content/store/quiz.yaml. The first rule that
matches the answers wins, and a save must leave no answer without a recommendation.
"""

import itertools
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.models import AppSetting

QUIZ_KEY = "quiz_rules"
QUIZ_SEED = CONTENT_DIR / "store" / "quiz.yaml"
STORIES = "stories"  # a rule's product: the personalized story books (Classic and Magic)
AGES = (3, 4, 5, 6)  # the quiz's answers: 3 = "3 or younger", 6 = "6–7"
Goal = Literal["gift", "learn", "family"]
Pen = Literal["yes", "no"]


class ProductRef(BaseModel):
    slug: str = Field(min_length=1, max_length=64)  # a catalog product, or "stories"
    options: dict[str, str] = Field(default_factory=dict, max_length=4)  # e.g. {"stage": "1"}
    title_ar: str = Field(default="", max_length=80)  # shown instead of the product name when set
    title_en: str = Field(default="", max_length=80)
    why_ar: str = Field(default="", max_length=200)
    why_en: str = Field(default="", max_length=200)


class QuizRule(BaseModel):
    goal: Goal
    age_min: int | None = Field(default=None, ge=2, le=8)
    age_max: int | None = Field(default=None, ge=2, le=8)
    pen: Pen | None = None  # only asked when the goal is learning
    product: ProductRef
    alternative: ProductRef


class QuizRules(BaseModel):
    rules: list[QuizRule] = Field(min_length=1, max_length=40)


def match(rules: list[QuizRule], age: int, goal: Goal, pen: Pen | None) -> QuizRule | None:
    """The first rule whose conditions all hold (a condition left empty matches anything)."""
    for rule in rules:
        if rule.goal != goal:
            continue
        if rule.age_min is not None and age < rule.age_min:
            continue
        if rule.age_max is not None and age > rule.age_max:
            continue
        if rule.pen is not None and pen != rule.pen:
            continue
        return rule
    return None


def gaps(rules: list[QuizRule]) -> list[dict[str, Any]]:
    """Answers that no rule covers (the quiz asks about the pen only for learning)."""
    out = []
    for age, goal in itertools.product(AGES, ("gift", "learn", "family")):
        pens: tuple[Pen | None, ...] = ("yes", "no") if goal == "learn" else (None,)
        for pen in pens:
            if match(rules, age, goal, pen) is None:  # type: ignore[arg-type]
                out.append({"age": age, "goal": goal, "pen": pen})
    return out


def seed_rules(path: Path = QUIZ_SEED) -> QuizRules:
    return QuizRules.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


async def load_rules(db: AsyncSession) -> QuizRules:
    """The admin's rules, or the seed until they are saved (a broken row never breaks the quiz)."""
    row = await db.get(AppSetting, QUIZ_KEY)
    if row is not None and row.value:
        try:
            return QuizRules.model_validate(row.value)
        except ValidationError:
            pass
    return seed_rules()


async def seed_quiz_rules(db: AsyncSession) -> list[str]:
    """`qamra seed-store`: store the default rules once; edits in the admin are never overwritten."""
    if await db.get(AppSetting, QUIZ_KEY) is not None:
        return []
    db.add(AppSetting(key=QUIZ_KEY, value=seed_rules().model_dump(mode="json")))
    return ["+quiz_rules"]
