"""«قلبي يعرف الله» (Addendum 10): the series plan, its rules and the retention matrix.

The plan lives in content/islamic/: plan.yaml (series, page types, retention forms), units.yaml,
concepts.yaml, volumes/*.yaml (lessons) and the source register (sources.yaml + sources.d/*.yaml).
This module loads it, places every page of every volume (numbers, type, unit, concepts, sources) and
checks the rules that can be checked at plan level.

    uv run python -m qamra_workbook.islamic check   # problems (exit 1 when any), page counts, coverage

It reads source *ids and kinds* only. Resolving a source's wording is `qamra_workbook.islamic_sources`:
no religious text is ever held here.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[4]
CONTENT = ROOT / "content/islamic"
FORMS = ("story", "activity", "question", "situation", "review", "home")
RANGE = (96, 120)  # Addendum 10 §1: a volume is ~96–120 pages (the seasonal book is smaller)
SEASONAL_RANGE = (48, 80)
MIN_FORMS = 5  # a concept should reach at least this many of the six forms across the series


@dataclass
class Page:
    n: int
    volume: str
    kind: str  # front, opener, lesson, closing, parent, cumulative, back
    type: str
    unit: str | None = None
    lesson: int | None = None
    title: str = ""
    concepts: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    forms: tuple[str, ...] = ()


@dataclass
class Plan:
    series: dict[str, Any]
    characters: list[dict[str, Any]]
    endings: list[dict[str, Any]]
    page_types: dict[str, dict[str, Any]]
    units: dict[str, dict[str, Any]]
    concepts: dict[str, dict[str, Any]]
    volumes: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    pages: dict[str, list[Page]] = field(default_factory=dict)


def _yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _forms_of(page_types: dict[str, dict[str, Any]], ptype: str) -> tuple[str, ...]:
    f = page_types.get(ptype, {}).get("form")
    return tuple(f) if isinstance(f, list) else ((f,) if f else ())


def load(content: Path = CONTENT) -> Plan:
    base = _yaml(content / "plan.yaml")
    sources: dict[str, dict[str, Any]] = {}
    files = [content / "sources.yaml", *sorted((content / "sources.d").glob("*.yaml"))]
    for f in files:
        if f.exists():
            for s in (_yaml(f) or {}).get("sources", []):
                sources[s["id"]] = s
    found = [_yaml(f) for f in sorted((content / "volumes").glob("*.yaml"))]
    volumes = {
        v["volume"]: v for v in sorted(found, key=lambda v: (v["volume"] == "R", v["volume"]))
    }  # V1…V5, then R
    plan = Plan(
        series=base["series"],
        characters=base["characters"],
        endings=base["unit_endings"],
        page_types=base["page_types"],
        units={u["id"]: u for u in _yaml(content / "units.yaml")["units"]},
        concepts={c["id"]: c for c in _yaml(content / "concepts.yaml")["concepts"]},
        volumes=volumes,
        sources=sources,
    )
    plan.pages = {vid: place(plan, vid) for vid in volumes}
    return plan


def place(plan: Plan, vid: str) -> list[Page]:
    """Every page of a volume in book order, with its concepts, sources and retention forms."""
    v = plan.volumes[vid]
    pt = plan.page_types
    out: list[Page] = []

    def add(kind: str, ptype: str, **kw: Any) -> None:
        out.append(Page(n=len(out) + 1, volume=vid, kind=kind, type=ptype, forms=_forms_of(pt, ptype), **kw))

    all_concepts = tuple(
        dict.fromkeys(c for u in v["units"] for les in u["lessons"] for c in les.get("c", []))
    )
    for _ in range(int(v["front"])):
        add("front", "front")
    cumulative = defaultdict(list)
    for cum in v.get("cumulative", []):
        cumulative[cum["after"]].append(cum)
    for unit in v["units"]:
        uid = unit["id"]
        ucon = tuple(dict.fromkeys(c for les in unit["lessons"] for c in les.get("c", [])))
        usrc = tuple(dict.fromkeys(s for les in unit["lessons"] for s in les.get("s", [])))
        add("opener", "unit-opener", unit=uid, title=plan.units[uid]["title_ar"])
        for i, les in enumerate(unit["lessons"], 1):
            for ptype in les["p"]:
                sacred = pt.get(ptype, {}).get("sacred", True)
                add(
                    "lesson",
                    ptype,
                    unit=uid,
                    lesson=i,
                    title=les["t"],
                    concepts=tuple(dict.fromkeys([*les.get("c", []), *les.get("r", [])])),
                    sources=tuple(les.get("s", [])) if sacred else (),
                )
        for _ in range(2):
            add("closing", "unit-closing", unit=uid, concepts=ucon, sources=usrc)
        add("parent", "parent-guide", unit=uid, concepts=ucon, sources=usrc)
        for cum in cumulative.get(uid, []):
            for ptype in cum["p"]:
                add("cumulative", ptype, unit=uid, concepts=tuple(cum["c"]))
    for ptype in v["back"]:
        add("back", ptype, concepts=all_concepts if ptype == "assessment" else ())
    return out


def unit_pages(plan: Plan, vid: str) -> dict[str, int]:
    return dict(Counter(p.unit for p in plan.pages[vid] if p.unit))


# ---- checks ------------------------------------------------------------


def coverage(plan: Plan) -> dict[str, dict[str, Any]]:
    """Per concept: pages per form, the volumes it is in and the span of its first and last page."""
    out: dict[str, dict[str, Any]] = {
        cid: {"forms": Counter(), "volumes": [], "pages": 0, "spans": {}} for cid in plan.concepts
    }
    for vid, pages in plan.pages.items():
        seen: dict[str, list[int]] = defaultdict(list)
        for p in pages:
            for c in p.concepts:
                if c in out:
                    out[c]["pages"] += 1
                    out[c]["forms"].update(p.forms)
                    seen[c].append(p.n)
        for c, ns in seen.items():
            out[c]["volumes"].append(vid)
            out[c]["spans"][vid] = (min(ns), max(ns))
    return out


def problems(plan: Plan) -> list[str]:
    found: list[str] = []
    kinds = {sid: s["kind"] for sid, s in plan.sources.items()}
    for vid, v in plan.volumes.items():
        total = len(plan.pages[vid])
        low, high = SEASONAL_RANGE if vid == "R" else RANGE
        if not low <= total <= high:
            found.append(f"{vid}: {total} pages, outside the {low}–{high} range")
        for unit in v["units"]:
            uid = unit["id"]
            if uid not in plan.units:
                found.append(f"{vid}: unknown unit {uid}")
            elif plan.units[uid]["volume"] != vid:
                found.append(f"{vid}: unit {uid} is declared in {plan.units[uid]['volume']} (units.yaml)")
            for i, les in enumerate(unit["lessons"], 1):
                where = f"{vid}/{uid}/lesson {i}"
                for ptype in les["p"]:
                    if ptype not in plan.page_types:
                        found.append(f"{where}: unknown page type {ptype}")
                for c in [*les.get("c", []), *les.get("r", [])]:
                    if c not in plan.concepts:
                        found.append(f"{where}: unknown concept {c}")
                for s in les.get("s", []):
                    if s not in plan.sources:
                        found.append(f"{where}: unknown source {s}")
                sacred = [t for t in les["p"] if plan.page_types.get(t, {}).get("sacred", True)]
                religious = [t for t in sacred if t not in ("find-objects", "match", "choose", "true-false")]
                if sacred and not les.get("s"):
                    found.append(f"{where}: religious pages ({', '.join(sacred)}) with no source id")
                if "dhikr" in les["p"] and not any(
                    kinds.get(s) in ("dua", "quran") for s in les.get("s", [])
                ):
                    found.append(f"{where}: a dhikr page needs a dua or Quran source")
                if "surah" in les["p"] and not any(kinds.get(s) == "quran" for s in les.get("s", [])):
                    found.append(f"{where}: a surah page needs a Quran source")
                if ("prophet-story" in les["p"] or "sira-story" in les["p"]) and not les.get("s"):
                    found.append(f"{where}: a prophet or sira story needs sources")
                del religious
        for cum in v.get("cumulative", []):
            if cum["after"] not in {u["id"] for u in v["units"]}:
                found.append(f"{vid}: cumulative review after unknown unit {cum['after']}")
            found += [
                f"{vid}: cumulative review names unknown concept {c}"
                for c in cum["c"]
                if c not in plan.concepts
            ]
    for sid, s in plan.sources.items():
        if s["kind"] == "dua" and s["dua"]["from"] not in plan.sources:
            found.append(f"source {sid}: dua.from {s['dua']['from']} is not a source")
        for b in s.get("basis", []):
            if b not in plan.sources:
                found.append(f"source {sid}: basis {b} is not a source")
    areas = {c["area"] for c in plan.concepts.values()}
    if areas != set(range(1, 17)):
        found.append(f"areas without a concept: {sorted(set(range(1, 17)) - areas)}")
    covered = {
        plan.concepts[c]["area"]
        for pages in plan.pages.values()
        for p in pages
        for c in p.concepts
        if c in plan.concepts
    }
    if covered != set(range(1, 17)):
        found.append(f"areas never taught: {sorted(set(range(1, 17)) - covered)}")
    return found


def weak_concepts(plan: Plan) -> list[tuple[str, int, list[str]]]:
    """Concepts that reach fewer than MIN_FORMS retention forms: (id, forms reached, forms missing)."""
    out = []
    for cid, cov in coverage(plan).items():
        got = [f for f in FORMS if cov["forms"][f]]
        if len(got) < MIN_FORMS:
            out.append((cid, len(got), [f for f in FORMS if f not in got]))
    return sorted(out, key=lambda t: (t[1], t[0]))


def unused_sources(plan: Plan) -> list[str]:
    used = {s for pages in plan.pages.values() for p in pages for s in p.sources}
    used |= {b for sid in used for b in plan.sources.get(sid, {}).get("basis", [])}
    used |= {
        plan.sources[sid]["dua"]["from"] for sid in used if plan.sources.get(sid, {}).get("kind") == "dua"
    }
    return sorted(set(plan.sources) - used)


def main(argv: list[str] | None = None) -> int:
    args = (argv if argv is not None else sys.argv[1:]) or ["check"]
    if args[0] != "check":
        print("usage: python -m qamra_workbook.islamic check")
        return 2
    plan = load()
    for vid in plan.volumes:
        up = unit_pages(plan, vid)
        print(
            f"{vid}: {len(plan.pages[vid])} pages, {len(up)} units: "
            + ", ".join(f"{u}={n}" for u, n in up.items())
        )
    weak = weak_concepts(plan)
    print(
        f"concepts: {len(plan.concepts)}; reaching ≥{MIN_FORMS} of 6 forms: {len(plan.concepts) - len(weak)}"
    )
    for cid, n, missing in weak[:12]:
        print(f"  weak {cid} ({n}): missing {', '.join(missing)}")
    print(f"sources: {len(plan.sources)}; planned but unused: {len(unused_sources(plan))}")
    found = problems(plan)
    for f in found:
        print("✗", f)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
