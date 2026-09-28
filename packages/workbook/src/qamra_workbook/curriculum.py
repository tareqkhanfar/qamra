"""Curriculum plan (Addendum 5 §2): the page-by-page sequence per level and volume, and its rules.

`content/workbook/curriculum/{level}.yaml` is the source. `docs/workbook/plan-{level}.md` and the Arabic
`docs/workbook/educator-{level}.md` are rendered from it (`python -m qamra_workbook.plan render kg2`), so
the plan an educator reviews never drifts from the data the workbook engine will build from. The rules
come from Addendum 5 §1–§3 and from Tareq's decisions of 28 September 2026
(`docs/workbook/decisions-2026-09-28.md`, cited below as "decision N"), which win where they differ.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

Level = Literal["kg1", "kg2"]
Subject = Literal["intro", "pen", "arabic", "math", "english", "thinking", "mixed"]
SUBJECTS: tuple[str, ...] = ("intro", "pen", "arabic", "math", "english", "thinking", "mixed")
# §2.5: an assessment ends each subject block per volume; decision 9 adds the pen-skills check
ASSESSED = ("pen", "arabic", "math", "english", "thinking")
SUBJECT_AR = {
    "intro": "البداية",
    "pen": "مهارات القلم",
    "arabic": "العربية",
    "math": "الرياضيات",
    "english": "الإنجليزية",
    "thinking": "التفكير والتركيز",
    "mixed": "مراجعة شاملة",
}

# The page-type library (Addendum 5 §4) …
LIBRARY_TYPES: dict[str, str] = {
    "pen-lines": "pen-control lines with dotted guides (params: line = horizontal|vertical|zigzag|curve…)",
    "maze": "procedurally generated maze (params: level 1–5)",
    "dot-to-dot": "connect numbered dots (params: to = highest number)",
    "trace-path": "trace a dotted path from a start picture to an end picture",
    "letter-intro": "meet the letter and 1–2 pictures of words starting with it, to color (letter, words)",
    "letter-trace": "trace the big dotted letter, then smaller sizes (params: letter, sizes)",
    "letter-write": "writing practice: guided rows, then independent rows (params: letter)",
    "find-letter": "find the letter among others, then choose the correct one (params: letter or letters)",
    "match-letter-picture": "match letter ↔ picture ↔ word (params: letter or letters, words)",
    "letter-position": "the letter at the beginning, middle and end of words (params: letter, words)",
    "harakat": "short vowels فتحة، ضمة، كسرة، سكون (params: haraka, letters)",
    "syllables": "read and build syllables (params: letters, harakat)",
    "word-read": "read simple words with pictures (params: words)",
    "word-write": "write words: dotted, then independent (params: words)",
    "number-intro": "meet the number: digit, quantity, word (params: number)",
    "number-trace": "trace the dotted number (params: number)",
    "count-and-circle": "count objects and circle the right number (params: numbers)",
    "number-quantity-match": "match numbers to quantities (params: numbers)",
    "compare": "more/less, many/few, big/small, long/short (params: concept)",
    "position-words": "above/below, inside/outside, in front/behind, right/left (params: concept)",
    "shapes": "recognize, trace and color shapes (params: shapes)",
    "pattern-complete": "complete a pattern or sequence (params: level)",
    "picture-add": "addition with pictures (params: max)",
    "picture-subtract": "subtraction with pictures (params: max)",
    "en-letter": "capital + small letter: recognize, trace, write, picture + word (params: letter, word)",
    "vocab-unit": "English vocabulary unit with pictures (params: unit, words)",
    "odd-one-out": "find the one that does not belong",
    "classify": "sort pictures into groups",
    "spot-difference": "spot the differences between two pictures (params: count)",
    "memory": "look, remember, answer",
    "coloring": "coloring inside borders (params: subject of the picture)",
    "cut-and-paste": "cut out pieces along printed cut lines and paste them (one-sided page)",
    "unit-review": "review of the unit just finished (params: letters/numbers/skills covered)",
    "assessment": (
        "simple assessment with a small teacher/parent score box (params: covers); the pen-skills check has "
        "an observation checklist and two tracing tasks instead (params: checklist, tracing)"
    ),
    "certificate": "certificate of achievement with the child's character (end of Volume 3)",
}
# … plus the structural and personalization pages the plan needs (§5).
EXTRA_TYPES: dict[str, str] = {
    "owner-page": "«هذا الكتاب لـ …» with the child's name and a handprint space",
    "name-trace": "trace and write the child's own name (params: script = ar|en)",
    "toc": "table of contents",
    "unit-opener": "unit opener with the child's character and the unit goal",
    "number-write": "write the number: guided rows, then independent (params: number)",
    "sentence-read": "read a very short sentence and match it to its picture (params: sentences)",
    "connect": "connect related pictures with lines",
    "drawing": "free drawing prompt",
    "blank": "intentionally blank (the back of a one-sided page)",
}
PAGE_TYPES = LIBRARY_TYPES | EXTRA_TYPES
# the page types as the educator's Arabic version names them (decision 10)
PAGE_TYPE_AR: dict[str, str] = {
    "pen-lines": "خطوط القلم",
    "maze": "متاهة",
    "dot-to-dot": "توصيل النقاط",
    "trace-path": "تتبّع طريق",
    "letter-intro": "أتعرّف على الحرف",
    "letter-trace": "تتبّع الحرف",
    "letter-write": "كتابة الحرف",
    "find-letter": "أجد الحرف",
    "match-letter-picture": "الحرف والصورة والكلمة",
    "letter-position": "مكان الحرف في الكلمة",
    "harakat": "الحركات",
    "syllables": "المقاطع",
    "word-read": "قراءة كلمات",
    "word-write": "كتابة كلمات",
    "number-intro": "أتعرّف على العدد",
    "number-trace": "تتبّع العدد",
    "count-and-circle": "أعدّ وأحوّط",
    "number-quantity-match": "العدد والكمية",
    "compare": "مقارنة",
    "position-words": "كلمات المكان",
    "shapes": "الأشكال",
    "pattern-complete": "أكمل النمط",
    "picture-add": "جمع بالصور",
    "picture-subtract": "طرح بالصور",
    "en-letter": "حرف إنجليزي",
    "vocab-unit": "مفردات إنجليزية",
    "odd-one-out": "المختلف",
    "classify": "تصنيف",
    "spot-difference": "الفروق بين صورتين",
    "memory": "ذاكرة",
    "coloring": "تلوين",
    "cut-and-paste": "قصّ ولصق",
    "unit-review": "مراجعة",
    "assessment": "تقييم",
    "certificate": "شهادة",
    "owner-page": "صفحة صاحب الكتاب",
    "name-trace": "اسمي",
    "toc": "الفهرس",
    "unit-opener": "افتتاح الوحدة",
    "number-write": "كتابة العدد",
    "sentence-read": "قراءة جمل",
    "connect": "توصيل",
    "drawing": "رسم",
    "blank": "صفحة فارغة",
}

ALIF = "ا"
ARABIC_LETTERS: tuple[str, ...] = tuple("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")  # alphabetical (أ ب ت ث …)
ENGLISH_LETTERS: tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
ENGLISH_BY_VOLUME = {
    1: ENGLISH_LETTERS[:8],
    2: ENGLISH_LETTERS[8:18],
    3: ENGLISH_LETTERS[18:],
}  # A–H, I–R, S–Z
# §1: 0–5 in Volume 1 and 6–10 in Volume 2. Decision 5: Volume 1 starts at 1; zero comes after 5, as «nothing»
NUMBERS_BY_VOLUME = {1: (1, 2, 3, 4, 5, 0), 2: tuple(range(6, 11))}
# the fixed per-letter sequence (§3), one page type per step group; letter-write only for the letters the
# level writes independently (decision 2)
LETTER_STEPS = ("letter-intro", "letter-trace", "letter-write", "find-letter", "match-letter-picture")
VOLUME_3_MUST_HAVE: dict[str, tuple[str, ...]] = {
    # decision 3: KG1 only listens to the short vowels, so it has no syllable pages
    "kg1": ("harakat", "word-read", "word-write", "picture-add", "picture-subtract", "vocab-unit"),
    "kg2": (
        "harakat",
        "syllables",
        "word-read",
        "word-write",
        "sentence-read",
        "picture-add",
        "picture-subtract",
        "vocab-unit",
    ),
}

MIN_PAGES, MAX_PAGES = 110, 130  # §1: lays flat, easy for small hands
MAX_RUN = 4  # §2.3: subjects rotate in short blocks
MIN_WEEK_SUBJECTS = 3  # §2.3: every week gets a balanced mix
TERM_WEEKS = {1: 12, 2: 11, 3: 11}  # decision 8: term 2 counts as 11 weeks (KG2's extra week is a review)

# ---- decisions of 28 September 2026 --------------------------------------------------------------------
NUMBER_CAP: dict[str, int] = {"kg1": 10, "kg2": 20}  # decision 5: 20 in KG2 Volume 3; nothing above 10 before
REVIEW_EVERY = (4, 5)  # decision 2: in KG1 a light review week comes after every 4–5 new letters
VOWEL_WEEKS = 3  # decision 3: KG1 listens to fatha, damma and kasra only in Volume 3's last weeks
AL_WEEKS = 3  # decision 6: KG2 reads «ال» only in Volume 3's last 3 weeks …
AL_MAX_WORDS = 6  # … with a few familiar words …
MOON_LETTERS = frozenset("ابجحخعغفقكمهوي")  # … before moon letters only, so no sun/moon lesson is needed
# decision 3: sukun moves to KG2; decision 6: tanween and shadda wait for Grade 1
HARAKAT: dict[str, tuple[str, ...]] = {
    "kg1": ("fatha", "damma", "kasra"),
    "kg2": ("fatha", "damma", "kasra", "sukun"),
}
HARAKA_NAMES = {
    "فتحة": "fatha",
    "ضمة": "damma",
    "كسرة": "kasra",
    "سكون": "sukun",
    "تنوين": "tanween",
    "شدة": "shadda",
}
SUKUN, SHADDA, TANWEEN = "\u0652", "\u0651", "\u064b\u064c\u064d"
# decision 7: the replaced picture words never come back; «طائرة» stays only as «طائرة ورقية»
REPLACED_WORDS = {"ظبي": "ظل", "لقلق": "لعبة", "ذئب": "ذيل", "طائرة": "طائرة ورقية"}
# decision 9: what the teacher or parent watches during the pen-skills check
PEN_CHECKLIST = ("grip", "pressure", "direction")
# a review week introduces nothing new: no letter, number, English letter, vowel, word, concept or unit
NEW_CONTENT_TYPES = (
    "letter-intro",
    "letter-position",
    "harakat",
    "syllables",
    "word-read",
    "sentence-read",
    "number-intro",
    "shapes",
    "position-words",
    "picture-add",
    "picture-subtract",
    "en-letter",
    "vocab-unit",
    "unit-opener",
)


class Page(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int
    week: int
    subject: Subject
    unit: str
    type: str
    skill: str  # the page's one clear goal, in Arabic, for the educator
    difficulty: int = Field(ge=1, le=5)
    params: dict[str, Any] = Field(default_factory=dict)
    one_sided: bool = False  # cut & paste: the back of the sheet stays blank


class Unit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    subject: Subject
    title_ar: str
    title_en: str = ""


class Volume(BaseModel):
    model_config = ConfigDict(extra="forbid")

    volume: int
    term: int
    weeks: int
    title_ar: str
    objectives: dict[Subject, list[str]]
    units: list[Unit]
    pages: list[Page]
    review_weeks: list[int] = Field(default_factory=list)  # light weeks that only review (decisions 2 and 8)


class Curriculum(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Level
    age: str
    title_ar: str
    title_en: str
    letter_order: list[str]  # the Arabic teaching order: all 28 letters, alphabetical (decision 1)
    # the letters the child writes alone; the others are traced and recognized. None: all 28 (decision 2)
    independent_writing: list[str] | None = None
    progression_notes: str
    interleaving_notes: str
    alignment_notes: str  # §2.6: general Palestinian/Jordanian KG expectations, no copied curriculum text
    # decision 10: the notes stay in English here and go to the educator in Arabic
    progression_notes_ar: str = ""
    interleaving_notes_ar: str = ""
    alignment_notes_ar: str = ""
    changes_ar: list[str] = Field(default_factory=list)  # what changed since the educator's last version
    volumes: list[Volume]


def load(path: Path) -> Curriculum:
    return Curriculum.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def norm_letter(letter: str) -> str:
    """أ / إ / آ are taught as alif."""
    return ALIF if letter in ("أ", "إ", "آ", "ا") else letter


def _letters(params: dict[str, Any]) -> set[str]:
    raw = params.get("letters") or ([params["letter"]] if "letter" in params else [])
    return {norm_letter(str(x)) for x in raw}


def _letter(p: Page) -> str:
    return norm_letter(str(p.params.get("letter", "")))


def _numbers(params: dict[str, Any]) -> set[int]:
    raw = params.get("numbers") or ([params["number"]] if "number" in params else [])
    return {int(x) for x in raw}


def _number_values(params: dict[str, Any]) -> list[int]:
    """Every number a page shows or counts up to (not item counts such as how many differences)."""
    out: list[int] = []
    for key in ("number", "numbers", "to", "max", "range", "start", "end"):
        raw = params.get(key)
        out += [x for x in (raw if isinstance(raw, list) else [raw]) if type(x) is int]
    return out


def _texts(value: Any) -> Iterator[str]:
    """Every string inside a params value, nested lists and dicts included."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)


def strip_marks(text: str) -> str:
    """The text without Arabic diacritics (harakat, tanween, shadda, sukun, dagger alif)."""
    return "".join(ch for ch in text if not ("\u064b" <= ch <= "\u065f" or ch == "\u0670"))


def _arabic_words(text: str) -> list[str]:
    return re.findall("[\u0621-\u064a]+", strip_marks(text))


def _without_al(word: str) -> str:
    """«الطائرة», «والطائرة» and «بالطائرة» → «طائرة»."""
    if len(word) > 4 and word[0] in "وبفك" and word[1:3] == "ال":
        word = word[1:]
    return word[2:] if word.startswith("ال") and len(word) > 3 else word


def _reading_words(p: Page) -> list[str]:
    """The Arabic words a child reads on the page: its words and sentences (not category labels)."""
    if p.subject not in ("arabic", "mixed"):
        return []
    texts = [t for key in ("word", "words", "sentences") for t in _texts(p.params.get(key, []))]
    return [w for t in texts for w in _arabic_words(t)]


def _harakat(params: dict[str, Any]) -> set[str]:
    """The vowels a page uses, by their English names (the plans write them in either language)."""
    raw = params.get("harakat") or ([params["haraka"]] if "haraka" in params else [])
    return {HARAKA_NAMES.get(strip_marks(str(h)), str(h)) for h in raw}


def _writes_alone(p: Page) -> bool:
    """The page asks the child to write without dotted guides."""
    return int(p.params.get("independent") or 0) > 0 or p.params.get("mode") in ("independent", "write")


# ---- rules: each returns human-readable problems ("V2 p37: …") -------------------------------------------


def check_numbering(v: Volume) -> list[str]:
    tag, n = f"V{v.volume}", len(v.pages)
    out = []
    if [p.n for p in v.pages] != list(range(1, n + 1)):
        out.append(f"{tag}: page numbers must run 1..{n} without gaps or repeats")
    if not MIN_PAGES <= n <= MAX_PAGES:
        out.append(f"{tag}: {n} pages; a volume has {MIN_PAGES}–{MAX_PAGES}")
    if n % 2:
        out.append(f"{tag}: {n} pages; printed sheets need an even count (add or remove one page)")
    return out


def check_fields(v: Volume) -> list[str]:
    tag = f"V{v.volume}"
    units = {u.id: u for u in v.units}
    out = [f"{tag}: unit id {k!r} used {c} times" for k, c in Counter(u.id for u in v.units).items() if c > 1]
    for p in v.pages:
        if p.type not in PAGE_TYPES:
            out.append(f"{tag} p{p.n}: unknown page type {p.type!r}")
        unit = units.get(p.unit)
        if unit is None:
            out.append(f"{tag} p{p.n}: unknown unit {p.unit!r}")
        elif unit.subject != p.subject:
            out.append(f"{tag} p{p.n}: subject {p.subject} but unit {p.unit} is {unit.subject}")
        if not p.skill.strip():
            out.append(f"{tag} p{p.n}: empty skill")
    for u in v.units:
        if not any(p.unit == u.id for p in v.pages):
            out.append(f"{tag}: unit {u.id} has no pages")
    return out


def check_one_sided(v: Volume) -> list[str]:
    """Cut & paste pages are one-sided: the other side of the sheet (odd front, even back) is blank."""
    tag, pages = f"V{v.volume}", {p.n: p for p in v.pages}
    out = []
    for p in v.pages:
        if p.type == "cut-and-paste" and not p.one_sided:
            out.append(f"{tag} p{p.n}: cut-and-paste pages must be one_sided")
        if p.one_sided:
            back = pages.get(p.n + 1 if p.n % 2 else p.n - 1)
            if back is None or back.type != "blank":
                out.append(f"{tag} p{p.n}: one-sided page; the other side of its sheet must be a blank page")
    return out


def check_weeks(v: Volume) -> list[str]:
    tag, weeks = f"V{v.volume}", [p.week for p in v.pages]
    out: list[str] = []
    if not weeks:
        return out
    if weeks[0] != 1 or any(b < a or b - a > 1 for a, b in pairwise(weeks)):
        out.append(f"{tag}: weeks must start at 1 and go up by one at a time")
    if weeks[-1] != v.weeks:
        out.append(f"{tag}: the last page is in week {weeks[-1]} but the volume has {v.weeks} weeks")
    if v.weeks != TERM_WEEKS.get(v.volume, v.weeks):
        out.append(f"{tag}: {v.weeks} weeks; term {v.volume} has {TERM_WEEKS[v.volume]} (decision 8)")
    for w in sorted(set(weeks)):
        taught = [p.subject for p in v.pages if p.week == w and p.subject not in ("intro", "mixed")]
        if len(taught) >= 6 and len(set(taught)) < MIN_WEEK_SUBJECTS:
            out.append(
                f"{tag} week {w}: only {sorted(set(taught))}; each week mixes ≥ {MIN_WEEK_SUBJECTS} subjects"
            )
    return out


def check_interleaving(v: Volume) -> list[str]:
    tag, out, run = f"V{v.volume}", [], 1
    for a, b in pairwise(v.pages):
        run = run + 1 if b.subject == a.subject else 1
        if run == MAX_RUN + 1:
            out.append(f"{tag} p{b.n}: more than {MAX_RUN} {b.subject} pages in a row")
    return out


def check_reviews(v: Volume) -> list[str]:
    """§2.5: a review page ends every unit; an assessment ends every subject block of the volume."""
    tag, out = f"V{v.volume}", []
    for u in v.units:
        pages = [p for p in v.pages if p.unit == u.id]
        if (
            u.subject != "intro"
            and pages
            and pages[-1].type not in ("unit-review", "assessment", "certificate")
        ):
            out.append(
                f"{tag}: unit {u.id} ends on p{pages[-1].n} ({pages[-1].type}); a unit ends with a review"
            )
    for s in ASSESSED:
        pages = [p for p in v.pages if p.subject == s]
        if not pages:
            out.append(f"{tag}: no {s} pages")
            continue
        taught = [p.n for p in pages if p.type != "assessment"]
        if not any(p.type == "assessment" and p.n > max(taught, default=0) for p in pages):
            out.append(f"{tag}: no {s} assessment after the last {s} page")
    return out


def check_pen_assessment(v: Volume) -> list[str]:
    """Decision 9: each volume closes with a pen-skills check: a short teacher/parent checklist (pen grip,
    pressure, direction) and two tracing tasks, among the final assessments of its last week."""
    tag = f"V{v.volume}"
    checks = [p for p in v.pages if p.subject == "pen" and p.type == "assessment"]
    if len(checks) != 1:
        return [f"{tag}: needs one pen-skills assessment at the end (decision 9); found {len(checks)}"]
    p, out = checks[0], []
    missing = [x for x in PEN_CHECKLIST if x not in p.params.get("checklist", [])]
    if missing:
        out.append(
            f"{tag} p{p.n}: the pen checklist must cover {', '.join(PEN_CHECKLIST)}; no {', '.join(missing)}"
        )
    if len(p.params.get("tracing", [])) != 2:
        out.append(f"{tag} p{p.n}: the pen-skills assessment has two tracing tasks (params.tracing)")
    after = [q for q in v.pages if q.n > p.n]
    if p.week != v.weeks or any(q.type not in ("assessment", "certificate") for q in after):
        out.append(
            f"{tag} p{p.n}: the pen-skills assessment belongs with the final assessments of the last week"
        )
    return out


def check_review_weeks(v: Volume) -> list[str]:
    """Decisions 2 and 8: a review week introduces nothing new, brings back every letter met since the last
    review week, and is light: fewer pages than the volume's average week."""
    tag, out = f"V{v.volume}", []
    average = len(v.pages) / v.weeks if v.weeks else 0
    since = 0  # the last page of the previous review week
    for w in sorted(v.review_weeks):
        week = [p for p in v.pages if p.week == w]
        if not week or w == v.weeks:
            out.append(f"{tag}: review week {w} must be a week of the volume before its last week")
            continue
        out += [
            f"{tag} p{p.n}: {p.type} in review week {w}; nothing new here"
            for p in week
            if p.type in NEW_CONTENT_TYPES
        ]
        if len(week) >= average:
            out.append(
                f"{tag}: review week {w} has {len(week)} pages; a light week has fewer than {average:.1f}"
            )
        start = week[0].n
        met = {_letter(p) for p in v.pages if p.type == "letter-intro" and since < p.n < start}
        reviewed = set().union(
            *(_letters(p.params) for p in week if p.subject == "arabic" and p.type == "unit-review")
        )
        if met - reviewed:
            out.append(f"{tag}: review week {w} does not review {'، '.join(sorted(met - reviewed))}")
        since = week[-1].n
    return out


def writers(c: Curriculum) -> list[str]:
    """The letters the level writes independently, alphabetically; all 28 when the plan lists none."""
    listed = set(ARABIC_LETTERS if c.independent_writing is None else map(norm_letter, c.independent_writing))
    return [x for x in ARABIC_LETTERS if x in listed] + sorted(listed - set(ARABIC_LETTERS))


def check_arabic_letters(c: Curriculum) -> list[str]:
    out = []
    order = [norm_letter(x) for x in c.letter_order]
    if order != list(ARABIC_LETTERS):
        out.append("letter_order must be the 28 letters in alphabetical order, أ ب ت ث … (decision 1)")
    intros = [_letter(p) for v in c.volumes for p in v.pages if p.type == "letter-intro"]
    if intros != order:
        out.append(
            f"letter-intro pages must introduce each letter once, in letter_order; found {''.join(intros)}"
        )
    writing = set(writers(c))
    for v in c.volumes:
        for letter in dict.fromkeys(_letter(p) for p in v.pages if p.type == "letter-intro"):
            # decision 2: a letter the level does not write alone is traced and recognized, with no write page
            steps = [s for s in LETTER_STEPS if s != "letter-write" or letter in writing]
            firsts: list[int | None] = []
            for step in steps:
                hits = [p.n for p in v.pages if p.type == step and letter in _letters(p.params)]
                firsts.append(min(hits) if hits else None)
            missing = [s for s, n in zip(steps, firsts, strict=True) if n is None]
            if missing:
                out.append(f"V{v.volume} letter {letter}: missing {', '.join(missing)}")
            elif firsts != sorted(n for n in firsts if n is not None):
                out.append(
                    f"V{v.volume} letter {letter}: steps out of order {dict(zip(steps, firsts, strict=True))}"
                )
    return out


def check_independent_writing(c: Curriculum) -> list[str]:
    """Decision 2: where the plan lists the letters written alone (KG1: the simple shapes), only those get
    writing pages, each with an independent row; words and vowels are traced, never written alone."""
    if c.independent_writing is None:
        return []
    listed, out = set(writers(c)), []
    unknown = listed - set(ARABIC_LETTERS)
    if unknown:
        out.append(f"independent_writing has {'، '.join(sorted(unknown))}, which are not Arabic letters")
    written: set[str] = set()
    for v in c.volumes:
        for p in v.pages:
            tag = f"V{v.volume} p{p.n}"
            if p.type == "letter-write":
                traced = _letters(p.params) - listed
                if traced:
                    out.append(
                        f"{tag}: letter-write for {'، '.join(sorted(traced))}; {c.level} only traces them"
                    )
                if _writes_alone(p):
                    written |= _letters(p.params)
            elif p.type in ("word-write", "syllables", "harakat", "sentence-read") and _writes_alone(p):
                out.append(
                    f"{tag}: {p.type} asks for writing alone; {c.level} writes alone only listed letters"
                )
    for letter in [x for x in writers(c) if x in listed - unknown - written]:
        out.append(
            f"letter {letter} is in independent_writing but no letter-write page has an independent row"
        )
    return out


def check_review_rhythm(c: Curriculum) -> list[str]:
    """Decision 2: in KG1 a light review week follows every 4–5 new letters (a volume's last week, the term
    review, closes the last group). Decision 8: KG2's term 2 has 11 weeks, and the extra one is a review."""
    out: list[str] = []
    if c.level == "kg2" and any(v.volume == 2 and not v.review_weeks for v in c.volumes):
        out.append("V2: term 2 counts 11 weeks and the extra week is a review week; list it in review_weeks")
    if c.level != "kg1":
        return out
    low, high = REVIEW_EVERY
    for v in c.volumes:
        count = 0
        for w in range(1, v.weeks + 1):
            if w in v.review_weeks:
                if not low <= count <= high:
                    out.append(
                        f"V{v.volume}: review week {w} comes after {count} new letters; KG1 reviews every "
                        f"{low}–{high}"
                    )
                count = 0
            count += sum(1 for p in v.pages if p.week == w and p.type == "letter-intro")
            if count > high:
                out.append(
                    f"V{v.volume} week {w}: {count} new letters since the last review week (at most {high})"
                )
                count = 0
    return out


def check_vowels(c: Curriculum) -> list[str]:
    """Decision 3: KG1 only listens to fatha, damma and kasra, in Volume 3's last weeks after the 28 letters,
    with no syllable writing, and never meets sukun; KG2 teaches all four.
    Decision 6: no tanween and no shadda at either level."""
    out: list[str] = []
    allowed = HARAKAT[c.level]
    taught = {h for v in c.volumes for p in v.pages if p.type == "harakat" for h in _harakat(p.params)}
    if taught != set(allowed):
        out.append(
            f"harakat pages must teach {', '.join(allowed)}; found {', '.join(sorted(taught)) or 'none'}"
        )
    banned = {"sukun", "tanween", "shadda"} - set(allowed)
    marks = TANWEEN + SHADDA + ("" if "sukun" in allowed else SUKUN)
    last = c.volumes[-1] if c.volumes else None
    for v in c.volumes:
        letters_done = max((p.n for p in v.pages if p.type == "letter-intro"), default=0)
        for p in v.pages:
            tag = f"V{v.volume} p{p.n}"
            if _harakat(p.params) & banned:
                out.append(
                    f"{tag}: {', '.join(sorted(_harakat(p.params) & banned))} is not taught in {c.level}"
                )
            # the skill is instruction text for adults (أتعرّف، خطوطًا); only KG1's no-sukun rule reaches it
            found = {ch for t in _texts(p.params) for ch in t if ch in marks}
            found |= {SUKUN} & set(p.skill) & set(marks)
            if found:
                out.append(f"{tag}: a {' or '.join(sorted(banned))} mark; {c.level} does not use it")
            named = {"تنوين", "التنوين", "شدة", "الشدة"} | (
                {"سكون", "السكون"} if "sukun" in banned else set()
            )
            if named & set(_arabic_words(p.skill)):
                out.append(f"{tag}: the skill names {'، '.join(sorted(named & set(_arabic_words(p.skill))))}")
            if c.level != "kg1" or p.type not in ("harakat", "syllables"):
                continue
            if v is not last or p.week <= v.weeks - VOWEL_WEEKS or p.n < letters_done:
                out.append(
                    f"{tag}: KG1 meets the vowels only in V3's last {VOWEL_WEEKS} weeks, after the letters"
                )
            if p.params.get("mode") != "listen" or _writes_alone(p):
                out.append(
                    f"{tag}: KG1 vowel pages are sound recognition only (params.mode: listen), no writing"
                )
    return out


def check_al(c: Curriculum) -> list[str]:
    """Decision 6: «ال» is read only in KG2 Volume 3's last 3 weeks, with a few familiar words (met earlier as
    picture words), before moon letters only, and no sun/moon lesson. KG1 never reads it."""
    out: list[str] = []
    seen: set[str] = set()  # picture words so far
    found: set[str] = set()
    for v in c.volumes:
        for p in v.pages:
            tag = f"V{v.volume} p{p.n}"
            if any(x in _arabic_words(p.skill) for x in ("الشمسية", "القمرية")):
                out.append(f"{tag}: no sun/moon letter lesson (decision 6)")
            for w in (w for w in _reading_words(p) if w.startswith("ال") and len(w) > 3):
                found.add(w)
                if c.level == "kg1" or v.volume != 3 or p.week <= v.weeks - AL_WEEKS:
                    out.append(f"{tag}: «{w}»; «ال» is read only in KG2 Volume 3's last {AL_WEEKS} weeks")
                elif norm_letter(w[2]) not in MOON_LETTERS:
                    out.append(
                        f"{tag}: «{w}»; «ال» comes only before moon letters, so no sun/moon lesson is needed"
                    )
                elif w[2:] not in seen:
                    out.append(
                        f"{tag}: «{w}» is not familiar; «{w[2:]}» should appear earlier as a picture word"
                    )
            seen |= {
                w
                for key in ("word", "words")
                for t in _texts(p.params.get(key, []))
                for w in _arabic_words(t)
            }
    if len(found) > AL_MAX_WORDS:
        out.append(f"{len(found)} «ال» words; decision 6 asks for a few (at most {AL_MAX_WORDS})")
    if c.level == "kg2" and not found:
        out.append(f"KG2 reads a few familiar «ال» words in Volume 3's last {AL_WEEKS} weeks (decision 6)")
    return out


def check_english(c: Curriculum) -> list[str]:
    out = []
    for v in c.volumes:
        intros = [str(p.params.get("letter", "")).upper() for p in v.pages if p.type == "en-letter"]
        if tuple(intros) != ENGLISH_BY_VOLUME[v.volume]:
            want = "".join(ENGLISH_BY_VOLUME[v.volume])
            out.append(f"V{v.volume}: en-letter pages must cover {want} in order; found {''.join(intros)}")
        for p in v.pages:
            if p.type != "en-letter":
                continue
            letter = str(p.params.get("letter", "")).upper()
            later = [
                q
                for q in v.pages
                if q.n > p.n
                and q.subject == "english"
                and q.type != "en-letter"
                and letter
                in {str(x).upper() for x in (q.params.get("letters") or [q.params.get("letter", "")])}
            ]
            if not later:
                out.append(
                    f"V{v.volume} English {letter}: no practice page (find, match, color or review) after it"
                )
    return out


def check_numbers(c: Curriculum) -> list[str]:
    out = []
    for v in c.volumes:
        missing = [p.n for p in v.pages if p.type == "number-intro" and not _numbers(p.params)]
        out += [f"V{v.volume} p{n}: number-intro needs params.number" for n in missing]
        intros = tuple(
            min(_numbers(p.params)) for p in v.pages if p.type == "number-intro" and _numbers(p.params)
        )
        want = NUMBERS_BY_VOLUME.get(v.volume, ())
        if want and intros[: len(want)] != want:
            out.append(f"V{v.volume}: number-intro pages must introduce {want} in this order; found {intros}")
        for number in intros:
            intro = min(p.n for p in v.pages if p.type == "number-intro" and number in _numbers(p.params))
            traced = [p.n for p in v.pages if p.type == "number-trace" and number in _numbers(p.params)]
            applied = [
                p.n
                for p in v.pages
                if p.type in ("count-and-circle", "number-quantity-match", "compare", "number-write")
                and number in _numbers(p.params)
            ]
            if not traced or min(traced) < intro:
                out.append(f"V{v.volume} number {number}: needs a number-trace page after its intro")
            if not applied or max(applied) < intro:
                out.append(f"V{v.volume} number {number}: needs a practice/apply page after its intro")
    five = False  # decision 5: counting starts at 1; zero comes after 5, as «nothing»
    for v in c.volumes:
        for p in v.pages:
            if 0 in _numbers(p.params) and not five:
                out.append(f"V{v.volume} p{p.n}: zero before 5; it comes after 5, as «nothing» (decision 5)")
            five = five or (p.type == "number-intro" and 5 in _numbers(p.params))
    return out


def check_number_range(c: Curriculum) -> list[str]:
    """Decision 5: KG2 counts to 20, only in Volume 3, and shows tens and ones in pictures only; KG1 stays
    within 10."""
    cap, out = NUMBER_CAP[c.level], []
    for v in c.volumes:
        for p in v.pages:
            tag, top = f"V{v.volume} p{p.n}", max(_number_values(p.params), default=0)
            if top > cap:
                out.append(f"{tag}: {top} is above the {c.level} cap of {cap}")
            elif top > 10 and v.volume != 3:
                out.append(f"{tag}: {top}; numbers above 10 wait for Volume 3")
            if max(_numbers(p.params), default=0) > 10 and p.params.get("tens_ones") != "pictures":
                out.append(
                    f"{tag}: numbers above 10 show tens and ones in pictures only (tens_ones: pictures)"
                )
    return out


def check_words(c: Curriculum) -> list[str]:
    """Decision 7: the replaced picture words (ظبي، لقلق، ذئب، and «طائرة» alone) never come back."""
    out = []
    for v in c.volumes:
        texts = [(f"V{v.volume} objectives", t) for items in v.objectives.values() for t in items]
        texts += [(f"V{v.volume} p{p.n}", t) for p in v.pages for t in (p.skill, *_texts(p.params))]
        for tag, text in texts:
            words = [_without_al(w) for w in _arabic_words(text)]
            for i, word in enumerate(words):
                new = REPLACED_WORDS.get(word)
                rest = new.split()[1:] if new else []
                if new and not (rest and words[i + 1 : i + 1 + len(rest)] == rest):
                    out.append(f"{tag}: «{word}» was replaced by «{new}» (decision 7)")
    return out


def check_scope(c: Curriculum) -> list[str]:
    """The volume content table in §1, and the certificate at the very end."""
    out = []
    kinds = {v.volume: {p.type for p in v.pages} for v in c.volumes}
    if [v.volume for v in c.volumes] != [1, 2, 3]:
        return ["volumes must be 1, 2 and 3"]
    if "pen-lines" not in kinds[1]:
        out.append("V1: pen skills (pen-lines) are missing")
    for t in VOLUME_3_MUST_HAVE[c.level]:
        if t not in kinds[3]:
            out.append(f"V3: {t} pages are missing")
    if c.level == "kg1":
        out += [
            f"V{v.volume}: KG1 has no sentences (decision 4)"
            for v in c.volumes
            if "sentence-read" in kinds[v.volume]
        ]
    last = c.volumes[2].pages[-1] if c.volumes[2].pages else None
    if last is None or last.type != "certificate":
        out.append("V3 must end with the certificate page")
    for v in c.volumes:
        seen: dict[tuple[str, str], int] = {}
        for p in v.pages:
            if p.type in ("blank", "unit-opener", "toc"):
                continue
            key = (p.type, yaml.safe_dump(p.params, allow_unicode=True, sort_keys=True) + p.skill)
            if key in seen:
                out.append(f"V{v.volume} p{p.n}: duplicates p{seen[key]}")
            seen.setdefault(key, p.n)
    return out


def check_notes(c: Curriculum) -> list[str]:
    """Decision 10: the educator reads every progression, interleaving and alignment note in Arabic."""
    pairs = {
        "progression_notes": (c.progression_notes, c.progression_notes_ar),
        "interleaving_notes": (c.interleaving_notes, c.interleaving_notes_ar),
        "alignment_notes": (c.alignment_notes, c.alignment_notes_ar),
    }
    return [
        f"{name}_ar is missing; the educator's version is in Arabic (decision 10)"
        for name, (en, ar) in pairs.items()
        if en.strip() and not ar.strip()
    ]


def problems(c: Curriculum) -> list[str]:
    out: list[str] = []
    for v in c.volumes:
        for rule in (
            check_numbering,
            check_fields,
            check_one_sided,
            check_weeks,
            check_interleaving,
            check_reviews,
            check_pen_assessment,
            check_review_weeks,
        ):
            out += rule(v)
    for crule in (
        check_arabic_letters,
        check_independent_writing,
        check_review_rhythm,
        check_vowels,
        check_al,
        check_english,
        check_numbers,
        check_number_range,
        check_words,
        check_scope,
        check_notes,
    ):
        out += crule(c)
    return out


# ---- the readable plan ------------------------------------------------------------------------------------


def picture_words(c: Curriculum) -> list[str]:
    words: set[str] = set()
    for v in c.volumes:
        for p in v.pages:
            for key in ("words", "word"):
                raw = p.params.get(key)
                for w in raw if isinstance(raw, list) else ([raw] if raw else []):
                    words.add(str(w))
    return sorted(words)


def render_markdown(c: Curriculum, source: str) -> str:
    lines = [
        f"# {c.title_ar} — {c.title_en}",
        "",
        f"Age {c.age}. Generated from `{source}` by `python -m qamra_workbook.plan render {c.level}`;",
        "edit the YAML, not this file.",
        "",
        "## Pages per volume",
        "",
        "| Volume | Weeks | Pages | " + " | ".join(SUBJECT_AR[s] for s in SUBJECTS) + " |",
        "|---|---|---|" + "---|" * len(SUBJECTS),
    ]
    for v in c.volumes:
        count: Counter[str] = Counter(p.subject for p in v.pages)
        lines.append(
            f"| {v.volume} | {v.weeks} | **{len(v.pages)}** | "
            + " | ".join(str(count.get(s, 0)) for s in SUBJECTS)
            + " |"
        )
    lines += [
        f"| **Total** | | **{sum(len(v.pages) for v in c.volumes)}** | " + " | " * (len(SUBJECTS) - 1) + " |",
        "",
        "## Progression",
        "",
        c.progression_notes.strip(),
        "",
        "## Interleaving",
        "",
        c.interleaving_notes.strip(),
        "",
        "## Alignment with Palestinian and Jordanian KG expectations",
        "",
        c.alignment_notes.strip(),
        "",
        "## Arabic letter order",
        "",
        "، ".join(c.letter_order),
        "",
    ]
    if c.independent_writing is not None:
        lines += [
            "## Letters written independently",
            "",
            "، ".join(writers(c)) + ". The other letters are traced and recognized (decision 2).",
            "",
        ]
    for v in c.volumes:
        lines += [f"## Volume {v.volume} (term {v.term}): {v.title_ar}", ""]
        if v.review_weeks:
            lines += [f"Review weeks: {', '.join(map(str, v.review_weeks))}.", ""]
        lines += ["### Learning objectives", ""]
        for subject, items in v.objectives.items():
            lines.append(f"**{SUBJECT_AR[subject]}**")
            lines += [f"- {item}" for item in items]
            lines.append("")
        lines += ["### Table of contents", "", "| Unit | Subject | Pages |", "|---|---|---|"]
        for u in v.units:
            ns = [p.n for p in v.pages if p.unit == u.id]
            span = f"{min(ns)}–{max(ns)}" if ns else "—"
            lines.append(f"| {u.title_ar} | {SUBJECT_AR[u.subject]} | {span} ({len(ns)}) |")
        lines += [
            "",
            "### Page by page",
            "",
            "| # | Week | Subject | Skill | Page type | Difficulty |",
            "|---|---|---|---|---|---|",
        ]
        for p in v.pages:
            mark = " ✂" if p.one_sided else ""
            label, dots = SUBJECT_AR[p.subject], "●" * p.difficulty
            week = f"{p.week} (review)" if p.week in v.review_weeks else str(p.week)
            lines.append(f"| {p.n} | {week} | {label} | {p.skill}{mark} | `{p.type}` | {dots} |")
        lines.append("")
    words = picture_words(c)
    lines += [
        f"## Picture words ({len(words)}), for the educator's review",
        "",
        "، ".join(words) if words else "—",
        "",
    ]
    return "\n".join(lines)


# ---- the educator's version, in Arabic (decisions 1 and 10) ---------------------------------------------

EDUCATOR_SIGN_OFF_AR = "لن يُطبع أيّ جزء للبيع قبل توقيعك على هذه الخطة وعلى أشكال الحروف."
ORDINAL_AR = {1: "الأول", 2: "الثاني", 3: "الثالث"}


def ar_digits(value: object) -> str:
    """Arabic-Indic digits (١٢٣), as the workbook's Arabic pages print them."""
    return str(value).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def render_educator(c: Curriculum, source: str) -> str:
    """The plan as it goes to the kindergarten educator: all in Arabic, with what changed since her last
    version at the top and the sign-off that printing for sale waits for."""
    lines = [
        f"<!-- Generated from {source} by `python -m qamra_workbook.plan render {c.level}`. Edit the YAML "
        "instead. -->",
        "",
        '<div dir="rtl">',
        "",
        f"# {c.title_ar}",
        "",
        f"نسخة المربّية من خطة الدوسية، للأطفال من عمر {ar_digits(c.age)} سنوات، "
        "في ثلاثة أجزاء (جزء لكل فصل).",
        "",
        f"> **{EDUCATOR_SIGN_OFF_AR}**",
        "",
    ]
    if c.changes_ar:
        lines += ["## ما الذي تغيّر منذ النسخة السابقة", "", *[f"- {x}" for x in c.changes_ar], ""]
    lines += [
        "## عدد الصفحات في كل جزء",
        "",
        "| الجزء | الأسابيع | الصفحات | " + " | ".join(SUBJECT_AR[s] for s in SUBJECTS) + " |",
        "|---|---|---|" + "---|" * len(SUBJECTS),
    ]
    for v in c.volumes:
        count: Counter[str] = Counter(p.subject for p in v.pages)
        cells = [
            ORDINAL_AR.get(v.volume, ar_digits(v.volume)),
            ar_digits(v.weeks),
            f"**{ar_digits(len(v.pages))}**",
        ]
        lines.append("| " + " | ".join(cells + [ar_digits(count.get(s, 0)) for s in SUBJECTS]) + " |")
    total = ar_digits(sum(len(v.pages) for v in c.volumes))
    lines += [
        f"| **المجموع** | | **{total}** | " + " | " * (len(SUBJECTS) - 1) + " |",
        "",
        "## التدرّج",
        "",
        c.progression_notes_ar.strip(),
        "",
        "## التنويع وتوزيع المواد",
        "",
        c.interleaving_notes_ar.strip(),
        "",
        "## المواءمة مع توقّعات رياض الأطفال في فلسطين والأردن",
        "",
        c.alignment_notes_ar.strip(),
        "",
        "## ترتيب الحروف العربية",
        "",
        "، ".join(c.letter_order),
        "",
    ]
    if c.independent_writing is not None:
        lines += [
            "## الحروف التي يكتبها الطفل وحده",
            "",
            "، ".join(writers(c)) + ". أمّا باقي الحروف فيتتبّعها الطفل ويتعرّف عليها فقط.",
            "",
        ]
    for v in c.volumes:
        lines += _educator_volume(v)
    words = picture_words(c)
    arabic = [w for w in words if _arabic_words(w)]
    english = [w for w in words if not _arabic_words(w)]
    lines += [
        "## كلمات الصور للمراجعة",
        "",
        f"**بالعربية ({ar_digits(len(arabic))}):** " + ("، ".join(arabic) or "—"),
        "",
        f"**بالإنجليزية ({ar_digits(len(english))}):** " + ("، ".join(english) or "—"),
        "",
        "## توقيع المربّية",
        "",
        "راجعتُ الخطة صفحةً صفحة، وأوافق عليها.",
        "",
        "الاسم: ………………………… التوقيع: ………………………… التاريخ: …………………………",
        "",
        "</div>",
        "",
    ]
    return "\n".join(lines)


def _educator_volume(v: Volume) -> list[str]:
    lines = [f"## {v.title_ar}", ""]
    facts = f"الفصل {ORDINAL_AR.get(v.term, ar_digits(v.term))}، الأسابيع: {ar_digits(v.weeks)}، الصفحات: "
    facts += ar_digits(len(v.pages)) + "."
    if v.review_weeks:
        facts += " أسابيع المراجعة: " + "، ".join(ar_digits(w) for w in v.review_weeks) + "."
    lines += [facts, "", "### أهداف التعلّم", ""]
    for subject, items in v.objectives.items():
        lines += [f"**{SUBJECT_AR[subject]}**", *[f"- {item}" for item in items], ""]
    lines += ["### فهرس الوحدات", "", "| الوحدة | المادة | الصفحات |", "|---|---|---|"]
    for u in v.units:
        ns = [p.n for p in v.pages if p.unit == u.id]
        span = f"{ar_digits(min(ns))}–{ar_digits(max(ns))} ({ar_digits(len(ns))})" if ns else "—"
        lines.append(f"| {u.title_ar} | {SUBJECT_AR[u.subject]} | {span} |")
    lines += [
        "",
        "### الصفحات صفحةً صفحة",
        "",
        "الصعوبة من ● (الأسهل) إلى ●●●●●. العلامة ✂ لصفحة قصّ ولصق تُطبع على وجه واحد، وظهرها فارغ.",
        "",
        "| الصفحة | الأسبوع | المادة | المهارة | نوع الصفحة | الصعوبة |",
        "|---|---|---|---|---|---|",
    ]
    for p in v.pages:
        mark = " ✂" if p.one_sided else ""
        week = ar_digits(p.week) + (" (مراجعة)" if p.week in v.review_weeks else "")
        kind = PAGE_TYPE_AR.get(p.type, p.type)
        cells = [ar_digits(p.n), week, SUBJECT_AR[p.subject], p.skill + mark, kind, "●" * p.difficulty]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return lines
