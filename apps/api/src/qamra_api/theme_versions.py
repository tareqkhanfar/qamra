"""Theme versions (Addendum 4 §3.1): the live definition, the open version, publishing and rollback.

Used by the deploy seed (content/themes files) and the template studio. A theme edited in the studio keeps
its live version on deploy: a file replaces it only with a higher version number, which then joins the
history as the live version (the studio's versions stay in the history, and a rollback brings them back).
"""

import copy
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import GENDERS, Theme, fill_title, render_template
from qamra_core.db.models import Book, Child, Locale
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.studio import OPEN_STATUSES, ThemeVersion, ThemeVersionStatus

V = ThemeVersionStatus
_LEFTOVER = re.compile(r"[{}]")


def theme_columns(theme: Theme) -> dict[str, Any]:
    """The catalog columns of `themes` that follow the definition."""
    return {
        "version": theme.version,
        "title_ar": theme.title_ar,
        "title_en": theme.title_en,
        "age_min": theme.age_range[0],
        "age_max": theme.age_range[1],
        "occasion": theme.catalog.occasions[0] if theme.catalog and theme.catalog.occasions else None,
        "is_b2b": theme.is_b2b,
        "active": theme.active,
        "companion_slot": theme.companion_slot,
    }


def display_titles(definition: dict[str, Any]) -> tuple[str, str]:
    """The theme's name for staff: the catalog name (no child's name in it), else the title template."""
    catalog = definition.get("catalog") or {}
    ar = catalog.get("name_ar") or definition.get("title_ar") or ""
    en = catalog.get("name_en") or definition.get("title_en") or ""
    return fill_title(str(ar), "…", None), fill_title(str(en), "…", None)


async def book_title(db: AsyncSession, book: Book) -> str:
    """The book's own title, else its theme's title for the child (name and {masc/fem} filled)."""
    if book.title:
        return book.title
    theme = await db.get(ThemeRow, book.theme_id) if book.theme_id else None
    if theme is None:
        return ""
    child = await db.get(Child, book.child_id) if book.child_id else None
    template = theme.title_ar if book.language == Locale.ar else theme.title_en
    if child is None:
        return fill_title(template, "", None)
    return fill_title(template, child.first_name, "f" if child.gender.value == "f" else "m")


def apply_definition(row: ThemeRow, definition: dict[str, Any]) -> Theme:
    """Make `definition` the theme's live one: what new books read (the catalog columns follow it)."""
    theme = Theme.model_validate(definition)
    for key, value in theme_columns(theme).items():
        setattr(row, key, value)
    row.definition = definition
    return theme


def problems(definition: dict[str, Any]) -> list[str]:
    """Why a definition cannot be saved: the story rules (Addendum 3) and the text placeholders."""
    try:
        theme = Theme.model_validate(definition)
    except ValidationError as e:
        return [str(err.get("msg", "invalid")).removeprefix("Value error, ")[:300] for err in e.errors()]
    out: list[str] = []
    texts = [("title", theme.title_ar), ("title", theme.title_en)]
    texts += [(f"page {p.index}", t) for p in theme.pages for t in (p.text_ar, p.text_en)]
    for label, text in texts:
        for gender in GENDERS:
            if _LEFTOVER.search(render_template(text, gender, "", "")):
                out.append(f"{label}: unknown placeholder or a broken {{…/…}} variant")
                break
    return sorted(set(out))


async def history(db: AsyncSession, theme_id: uuid.UUID) -> list[ThemeVersion]:
    """Newest first."""
    q = select(ThemeVersion).where(ThemeVersion.theme_id == theme_id).order_by(ThemeVersion.version.desc())
    return list((await db.execute(q)).scalars())


async def find(db: AsyncSession, theme_id: uuid.UUID, *statuses: ThemeVersionStatus) -> ThemeVersion | None:
    q = select(ThemeVersion).where(ThemeVersion.theme_id == theme_id, ThemeVersion.status.in_(statuses))
    return (await db.execute(q.order_by(ThemeVersion.version.desc()))).scalars().first()


async def open_version(db: AsyncSession, theme_id: uuid.UUID) -> ThemeVersion | None:
    return await find(db, theme_id, *OPEN_STATUSES)


async def ensure_live(db: AsyncSession, row: ThemeRow) -> ThemeVersion:
    """The live version; a theme saved before versions existed gets its current definition recorded."""
    live = await find(db, row.id, V.live)
    if live is None:
        live = ThemeVersion(
            theme_id=row.id,
            version=row.version,
            status=V.live,
            source="file",
            definition=row.definition,
            meta={},
            published_at=datetime.now(UTC),
        )
        db.add(live)
        await db.flush()
    return live


async def new_draft(
    db: AsyncSession, row: ThemeRow, base: ThemeVersion, actor: uuid.UUID | None, note: str | None = None
) -> ThemeVersion:
    """A draft copied from `base`, numbered after every version the theme has had."""
    numbers = [v.version for v in await history(db, row.id)]
    number = max([row.version, *numbers]) + 1
    definition = copy.deepcopy(base.definition)
    definition["version"] = number
    draft = ThemeVersion(
        theme_id=row.id,
        version=number,
        status=V.draft,
        source="studio",
        base_version=base.version,
        definition=definition,
        note=note,
        meta={},
        created_by_user_id=actor,
    )
    db.add(draft)
    await db.flush()
    return draft


async def publish(
    db: AsyncSession, row: ThemeRow, version: ThemeVersion, actor: uuid.UUID | None
) -> ThemeVersion | None:
    """`version` becomes the live definition; the one it replaces is retired (and returned)."""
    current = await find(db, row.id, V.live)
    if current is not None and current.id != version.id:
        current.status = V.retired
        await db.flush()  # one live version per theme (a partial unique index)
    apply_definition(row, version.definition)
    version.status = V.live
    version.published_at, version.published_by_user_id = datetime.now(UTC), actor
    if version not in db:
        db.add(version)
    await db.flush()
    return current if current is not None and current.id != version.id else None


async def sync_file(db: AsyncSession, row: ThemeRow, theme: Theme, raw: dict[str, Any]) -> str:
    """Deploy: the file's definition goes live if it is newer than every version, or corrects its own live
    version in place (as before versions existed). Otherwise the studio's live version stays."""
    versions = await history(db, row.id)
    live = next((v for v in versions if v.status == V.live), None)
    if theme.version > max((v.version for v in versions), default=0):
        await publish(db, row, ThemeVersion(theme_id=row.id, version=theme.version, source="file",
                                            definition=raw, meta={}), None)  # fmt: skip
        return f"~{theme.slug}"
    if live is not None and live.source == "file" and live.version == theme.version:
        live.definition = raw
        apply_definition(row, raw)
        return f"~{theme.slug}"
    return f"={theme.slug}"  # the studio's live version stays
