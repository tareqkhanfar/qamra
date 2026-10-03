"""«قلبي يعرف الله» (Addendum 10 §7): importing this module registers the series' page types with the engine.

    prophet-story  sira-story  wudu-steps  prayer-steps  dhikr-situation  what-would-you-do  what-do-i-do-if
    blessings-hunt  islamic-coloring  islamic-unit-review  parent-guide  muslim-passport  muslim-certificate
    surah-page  my-day-with-allah  pillar-card  true-false  unit-closing  final-assessment
    islamic-story  islamic-role-play  islamic-find-objects  islamic-match  islamic-choose  islamic-maze
    islamic-draw  islamic-cut-paste  islamic-unit-opener  islamic-front-title  islamic-front-characters
    islamic-front-how-to-use  islamic-this-is-me  islamic-back-page  islamic-home-challenge
    islamic-self-test  islamic-assessment  islamic-missing  islamic-cover-front  islamic-cover-back

`islamic_*` modules hold the builders; their templates are `templates/pages/islamic-*.html.j2`. The content
models are `render/islamic_content.py`; a whole volume is `render/islamic_volume.py`.
"""

from qamra_workbook.render import islamic_units  # noqa: F401  (registers the unit styles and icons first)
from qamra_workbook.render.pages import (
    islamic_activity,
    islamic_frame,
    islamic_keepsake,
    islamic_more,
    islamic_play,
    islamic_quiz,
    islamic_review,
    islamic_situation,
    islamic_story,
    islamic_tell,
)

__all__ = [
    "islamic_activity",
    "islamic_frame",
    "islamic_keepsake",
    "islamic_more",
    "islamic_play",
    "islamic_quiz",
    "islamic_review",
    "islamic_situation",
    "islamic_story",
    "islamic_tell",
]
