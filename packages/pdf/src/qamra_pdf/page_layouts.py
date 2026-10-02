"""The interior layout library (Addendum 11 §3): eight designed page layouts instead of one white box.

Each layout has an image geometry the pipeline draws for (`full` square page, `split` 3:2 picture,
`spread` double page) and says whether its text sits on the art (then the busy-area check runs on the text
area) or on paper beside a framed/vignetted picture. The text area itself (top / bottom / side) still comes
from the theme's `text_pos`, so the image prompt, the busy check (`checks.AREAS`) and the page always agree.

Templates and CSS live in `packages/pdf/layouts/<name>/page.{html,css}.j2`.
"""

import re
from typing import Literal

PageLayout = Literal[
    "full-bleed-cloud",
    "full-bleed-fade",
    "spread-panorama",
    "vignette-text",
    "split-frame",
    "big-moment",
    "dialogue",
    "ornament-text",
]
Geometry = Literal["full", "split", "spread"]

LAYOUTS: tuple[PageLayout, ...] = (
    "full-bleed-cloud",
    "full-bleed-fade",
    "spread-panorama",
    "vignette-text",
    "split-frame",
    "big-moment",
    "dialogue",
    "ornament-text",
)
GEOMETRY: dict[PageLayout, Geometry] = {
    "full-bleed-cloud": "full",
    "full-bleed-fade": "full",
    "spread-panorama": "spread",
    "vignette-text": "full",
    "split-frame": "split",
    "big-moment": "full",
    "dialogue": "full",
    "ornament-text": "full",
}
# Theme schema v2 values → the layout that renders them (every existing theme keeps rendering).
LEGACY: dict[str, PageLayout] = {
    "full": "full-bleed-cloud",
    "split": "split-frame",
    "spread": "spread-panorama",
}
# Text set over the illustration: the text area must be calm (busy check + panel opacity).
ON_ART: frozenset[str] = frozenset(
    {"full-bleed-cloud", "full-bleed-fade", "spread-panorama", "big-moment", "dialogue"}
)
# Layouts that can set their text in a side area (theme `text_pos: side`).
SIDE_OK: frozenset[str] = frozenset({"full-bleed-cloud", "full-bleed-fade", "dialogue"})
# Full-page layouts the planner rotates through, in order of preference.
FULL_ROTATION: tuple[PageLayout, ...] = (
    "full-bleed-cloud",
    "full-bleed-fade",
    "dialogue",
    "big-moment",
    "vignette-text",
    "ornament-text",
)
BIG_MOMENT_MAX_WORDS = 9  # «one line in huge type»: only short climax lines
PAPER_MAX_WORDS = 24  # vignette-text / ornament-text set larger text in a smaller area
REST_PAGES_MAX = 2  # vignette-text / ornament-text each: rest pages, not the book's default

_QUOTE = r"«[^«»]+»|“[^“”]+”|\"[^\"]+\""
# A spoken line that ends the page's text (a quote in the middle stays in the narration: its bubble would
# be read out of order).
_TRAILING_QUOTE = re.compile(rf"({_QUOTE})[\s.!؟?…]*$")


def normalize(layout: str | None) -> PageLayout:
    """A library name, or a legacy `full/split/spread` value, as the layout that renders it."""
    for name in LAYOUTS:
        if layout == name:
            return name
    return LEGACY.get(layout or "full", "full-bleed-cloud")


def geometry_of(layout: str | None) -> Geometry:
    return GEOMETRY[normalize(layout)]


def has_dialogue(text: str) -> bool:
    return bool(_TRAILING_QUOTE.search(text.strip()))


def split_dialogue(text: str) -> tuple[str, list[str]]:
    """(narration, [spoken line]) for the `dialogue` layout: a quote that ends the text becomes the speech
    bubble; the narration before it keeps its words and punctuation. Without one, everything is narration."""
    text = text.strip()
    m = _TRAILING_QUOTE.search(text)
    if not m:
        return text, []
    spoken = m.group(1)[1:-1].strip()
    tail = text[m.end(1) :].strip()  # punctuation after the closing quote, e.g. «…».
    if tail and tail[-1] in "!؟?…" and not spoken.endswith(tail):
        spoken += tail
    narration = text[: m.start(1)].strip()
    return narration, [spoken]


def word_count(text: str) -> int:
    return len([w for w in text.split() if re.search(r"\w", w)])


def fits(layout: PageLayout, geometry: Geometry, area: str, text: str) -> bool:
    """Can `layout` set this page (image geometry, text area, the theme's text)?"""
    if GEOMETRY[layout] != geometry:
        return False
    side = area in ("left", "right")
    if side and layout not in SIDE_OK:
        return False
    if layout == "dialogue":
        return has_dialogue(text)
    if layout == "big-moment":
        return word_count(text) <= BIG_MOMENT_MAX_WORDS
    if layout in ("vignette-text", "ornament-text"):
        return word_count(text) <= PAPER_MAX_WORDS
    return True


def choose(
    geometry: Geometry,
    area: str,
    text: str,
    *,
    wanted: PageLayout | None,
    previous: list[PageLayout],
    used: dict[PageLayout, int],
) -> PageLayout:
    """The layout for one page: the theme's choice unless it repeats the page before, else the least-used
    layout that fits (never the same as the previous page, and not the one before it when there is a choice).
    """
    last = previous[-1] if previous else None
    if wanted is not None and GEOMETRY[wanted] == geometry and wanted != last:
        return wanted
    if geometry != "full":
        return LEGACY[geometry]
    options = [
        name
        for name in FULL_ROTATION
        if fits(name, geometry, area, text)
        and not (name in ("vignette-text", "ornament-text") and used.get(name, 0) >= REST_PAGES_MAX)
    ]
    fresh = [n for n in options if n not in previous[-2:]] or [n for n in options if n != last]
    if not fresh:
        return "full-bleed-fade" if last == "full-bleed-cloud" else "full-bleed-cloud"
    return min(fresh, key=lambda n: (used.get(n, 0), FULL_ROTATION.index(n)))


def drop_word(text: str) -> tuple[str, str]:
    """(first word(s), rest) for the ornament page's large first word. Arabic letters join, so the drop is a
    whole word, never one letter; a one- or two-letter word («في») takes the next word with it."""
    words = text.split()
    if not words:
        return "", ""
    take = (
        2
        if len(re.sub(r"[\u064b-\u0652\u0670\u0640«»\"“”،,.!؟?:]", "", words[0])) <= 2 and len(words) > 2
        else 1
    )
    return " ".join(words[:take]), " ".join(words[take:])
