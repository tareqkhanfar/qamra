"""«قلبي يعرف الله» (Addendum 10 §7): importing this module registers the series' page types with the engine.

    prophet-story  wudu-steps  dhikr-situation  what-would-you-do  what-do-i-do-if  blessings-hunt
    islamic-coloring
    islamic-unit-review  parent-guide  muslim-passport  muslim-certificate  surah-page
    (and the thin ones: prayer-steps  my-day-with-allah  pillar-card  true-false  unit-closing
    final-assessment)

`islamic_*` modules hold the builders; their templates are `templates/pages/islamic-*.html.j2`.
"""

from qamra_workbook.render import islamic_units  # noqa: F401  (registers the unit styles and icons first)
from qamra_workbook.render.pages import (
    islamic_activity,
    islamic_keepsake,
    islamic_more,
    islamic_review,
    islamic_situation,
    islamic_story,
)

__all__ = [
    "islamic_activity",
    "islamic_keepsake",
    "islamic_more",
    "islamic_review",
    "islamic_situation",
    "islamic_story",
]
