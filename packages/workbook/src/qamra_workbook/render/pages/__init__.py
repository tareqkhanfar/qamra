"""Page-type builders. Importing this package registers every page type with the engine.

To add a page type: write a builder decorated with `@page_type("name")` in one of these modules (or a new
one imported below) and add `render/templates/pages/<name>.html.j2` for its work area.
"""

from qamra_workbook.render.pages import (
    adventures,
    family,
    family_cards,
    family_cover,
    family_day,
    family_front,
    family_games,
    family_talk,
    inserts,
    journey,
    letters,
    listening,
    motor,
    numbers,
    thinking,
)

__all__ = [
    "adventures",
    "family",
    "family_cards",
    "family_cover",
    "family_day",
    "family_front",
    "family_games",
    "family_talk",
    "inserts",
    "journey",
    "letters",
    "listening",
    "motor",
    "numbers",
    "thinking",
]
