"""«رحلتي الأولى للتعلّم» (Addendum 6): the journey plan, its rules and the readable plan.

The second product on the workbook engine. It shares the page-type library and letter data with the
«دوسية التأسيس» curriculum (`qamra_workbook.curriculum`) and adds the Addendum 6 page types. Every stage walks
the whole journey map in order: every section is one block that opens on the map and ends with «ماذا تعلمت؟»;
two small neighbouring sections may share their opener and their «ماذا تعلمت؟» page. Tareq's decisions of
2026-09-28 (docs/workbook/decisions-2026-09-28.md) override the addendum where they differ.

    uv run python -m qamra_workbook.journey check    # rule problems (exit 1 when any) and page counts
    uv run python -m qamra_workbook.journey render   # also writes docs/journey/plan.md
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from collections.abc import Iterator
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from qamra_workbook.curriculum import ENGLISH_LETTERS, EXTRA_TYPES, LIBRARY_TYPES, norm_letter

# Addendum 6 §5, plus the journey's structural pages
JOURNEY_TYPES_NEW: dict[str, str] = {
    "whats-missing": "what's missing from the picture",
    "hidden-picture": "objects hidden inside a line-art scene (positions logged in the answer key)",
    "find-identical-pair": "find the two identical pictures",
    "belongs-to-group": "which picture belongs to the group",
    "memory-look": "look and remember (front of a sheet; memory-recall is on its back)",
    "memory-recall": "recall what was on the previous page",
    "sequence-story": "order 3–6 picture panels into a story (params: panels)",
    "classify-by": "sort by shape, color or use (params: by)",
    "connect-pairs": "connect each picture to its partner",
    "shortest-path": "choose the shortest path",
    "overlapping-paths": "follow overlapping paths to the right end",
    "shadow-match": "match pictures to their silhouettes",
    "part-to-whole": "match a part to the whole picture",
    "themed-pen-drill": "themed pre-writing drill (params: theme = rain|grass|waves|mountains…)",
    "complete-the-shape": "complete the dotted half of a shape",
    "draw-missing-part": "draw the missing part of a picture",
    "create-your-pattern": "the child makes their own pattern (blank slots, stickers or drawing)",
    "smart-coloring": "rule-based coloring with a printed color model (params: rule)",
    "shape-journey": "a shape's 6 steps: meet, trace, match, find, color, draw (params: shape)",
    "color-journey": "a color: meet, match, find, sort, choose (params: color)",
    "quantity-first": (
        "how many? count a group, then answer (params: numbers, answer_with = dots|dot-cards|fingerprints|"
        "coloring|ten-frame, or numerals once the numerals are met)"
    ),
    "number-before-after": "the number before and after",
    "same-amount": "find groups with the same amount",
    "near-far": "near and far",
    "listen-and-choose": "listen (QR) and choose the picture (params: words)",
    "loud-soft": "loud or soft sounds (QR)",
    "fast-slow": "fast or slow sounds (QR)",
    "first-sound": "the first sound of a word (QR) (params: letter, words)",
    "finger-trace": (
        "trace a big solid path with a finger, following the arrows (params: letter or shape); with a "
        "letter it is the letter's first page: meet it, hear it (QR) and link it to a picture word"
    ),
    "write-progression": "one level of the 7-level writing progression (params: level 1–7, target)",
    "picture-riddle": "a picture riddle",
    "observation-checklist": "parent/teacher observation checklist with 3 faces per skill (final assessment)",
    "mini-certificate": "mini-certificate at the end of stages 1 and 2",
    "journey-map": "the journey map with the child's character",
    "section-opener": "section opener: the map with the character moved one stop, and the section's goal",
    "what-i-learned": "«ماذا تعلمت؟»: the section's closing review, combining earlier skills",
}
JOURNEY_TYPES: dict[str, str] = LIBRARY_TYPES | EXTRA_TYPES | JOURNEY_TYPES_NEW

AUDIO_TYPES = ("listen-and-choose", "loud-soft", "fast-slow", "first-sound", "letter-intro", "en-letter")
NO_INSTRUCTION = ("blank", "toc")  # every other page is a mission with a ≤ 7-word instruction
# §4.9's eleven steps on three pages per Arabic letter: finger-trace (meet it, hear it, link it to a picture,
# trace it with a finger), letter-trace (the pen, then writing next to the model) and find-letter (find it,
# pick the right one, spot it in words, color). Step 11, writing it alone, is writing level 7 in stage 3.
LETTER_STEPS = ("finger-trace", "letter-trace", "find-letter")
LETTER_SPLIT = {1: (0, 0), 2: (0, 14), 3: (14, 28)}  # decision §2: letter_order split 14/14 over stages 2–3
# Decision 2026-09-28 §2: at most one new letter per page; a letter is new from its finger-trace page (or
# its en-letter page) to its letter-trace page. Only review pages combine four letters or more.
MAX_NEW_LETTERS = 1
REVIEW_LETTERS = 4
REVIEW_TYPES = ("unit-review", "what-i-learned", "assessment")
LETTER_KEYS = ("letter", "letters", "target", "key")  # params that show letters (not `distractors`)
SOUND_ONLY = ("first-sound",)  # the child hears the sound; the letter itself comes later
# numerals the child reads (recognition) and numerals the child writes (§4.7)
NUMERAL_SEEN = ("number-intro", "number-quantity-match", "count-and-circle")
NUMERAL_WRITTEN = ("number-trace", "number-write")
NUMERAL_TYPES = NUMERAL_SEEN + NUMERAL_WRITTEN
STAGE_ONE_NUMERALS = range(1, 6)  # decision §3: stage 1 recognizes 1–5 and matches them, never writes them
# Decision §1: every stage visits every section. Two neighbouring small sections may share one opener and
# one «ماذا تعلمت؟» page; small means at most this many pages besides the opener and «ماذا تعلمت؟».
SMALL_SECTION = 5
STRUCTURE_TYPES = ("section-opener", "what-i-learned")
# Decision §5 (and the دوسية's §7): retired words and their replacements; لسان and ضرس stay.
RETIRED_WORDS = {"ظبي": "ظِلّ", "ذئب": "ذَيْل"}
# §2: the development goals every plan must map to pages
GOALS = (
    "attention",
    "memory",
    "observation",
    "visual_discrimination",
    "auditory_discrimination",
    "logic",
    "classification",
    "sequencing",
    "visual_motor",
    "pen_control",
    "fine_motor",
    "writing_readiness",
    "reading_readiness",
    "arabic",
    "numbers",
    "english",
    "independence",
)
MIN_PAGES, MAX_PAGES = 100, 120  # §3: ~100–120 pages per stage
MAX_INSTRUCTION_WORDS = 7  # §2, §6
MAX_SAME_TYPE = 2  # §2: never the same activity format in a boring way
MIN_PRACTICE = 3  # §4.10: pages at a writing level before the next level starts
MAX_WRITING_LEVEL = {1: 2, 2: 5, 3: 7}  # stage 1 has no letter writing
MIN_GOAL_PAGES = 3
SAMPLE_COUNT, SAMPLE_SECTIONS = 12, 8


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title_ar: str
    icon: str
    journey_step: str  # the stop on the journey map: أفكر، ألاحظ، أسمع، أحرّك يدي، …


class JourneyPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int
    section: str  # a section id, or "intro"
    type: str
    title: str  # the mission's big title
    instruction: str  # ≤ 7 words, read-aloud friendly
    skill: str  # the goal, for the educator
    goals: list[str] = Field(default_factory=list)
    difficulty: int = Field(ge=1, le=5)
    params: dict[str, Any] = Field(default_factory=dict)
    audio: bool = False  # a QR code plays the sound or word
    example: bool = False  # a solved example is printed on the page
    one_sided: bool = False
    # a section-opener or «ماذا تعلمت؟» shared by two small neighbouring sections: both ids, in journey order
    # (the opener sits in the first section, the «ماذا تعلمت؟» at the end of the second)
    merged: list[str] = Field(default_factory=list)


class Stage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: int
    age: str
    title_ar: str
    objectives: dict[str, list[str]]  # per section
    pages: list[JourneyPage]


class SampleRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: int
    n: int


class Journey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_ar: str
    title_en: str
    idea: str  # §3.1 the general idea
    skill_order: str  # §3.4
    difficulty_notes: str  # §3.6 difficulty per stage
    writing_notes: str  # §4.10 how the writing progression is paced
    letter_order: list[str]
    sections: list[Section]  # in journey order
    samples: list[SampleRef]  # §3.7: the 12 sample pages
    stages: list[Stage]


def load(path: Path) -> Journey:
    return Journey.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _values(params: dict[str, Any], one: str, many: str) -> list[Any]:
    raw = params.get(many) or ([params[one]] if one in params else [])
    return list(raw) if isinstance(raw, list) else [raw]


def _numbers(params: dict[str, Any]) -> set[int]:
    return {int(x) for x in _values(params, "number", "numbers") if str(x).lstrip("-").isdigit()}


_MARKS = re.compile("[\u064b-\u065f\u0670\u0640]")  # harakat, superscript alif, tatweel
_NAMED = re.compile(r"\{child(?::acc|:gen)?\}")  # the child's name, as typed or in its case
ARABIC_LETTERS = frozenset("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")  # alif forms count as ا (norm_letter)


def plain(text: str) -> str:
    """The text without harakat and tatweel, for comparing letters and words."""
    return _MARKS.sub("", text)


def as_letter(value: Any) -> str | None:
    """A single Arabic letter (norm_letter; «هـ» is «ه») or English letter (as a capital), else None."""
    text = plain(str(value)).strip()
    if len(text) != 1:
        return None
    if text.upper() in ENGLISH_LETTERS:
        return text.upper()
    arabic = norm_letter(text)
    return arabic if arabic in ARABIC_LETTERS else None


def page_letters(p: JourneyPage) -> list[str]:
    """The letters a page shows, from `letter`, `letters`, `target` and a color `key`; `letters: all` is the
    whole Arabic alphabet. Distractors and sound-only pages (first-sound) show no letter to learn."""
    if p.type in SOUND_ONLY:
        return []
    out: list[str] = []
    for key in LETTER_KEYS:
        raw = p.params.get(key)
        if raw == "all":
            out += sorted(ARABIC_LETTERS)
            continue
        values = list(raw) if isinstance(raw, dict | list) else [raw] if raw is not None else []
        out += [x for x in (as_letter(v) for v in values) if x and x not in out]
    return out


def shows_numerals(p: JourneyPage) -> bool:
    """The page prints numerals for the child to read or write (not only quantities, dots or fingers)."""
    answers_with_numerals = p.type == "quantity-first" and p.params.get("answer_with") == "numerals"
    return p.type in NUMERAL_TYPES or answers_with_numerals


def blocks_of(s: Stage) -> list[tuple[str, list[JourneyPage]]]:
    """The stage's pages grouped into runs of one section, in page order."""
    blocks: list[tuple[str, list[JourneyPage]]] = []
    for p in s.pages:
        if blocks and blocks[-1][0] == p.section:
            blocks[-1][1].append(p)
        else:
            blocks.append((p.section, [p]))
    return blocks


def section_size(pages: list[JourneyPage]) -> int:
    """A section's pages besides its opener and «ماذا تعلمت؟» (and certificates): what makes it small."""
    return sum(1 for p in pages if p.type not in (*STRUCTURE_TYPES, "certificate", "mini-certificate"))


# ---- rules ------------------------------------------------------------------------------------------------


def check_stage_pages(s: Stage) -> list[str]:
    tag, n = f"S{s.stage}", len(s.pages)
    out = []
    if [p.n for p in s.pages] != list(range(1, n + 1)):
        out.append(f"{tag}: page numbers must run 1..{n} without gaps or repeats")
    if not MIN_PAGES <= n <= MAX_PAGES:
        out.append(f"{tag}: {n} pages; a stage has {MIN_PAGES}–{MAX_PAGES}")
    if n % 2:
        out.append(f"{tag}: {n} pages; printed sheets need an even count")
    for p in s.pages:
        if p.type not in JOURNEY_TYPES:
            out.append(f"{tag} p{p.n}: unknown page type {p.type!r}")
        if p.type not in NO_INSTRUCTION:
            words = len(p.instruction.split())
            if not p.title.strip() or words == 0:
                out.append(f"{tag} p{p.n}: a mission needs a title and an instruction")
            elif words > MAX_INSTRUCTION_WORDS:
                out.append(f"{tag} p{p.n}: instruction has {words} words (max {MAX_INSTRUCTION_WORDS})")
        letter_page = p.type == "finger-trace" and "letter" in p.params  # a letter's first page
        if (p.type in AUDIO_TYPES or letter_page) and p.section != "intro" and not p.audio:
            out.append(f"{tag} p{p.n}: {p.type} pages carry an audio QR (audio: true)")
        unknown = [g for g in p.goals if g not in GOALS]
        if unknown:
            out.append(f"{tag} p{p.n}: unknown goals {unknown}")
    return out


def check_sections(s: Stage, sections: list[Section]) -> list[str]:
    """Every section is one block, in journey order, in every stage (decision §1). A block opens on the map
    (section-opener) and ends with «ماذا تعلمت؟»; the stage's last block ends with its certificate."""
    tag, order = f"S{s.stage}", [x.id for x in sections]
    out = []
    blocks = blocks_of(s)
    if not blocks or blocks[0][0] != "intro":
        out.append(f"{tag}: the stage starts with its intro pages")
    elif "journey-map" not in {p.type for p in blocks[0][1]}:
        out.append(f"{tag}: the intro needs the journey map")
    seen = [b for b, _ in blocks if b != "intro"]
    if len(seen) != len(set(seen)):
        out.append(f"{tag}: a section appears in more than one block: {seen}")
    unknown = [b for b in seen if b not in order]
    if unknown:
        out.append(f"{tag}: unknown sections {unknown}")
    known = [b for b in seen if b in order]
    if known != sorted(known, key=order.index):
        out.append(f"{tag}: sections out of journey order: {known}")
    missing = [x for x in order if x not in seen]
    if missing:
        out.append(f"{tag}: every stage visits every section of the map; missing {missing}")
    for i, (sid, pages) in enumerate(blocks):
        if sid == "intro":
            continue
        before = blocks[i - 1] if i > 0 else None
        after = blocks[i + 1] if i + 1 < len(blocks) else None
        # opened by its own section-opener, or by the previous section's opener shared with this one
        opens = int(pages[0].type == "section-opener")
        opens += int(before is not None and _shares(before[1][0], "section-opener", [before[0], sid]))
        if opens != 1:
            what = "starts with a section-opener" if opens == 0 else "has two openers"
            out.append(f"{tag} p{pages[0].n}: section {sid} {what}")
        if after is None:
            if pages[-1].type not in ("certificate", "mini-certificate"):
                want = "certificate or mini-certificate"
                out.append(f"{tag} p{pages[-1].n}: section {sid} must end with {want}")
            continue
        # closed by its own «ماذا تعلمت؟», or by the next section's one shared with this one
        closes = int(pages[-1].type == "what-i-learned")
        closes += int(_shares(after[1][-1], "what-i-learned", [sid, after[0]]))
        if closes != 1:
            what = "must end with what-i-learned" if closes == 0 else "has two «ماذا تعلمت؟» pages"
            out.append(f"{tag} p{pages[-1].n}: section {sid} {what}")
    return out + check_merged(s, blocks)


def _shares(p: JourneyPage, kind: str, pair: list[str]) -> bool:
    return p.type == kind and p.merged == pair


def check_merged(s: Stage, blocks: list[tuple[str, list[JourneyPage]]]) -> list[str]:
    """Decision §1: one opener, or one «ماذا تعلمت؟», for two small neighbouring sections. The shared opener
    is the first page of the first section; the shared «ماذا تعلمت؟» is the last page of the second."""
    tag, out = f"S{s.stage}", []
    ids = [sid for sid, _ in blocks]
    sizes = {sid: section_size(pages) for sid, pages in blocks}
    for i, (_, pages) in enumerate(blocks):
        for p in pages:
            if not p.merged:
                continue
            first = p.type == "section-opener" and p is pages[0]
            last = p.type == "what-i-learned" and p is pages[-1]
            pair = ids[i : i + 2] if first else ids[i - 1 : i + 1] if last and i > 0 else []
            if not (first or last) or p.merged != pair or len(pair) != 2 or "intro" in pair:
                out.append(
                    f"{tag} p{p.n}: only a section's opener or closing «ماذا تعلمت؟» is shared, with the "
                    f"neighbouring section (merged: {p.merged})"
                )
                continue
            big = [x for x in pair if sizes[x] > SMALL_SECTION]
            if big:
                out.append(
                    f"{tag} p{p.n}: only small sections (≤ {SMALL_SECTION} pages besides the opener and "
                    f"«ماذا تعلمت؟») share a page; {', '.join(f'{x} has {sizes[x]}' for x in big)}"
                )
    return out


def check_variety(s: Stage) -> list[str]:
    tag, out, run = f"S{s.stage}", [], 1
    for a, b in pairwise(s.pages):
        run = run + 1 if b.type == a.type and b.type != "blank" else 1
        if run == MAX_SAME_TYPE + 1:
            out.append(f"{tag} p{b.n}: more than {MAX_SAME_TYPE} {b.type} pages in a row")
    return out


def check_memory_pairs(s: Stage) -> list[str]:
    """memory-look is the front of a sheet (odd page); memory-recall is its back, seen after turning."""
    tag, by_n, out = f"S{s.stage}", {p.n: p for p in s.pages}, []
    for p in s.pages:
        if p.type == "memory-look":
            back = by_n.get(p.n + 1)
            if p.n % 2 == 0 or back is None or back.type != "memory-recall":
                out.append(f"{tag} p{p.n}: memory-look must be an odd page followed by memory-recall")
        if p.type == "memory-recall":
            front = by_n.get(p.n - 1)
            if front is None or front.type != "memory-look":
                out.append(f"{tag} p{p.n}: memory-recall must follow its memory-look")
        if p.one_sided:
            back = by_n.get(p.n + 1 if p.n % 2 else p.n - 1)
            if back is None or back.type != "blank":
                out.append(f"{tag} p{p.n}: one-sided page; the other side of its sheet must be blank")
    return out


def check_stage_scope(s: Stage) -> list[str]:
    tag, out = f"S{s.stage}", []
    types = [p.type for p in s.pages]
    if s.stage == 1:
        letter_types = ("en-letter", "find-letter", "match-letter-picture", "name-trace")
        letters = [p.n for p in s.pages if p.type.startswith("letter-") or p.type in letter_types]
        letters += [p.n for p in s.pages if page_letters(p) and p.n not in letters]
        if letters:
            out.append(f"{tag}: no letters in stage 1 (pages {sorted(letters)[:5]})")
        out += check_stage_one_numerals(s)
        big = [p.n for p in s.pages if any(x > max(STAGE_ONE_NUMERALS) for x in _numbers(p.params))]
        if big:
            out.append(f"{tag}: stage 1 stays within quantities 1–5 and numerals 1–5 (pages {big[:5]})")
    for p in s.pages:
        if p.type == "write-progression":
            level = int(p.params.get("level", 0))
            if not 1 <= level <= MAX_WRITING_LEVEL[s.stage]:
                out.append(f"{tag} p{p.n}: writing level {level} is past stage {s.stage}'s limit")
    if s.stage in (2, 3):
        scripts = {str(p.params.get("script")) for p in s.pages if p.type == "name-trace"}
        if not {"ar", "en"} <= scripts:
            out.append(f"{tag}: name tracing in Arabic and English (name-trace, params.script)")
    named = [p for p in s.pages if _NAMED.search(p.title) or _NAMED.search(p.instruction)]
    if len(named) < 2:
        out.append(f"{tag}: at least 2 missions use the child's name ({{child}})")
    last = s.pages[-1].type if s.pages else ""
    if s.stage in (1, 2) and last != "mini-certificate":
        out.append(f"{tag}: the stage ends with its mini-certificate")
    if s.stage == 3:
        if last != "certificate":
            out.append(f"{tag}: stage 3 ends with the certificate")
        if "observation-checklist" not in types:
            out.append(f"{tag}: the final assessment (observation-checklist) is missing")
    return out


def check_stage_one_numerals(s: Stage) -> list[str]:
    """Decision §3: stage 1 counts quantities, then recognizes the numerals 1–5 by sight and matches them to
    quantities. It never writes a numeral: no number-trace or number-write, no numeral on a writing page."""
    tag, out = f"S{s.stage}", []
    written = [p.n for p in s.pages if p.type in NUMERAL_WRITTEN]
    for p in s.pages:
        target = p.params.get("target")
        targets = target if isinstance(target, list) else [target]
        if p.type in ("write-progression", "pen-lines") and any(str(t).strip().isdigit() for t in targets):
            written.append(p.n)
    if written:
        out.append(f"{tag}: stage 1 recognizes numerals but never writes them (pages {written[:5]})")
    met = {x for p in s.pages if p.type == "number-intro" for x in _numbers(p.params)}
    if not set(STAGE_ONE_NUMERALS) <= met:
        missing = sorted(set(STAGE_ONE_NUMERALS) - met)
        out.append(f"{tag}: stage 1 meets the numerals 1–5 on number-intro pages; missing {missing}")
    matched = {
        x for p in s.pages if shows_numerals(p) and p.type != "number-intro" for x in _numbers(p.params)
    }
    if not set(STAGE_ONE_NUMERALS) <= matched:
        out.append(
            f"{tag}: stage 1 matches every numeral 1–5 to its quantity (number-quantity-match, "
            f"count-and-circle or quantity-first with answer_with: numerals); found {sorted(matched)}"
        )
    return out


def check_letters(j: Journey) -> list[str]:
    """Each Arabic letter's first page is its finger-trace page (all 28 once, in letter_order), then in the
    same stage a letter-trace page and a find-letter page, in that order (LETTER_STEPS)."""
    out = []
    intros = [(s.stage, p.n, x) for s, p in _pages(j) if (x := _introduces(p)) and x not in ENGLISH_LETTERS]
    order = [norm_letter(x) for x in j.letter_order]
    if [x for _, _, x in intros] != order or len(set(order)) != 28:
        found = "".join(x for _, _, x in intros)
        out.append(f"finger-trace pages must introduce all 28 letters once, in letter_order; found {found}")
    for stage, (lo, hi) in LETTER_SPLIT.items():  # decision §2: 14 letters in stage 2, 14 in stage 3
        if len(order) == 28 and [x for st, _, x in intros if st == stage] != order[lo:hi]:
            found = "".join(x for st, _, x in intros if st == stage)
            want = f"letters {lo + 1}–{hi} of letter_order (14 per stage)" if hi > lo else "no letters"
            out.append(f"S{stage} introduces {want}; found {found}")
    for stage, first, letter in intros:
        pages = next(s.pages for s in j.stages if s.stage == stage)
        steps: list[int | None] = [first]
        for step in LETTER_STEPS[1:]:
            after = steps[-1] or first
            hits = [p.n for p in pages if p.type == step and p.n > after and letter in page_letters(p)]
            steps.append(min(hits) if hits else None)
        missing = [t for t, n in zip(LETTER_STEPS, steps, strict=True) if n is None]
        if missing:
            out.append(f"S{stage} letter {letter}: missing {', '.join(missing)} after its finger-trace page")
    english = [
        str(p.params.get("letter", "")).upper() for s in j.stages for p in s.pages if p.type == "en-letter"
    ]
    if tuple(english) != ENGLISH_LETTERS:
        out.append(f"en-letter pages must cover A–Z once, in order; found {''.join(english)}")
    return out


def _pages(j: Journey) -> Iterator[tuple[Stage, JourneyPage]]:
    """Every page of the book in order, with its stage."""
    for s in j.stages:
        for p in s.pages:
            yield s, p


def _introduces(p: JourneyPage) -> str | None:
    """The letter a page introduces: an Arabic letter's finger-trace page, or an English en-letter page."""
    if p.type == "finger-trace" or p.type == "en-letter":
        return as_letter(p.params.get("letter", ""))
    return None


def check_letter_pace(j: Journey) -> list[str]:
    """Decision §2: a page brings at most one new letter, and only review pages combine four letters or more.
    A letter is new from its first page (finger-trace, or en-letter) until its letter-trace page, when the
    child has met it, heard it and traced it with a finger and with the pen; no page shows it earlier."""
    pages = list(_pages(j))
    start: dict[str, int] = {}
    end: dict[str, int] = {}
    for k, (_, p) in enumerate(pages):
        letter = _introduces(p)
        if letter and letter not in start:
            start[letter] = end[letter] = k
    for k, (_, p) in enumerate(pages):
        if p.type != "letter-trace":
            continue
        for letter in page_letters(p):
            if letter in start and start[letter] < k and end[letter] == start[letter]:
                end[letter] = k  # its first pen page after its finger-trace page
    out = []
    for k, (s, p) in enumerate(pages):
        letters = page_letters(p)
        new = [x for x in letters if x in start and start[x] <= k <= end[x]]
        early = [x for x in letters if x in start and k < start[x]]
        if len(new) > MAX_NEW_LETTERS:
            letters_new = " ".join(new)
            out.append(f"S{s.stage} p{p.n}: {len(new)} new letters ({letters_new}); one new letter per page")
        if early:
            out.append(f"S{s.stage} p{p.n}: shows {' '.join(early)} before the page that introduces it")
        if len(letters) >= REVIEW_LETTERS and p.type not in REVIEW_TYPES:
            out.append(
                f"S{s.stage} p{p.n}: {len(letters)} letters on a {p.type} page; only review pages "
                f"({', '.join(REVIEW_TYPES)}) combine {REVIEW_LETTERS} letters or more"
            )
    return out


def check_numbers(j: Journey) -> list[str]:
    """§4.7: quantity before numerals, for every number 1–10: a quantity-first page that shows no numeral
    comes before the first page that prints it (to read or to write)."""
    out, pages = [], [p for _, p in _pages(j)]
    for number in range(1, 11):
        with_number = [(i, p) for i, p in enumerate(pages) if number in _numbers(p.params)]
        quantity = [i for i, p in with_number if p.type == "quantity-first" and not shows_numerals(p)]
        numeral = [i for i, p in with_number if shows_numerals(p)]
        if not quantity:
            out.append(f"number {number}: needs a quantity-first page")
        if not numeral:
            out.append(f"number {number}: needs numeral pages (number-intro / trace / write)")
        elif quantity and min(quantity) > min(numeral):
            out.append(f"number {number}: the numeral comes before its quantity page")
    return out


def _texts(value: Any) -> Iterator[str]:
    """Every string in a plan value (a page, its params, the notes), for the word rules."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _texts(k)
            yield from _texts(v)
    elif isinstance(value, list | tuple):
        for v in value:
            yield from _texts(v)


def retired_words(value: Any) -> list[str]:
    """The retired words (decision §5) found anywhere in `value`, harakat ignored."""
    found = {w for text in _texts(value) for w in RETIRED_WORDS if w in plain(text)}
    return sorted(found)


def check_words(j: Journey) -> list[str]:
    """Decision §5: ظبي is now ظِلّ and ذئب is now ذَيل, on every page and in every note."""
    out = []
    for s, p in _pages(j):
        for word in retired_words(p.model_dump()):
            out.append(f"S{s.stage} p{p.n}: «{word}» was replaced by «{RETIRED_WORDS[word]}»")
    rest = j.model_dump(exclude={"stages"}) | {"stages": [s.model_dump(exclude={"pages"}) for s in j.stages]}
    for word in retired_words(rest):
        out.append(f"the plan's notes still use «{word}»; it was replaced by «{RETIRED_WORDS[word]}»")
    return out


def check_writing(j: Journey) -> list[str]:
    """§4.10: a writing level starts only after enough practice at the level before it."""
    done: Counter[int] = Counter()
    out = []
    for s in j.stages:
        for p in s.pages:
            if p.type != "write-progression":
                continue
            level = int(p.params.get("level", 0))
            if level > 1 and done[level] == 0 and done[level - 1] < MIN_PRACTICE:
                out.append(f"S{s.stage} p{p.n}: level {level} begins after {done[level - 1]} practice pages")
            done[level] += 1
    missing = [lv for lv in range(1, 8) if done[lv] == 0]
    if missing:
        out.append(f"writing levels without pages: {missing}")
    return out


def check_book(j: Journey) -> list[str]:
    out = []
    if [s.stage for s in j.stages] != [1, 2, 3]:
        return ["stages must be 1, 2 and 3"]
    goals = Counter(g for s in j.stages for p in s.pages for g in p.goals)
    thin = [g for g in GOALS if goals[g] < MIN_GOAL_PAGES]
    if thin:
        out.append(f"development goals with fewer than {MIN_GOAL_PAGES} pages: {thin}")
    pages = {(s.stage, p.n): p for s in j.stages for p in s.pages}
    refs = [(r.stage, r.n) for r in j.samples]
    if len(refs) != SAMPLE_COUNT or len(set(refs)) != SAMPLE_COUNT:
        out.append(f"samples: {SAMPLE_COUNT} different pages")
    missing = [r for r in refs if r not in pages]
    if missing:
        out.append(f"samples: unknown pages {missing}")
    sections = {pages[r].section for r in refs if r in pages}
    if len(sections) < SAMPLE_SECTIONS:
        out.append(f"samples: cover at least {SAMPLE_SECTIONS} sections (found {len(sections)})")
    return out


def problems(j: Journey) -> list[str]:
    out: list[str] = []
    for s in j.stages:
        out += check_stage_pages(s)
        out += check_sections(s, j.sections)
        out += check_variety(s)
        out += check_memory_pairs(s)
        out += check_stage_scope(s)
    out += check_book(j) + check_words(j)
    if len(j.stages) == 3:
        out += check_letters(j) + check_letter_pace(j) + check_numbers(j) + check_writing(j)
    return out


# ---- the readable plan ------------------------------------------------------------------------------------


def render_markdown(j: Journey, source: str) -> str:
    titles = {x.id: f"{x.icon} {x.title_ar}" for x in j.sections} | {"intro": "البداية"}
    order = ["intro", *[x.id for x in j.sections]]
    lines = [
        f"# {j.title_ar} — {j.title_en}",
        "",
        f"Generated from `{source}` by `python -m qamra_workbook.journey render`;",
        "edit the YAML, not this file.",
        "",
        "## The idea",
        "",
        j.idea.strip(),
        "",
        "## Journey map and sections",
        "",
        "| Section | Journey stop |",
        "|---|---|",
        *[f"| {x.icon} {x.title_ar} | {x.journey_step} |" for x in j.sections],
        "",
        "## Pages per section and stage",
        "",
        "| Section | " + " | ".join(f"Stage {s.stage} ({s.age})" for s in j.stages) + " |",
        "|---|" + "---|" * len(j.stages),
    ]
    counts = {s.stage: Counter(p.section for p in s.pages) for s in j.stages}
    for sid in order:
        if any(counts[s.stage][sid] for s in j.stages):
            lines.append(
                f"| {titles.get(sid, sid)} | "
                + " | ".join(str(counts[s.stage][sid]) for s in j.stages)
                + " |"
            )
    lines.append("| **Total** | " + " | ".join(f"**{len(s.pages)}**" for s in j.stages) + " |")
    lines += [
        "",
        "## Skill order",
        "",
        j.skill_order.strip(),
        "",
        "## Difficulty per stage",
        "",
        j.difficulty_notes.strip(),
        "",
    ]
    lines += ["| Stage | Easiest | Average | Hardest |", "|---|---|---|---|"]
    for s in j.stages:
        d = [p.difficulty for p in s.pages]
        lines.append(
            f"| {s.stage} | {min(d, default=0)} | {sum(d) / max(1, len(d)):.1f} | {max(d, default=0)} |"
        )
    levels = Counter(
        int(p.params.get("level", 0)) for s in j.stages for p in s.pages if p.type == "write-progression"
    )
    lines += ["", "## Writing progression", "", j.writing_notes.strip(), "", "| Level | Pages |", "|---|---|"]
    lines += [f"| {lv} | {levels[lv]} |" for lv in range(1, 8)]
    lines += ["", "## Sample pages", ""]
    by_key = {(s.stage, p.n): p for s in j.stages for p in s.pages}
    for r in j.samples:
        p = by_key.get((r.stage, r.n))
        if p:
            lines.append(
                f"- Stage {r.stage}, page {r.n}: {titles.get(p.section, p.section)} — {p.title} (`{p.type}`)"
            )
    for s in j.stages:
        lines += ["", f"## Stage {s.stage} ({s.age}): {s.title_ar}", "", "### Objectives", ""]
        for sid, items in s.objectives.items():
            lines.append(f"**{titles.get(sid, sid)}**")
            lines += [f"- {item}" for item in items]
            lines.append("")
        lines += ["### Table of contents", "", "| Section | Pages |", "|---|---|"]
        for sid in order:
            ns = [p.n for p in s.pages if p.section == sid]
            if ns:
                lines.append(f"| {titles.get(sid, sid)} | {min(ns)}–{max(ns)} ({len(ns)}) |")
        lines += [
            "",
            "### Page by page",
            "",
            "| # | Section | Mission | Instruction | Type | Difficulty |",
            "|---|---|---|---|---|---|",
        ]
        for p in s.pages:
            extra = (" 🔊" if p.audio else "") + (" ✂" if p.one_sided else "")
            if p.merged:
                extra += f" (shared: {' + '.join(titles.get(x, x) for x in p.merged)})"
            lines.append(
                f"| {p.n} | {titles.get(p.section, p.section)} | {p.title}{extra} | {p.instruction} "
                f"| `{p.type}` | {'●' * p.difficulty} |"
            )
    lines.append("")
    return "\n".join(lines)


PLAN = Path("content/journey/plan.yaml")
DOC = Path("docs/journey/plan.md")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in ("check", "render"):
        print(__doc__)
        return 2
    plan = load(PLAN)
    found = problems(plan)
    for s in plan.stages:
        print(f"S{s.stage}: {len(s.pages)} pages, {dict(Counter(p.section for p in s.pages))}")
    for line in found:
        print("✗", line)
    print(f"{len(found)} problem(s)")
    if args[0] == "render":
        DOC.parent.mkdir(parents=True, exist_ok=True)
        DOC.write_text(render_markdown(plan, str(PLAN)), encoding="utf-8")
        print("wrote", DOC)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
