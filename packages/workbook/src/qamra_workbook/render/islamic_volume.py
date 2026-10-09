"""Render a whole volume of «قلبي يعرف الله» (Addendum 10) from its plan and its content file.

    uv run python -m qamra_workbook.render.islamic_volume --volume v1 --check   # what is missing or wrong
    uv run python -m qamra_workbook.render.islamic_volume --volume v1 --keys    # the places and their keys
    uv run python -m qamra_workbook.render.islamic_volume --vocab               # what a page may draw
    uv run python -m qamra_workbook.render.islamic_volume --volume v1 [--size 21x28|a4] [--print]
        [--name ليان --gender f] [--only u-allah/,end/] [--out DIR]

The plan (`qamra_workbook.islamic.place`) gives the volume's pages in order, the automatic ones included
(front pages, unit openers, closings, parent pages, cumulative reviews, the final pages). The content of each
page is an entry of `content/islamic/pages/<volume>.yaml` (the same schema as the samples' pages) with a `key`
that names its place:

    front/<k>            the k-th front page          <unit>/opener       the unit's first page
    <unit>/l<i>-<j>      lesson i of the unit (from 1), its j-th page (from 1), as volumes/<v>.yaml lists them
    <unit>/closing-<k>   its two closing pages        <unit>/parent       its parent page
    <unit>/review-<k>    the k-th cumulative review page after the unit
    end/<k>              the k-th final page

The engine derives each page's `id` (`v1-u-allah-l1-1`), its `unit`, its `volume` and, when the entry has
none, its `title` (the lesson's title, the unit's title, or the type's default). An entry may fill a place
whose plan type it suits (`FILLS`). docs/islamic/content-guide.md is the writers' guide.

A preview build prints a clearly marked placeholder page for content not yet written and a marked placeholder
for a source with no verified text; `--print` refuses (and writes nothing) while any page is missing, any
check fails, or any source the volume uses is not `scholar_approved`. Writes interior.pdf, cover.pdf,
answer-key.pdf, preflight.json, png/ and contact-sheet.png. The order job awaits `render_volume`."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from qamra_pdf import preflight
from qamra_workbook import islamic
from qamra_workbook import islamic_checks as checks
from qamra_workbook.islamic_checks import Problem
from qamra_workbook.islamic_sources import REPO, Resolver, SourceError
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render import covers
from qamra_workbook.render.engine import (
    PageProblems,
    RenderedPage,
    answer_key_html,
    book_html,
    build_pages,
    contact_sheet,
    previews,
    print_pdf,
)
from qamra_workbook.render.islamic_content import (
    AnyPage,
    IslamicContext,
    Missing,
    Page,
    page_spec,
    parse_page,
)
from qamra_workbook.render.islamic_figures import SAMPLE_SHEET, kit_for
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import assets_for
from qamra_workbook.render.spec import BookSpec, Child, Geometry, Numerals, PageSpec, product_geometry

PAGES_DIR = REPO / "content/islamic/pages"
# the scholar's approvals (qamra_core.islamic_review.build_export): the worker writes the export next to every
# render and points this variable at it; `qamra islamic-review-export` writes REVIEW_FILE for local renders
REVIEW_ENV = "QAMRA_ISLAMIC_REVIEW_FILE"
REVIEW_FILE = REPO / "content/islamic/review-status.json"
OUT = Path("out/islamic")
SIZES = ("21x28", "a4")
SERIES_AR = "قلبي يعرف الله"
CHILDREN = {"f": "ليان", "m": "يوسف"}
SAMPLE_DATE = dt.date(2026, 10, 1)

# the plan's page type → the content types that may fill a place of that type
FILLS: dict[str, tuple[str, ...]] = {
    "unit-opener": ("unit-opener",),
    "story": ("story",),
    "prophet-story": ("prophet-story",),
    "sira-story": ("sira-story",),
    "pillar-card": ("pillar-card",),
    "coloring": ("coloring",),
    "maze": ("maze",),
    "find-objects": ("find-objects", "blessings-hunt"),
    "blessings-hunt": ("blessings-hunt", "find-objects"),
    "order-steps": ("order-steps", "prayer-steps"),
    "match": ("match",),
    "draw": ("draw",),
    "cut-paste": ("cut-paste",),
    "surah": ("surah",),
    "true-false": ("true-false",),
    "choose": ("choose",),
    "quiz": ("quiz", "self-test"),
    "dhikr": ("dhikr",),
    "wwyd": ("wwyd",),
    "wdif": ("wdif",),
    "role-play": ("role-play",),
    "day": ("day", "my-day-with-allah"),
    "unit-review": ("unit-review",),
    "self-test": ("self-test", "quiz", "unit-review"),
    "unit-closing": ("unit-closing",),
    "parent-guide": ("parent-guide",),
    "home-challenge": ("home-challenge",),
    "passport": ("passport",),
    "front": (
        "front-title",
        "front-characters",
        "front-how-to-use",
        "front-this-is-me",
        "passport",
        "back-page",
    ),
    "assessment": ("assessment", "final-assessment"),
    "certificate": ("certificate",),
}
# a page's title when its entry gives none: {unit} and {volume} are the unit's and the volume's titles
DEFAULT_TITLES: dict[str, str] = {
    "unit-opener": "{unit}",
    "front-title": "{volume}",
    "unit-closing": "خِتَامُ الْوَحْدَةِ",
    "parent-guide": "لِلْأَهْلِ: {unit}",
    "self-test": "{اخْتَبِرْ نَفْسَكَ/اخْتَبِرِي نَفْسَكِ}",
    "quiz": "{اخْتَبِرْ نَفْسَكَ/اخْتَبِرِي نَفْسَكِ}",
    "unit-review": "مَاذَا أَتَذَكَّرُ؟",
    "assessment": "مَاذَا تَعَلَّمْتُ فِي رِحْلَتِي؟",
    "final-assessment": "مَاذَا تَعَلَّمْتُ فِي رِحْلَتِي؟",
    "passport": "{جَوَازُ الْمُسْلِمِ الصَّغِيرِ/جَوَازُ الْمُسْلِمَةِ الصَّغِيرَةِ}",
    "certificate": "{شَهَادَةُ الْمُسْلِمِ الصَّغِيرِ/شَهَادَةُ الْمُسْلِمَةِ الصَّغِيرَةِ}",
    "front-characters": "أَصْدِقَائِي فِي الرِّحْلَةِ",
    "front-how-to-use": "كَيْفَ نَسْتَعْمِلُ هَذَا الْكِتَابَ؟",
    "front-this-is-me": "هَذَا أَنَا",
    "back-page": "إِلَى اللِّقَاءِ",
    "home-challenge": "تَحَدِّي الْأُسْبُوعِ",
}
# The most words a child-facing field may hold (counted on the text as printed, for both genders): what the
# layouts hold at their normal size. Per type overrides first, then the field's general limit.
WORD_LIMITS: dict[str, int] = {
    "title": 8,
    "instruction": 7,
    "tracker": 7,
    "stars": 7,
    "role_play": 7,
    "draw_box": 7,
    "t": 16,
    "text": 24,
    "scenario": 24,
    "intro": 26,
    "feedback": 12,
    "word": 3,
    "when": 6,
    "question": 18,
    "prompt": 16,
    "challenge": 24,
    "message": 30,
    "apply": 14,
    "apply_choices": 8,
    "learned": 14,
    "dhikr_when": 10,
    "subtitle": 10,
    "home": 22,
    "tip": 30,
    "care_note": 40,
    "parent_line": 24,
    "skill": 4,
    "steps": 12,
    "prompts": 6,
    "boxes": 4,
    "slots": 4,
    "role": 4,
    "by": 4,
    "next": 20,
    "goal_word": 3,
    "pillar": 4,
    "reward": 10,
    "note": 24,
    "label": 6,
    "lesson_title": 10,
}
TYPE_WORD_LIMITS: dict[str, dict[str, int]] = {
    "parent-guide": {"text": 42, "ask": 20, "together": 34, "care_note": 40},
    "front-how-to-use": {"t": 18},
    "front-characters": {"t": 18},
    "unit-opener": {"t": 20},
}
LIST_FIELDS = frozenset({"learned", "apply_choices", "steps", "prompts", "boxes", "slots"})


@dataclass(frozen=True)
class Slot:
    """A place in the volume: its key and the plan's page (number, type, unit, lesson, concepts, sources)."""

    key: str
    page: islamic.Page

    @property
    def fills(self) -> tuple[str, ...]:
        return FILLS.get(self.page.type, (self.page.type,))


def page_id(volume: str, key: str) -> str:
    return f"{volume.lower()}-{key.replace('/', '-')}"


def volume_id(name: str) -> str:
    """`v1`, `V1` → `V1`; `r` → `R`."""
    return name.strip().upper()


def slots(plan: islamic.Plan, volume: str) -> list[Slot]:
    """The volume's places in book order, with their keys."""
    counts: Counter[tuple[str, ...]] = Counter()
    out: list[Slot] = []
    for p in plan.pages[volume]:
        unit = p.unit or ""
        match p.kind:
            case "front":
                counts["front",] += 1
                key = f"front/{counts['front',]}"
            case "opener":
                key = f"{unit}/opener"
            case "lesson":
                counts[unit, str(p.lesson)] += 1
                key = f"{unit}/l{p.lesson}-{counts[unit, str(p.lesson)]}"
            case "closing":
                counts[unit, "closing"] += 1
                key = f"{unit}/closing-{counts[unit, 'closing']}"
            case "parent":
                key = f"{unit}/parent"
            case "cumulative":
                counts[unit, "review"] += 1
                key = f"{unit}/review-{counts[unit, 'review']}"
            case _:
                counts["end",] += 1
                key = f"end/{counts['end',]}"
        out.append(Slot(key, p))
    return out


def default_title(plan: islamic.Plan, volume: str, slot: Slot, content_type: str) -> str:
    p = slot.page
    if p.kind == "lesson":
        return p.title
    unit = plan.units[p.unit]["title_ar"] if p.unit else ""
    template = DEFAULT_TITLES.get(content_type, "")
    return template.replace("{unit}", unit).replace("{volume}", plan.volumes[volume]["title_ar"])


# ---- the content file -----------------------------------------------------------------------------------


def content_path(volume: str, root: Path = PAGES_DIR) -> Path:
    return root / f"{volume.lower()}.yaml"


def read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pages = raw.get("pages") or []
    if not isinstance(pages, list) or not all(isinstance(p, dict) for p in pages):
        raise ValueError(f"{path}: `pages` must be a list of page entries")
    return [dict(p) for p in pages]


@dataclass
class VolumeContent:
    """A volume's places, the content that fills them, and everything wrong with it."""

    volume: str
    slots: list[Slot]
    raw: dict[str, dict[str, Any]] = field(default_factory=dict)  # key → the entry with the derived fields
    pages: dict[str, Page] = field(default_factory=dict)  # key → its valid model
    problems: list[Problem] = field(default_factory=list)

    @property
    def missing(self) -> list[Slot]:
        return [s for s in self.slots if s.key not in self.pages]

    @property
    def written(self) -> list[Slot]:
        return [s for s in self.slots if s.key in self.raw]

    @property
    def errors(self) -> list[Problem]:
        return checks.errors(self.problems)


def _suggest(key: str, known: Iterable[str]) -> str:
    same_unit = [k for k in known if k.split("/")[0] == key.split("/")[0]]
    return f" (this unit's places: {', '.join(same_unit[:12])})" if same_unit else ""


def match_content(
    plan: islamic.Plan, volume: str, entries: Sequence[Mapping[str, Any]]
) -> tuple[VolumeContent, dict[str, Slot]]:
    """The entries matched to the volume's places: derived fields filled in, each parsed with its model."""
    places = slots(plan, volume)
    by_key = {s.key: s for s in places}
    out = VolumeContent(volume, places)
    for i, entry in enumerate(entries, start=1):
        key = str(entry.get("key", ""))
        where = key or f"entry {i}"
        if not key:
            out.problems.append(
                Problem("no-key", where, "every entry needs a `key` (its place in the volume)")
            )
            continue
        slot = by_key.get(key)
        if slot is None:
            out.problems.append(
                Problem("unknown-key", key, f"no place {key!r} in {volume}{_suggest(key, by_key)}")
            )
            continue
        if key in out.raw:
            out.problems.append(Problem("duplicate-key", key, "two entries for the same place"))
            continue
        ctype = str(entry.get("type", ""))
        if ctype not in slot.fills:
            out.problems.append(
                Problem(
                    "wrong-type",
                    key,
                    f"place {key} is a {slot.page.type!r} page: its content type is one of "
                    f"{list(slot.fills)}, "
                    f"not {ctype!r}",
                )
            )
            continue
        if "id" in entry:
            out.problems.append(Problem("id", key, "do not write `id`: the engine derives it from the key"))
            continue
        unit = slot.page.unit or ""
        if entry.get("unit") not in (None, "", unit):
            out.problems.append(
                Problem("unit", key, f"`unit` is {entry.get('unit')!r}, the place is in {unit!r}")
            )
            continue
        raw = {
            **entry,
            "id": page_id(volume, key),
            "unit": unit,
            "volume": volume,
            "title": entry.get("title") or default_title(plan, volume, slot, ctype),
        }
        if not raw["title"]:
            out.problems.append(Problem("no-title", key, f"a {ctype!r} page needs a `title`"))
            continue
        out.raw[key] = raw
        try:
            out.pages[key] = parse_page(raw)
        except ValueError as err:
            out.problems.append(Problem("invalid", key, str(err).split(": ", 1)[-1]))
    return out, by_key


# ---- the checks on the written pages --------------------------------------------------------------------

_LEFTOVER = re.compile(r"\{(?!src:)[^{}]*\}")
_WORD = re.compile(r"\S+")


def _limit(ptype: str, name: str) -> int | None:
    return TYPE_WORD_LIMITS.get(ptype, {}).get(name, WORD_LIMITS.get(name))


def text_problems(key: str, raw: Mapping[str, Any]) -> list[Problem]:
    """Word limits and personalization of every child-facing text, for a boy and for a girl."""
    out: list[Problem] = []
    ptype = str(raw.get("type", ""))
    for path, name, text in checks._strings(raw):
        if name in checks.NOT_PROSE or name in ("type", "lang"):
            continue
        for gender in ("m", "f"):
            shown = Child("ريم", gender).personalize(checks.TOKEN.sub("ذكر", text))
            left = _LEFTOVER.findall(shown) or [c for c in "{}" if c in shown]
            if left:
                out.append(Problem("placeholder", key, f"{path}: unresolved {left} in {text!r}"))
                break
            limit = _limit(ptype, name)
            words = len(_WORD.findall(shown))
            if limit is not None and words > limit:
                out.append(Problem("too-long", key, f"{path}: {words} words (max {limit}): {text}"))
                break
    return out


_CLOSING_PARTS = {
    "learned": "«ماذا تعلّمت؟»",
    "apply": "«ماذا سأطبّق؟»",
    "dhikr": "ذكر الوحدة",
    "challenge": "التحدّي",
}


def closing_problems(content: VolumeContent) -> list[Problem]:
    """The two closing pages of a unit carry the four endings between them (Addendum 10 §5)."""
    by_unit: dict[str, list[str]] = defaultdict(list)
    for slot in content.slots:
        if slot.page.kind == "closing":
            by_unit[slot.page.unit or ""].append(slot.key)
    out = []
    for unit, keys in by_unit.items():
        if not all(k in content.raw for k in keys):
            continue  # judged once both are written
        have = {part for k in keys for part in _CLOSING_PARTS if content.raw[k].get(part)}
        lacking = [label for part, label in _CLOSING_PARTS.items() if part not in have]
        if lacking:
            out.append(
                Problem("closing", f"{unit}/closing", f"the unit's closing pages lack {', '.join(lacking)}")
            )
    return out


def planned_source_warnings(content: VolumeContent) -> list[Problem]:
    """A page citing a source its lesson does not plan (volumes/<v>.yaml `s`) is worth a look."""
    out = []
    for slot in content.written:
        planned = set(slot.page.sources)
        if slot.page.kind != "lesson" or not planned:
            continue
        cited = set(checks.page_ids(content.raw[slot.key]))
        extra = sorted(cited - planned)
        if extra:
            out.append(
                Problem(
                    "unplanned-source",
                    slot.key,
                    f"cites {extra}, not planned for this lesson ({', '.join(sorted(planned))})",
                    "warning",
                )
            )
    return out


# a prophets' unit's picture pages show places, nature and objects only, like its stories (A10 §3.5)
PICTURE_PAGES = frozenset({"coloring", "maze", "find-objects", "cut-paste", "draw"})


def prophets_units(plan: islamic.Plan, volume: str) -> set[str]:
    """The units that tell a prophet's story or the Prophet's ﷺ life (a lesson with such a page)."""
    return {
        unit["id"]
        for unit in plan.volumes[volume]["units"]
        if any(t in ("prophet-story", "sira-story") for les in unit["lessons"] for t in les["p"])
    }


def volume_extra(plan: islamic.Plan, volume: str, slot: Slot) -> dict[str, Any]:
    """What a page of the volume knows besides its content: the volume and, for an opener, its lessons."""
    v = plan.volumes[volume]
    extra: dict[str, Any] = {
        "volume_info": {
            "id": volume,
            "title": v["title_ar"],
            "level": v.get("level"),
            "age": list(v.get("age", [])),
            "goal": v.get("goal", ""),
            "units": [u["id"] for u in v["units"]],
        },
        "key": slot.key,
    }
    if slot.page.kind == "opener" and slot.page.unit:
        unit = next(u for u in v["units"] if u["id"] == slot.page.unit)
        extra["lessons"] = [les["t"] for les in unit["lessons"]]
    return extra


def missing_page(volume: str, slot: Slot) -> Missing:
    p = slot.page
    return Missing(
        id=page_id(volume, slot.key),
        title=p.title or slot.key,
        key=slot.key,
        unit=p.unit or "",
        volume=volume,
        type="missing",
        planned=p.type,
        lesson_title=p.title,
        concepts=list(p.concepts),
        sources=list(p.sources),
    )


def volume_specs(
    plan: islamic.Plan, content: VolumeContent, context: IslamicContext, only: set[str] | None = None
) -> list[PageSpec]:
    """Every place as an engine page: its content, or (preview) the marked placeholder page."""
    specs = []
    for slot in content.slots:
        if only is not None and not any(slot.key == o or slot.key.startswith(o) for o in only):
            continue
        page: AnyPage = content.pages.get(slot.key) or missing_page(content.volume, slot)
        specs.append(page_spec(page, slot.page.n, context, volume_extra(plan, content.volume, slot)))
    return specs


def volume_book(
    plan: islamic.Plan,
    content: VolumeContent,
    context: IslamicContext,
    child: Child,
    *,
    size: str = "21x28",
    numerals: Numerals = "hindi",
    only: set[str] | None = None,
) -> BookSpec:
    return BookSpec(
        product="islamic",
        title_ar=SERIES_AR,
        child=child,
        pages=tuple(volume_specs(plan, content, context, only)),
        date=context.date,
        numerals=numerals,
        geometry=product_geometry("family", size),
    )


def cover_book(
    plan: islamic.Plan,
    volume: str,
    context: IslamicContext,
    book: BookSpec,
    art: Path | None = None,
    *,
    pages: int | None = None,
) -> BookSpec:
    """The perfect-bound cover (on card, no page numbers): one wrap [front | spine | back] whose spine fits
    `pages` interior pages (default: the book's). `art` is kept for older callers: the scene now comes from
    `render.covers` (the part's drawn scene, else this same plate)."""
    v = plan.volumes[volume]
    books = [{"id": vid, "title": vol["title_ar"]} for vid, vol in plan.volumes.items()]
    info = {
        "id": volume,
        "title": v["title_ar"],
        "level": v.get("level"),
        "age": list(v.get("age", [])),
        "goal": v.get("goal", ""),
        "units": [u["id"] for u in v["units"]],
    }
    count = pages if pages is not None else len(book.pages)
    spine = covers.spine_mm(count)
    page = PageSpec(
        id=f"{volume.lower()}-cover-wrap",
        type="islamic-cover-wrap",
        number=0,
        section="finale",
        title=v["title_ar"],
        instruction="",
        params={"volume_info": info, "islamic": context, "books": books, "pages": count, "spine_mm": spine},
    )
    return BookSpec(
        product="islamic",
        title_ar=SERIES_AR,
        child=book.child,
        pages=(page,),
        date=book.date,
        numerals=book.numerals,
        geometry=covers.wrap_geometry(book.geometry, spine),
    )


_RULES: checks.PageRules | None = None


def no_sacred_text(spec: PageSpec) -> bool:
    """A page that may be shown small on the back cover: its type never carries a verse, a hadith or a dhikr
    (plan.yaml `sacred: false`: colouring, mazes, the passport…), so no sacred text is ever printed as a
    decoration (Addendum 10 §3.6)."""
    global _RULES
    _RULES = _RULES or checks.PageRules.load()
    page = spec.params.get("page")
    kind = str(getattr(page, "type", "") or "")
    if not kind:
        return False
    return not _RULES.may_carry_sacred({"type": kind, "sacred_text": getattr(page, "sacred_text", None)})


@dataclass(frozen=True)
class Review:
    """The scholar's approvals as the review export gives them: per volume `approved`, its `units`,
    `approved_on` and `credit_name` (set only when every approving scholar agreed to be named), per unit its
    `status`. No export at all means nothing is approved (Addendum 10 §3.3)."""

    data: Mapping[str, Any]
    path: Path | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> Review:
        """`path`, else $QAMRA_ISLAMIC_REVIEW_FILE, else content/islamic/review-status.json, else nothing."""
        env = os.environ.get(REVIEW_ENV)
        chosen = path or (Path(env) if env else REVIEW_FILE)
        if not chosen.is_file():
            return cls({}, None)
        try:
            data = json.loads(chosen.read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            raise ValueError(f"the review export {chosen} cannot be read: {err}") from None
        if not isinstance(data, dict):
            raise ValueError(f"the review export {chosen} is not an object")
        return cls(data, chosen)

    def _volume(self, volume: str) -> Mapping[str, Any]:
        entry = (self.data.get("volumes") or {}).get(volume)
        return entry if isinstance(entry, dict) else {}

    def problems(self, volume: str, units: Iterable[str]) -> list[str]:
        """Why a print build of the volume is refused: not approved, or a unit not approved (the volume's
        units, and every unit the export lists for it, e.g. its front and back matter)."""
        if self.path is None:
            return [f"no review export ({REVIEW_ENV} or {REVIEW_FILE.name}): nothing is approved yet"]
        entry = self._volume(volume)
        out = [] if entry.get("approved") is True else [f"{volume} is not approved by the scholar"]
        listed = [str(u) for u in entry.get("units") or []]
        statuses = self.data.get("units") or {}
        for unit in dict.fromkeys([*units, *listed]):
            row = statuses.get(unit)
            status = row.get("status") if isinstance(row, dict) else None
            if unit not in listed:
                out.append(f"unit {unit} is not in the review export of {volume}")
            elif status != "approved":
                out.append(f"unit {unit} is {status or 'not reviewed'}, not approved")
        return out

    def credit(self, volume: str) -> str:
        """The name for «راجعه علميًّا: …», only for an approved volume whose scholars agreed to be named."""
        entry = self._volume(volume)
        name = entry.get("credit_name") if entry.get("approved") is True else None
        return str(name).strip() if name else ""


def check_volume(
    plan: islamic.Plan,
    volume: str,
    resolver: Resolver,
    *,
    entries: Sequence[Mapping[str, Any]] | None = None,
    print_build: bool = False,
    build: bool = True,
    review: Review | None = None,
) -> VolumeContent:
    """Match the volume's content to its places and run every check that needs no PDF: the strict models, the
    source / sacred-page / no-depiction checks, word limits and personalization, the closings, and (`build`)
    each page's own builder checks. A print build adds the missing pages, the print gate (every source
    `scholar_approved`, no placeholder) and the scholar's approval of every unit (`review`, default: the
    review export)."""
    if entries is None:
        entries = read_entries(content_path(volume))
    content, _ = match_content(plan, volume, entries)
    rules = checks.PageRules.load()
    told = prophets_units(plan, volume)
    for key, raw in content.raw.items():
        judged = raw
        if raw.get("unit") in told and raw.get("type") in PICTURE_PAGES:  # a prophets' unit: no people
            judged = {**raw, "tags": [*raw.get("tags", []), "prophet_story"]}
        content.problems += [_at(key, p) for p in checks.check_page(judged, resolver, rules)]
        content.problems += text_problems(key, raw)
    content.problems += closing_problems(content)
    content.problems += planned_source_warnings(content)
    if print_build:
        content.problems += [
            Problem("missing", s.key, f"no content for this {s.page.type!r} page") for s in content.missing
        ]
        content.problems += [_at_page(content, p) for p in checks.check_print(content.raw.values(), resolver)]
        review = review if review is not None else Review.load()
        units = [u["id"] for u in plan.volumes[volume]["units"]]
        content.problems += [Problem("not-reviewed", volume, m) for m in review.problems(volume, units)]
    if build and content.pages:
        context = IslamicContext(resolver, kit_for(None, Path()), "print" if print_build else "preview")
        written = {s.key for s in content.slots if s.key in content.pages}
        book = volume_book(plan, content, context, Child(CHILDREN["f"], "f"), only=written)
        try:
            build_pages(book, Assets(LibraryStore()))
        except PageProblems as err:
            for line in str(err).splitlines():
                pid, _, message = line.partition(" ")
                key = next((k for k in written if page_id(volume, k) == pid), pid)
                content.problems.append(Problem("page", key, message.strip()))
    return content


def _at(key: str, problem: Problem) -> Problem:
    return Problem(problem.code, key, problem.message, problem.level)


def _at_page(content: VolumeContent, problem: Problem) -> Problem:
    key = next((k for k, raw in content.raw.items() if raw["id"] == problem.where), problem.where)
    return Problem(problem.code, key, problem.message, problem.level)


# ---- rendering --------------------------------------------------------------------------------------------


@dataclass
class VolumeFiles:
    """What the order job gets back (mirrors `journey_order.OrderFiles`)."""

    interior: Path
    cover: Path
    answer_key: Path | None = None
    pages: int = 0
    preflight: dict[str, dict[str, Any]] = field(default_factory=dict)  # file name → report
    inserts: dict[str, Path] = field(default_factory=dict)  # print file name → the layered PDF (stickers)
    dies: dict[str, Path] = field(default_factory=dict)  # print file name → its die lines alone

    @property
    def passed(self) -> bool:
        return all(r.get("passed") for r in self.preflight.values())


class VolumeRefused(PageProblems):
    """A print build of a volume that is not ready: pages missing, checks failing, sources not approved."""


def _report(pdf: Path, g: Geometry) -> dict[str, Any]:
    return preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe).to_dict()


async def _pdf(
    book: BookSpec, assets: Assets, pdf: Path, key: Path | None = None
) -> tuple[list[RenderedPage], Path | None]:
    pages = build_pages(book, assets)
    await print_pdf(book_html(book, pages, assets), pdf.with_suffix(".html"), pdf, book.geometry)
    if key is None or not any(p.built.answer for p in pages):
        return pages, None
    return pages, await print_pdf(
        answer_key_html(book, pages, assets), key.with_suffix(".html"), key, book.geometry
    )


async def render_volume(
    volume: str,
    child: Child,
    out: Path,
    *,
    size: str = "21x28",
    numerals: Numerals = "hindi",
    print_build: bool = False,
    day: dt.date | None = None,
    resolver: Resolver | None = None,
    plan: islamic.Plan | None = None,
    entries: Sequence[Mapping[str, Any]] | None = None,
    only: set[str] | None = None,
    review: Review | None = None,
    stickers: bool = True,
) -> VolumeFiles:
    """One child's copy of a volume into `out`: interior.pdf, cover.pdf and answer-key.pdf, with a preflight
    report per file. The cover carries the child's character and name; the passport and the certificate the
    child's cut-out and name, in the child's gender. A print build raises `VolumeRefused` (writing nothing)
    while any page is missing, any check fails, any source is not `scholar_approved`, or any unit of the
    volume is not approved in the review export (`review`, default: $QAMRA_ISLAMIC_REVIEW_FILE, else
    content/islamic/review-status.json, else nothing is approved). A print build prints «راجعه علميًّا: …»
    when the export names the scholar.

    With `stickers` (and no `only`), also the volume's sticker sheet: inserts/stickers.pdf and its die
    inserts/stickers-die.pdf (a stamp for every circle of its passport pages, stars for its home boards,
    rewards; `render.stickers`)."""
    vid = volume_id(volume)
    plan = plan or islamic.load()
    if vid not in plan.volumes:
        raise ValueError(f"no volume {volume!r} (have: {', '.join(plan.volumes)})")
    if print_build and only:
        raise ValueError("a print build renders the whole volume (no `only`)")
    resolver = resolver or Resolver.load()
    if print_build and review is None:
        review = Review.load()
    content = check_volume(plan, vid, resolver, entries=entries, print_build=print_build, review=review)
    if print_build and content.errors:
        raise VolumeRefused("\n".join(str(p) for p in content.errors))
    out.mkdir(parents=True, exist_ok=True)
    kit = kit_for(child.character_sheet, out / "assets")
    credit = review.credit(vid) if print_build and review is not None else ""
    mode: Literal["preview", "print"] = "print" if print_build else "preview"
    context = IslamicContext(resolver, kit, mode, day or dt.date.today(), credit=credit)
    book = volume_book(plan, content, context, child, size=size, numerals=numerals, only=only)
    assets = assets_for(book, out)
    _, key = await _pdf(book, assets, out / "interior.pdf", out / "answer-key.pdf")
    cover = cover_book(plan, vid, context, book, pages=len(content.slots))
    cover = covers.with_thumbs(
        cover, book, out / "interior.pdf", out / "assets", covers.THUMBS["islamic"], no_sacred_text
    )
    await _pdf(cover, assets, out / "cover.pdf")
    files = VolumeFiles(out / "interior.pdf", out / "cover.pdf", key, pages=len(book.pages))
    g = book.geometry
    files.preflight = {
        "interior.pdf": _report(files.interior, g),
        "cover.pdf": _report(files.cover, cover.geometry),
    }
    if stickers and not only:
        from qamra_workbook.render.stickers import NAME, render_sheet

        sheet = await render_sheet(book, assets, out / "inserts")
        files.inserts[NAME], files.dies[NAME] = sheet.pdf, sheet.die
        files.preflight[f"inserts/{NAME}.pdf"] = sheet.report
    return files


def contact(files: VolumeFiles, book_pages: Sequence[PageSpec], out: Path, geometry: Geometry) -> Path:
    names = [f"{p.number:03d}-{p.params.get('key', p.id).replace('/', '_')}" for p in book_pages]
    pngs = previews(files.interior, out / "png", names, geometry, dpi=60)
    labels = [f"{p.number} · {p.params.get('key', p.id)}" for p in book_pages]
    return contact_sheet(pngs, out / "contact-sheet.png", labels, columns=6, rtl=True)


def print_check(content: VolumeContent) -> None:
    errors, warnings = content.errors, [p for p in content.problems if p.level == "warning"]
    for problem in [*errors, *warnings]:
        print(problem)
    written = len(content.written)
    print(
        f"{content.volume}: {len(content.slots)} places · {written} written · "
        f"{len(content.missing)} to write · {len(errors)} error(s) · {len(warnings)} warning(s)"
    )
    todo = Counter(s.page.type for s in content.missing)
    if todo:
        print("  to write: " + ", ".join(f"{t}×{n}" for t, n in todo.most_common()))


def print_vocab() -> None:
    """What a page may draw: the scenes, the backdrops, the series' icons and the library's pictures."""
    from qamra_workbook.pictures import PICTURES
    from qamra_workbook.pictures.islamic import SCENES, UNIT_GLYPHS
    from qamra_workbook.pictures.islamic_backdrops import BACKDROPS, PERSON_PICTURES

    print("scenes (art):")
    for name, sc in SCENES.items():
        print(f"  {name:22s} {'with the cast' if sc.figures else 'no people'} · {sc.note}")
    print("backdrops (scene: {backdrop, props, figures}):")
    for name, b in BACKDROPS.items():
        print(f"  {name:22s} up to {len(b.spots)} props · {b.note}")
    print("series icons (isl:<name>): " + ", ".join(sorted(UNIT_GLYPHS)))
    by_category: dict[str, list[str]] = defaultdict(list)
    for pid, pic in sorted(PICTURES.items()):
        if pid not in PERSON_PICTURES:
            by_category[pic.category].append(f"{pid} ({pic.word_ar})")
    print("library pictures (pic / props / pics / hints…):")
    for category, items in sorted(by_category.items()):
        print(f"  {category}: " + ", ".join(items))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--volume", default="v1", help="v1 … v5, or r (the Ramadan and Eid book)")
    parser.add_argument("--size", choices=SIZES, default="21x28")
    parser.add_argument(
        "--print", action="store_true", dest="print_build", help="refuses unless all is ready"
    )
    parser.add_argument("--check", action="store_true", help="list missing and invalid pages; render nothing")
    parser.add_argument("--complete", action="store_true", help="with --check: missing pages are errors too")
    parser.add_argument("--keys", action="store_true", help="list the volume's places and their keys")
    parser.add_argument("--vocab", action="store_true", help="list the scenes, backdrops, icons and pictures")
    parser.add_argument("--only", help="comma-separated keys or key prefixes to render (u-allah/,end/)")
    parser.add_argument("--name", help="the child's name (default: ليان / يوسف)")
    parser.add_argument("--gender", choices=("m", "f"), default="f")
    parser.add_argument("--numerals", choices=("hindi", "latin"), default="hindi")
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--review", type=Path, help=f"the review export (default: ${REVIEW_ENV} or {REVIEW_FILE.name})"
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.vocab:
        print_vocab()
        return 0
    vid = volume_id(args.volume)
    try:
        plan = islamic.load()
        resolver = Resolver.load()
        if vid not in plan.volumes:
            print(f"✗ no volume {args.volume!r} (have: {', '.join(plan.volumes)})")
            return 2
        if args.keys:
            content, _ = match_content(plan, vid, read_entries(content_path(vid)))
            for s in content.slots:
                mark = "✓" if s.key in content.pages else "·"
                print(f"{mark} {s.page.n:3d}  {s.key:24s} {s.page.type:15s} {s.page.title}")
            return 0
        review = Review.load(args.review) if args.print_build else None
        content = check_volume(plan, vid, resolver, print_build=args.print_build, review=review)
    except (SourceError, ValueError) as err:
        print(f"✗ {err}")
        return 1
    if args.check:
        if args.complete:
            content.problems += [
                Problem("missing", s.key, f"no content for this {s.page.type!r} page")
                for s in content.missing
            ]
        print_check(content)
        return 1 if content.errors else 0
    if args.print_build and content.errors:
        print_check(content)
        print(f"✗ print build refused: {len(content.errors)} problem(s); nothing was written")
        return 1
    for problem in content.errors:
        print(problem)
    child = Child(
        args.name or CHILDREN[args.gender], args.gender, SAMPLE_SHEET if SAMPLE_SHEET.is_file() else None
    )
    out = args.out or OUT / vid.lower()
    only = set(args.only.split(",")) if args.only else None
    try:
        files = asyncio.run(
            render_volume(
                vid,
                child,
                out,
                size=args.size,
                numerals=args.numerals,
                print_build=args.print_build,
                day=SAMPLE_DATE,
                resolver=resolver,
                plan=plan,
                only=only,
                review=review,
            )
        )
    except PageProblems as err:
        print(f"✗ {err}")
        return 1
    kit = kit_for(child.character_sheet, out / "assets")
    context = IslamicContext(resolver, kit, "print" if args.print_build else "preview", SAMPLE_DATE)
    book = volume_book(plan, content, context, child, size=args.size, only=only)
    sheet = contact(files, book.pages, out, book.geometry)
    (out / "preflight.json").write_text(
        json.dumps(files.preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for name, report in files.preflight.items():
        print(
            f"{out / name}: preflight {'passed' if report['passed'] else 'FAILED'} "
            f"(min image DPI {report.get('min_dpi')})"
        )
        for item in report["checks"]:
            if not item["ok"]:
                print(f"  {'!' if item['level'] == 'warning' else '✗'} {item['name']}: {item['detail']}")
    print(f"{files.pages} pages · answer key: {files.answer_key} · contact sheet: {sheet}")
    print_check(content)
    return 0 if files.passed and not content.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
