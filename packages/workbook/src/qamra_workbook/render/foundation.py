"""«دوسية التأسيس» (Addendum 5) from its curriculum plan: every page of a volume as an engine page for one
child.

The plan (content/workbook/curriculum/{level}.yaml, `qamra_workbook.curriculum`) gives each page its subject,
unit, week, type, skill and params. Here each page gets what the engine prints for the child: a title and a
short instruction (`foundation_text`), the page's language (English pages are LTR and bilingual), and the
params its builder reads, including a few taken from the plan around it (the unit's title, the subject's
objectives for an opener, the table of contents, the week). The plan's own params always win.

A plan type whose name another product already registered with a different page (`drawing`, `certificate`,
`toc`) is rendered by its foundation builder (`ENGINE_TYPES`).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from qamra_workbook.curriculum import SUBJECT_AR, Curriculum, Page, Volume
from qamra_workbook.render.foundation_text import objective_as_child, page_texts
from qamra_workbook.render.spec import BookSpec, Child, Geometry, Lang, Numerals, PageSpec

PRODUCT = "foundation"
ENGINE_TYPES = {"drawing": "symmetry-drawing", "certificate": "workbook-certificate", "toc": "workbook-toc"}
# English-subject pages printed LTR with the instruction in English and Arabic; openers stay Arabic
ENGLISH_PAGES = frozenset(
    {
        "en-letter",
        "find-letter",
        "match-letter-picture",
        "unit-review",
        "assessment",
        "word-read",  # volume 3: first English words and sentences read with their pictures
        "sentence-read",
    }
)
VOLUME_AR = {1: "الجزء الأول", 2: "الجزء الثاني", 3: "الجزء الثالث"}


def page_id(level: str, volume: int, n: int) -> str:
    return f"{level}-v{volume}-p{n}"


def engine_type(page: Page, level: str = "kg2") -> str:
    from qamra_workbook.render.foundation_kg1 import engine_type_kg1  # lazy: KG1 imports this module
    from qamra_workbook.render.foundation_v2 import engine_type_v2  # lazy: volume 2 imports this module
    from qamra_workbook.render.foundation_v3 import engine_type_v3  # lazy: volume 3 imports this module

    return (
        (engine_type_kg1(page) if level == "kg1" else None)  # KG1's own pages first
        or engine_type_v3(page)
        or engine_type_v2(page)
        or ENGINE_TYPES.get(page.type, page.type)
    )


def toc_entries(volume: Volume) -> list[dict[str, Any]]:
    """The volume's units in book order with their first page (assessments and front pages left out)."""
    first: dict[str, int] = {}
    for p in volume.pages:
        first.setdefault(p.unit, p.n)
    out = []
    for u in volume.units:
        if u.subject == "intro" or u.id not in first:
            continue
        out.append({"subject": u.subject, "title": u.display_ar, "page": first[u.id]})
    return sorted(out, key=lambda e: e["page"])


def plan_params(page: Page, plan: Curriculum, volume: Volume, name_en: str) -> dict[str, Any]:
    """The page's params with what its builder needs from the rest of the plan (the plan's own win)."""
    unit = next(u for u in volume.units if u.id == page.unit)
    extra: dict[str, Any] = {
        "week": page.week,
        "level": plan.level,
        "volume": volume.volume,
        "difficulty": page.difficulty,
        "unit_title": unit.display_ar,  # vowelized for the child (decisions 3 and 6 cover reading only)
    }
    match page.type:
        case "unit-opener":
            # in the child's voice under «في هذا الجزء سأتعلّم» (the plan writes them about the child)
            extra["objectives"] = [objective_as_child(o) for o in volume.objectives.get(page.subject, [])]
            extra["subject_ar"] = SUBJECT_AR[page.subject]
        case "toc":
            extra["units"] = toc_entries(volume)
            extra["volume_title"] = volume.title_v or volume.title_ar
        case "owner-page":
            extra["volume_title"] = volume.title_v or volume.title_ar
            extra["level_title"] = plan.title_ar
        case "name-trace":
            extra["name_en"] = name_en
        case "maze":  # levels 1–5 (Addendum 5 §8): a bigger grid each level
            level = int(page.params.get("level", 1))
            extra["cols"] = extra["rows"] = 4 + level
        case "odd-one-out":  # a solved example row (seen), then the rows: named groups come in by level
            rows = int(page.params.get("rows", 3))
            level = min(max(int(page.params.get("level", 1)), 1), 3)
            ladders = (["same"] * 2 + ["category"] * 3, ["same"] + ["category"] * 4, ["category"] * 5)
            ladder = ladders[level - 1]
            extra["rules"] = ["same", *ladder[:rows]]
            extra["sizes"] = [4] * (rows + 1)
        case "pattern-complete":
            pattern = str(page.params.get("pattern", "AB"))
            extra["units"] = [pattern] * 4
            extra["shown"] = [len(pattern) * 2, len(pattern) * 2, len(pattern) * 2 + 1, len(pattern) * 2 + 2]
        case "en-letter":
            extra["color_in"] = True  # «وألوّن صورة apple»: the picture is line art to color
        case "assessment" | "unit-review":
            extra["subject_ar"] = SUBJECT_AR[page.subject]
    return {**extra, **page.params}


def turn_of(page: Page, volume: Volume, level: str) -> int:
    """How many pages with the same builder and subject come before `page` in its volume: a recurring exercise
    turns through its instruction's wordings with it (`foundation_text.pick`)."""
    kind = engine_type(page, level)
    return sum(
        1
        for q in volume.pages
        if q.n < page.n and q.subject == page.subject and engine_type(q, level) == kind
    )


def from_curriculum(page: Page, plan: Curriculum, volume: Volume, name_en: str = "") -> PageSpec:
    params = plan_params(page, plan, volume, name_en)
    lang: Lang = "en" if page.subject == "english" and page.type in ENGLISH_PAGES else "ar"
    from qamra_workbook.render.foundation_kg1 import params_kg1, texts_kg1  # lazy: KG1 imports this module
    from qamra_workbook.render.foundation_v2 import texts_v2  # lazy: volume 2 imports this module
    from qamra_workbook.render.foundation_v3 import texts_v3  # lazy: volume 3 imports this module

    kg1 = plan.level == "kg1"
    if kg1:
        params = params_kg1(page, params)
    said = {
        **params,
        "turn": turn_of(page, volume, plan.level),
    }  # the texts' params (the builders' stay as they are)
    title, instruction, instruction_en = (
        (texts_kg1(page.subject, page.type, said, params["unit_title"]) if kg1 else None)
        or texts_v3(page.subject, page.type, said, params["unit_title"])
        or texts_v2(page.subject, page.type, said, params["unit_title"])
        or page_texts(page.subject, page.type, said, params["unit_title"])
    )
    if page.type == "unit-opener" and ":" in page.skill:  # «أنا وعالم الأرقام: أتعرّف على ما سأتعلّمه»
        title = page.skill.split(":")[0].strip()
    return PageSpec(
        id=page_id(plan.level, volume.volume, page.n),
        type=engine_type(page, plan.level),
        number=page.n,
        section=page.subject,
        title=title,
        instruction=instruction,
        lang=lang,
        instruction_en=instruction_en if lang == "en" else "",
        skill=page.skill,
        params=params,
    )


def volume_of(plan: Curriculum, number: int) -> Volume:
    for v in plan.volumes:
        if v.volume == number:
            return v
    raise KeyError(f"{plan.level} has no volume {number}")


def volume_book(
    plan: Curriculum,
    number: int,
    child: Child,
    *,
    name_en: str = "",
    date: dt.date | None = None,
    numerals: Numerals = "hindi",
    geometry: Geometry | None = None,
    pages: range | None = None,
) -> BookSpec:
    """The volume (or its `pages`) as a book for `child`."""
    volume = volume_of(plan, number)
    specs = tuple(
        from_curriculum(p, plan, volume, name_en) for p in volume.pages if pages is None or p.n in pages
    )
    return BookSpec(
        product=PRODUCT,
        title_ar=f"{plan.title_ar} — {VOLUME_AR.get(number, number)}",
        child=child,
        pages=specs,
        date=date or dt.date.today(),
        numerals=numerals,
        geometry=geometry or Geometry(),
    )
