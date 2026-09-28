"""«رحلتي الأولى للتعلّم» (Addendum 6): the journey plan, its rules and the readable plan.

The second product on the workbook engine. It shares the page-type library and letter data with the
«دوسية التأسيس» curriculum (`qamra_workbook.curriculum`) and adds the Addendum 6 page types. A stage walks the
journey map in order: every section is one block that opens on the map and ends with «ماذا تعلمت؟».

    uv run python -m qamra_workbook.journey check    # rule problems (exit 1 when any) and page counts
    uv run python -m qamra_workbook.journey render   # also writes docs/journey/plan.md
"""

from __future__ import annotations

import sys
from collections import Counter
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
    "quantity-first": "how many? quantities before numerals (params: numbers)",
    "number-before-after": "the number before and after",
    "same-amount": "find groups with the same amount",
    "near-far": "near and far",
    "listen-and-choose": "listen (QR) and choose the picture (params: words)",
    "loud-soft": "loud or soft sounds (QR)",
    "fast-slow": "fast or slow sounds (QR)",
    "first-sound": "the first sound of a word (QR) (params: letter, words)",
    "finger-trace": "trace a big solid path with a finger, following the arrows (params: letter or shape)",
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
LETTER_STEPS = ("letter-intro", "finger-trace", "letter-trace", "letter-write", "find-letter")
NUMERAL_TYPES = ("number-intro", "number-trace", "number-write")
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
        if p.type in AUDIO_TYPES and p.section != "intro" and not p.audio:
            out.append(f"{tag} p{p.n}: {p.type} pages carry an audio QR (audio: true)")
        unknown = [g for g in p.goals if g not in GOALS]
        if unknown:
            out.append(f"{tag} p{p.n}: unknown goals {unknown}")
    return out


def check_sections(s: Stage, sections: list[Section]) -> list[str]:
    """Each section is one block, in journey order; it opens on the map and ends with «ماذا تعلمت؟»."""
    tag, order = f"S{s.stage}", [x.id for x in sections]
    out = []
    blocks: list[tuple[str, list[JourneyPage]]] = []
    for p in s.pages:
        if blocks and blocks[-1][0] == p.section:
            blocks[-1][1].append(p)
        else:
            blocks.append((p.section, [p]))
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
    for i, (sid, pages) in enumerate(blocks):
        if sid == "intro":
            continue
        if pages[0].type != "section-opener":
            out.append(f"{tag} p{pages[0].n}: section {sid} starts with a section-opener")
        last_block = i == len(blocks) - 1
        want = ("certificate", "mini-certificate") if last_block else ("what-i-learned",)
        if pages[-1].type not in want:
            out.append(f"{tag} p{pages[-1].n}: section {sid} must end with {' or '.join(want)}")
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
        letters = [p.n for p in s.pages if p.type.startswith("letter-") or p.type == "en-letter"]
        if letters:
            out.append(f"{tag}: no letters in stage 1 (pages {letters[:5]})")
        if "number-write" in types:
            out.append(f"{tag}: no number writing in stage 1")
        big = [p.n for p in s.pages if any(x > 5 for x in _numbers(p.params))]
        if big:
            out.append(f"{tag}: stage 1 stays within quantities 1–5 (pages {big[:5]})")
    for p in s.pages:
        if p.type == "write-progression":
            level = int(p.params.get("level", 0))
            if not 1 <= level <= MAX_WRITING_LEVEL[s.stage]:
                out.append(f"{tag} p{p.n}: writing level {level} is past stage {s.stage}'s limit")
    if s.stage in (2, 3):
        scripts = {str(p.params.get("script")) for p in s.pages if p.type == "name-trace"}
        if not {"ar", "en"} <= scripts:
            out.append(f"{tag}: name tracing in Arabic and English (name-trace, params.script)")
    named = [p for p in s.pages if "{child}" in p.title or "{child}" in p.instruction]
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


def check_letters(j: Journey) -> list[str]:
    out = []
    intros = [
        (s.stage, norm_letter(str(p.params.get("letter", ""))))
        for s in j.stages
        for p in s.pages
        if p.type == "letter-intro"
    ]
    order = [norm_letter(x) for x in j.letter_order]
    if [x for _, x in intros] != order or len(set(order)) != 28:
        found = "".join(x for _, x in intros)
        out.append(f"letter-intro pages must introduce all 28 letters once, in letter_order; found {found}")
    for s in j.stages:
        for letter in {x for st, x in intros if st == s.stage}:
            firsts: list[int | None] = []
            for step in LETTER_STEPS:
                hits = [
                    p.n
                    for p in s.pages
                    if p.type == step
                    and letter in {norm_letter(str(x)) for x in _values(p.params, "letter", "letters")}
                ]
                firsts.append(min(hits) if hits else None)
            missing = [t for t, n in zip(LETTER_STEPS, firsts, strict=True) if n is None]
            if missing:
                out.append(f"S{s.stage} letter {letter}: missing {', '.join(missing)}")
            elif firsts != sorted(n for n in firsts if n is not None):
                out.append(f"S{s.stage} letter {letter}: steps out of order")
    english = [
        str(p.params.get("letter", "")).upper() for s in j.stages for p in s.pages if p.type == "en-letter"
    ]
    if tuple(english) != ENGLISH_LETTERS:
        out.append(f"en-letter pages must cover A–Z once, in order; found {''.join(english)}")
    return out


def check_numbers(j: Journey) -> list[str]:
    """§4.7: quantity before numerals, for every number 1–10."""
    out, pages = [], [(s.stage, p) for s in j.stages for p in s.pages]
    for number in range(1, 11):
        quantity = [
            i for i, (_, p) in enumerate(pages) if p.type == "quantity-first" and number in _numbers(p.params)
        ]
        numeral = [
            i for i, (_, p) in enumerate(pages) if p.type in NUMERAL_TYPES and number in _numbers(p.params)
        ]
        if not quantity:
            out.append(f"number {number}: needs a quantity-first page")
        if not numeral:
            out.append(f"number {number}: needs numeral pages (number-intro / trace / write)")
        elif quantity and min(quantity) > min(numeral):
            out.append(f"number {number}: the numeral comes before its quantity page")
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
    out += check_book(j)
    if len(j.stages) == 3:
        out += check_letters(j) + check_numbers(j) + check_writing(j)
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
