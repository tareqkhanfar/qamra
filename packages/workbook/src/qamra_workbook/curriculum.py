"""Curriculum plan (Addendum 5 §2): the page-by-page sequence per level and volume, and its rules.

`content/workbook/curriculum/{level}.yaml` is the source. `docs/workbook/plan-{level}.md` is rendered
from it (`python -m qamra_workbook.plan render kg2`), so the plan an educator reviews never drifts from
the data the workbook engine will build from. Every rule below comes from Addendum 5 §1–§3.
"""

from __future__ import annotations

from collections import Counter
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

Level = Literal["kg1", "kg2"]
Subject = Literal["intro", "pen", "arabic", "math", "english", "thinking", "mixed"]
SUBJECTS: tuple[str, ...] = ("intro", "pen", "arabic", "math", "english", "thinking", "mixed")
ASSESSED = ("arabic", "math", "english", "thinking")  # §2.5: an assessment ends each subject block per volume
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
    "assessment": "simple assessment with a small teacher/parent score box (params: covers)",
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

ALIF = "ا"
ARABIC_LETTERS: tuple[str, ...] = tuple("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
ENGLISH_LETTERS: tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
ENGLISH_BY_VOLUME = {
    1: ENGLISH_LETTERS[:8],
    2: ENGLISH_LETTERS[8:18],
    3: ENGLISH_LETTERS[18:],
}  # A–H, I–R, S–Z
NUMBERS_BY_VOLUME = {1: tuple(range(0, 6)), 2: tuple(range(6, 11))}  # 0–5, 6–10 (§1)
# the fixed per-letter sequence (§3), one page type per step group
LETTER_STEPS = ("letter-intro", "letter-trace", "letter-write", "find-letter", "match-letter-picture")
VOLUME_3_MUST_HAVE = (
    "harakat",
    "syllables",
    "word-read",
    "word-write",
    "picture-add",
    "picture-subtract",
    "vocab-unit",
)

MIN_PAGES, MAX_PAGES = 110, 130  # §1: lays flat, easy for small hands
MAX_RUN = 4  # §2.3: subjects rotate in short blocks
MIN_WEEK_SUBJECTS = 3  # §2.3: every week gets a balanced mix


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


class Curriculum(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Level
    age: str
    title_ar: str
    title_en: str
    letter_order: list[str]  # the Arabic teaching order: all 28 letters across the three volumes
    progression_notes: str
    interleaving_notes: str
    alignment_notes: str  # §2.6: general Palestinian/Jordanian KG expectations, no copied curriculum text
    volumes: list[Volume]


def load(path: Path) -> Curriculum:
    return Curriculum.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def norm_letter(letter: str) -> str:
    """أ / إ / آ are taught as alif."""
    return ALIF if letter in ("أ", "إ", "آ", "ا") else letter


def _letters(params: dict[str, Any]) -> set[str]:
    raw = params.get("letters") or ([params["letter"]] if "letter" in params else [])
    return {norm_letter(str(x)) for x in raw}


def _numbers(params: dict[str, Any]) -> set[int]:
    raw = params.get("numbers") or ([params["number"]] if "number" in params else [])
    return {int(x) for x in raw}


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


def check_arabic_letters(c: Curriculum) -> list[str]:
    out = []
    order = [norm_letter(x) for x in c.letter_order]
    if sorted(order) != sorted(ARABIC_LETTERS):
        out.append("letter_order must list the 28 Arabic letters, each once")
    intros = [
        norm_letter(str(p.params.get("letter", "")))
        for v in c.volumes
        for p in v.pages
        if p.type == "letter-intro"
    ]
    if intros != order:
        out.append(
            f"letter-intro pages must introduce each letter once, in letter_order; found {''.join(intros)}"
        )
    for v in c.volumes:
        for letter in {
            norm_letter(str(p.params.get("letter", ""))) for p in v.pages if p.type == "letter-intro"
        }:
            firsts: list[int | None] = []
            for step in LETTER_STEPS:
                hits = [p.n for p in v.pages if p.type == step and letter in _letters(p.params)]
                firsts.append(min(hits) if hits else None)
            missing = [s for s, n in zip(LETTER_STEPS, firsts, strict=True) if n is None]
            if missing:
                out.append(f"V{v.volume} letter {letter}: missing {', '.join(missing)}")
            elif firsts != sorted(n for n in firsts if n is not None):
                steps = dict(zip(LETTER_STEPS, firsts, strict=True))
                out.append(f"V{v.volume} letter {letter}: steps out of order {steps}")
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
        intros = tuple(int(p.params.get("number", -1)) for p in v.pages if p.type == "number-intro")
        want = NUMBERS_BY_VOLUME.get(v.volume, ())
        if want and intros[: len(want)] != want:
            out.append(
                f"V{v.volume}: number-intro pages must cover {want[0]}–{want[-1]} in order; found {intros}"
            )
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
    return out


def check_scope(c: Curriculum) -> list[str]:
    """The volume content table in §1, and the certificate at the very end."""
    out = []
    kinds = {v.volume: {p.type for p in v.pages} for v in c.volumes}
    if [v.volume for v in c.volumes] != [1, 2, 3]:
        return ["volumes must be 1, 2 and 3"]
    if "pen-lines" not in kinds[1]:
        out.append("V1: pen skills (pen-lines) are missing")
    for t in VOLUME_3_MUST_HAVE:
        if t not in kinds[3]:
            out.append(f"V3: {t} pages are missing")
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
        ):
            out += rule(v)
    for crule in (check_arabic_letters, check_english, check_numbers, check_scope):
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
    for v in c.volumes:
        lines += [f"## Volume {v.volume} (term {v.term}): {v.title_ar}", "", "### Learning objectives", ""]
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
            lines.append(f"| {p.n} | {p.week} | {label} | {p.skill}{mark} | `{p.type}` | {dots} |")
        lines.append("")
    words = picture_words(c)
    lines += [
        f"## Picture words ({len(words)}), for the educator's review",
        "",
        "، ".join(words) if words else "—",
        "",
    ]
    return "\n".join(lines)
