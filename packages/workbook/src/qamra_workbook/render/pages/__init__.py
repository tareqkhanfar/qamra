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
    islamic,  # «قلبي يعرف الله» (Addendum 10): islamic_* modules
    journey,
    journey_eye,  # «رحلتي الأولى» stage pages (Addendum 6 §5): journey_* modules
    journey_frame,
    journey_hand,
    journey_letters,
    journey_listen,
    journey_math,
    journey_review,
    journey_shapes,
    journey_think,
    letters,
    listening,
    motor,
    numbers,
    reward_stickers,  # the journey's and «قلبي يعرف الله»'s sticker sheet
    thinking,
    workbook,
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
    "islamic",
    "journey",
    "journey_eye",
    "journey_frame",
    "journey_hand",
    "journey_letters",
    "journey_listen",
    "journey_math",
    "journey_review",
    "journey_shapes",
    "journey_think",
    "letters",
    "listening",
    "motor",
    "numbers",
    "reward_stickers",
    "thinking",
    "workbook",
]
