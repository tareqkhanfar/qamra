"""The language pass (92c7710) on store rows that already exist: parents addressed in the plural, «ـًا».

Revision ID: 3f7ceee7a4df
Revises: b7d2e91c4a05
Create Date: 2026-10-01

`qamra seed-store` is insert-only, so the corrected text in `content/store/catalog.yaml` and
`content/store/quiz.yaml` reaches fresh installs only. This rewrites the existing product, add-on and quiz
rows, but only where a field still holds the old seeded text: anything an admin has edited is left alone.
Downgrade restores the old text the same way. Variants carry no names; English did not change.
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection

revision: str = "3f7ceee7a4df"
down_revision: str | None = "b7d2e91c4a05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (slug, column, old, new)
PRODUCTS: list[tuple[str, str, str, str]] = [
    (
        "classic-book",
        "description_ar",
        "حكاية جاهزة برسوم جميلة، نرسم فيها طفلك بطلاً في كل صفحة يظهر فيها.",
        "حكاية جاهزة برسوم جميلة، نرسم فيها طفلكم بطلًا في كل صفحة يظهر فيها.",
    ),
    (
        "magic-book",
        "description_ar",
        "كتاب فريد تُرسم كل صفحة فيه لطفلك، مع صاحبه المرسوم من رسمته.",
        "كتاب فريد تُرسم كل صفحة فيه لطفلكم، مع صاحبه المرسوم من رسمته.",
    ),
    ("coloring-book", "name_ar", "كتاب تلوين باسم طفلك", "كتاب تلوين باسم طفلكم"),
    (
        "coloring-book",
        "description_ar",
        "حكاية طفلك بالخطوط فقط ليلوّنها بنفسه.",
        "حكاية طفلكم بالخطوط فقط ليلوّنها بنفسه.",
    ),
    (
        "foundation-workbook",
        "description_ar",
        "منهج متكامل للروضة في ثلاثة أجزاء، باسم طفلك وشخصيته.",
        "منهج متكامل للروضة في ثلاثة أجزاء، باسم طفلكم وشخصيته.",
    ),
    (
        "learning-journey",
        "description_ar",
        "كتاب مغامرة يتعلّم فيه طفلك وهو يلعب، من التفكير حتى القراءة.",
        "كتاب مغامرة يتعلّم فيه طفلكم وهو يلعب، من التفكير حتى القراءة.",
    ),
    (
        "family-adventures",
        "description_ar",
        "مغامرات حقيقية مع العائلة، من المطبخ إلى السوق والطبيعة، باسم طفلك وشخصيته.",
        "مغامرات حقيقية مع العائلة، من المطبخ إلى السوق والطبيعة، باسم طفلكم وشخصيته.",
    ),
]
ADDONS: list[tuple[str, str, str, str]] = [
    ("hardcover-upgrade", "badge_ar", "الأكثر اختياراً", "الأكثر اختيارًا"),
    (
        "gift-box",
        "description_ar",
        "جاهز للإهداء، ونكتب رسالتك على البطاقة",
        "جاهز للإهداء، ونكتب رسالتكم على البطاقة",
    ),
    ("dedication-page", "description_ar", "سطرين منك بأول الكتاب", "سطرين منكم بأول الكتاب"),
    (
        "drawing-companion",
        "description_ar",
        "رسمة طفلك تتحوّل لشخصية ترافقه في كل الصفحات",
        "رسمة طفلكم تتحوّل لشخصية ترافقه في كل الصفحات",
    ),
    (
        "family-voice",
        "description_ar",
        "سجّل القصة بصوتك، وتسمعها بمسح الرمز",
        "سجّلوا القصة بصوتكم، وتسمعونها بمسح الرمز",
    ),
    ("extra-copy", "description_ar", "نفس الكتاب بنص السعر تقريباً", "نفس الكتاب بنص السعر تقريبًا"),
    (
        "coloring-version",
        "description_ar",
        "نفس الصفحات بالأبيض والأسود ليلوّنها طفلك",
        "نفس الصفحات بالأبيض والأسود ليلوّنها طفلكم",
    ),
    (
        "cover-poster",
        "description_ar",
        "غلاف الكتاب بحجم كبير لغرفة طفلك",
        "غلاف الكتاب بحجم كبير لغرفة طفلكم",
    ),
    ("printed-answer-key", "name_ar", "مفتاح الإجابات مطبوعاً", "مفتاح الإجابات مطبوعًا"),
]
# the quiz's rules are one JSON row (app_settings.quiz_rules); (field of a product/alternative, old, new)
QUIZ_KEY = "quiz_rules"
QUIZ: list[tuple[str, str, str]] = [
    ("title_ar", "قصة قمرة، طفلك بطلها", "قصة قمرة، طفلكم بطلها"),
    ("why_ar", "قصة مطبوعة بطلها طفلك", "قصة مطبوعة بطلها طفلكم"),
]


def _rows(table: str, column: str) -> sa.TableClause:
    return sa.table(table, sa.column("slug", sa.String), sa.column(column, sa.Text))


def rewrite_quiz(value: Any, forward: bool) -> tuple[Any, bool]:
    """The rules with every product/alternative field still holding the from-text rewritten."""
    if not isinstance(value, dict) or not isinstance(value.get("rules"), list):
        return value, False
    changed = False
    for rule in value["rules"]:
        for ref in (rule.get("product"), rule.get("alternative")) if isinstance(rule, dict) else ():
            if not isinstance(ref, dict):
                continue
            for field, old, new in QUIZ:
                frm, to = (old, new) if forward else (new, old)
                if ref.get(field) == frm:
                    ref[field] = to
                    changed = True
    return value, changed


def apply(conn: Connection, forward: bool) -> None:
    """Rewrite the rows whose field still equals the from-text (forward: old → new; back: new → old)."""
    for table, changes in (("products", PRODUCTS), ("addons", ADDONS)):
        for slug, column, old, new in changes:
            frm, to = (old, new) if forward else (new, old)
            rows = _rows(table, column)
            conn.execute(rows.update().where(rows.c.slug == slug, rows.c[column] == frm).values({column: to}))
    settings = sa.table("app_settings", sa.column("key", sa.String), sa.column("value", JSONB))
    current = conn.execute(sa.select(settings.c.value).where(settings.c.key == QUIZ_KEY)).scalar_one_or_none()
    value, changed = rewrite_quiz(current, forward)
    if changed:
        conn.execute(settings.update().where(settings.c.key == QUIZ_KEY).values(value=value))


def upgrade() -> None:
    apply(op.get_bind(), forward=True)


def downgrade() -> None:
    apply(op.get_bind(), forward=False)
