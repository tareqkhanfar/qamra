"""The class book's page plan in the API (Addendum 1 §2): which children are ready, the automatic plan, the
teacher's edits from the planner, and whether the plan still matches the class before drawing."""

import random
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.classbook import (
    ClassLine,
    ClassTemplate,
    build_plan,
    coverage,
    load_class_template,
    refs_per_picture,
)
from qamra_core.db.models import Character, CharacterStatus, Child, Classroom
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.portal import ClassBook


async def ready_children(db: AsyncSession, room: Classroom, style: str) -> list[Child]:
    """Children with a parent-approved character in the class book's style, by name."""
    rows = (
        await db.execute(
            select(Child)
            .join(Character, Character.child_id == Child.id)
            .where(
                Child.classroom_id == room.id,
                Character.status == CharacterStatus.approved,
                Character.art_style == style,
                Character.sheet_image_key.is_not(None),
            )
            .order_by(Child.first_name)
        )
    ).scalars()
    return list({c.id: c for c in rows}.values())


async def template_of(db: AsyncSession, cb: ClassBook) -> ClassTemplate | None:
    theme = await db.get(ThemeRow, cb.theme_id) if cb.theme_id else None
    if theme is None:
        return None
    try:
        return load_class_template(theme.slug)
    except KeyError:
        return None


def cap_for(values: dict[str, Any]) -> int:
    """Children per picture for the image provider in use (`class_book_refs`)."""
    return refs_per_picture(str(values.get("class_book_refs") or ""), str(values.get("image_provider") or ""))


def auto_plan(
    cb: ClassBook, template: ClassTemplate, children: list[str], cap: int, seed: int | None = None
) -> dict[str, Any]:
    seed = (
        seed if seed is not None else int((cb.plan or {}).get("seed") or random.randrange(1, 2_000_000_000))
    )
    line: ClassLine = "classic" if cb.line == "classic" else "magic"
    pages = build_plan(template, children, min_each=cb.min_appearances, cap=cap, line=line, seed=seed)
    return {
        "template": template.slug,
        "version": template.version,
        "line": line,
        "min_each": cb.min_appearances,
        "cap": cap,
        "seed": seed,
        "manual": False,
        "children": list(children),
        "pages": [
            {"index": p.index, "key": p.key, "slots": p.slots, "children": list(p.children)} for p in pages
        ],
    }


def outdated(cb: ClassBook, template: ClassTemplate, children: list[str]) -> bool:
    """The plan was made for other children, another story, line or minimum."""
    plan = cb.plan or {}
    return (
        not plan.get("pages")
        or plan.get("template") != template.slug
        or plan.get("line") != ("classic" if cb.line == "classic" else "magic")
        or plan.get("min_each") != cb.min_appearances
        or sorted(plan.get("children") or []) != sorted(children)
    )


def plan_coverage(cb: ClassBook) -> dict[str, int]:
    plan = cb.plan or {}
    return coverage([p.get("children") or [] for p in plan.get("pages", [])], plan.get("children") or [])


def short(cb: ClassBook) -> list[str]:
    """Children below the minimum number of appearances (Magic class books)."""
    if cb.line == "classic":
        return []
    return [c for c, n in plan_coverage(cb).items() if n < cb.min_appearances]


@dataclass(frozen=True)
class PlanEdit:
    index: int
    children: list[uuid.UUID]


def apply_edits(cb: ClassBook, edits: list[PlanEdit]) -> dict[str, Any] | None:
    """The teacher's planner edits on top of the current plan; None when an edit doesn't fit."""
    plan = dict(cb.plan or {})
    members = set(plan.get("children") or [])
    pages = {int(p["index"]): dict(p) for p in plan.get("pages", [])}
    for edit in edits:
        page = pages.get(edit.index)
        kids = [str(c) for c in edit.children]
        if page is None or len(kids) != len(set(kids)) or len(kids) > int(page["slots"]):
            return None
        if any(k not in members for k in kids):
            return None
        page["children"] = kids
    plan["pages"] = [pages[i] for i in sorted(pages)]
    plan["manual"] = True
    return plan
