"""«قمرة كلاسيك» in the shop's flow (Addendum 4 §1A): which template a book uses; the final after ordering.

A Classic book is drawn by `qamra_worker.jobs.classic`: its preview (the cover and two hero pages,
watermarked) right after the story step, and the whole book once the order is confirmed.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.classic import classic_budget_usd, variant_for
from qamra_core.db.classic import ClassicTemplate, TemplateStatus
from qamra_core.db.models import Book, BookStatus, Child, OrderItem
from qamra_core.db.models import Theme as ThemeRow

CLASSIC_JOB = "qamra_worker.jobs.classic.generate_classic_book"


async def live_template(
    db: AsyncSession, theme_id: uuid.UUID, style: str, child: Child
) -> ClassicTemplate | None:
    """The live template for a theme, an art style and the child's look (girl, girl with hijab, boy)."""
    variant = variant_for(child.gender.value, child.wears_hijab)
    return (
        await db.execute(
            select(ClassicTemplate).where(
                ClassicTemplate.theme_id == theme_id,
                ClassicTemplate.art_style == style,
                ClassicTemplate.variant == variant,
                ClassicTemplate.status == TemplateStatus.live,
            )
        )
    ).scalar_one_or_none()


async def start_classic_finals(db: AsyncSession, order_id: uuid.UUID) -> list[str]:
    """The order is confirmed: every Classic book in it is drawn in full. A book still drawing its preview
    finishes it and continues to the full book on its own. Returns the books to enqueue (caller commits)."""
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))).scalars().all()
    ids = [i.book_id for i in items if i.book_id is not None]
    if not ids:
        return []
    books = (await db.execute(select(Book).where(Book.id.in_(ids)))).scalars().all()
    start: list[str] = []
    for book in books:
        if (book.generation or {}).get("line") != "classic":
            continue
        if book.status == BookStatus.generating:
            book.generation = {**book.generation, "final_requested": True}
        elif book.status in (BookStatus.draft, BookStatus.preview, BookStatus.failed):
            book.status = BookStatus.generating
            start.append(str(book.id))
    return start


async def resume_classic_draft(db: AsyncSession, book: Book, values: dict[str, Any]) -> bool:
    """A Classic book created before its template went live waits as a draft; once a live template exists,
    the parent's next visit starts its preview. True when the caller should enqueue the job."""
    if (book.generation or {}).get("line") != "classic" or book.status != BookStatus.draft:
        return False
    child = await db.get(Child, book.child_id)
    template = await live_template(db, book.theme_id, book.art_style, child) if child else None
    if template is None:
        return False
    book.status = BookStatus.generating
    book.budget_usd = classic_budget_usd(values)  # drafts from before were given the Magic cap
    book.generation = {**book.generation, "template_id": str(template.id), "budget_pinned": True}
    await db.commit()
    return True


async def classic_availability(db: AsyncSession) -> dict[str, dict[str, list[str]]]:
    """theme slug → art style → the looks with a live template, e.g. {"graduation": {"watercolor": ["boy"]}}.
    Classic is offered only where this lists the child's look (Addendum 4 §1A)."""
    rows = (
        await db.execute(
            select(ThemeRow.slug, ClassicTemplate.art_style, ClassicTemplate.variant)
            .join(ThemeRow, ThemeRow.id == ClassicTemplate.theme_id)
            .where(ClassicTemplate.status == TemplateStatus.live)
            .order_by(ClassicTemplate.art_style, ClassicTemplate.variant)
        )
    ).all()
    out: dict[str, dict[str, list[str]]] = {}
    for slug, style, variant in rows:
        out.setdefault(slug, {}).setdefault(style, []).append(variant)
    return out
