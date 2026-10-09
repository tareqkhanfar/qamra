"""«مغامراتي مع عائلتي» (Addendum 7): the family adventure book's plan, its rules and the proposal text.

The third product on the workbook engine. The unit is the *activity* (an adventure with a goal, a part the
child does alone and often a mission with a grown-up); an activity has one or more pages. The book runs:
front pages (title, «عائلتي», the adventurer's passport), then each adventure section (an opening spread,
its activities, a «ذكرى اليوم» memory page), then the back pages (the 7-day challenge, the certificate).
Page numbers are derived from that order, so the checker can see spreads, neighbours and the last page.

    uv run python -m qamra_workbook.family check    # rule problems (exit 1 when any) and page counts
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

# Addendum 7 §1: every activity maps to at least one of these
SKILLS: dict[str, str] = {
    "thinking": "الذكاء والتفكير",
    "observation": "الملاحظة والتركيز",
    "memory": "الذاكرة",
    "counting": "العدّ والحساب البسيط",
    "speaking": "التعبير والتحدّث",
    "emotions": "المشاعر والتواصل",
    "problem_solving": "حلّ المشكلات",
    "creativity": "الإبداع والخيال",
    "responsibility": "المسؤولية",
    "life_skills": "مهارات الحياة",
    "cooperation": "التعاون مع الأهل",
}
# Addendum 7 §6, plus the book's structural pages
PAGE_TYPES: dict[str, str] = {
    "scavenger-hunt": "treasure hunt: a checklist and drawing boxes",
    "shopping-list": "a shopping list to draw or write",
    "price-tags": "price tags to read, count and match with play money",
    "play-money": "fictional Qamra play money to cut out (card-stock insert)",
    "recipe-steps": "a recipe: picture cards to order, ingredients to count, the safety box",
    "routine-builder": "build my routine chart with stickers",
    "conversation-cards": "conversation cards and questions for child and grown-up",
    "picture-talk": "describe a picture, or tell a story from 3 pictures",
    "feelings-faces": "recognize feelings from faces",
    "feelings-thermometer": "how big is the feeling? (a thermometer)",
    "situation-feeling-match": "which feeling fits the situation?",
    "chore-chart": "a weekly chart of home tasks with reward stickers",
    "nature-bingo": "nature bingo outdoors",
    "observation-journal": "an observation journal: draw, rub, note",
    "interview-template": "interview a family member about their work",
    "role-cards": "role cards for play-acting (card-stock insert)",
    "family-game-cards": "game cards to cut out, with the family scoreboard",
    "story-finish": "finish the story, or find a solution",
    "memory-page": "«ذكرى اليوم»: photo slot, drawing, stars and a grown-up's quote",
    "seven-day-challenge": "a different family activity every day for 7 days",
    "passport": "the adventurer's passport: a stamp slot per badge",
    "badge-sticker-sheet": "the sticker sheet: passport badges, rewards, routine icons (insert)",
    "certificate-family": "the adventurer's certificate with the child and «عائلة {family_name}»",
    "section-opener": "the opening spread of an adventure (two facing pages)",
    "title-page": "title page with the child's character",
    "my-family": "«عائلتي»: the family members' names (and faces, with the add-on)",
    "toc": "table of contents",
    "drawing": "free drawing with a prompt",
    "counting": "count and compare what was found or bought",
    "sort-choose": "sort or choose (healthy / needed / not needed, before / after…)",
    "sequence-cards": "order picture cards (the day, a recipe, a story)",
    "puppets": "finger puppets to cut out (card-stock insert)",
    "cover-front": "the front cover: the child in the middle of the family",
    "cover-back": "the back cover: what is inside, for grown-ups",
    "recipe-cards": "the recipes' step picture cards to cut out and order (card-stock insert)",
    "memory-cards": "the memory game's picture pairs to cut out (card-stock insert)",
    "question-cards": "the family question cards to cut out (card-stock insert)",
}
# printed on the separate sticker and card-stock sheets, never as book pages (A7 §6)
INSERT_TYPES = (
    "play-money",
    "role-cards",
    "puppets",
    "badge-sticker-sheet",
    "recipe-cards",
    "memory-cards",
    "question-cards",
)
PLACEHOLDERS = {"child", "adult", "member", "family_name", "city"}
# Inclusive (A7 §9): a mission is done "with {adult}" or "with {member}", never assumed mother and father.
# Whole words, with an attached و/ف/ب/ل/ك/لل, so «أبيض» and «أميرة» are not caught.
ASSUMED_PARENTS = re.compile(r"(?<!\w)(?:[وفبلك]|لل)?(?:ماما|بابا|أمّك|أمك|أبوك|أبيك|والديك|أمي|أبي)(?!\w)")
NUTS_AND_RAW_EGGS = re.compile(
    r"(مكسّرات|مكسرات|جوز|لوز|فستق|بندق|كاجو|فول سوداني|زبدة الفول|بيض ني|بيض غير مطبوخ)"
)
_PLACEHOLDER = re.compile(r"\{([a-z_]+)(?::acc)?\}")  # `{adult:acc}`: the name in the accusative
_TASHKEEL = re.compile(r"[\u064B-\u0652\u0670]")  # the printed texts are vowelized; the checks match letters


def letters(text: str) -> str:
    """`text` without its tashkeel, so a rule written in plain letters still finds a vowelized word."""
    return _TASHKEEL.sub("", text)


_PAIR = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")  # {masc/fem}
# How the proposal shows a placeholder to its readers (the book fills in the family's own words)
SHOWN = {
    "child": "اسم الطفل",
    "adult": "الكبير المرافق",
    "member": "فرد من العائلة",
    "family_name": "اسم العائلة",
    "city": "المدينة",
}

MIN_PAGES, MAX_PAGES = 96, 128  # A7 §3.4
MAX_CHILD_WORDS = 10  # A7 §5
MIN_MINUTES, MAX_MINUTES = 5, 20  # A7 §3.3
MIN_SKILL_ACTIVITIES = 3
MIN_CHALLENGE_SHARE = 0.5  # "a challenge version where it makes sense"
SAMPLES_MIN, SAMPLES_MAX, SAMPLE_SECTIONS = 8, 10, 6  # book pages (a spread counts once); inserts extra

Where = Literal["home", "outside"]


class Page(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    instruction: str  # for the child, ≤ 10 words
    parent: list[str] = Field(default_factory=list)  # the «للأهل» box: 1–3 short lines
    params: dict[str, Any] = Field(default_factory=dict)


class Levels(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simple: str  # ⭐ ages 3–4
    challenge: str | None = None  # ⭐⭐ ages 5–7


class Activity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    section: str
    title: str
    goal: str
    skills: list[str]
    child_part: str
    parent_part: str | None = None
    together: bool = False  # «هيا نفعلها معًا! 👨‍👩‍👧»
    where: Where = "home"
    materials: list[str] = Field(default_factory=list)  # common household items only
    minutes: int
    levels: Levels
    safety: str | None = None  # required for recipes and outdoor activities
    pages: list[Page]


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title_ar: str
    icon: str
    hook: str  # the opening spread's short story
    badge: str  # the passport stamp this adventure earns


class Insert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["stickers", "card-stock"]
    title: str
    items: list[str]
    id: str = ""  # the print file's name (out/family-book/inserts/<id>-<size>.pdf)
    sheets: list[Page] = Field(default_factory=list)  # the printed sheets, each an insert-only page type


class SampleRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int  # a book page number, or 0 with `insert` for an insert sheet
    insert: str | None = None


class Proposal(BaseModel):
    """The proposal texts (A7 §3): the vision, and the size, paper and printing recommendations."""

    model_config = ConfigDict(extra="forbid")

    concept: str
    size: str
    paper: str
    binding: str


class FamilyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_ar: str
    title_en: str
    proposal: Proposal
    front: list[Page]  # title page, «عائلتي», passport, contents…
    sections: list[Section]  # in the book's order
    activities: list[Activity]  # grouped by section, in order
    back: list[Page]  # the 7-day challenge, the certificate
    cover: list[Page] = Field(default_factory=list)  # the front and back cover (card, printed apart)
    inserts: list[Insert]
    samples: list[SampleRef]


@dataclass(frozen=True)
class Placed:
    """A page with its number in the book, and the activity or section it belongs to."""

    n: int
    page: Page
    section: str  # "front", a section id, or "back"
    activity: Activity | None


def load(path: Path) -> FamilyPlan:
    return FamilyPlan.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def book_pages(plan: FamilyPlan) -> list[Placed]:
    """The book in page order: front, then per section the opening spread and its activities, then back."""
    pages = [Placed(0, p, "front", None) for p in plan.front]
    for section in plan.sections:
        opener = Page(type="section-opener", title=section.title_ar, instruction=section.hook)
        pages += [Placed(0, opener, section.id, None), Placed(0, opener, section.id, None)]
        for activity in (a for a in plan.activities if a.section == section.id):
            pages += [Placed(0, p, section.id, activity) for p in activity.pages]
    pages += [Placed(0, p, "back", None) for p in plan.back]
    return [Placed(i + 1, p.page, p.section, p.activity) for i, p in enumerate(pages)]


def _words(text: str) -> int:
    return len(_PLACEHOLDER.sub("x", text).split())


# ---- rules ------------------------------------------------------------------------------------------------


def check_pages(plan: FamilyPlan, pages: list[Placed]) -> list[str]:
    out = []
    n = len(pages)
    if not MIN_PAGES <= n <= MAX_PAGES:
        out.append(f"{n} pages; the book has {MIN_PAGES}–{MAX_PAGES}")
    if n % 2:
        out.append(f"{n} pages; printed sheets need an even count")
    for p in pages:
        if p.page.type not in PAGE_TYPES:
            out.append(f"p{p.n}: unknown page type {p.page.type!r}")
        if p.page.type in INSERT_TYPES:
            out.append(f"p{p.n}: {p.page.type} belongs on an insert sheet, not in the book")
        words = _words(p.page.instruction)
        if p.page.type not in ("section-opener", "toc") and not 1 <= words <= MAX_CHILD_WORDS:
            out.append(f"p{p.n}: the child's instruction has {words} words (1–{MAX_CHILD_WORDS})")
        if len(p.page.parent) > 3:
            out.append(f"p{p.n}: the parent box has {len(p.page.parent)} lines (max 3)")
        for text in (p.page.title, p.page.instruction, *p.page.parent):
            unknown = set(_PLACEHOLDER.findall(text)) - PLACEHOLDERS
            if unknown:
                out.append(f"p{p.n}: unknown placeholders {sorted(unknown)}")
            if ASSUMED_PARENTS.search(letters(text)):
                out.append(f"p{p.n}: write {{adult}} or {{member}}, not a fixed mother or father: {text!r}")
    return out


def check_structure(plan: FamilyPlan, pages: list[Placed]) -> list[str]:
    out = []
    ids = [s.id for s in plan.sections]
    if len(ids) != len(set(ids)):
        out.append("section ids repeat")
    for a in plan.activities:
        if a.section not in ids:
            out.append(f"activity {a.id}: unknown section {a.section!r}")
    order = [a.section for a in plan.activities]
    grouped = [s for i, s in enumerate(order) if i == 0 or s != order[i - 1]]
    if grouped != [s for s in ids if s in set(order)]:
        out.append("activities must be grouped by section, in the sections' order")
    for s in plan.sections:
        mine = [p for p in pages if p.section == s.id]
        if not mine:
            continue
        if mine[0].n % 2:
            out.append(f"{s.id}: the opening spread starts on p{mine[0].n}; a spread starts on an even page")
        if mine[-1].page.type != "memory-page":
            out.append(f"{s.id}: an adventure ends with its «ذكرى اليوم» memory page")
    front = [p.n for p in pages if p.page.type == "passport"]
    if not front or min(front) > 8:
        out.append("the passport sits at the front (within the first 8 pages)")
    if not pages or pages[-1].page.type != "certificate-family":
        out.append("the book ends with the family certificate")
    if "seven-day-challenge" not in {p.page.type for p in pages if p.section == "back"}:
        out.append("the 7-day family challenge belongs in the back pages")
    return out


def check_variety(pages: list[Placed]) -> list[str]:
    """A7 §11: no identical page type on consecutive pages (the two halves of an opening spread aside)."""
    out = []
    for a, b in pairwise(pages):
        if a.page.type == b.page.type and a.page.type != "section-opener":
            out.append(f"p{b.n}: {b.page.type} again right after p{a.n}")
    return out


def check_activities(plan: FamilyPlan) -> list[str]:
    out = []
    for a in plan.activities:
        tag = f"activity {a.id}"
        if not a.skills or any(s not in SKILLS for s in a.skills):
            out.append(f"{tag}: skills must come from {sorted(SKILLS)}")
        if not MIN_MINUTES <= a.minutes <= MAX_MINUTES:
            out.append(f"{tag}: {a.minutes} minutes ({MIN_MINUTES}–{MAX_MINUTES})")
        if not a.pages:
            out.append(f"{tag}: no pages")
        if a.together and not (a.parent_part and any(p.parent for p in a.pages)):
            out.append(f"{tag}: a «هيا نفعلها معًا!» mission needs a parent part and a parent box")
        recipe = any(p.type == "recipe-steps" for p in a.pages)
        if (recipe or a.where == "outside") and not (a.safety or "").strip():
            out.append(f"{tag}: {'recipes' if recipe else 'outdoor activities'} need a safety note")
        if recipe:
            if "حساسي" not in letters(a.safety or ""):
                out.append(f"{tag}: every recipe reminds grown-ups to ask about allergies")
            ingredients = " ".join(str(x) for p in a.pages for x in p.params.get("ingredients", []))
            if NUTS_AND_RAW_EGGS.search(letters(ingredients + " " + " ".join(a.materials))):
                out.append(f"{tag}: no nuts or raw eggs by default (A7 §9)")
    counts = Counter(s for a in plan.activities for s in set(a.skills))
    thin = [s for s in SKILLS if counts[s] < MIN_SKILL_ACTIVITIES]
    if thin:
        out.append(f"skills with fewer than {MIN_SKILL_ACTIVITIES} activities: {thin}")
    if plan.activities:
        share = sum(a.levels.challenge is not None for a in plan.activities) / len(plan.activities)
        if share < MIN_CHALLENGE_SHARE:
            out.append(f"only {share:.0%} of activities have a ⭐⭐ challenge version")
    return out


def check_samples(plan: FamilyPlan, pages: list[Placed]) -> list[str]:
    out = []
    by_n = {p.n: p for p in pages}
    inserts = {i.title for i in plan.inserts}
    book_refs = [r for r in plan.samples if r.insert is None]
    if not SAMPLES_MIN <= len(book_refs) <= SAMPLES_MAX:
        out.append(f"{len(book_refs)} sample pages; the proposal shows {SAMPLES_MIN}–{SAMPLES_MAX}")
    missing = [r.n for r in book_refs if r.n not in by_n] + [
        r.insert for r in plan.samples if r.insert and r.insert not in inserts
    ]
    if missing:
        out.append(f"samples point at missing pages or inserts: {missing}")
    sections = {by_n[r.n].section for r in book_refs if r.n in by_n}
    if len(sections) < SAMPLE_SECTIONS:
        out.append(f"samples cover {len(sections)} parts of the book; show at least {SAMPLE_SECTIONS}")
    kinds = Counter(i.kind for i in plan.inserts)
    if not kinds["stickers"] or not kinds["card-stock"]:
        out.append("the kit has a sticker sheet and at least one card-stock sheet")
    return out


def check_inserts(plan: FamilyPlan) -> list[str]:
    """The insert sheets are printed on their own paper: only insert page types, the stickers on the
    sticker sheet and the cut-outs on card stock."""
    out = []
    for insert in plan.inserts:
        for sheet in insert.sheets:
            if sheet.type not in INSERT_TYPES:
                out.append(f"insert «{insert.title}»: {sheet.type} is a book page, not an insert sheet")
            stickers = sheet.type == "badge-sticker-sheet"
            if stickers != (insert.kind == "stickers"):
                out.append(f"insert «{insert.title}»: {sheet.type} does not print on {insert.kind}")
            for text in (sheet.title, sheet.instruction):
                if ASSUMED_PARENTS.search(letters(text)):
                    out.append(f"insert «{insert.title}»: write {{adult}}, not a fixed mother or father")
    return out


def problems(plan: FamilyPlan) -> list[str]:
    pages = book_pages(plan)
    return (
        check_pages(plan, pages)
        + check_structure(plan, pages)
        + check_variety(pages)
        + check_activities(plan)
        + check_samples(plan, pages)
        + check_inserts(plan)
    )


# ---- the proposal (A7 §3) ---------------------------------------------------------------------------------


def shown(text: object) -> str:
    """A plan text for readers of the proposal: «اسم الطفل» for {child}, «أ/ب» for a {masc/fem} pair."""
    out = _PAIR.sub(lambda m: f"{m.group(1)}/{m.group(2)}", str(text))
    return _PLACEHOLDER.sub(lambda m: f"«{SHOWN.get(m.group(1), m.group(1))}»", out)


def e(text: object) -> str:
    return shown(text).replace("|", "\\|").replace("\n", " ")


def render_markdown(plan: FamilyPlan, source: str, price_table: list[dict[str, str]] | None = None) -> str:
    pages = book_pages(plan)
    titles = {s.id: f"{s.icon} {shown(s.title_ar)}" for s in plan.sections} | {
        "front": "الصفحات الأولى",
        "back": "الختام",
    }
    order = ["front", *[s.id for s in plan.sections], "back"]
    count = Counter(p.section for p in pages)
    lines = [
        f"# {plan.title_ar} — {plan.title_en}",
        "",
        f"Proposal package (Addendum 7 §3). Generated from `{source}`; edit the YAML, not this file.",
        "",
        "## 1. The concept",
        "",
        plan.proposal.concept.strip(),
        "",
        "## 2. Table of contents",
        "",
        "| # | Part | Pages | Passport stamp |",
        "|---|---|---|---|",
    ]
    for i, sid in enumerate(order, 1):
        ns = [p.n for p in pages if p.section == sid]
        if not ns:
            continue
        badge = next((s.badge for s in plan.sections if s.id == sid), "")
        lines.append(f"| {i} | {titles[sid]} | {min(ns)}–{max(ns)} | {e(badge)} |")
    lines += ["", "## 3. Sections and activities", ""]
    for s in plan.sections:
        lines += [f"### {s.icon} {shown(s.title_ar)}", "", f"*{e(s.hook)}*", ""]
        lines += [
            "| Activity | Goal | The child | With the family | Materials | Time | Level | Skills |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for a in (a for a in plan.activities if a.section == s.id):
            level = "⭐" + (" / ⭐⭐" if a.levels.challenge else "")
            where = "🌳" if a.where == "outside" else "🏠"
            together = " 👨‍👩‍👧" if a.together else ""
            skills = "، ".join(SKILLS[k] for k in a.skills if k in SKILLS)
            lines.append(
                f"| {where}{together} {e(a.title)} | {e(a.goal)} | {e(a.child_part)} "
                f"| {e(a.parent_part or '—')} | {e('، '.join(a.materials) or '—')} | {a.minutes} د "
                f"| {level} | {e(skills)} |"
            )
        lines.append("")
    lines += ["## 4. Page count", "", "| Part | Pages |", "|---|---|"]
    lines += [f"| {titles[sid]} | {count[sid]} |" for sid in order if count[sid]]
    lines += [f"| **Book** | **{len(pages)}** |", ""]
    for sheet in plan.inserts:
        kind = "sticker sheet" if sheet.kind == "stickers" else "card stock"
        lines.append(f"- **{e(sheet.title)}** ({kind}): {e('، '.join(sheet.items))}")
    lines += ["", "## 5. Sample pages", ""]
    by_n = {p.n: p for p in pages}
    for r in plan.samples:
        if r.insert:
            lines.append(f"- insert: {e(r.insert)}")
        elif r.n in by_n:
            p = by_n[r.n]
            lines.append(
                f"- page {r.n}: {titles.get(p.section, p.section)} — {e(p.page.title)} (`{p.page.type}`)"
            )
    lines += [
        "",
        "## 6. Book size",
        "",
        plan.proposal.size.strip(),
        "",
        "## 7. Paper",
        "",
        plan.proposal.paper.strip(),
    ]
    lines += [
        "",
        "## 8. Binding and printing",
        "",
        plan.proposal.binding.strip(),
        "",
        "## 9. Price by quantity",
        "",
    ]
    if price_table:
        head = list(price_table[0])
        lines += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(str(row[h]) for h in head) + " |" for row in price_table]
    else:
        lines.append(
            "_The price table is added by `scripts/family_proposal.py` from the printer's cost tiers._"
        )
    lines.append("")
    return "\n".join(lines)


PLAN = Path("content/family-book/plan.yaml")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["check"]:
        print(__doc__)
        return 2
    plan = load(PLAN)
    pages = book_pages(plan)
    found = problems(plan)
    print(f"{len(pages)} pages, {len(plan.activities)} activities, {dict(Counter(p.section for p in pages))}")
    for line in found:
        print("✗", line)
    print(f"{len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
