"""«دوسية التأسيس» page types (Addendum 5 §4). Importing this module registers them all; each subject's
builders live in their own `workbook_*` module."""

from qamra_workbook.render.pages import (
    workbook_arabic,
    workbook_find,
    workbook_front,
    workbook_math,
    workbook_pen,
    workbook_review,
    workbook_thinking,
    workbook_kg1,  # KG1's own page types
    workbook_v2,  # «دوسية التأسيس» volume 2
    workbook_v3,  # volume 3
)

__all__ = [
    "workbook_arabic",
    "workbook_find",
    "workbook_front",
    "workbook_math",
    "workbook_pen",
    "workbook_review",
    "workbook_thinking",
    "workbook_kg1",
    "workbook_v2",
    "workbook_v3",
]
