"""«دوسية التأسيس» KG1 page types (ages 4–5): bigger rows, fewer items, and the page types only KG1 has.
Importing this module registers them all; `foundation_kg1` routes the plan's pages to them."""

from qamra_workbook.render.pages import (
    workbook_kg1_activity,
    workbook_kg1_arabic,
    workbook_kg1_english,
    workbook_kg1_math,
    workbook_kg1_pen,
    workbook_kg1_review,
    workbook_kg1_thinking,
)

__all__ = [
    "workbook_kg1_activity",
    "workbook_kg1_arabic",
    "workbook_kg1_english",
    "workbook_kg1_math",
    "workbook_kg1_pen",
    "workbook_kg1_review",
    "workbook_kg1_thinking",
]
