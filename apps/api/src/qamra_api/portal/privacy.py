"""«Delete all my child's data» (CLAUDE.md §3.1) reaches the class book too.

A child's own copy (cover, print files) lives under the child's storage prefix and goes with it. The class's
shared pictures that show the child's drawn character, and the combined print file with their copy, are
removed here as well; those pages are drawn again without the child when the school next draws the class.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import Child, PageStatus
from qamra_core.db.portal import ClassBook, ClassBookPage
from qamra_core.storage import ObjectStorage


def thumb_of(key: str) -> str:
    """The worker keeps a small JPEG beside every picture: …/raw/NN.png → …/thumb/NN.jpg."""
    return key.replace("/raw/", "/thumb/").rsplit(".", 1)[0] + ".jpg"


async def forget_in_class_book(db: AsyncSession, storage: ObjectStorage, child: Child) -> int:
    """Removes the child from their class book; returns how many shared pictures were deleted."""
    if child.classroom_id is None:
        return 0
    cb = (
        await db.execute(select(ClassBook).where(ClassBook.classroom_id == child.classroom_id))
    ).scalar_one_or_none()
    if cb is None:
        return 0
    cid = str(child.id)
    removed = 0
    pages = (await db.execute(select(ClassBookPage).where(ClassBookPage.class_book_id == cb.id))).scalars()
    for page in pages:
        if cid not in (page.child_ids or []):
            continue
        keys = [page.image_key, page.print_image_key, thumb_of(page.image_key) if page.image_key else None]
        for key in keys:
            if key:
                storage.delete(key)
        page.image_key = page.print_image_key = None
        page.status = PageStatus.pending
        page.child_ids = [c for c in page.child_ids if c != cid]
        removed += 1
    plan = dict(cb.plan or {})
    plan["children"] = [c for c in plan.get("children") or [] if c != cid]
    plan["pages"] = [
        {**p, "children": [c for c in p.get("children") or [] if c != cid]} for p in plan.get("pages", [])
    ]
    cb.plan = plan
    bundle = dict(cb.bundle or {})
    if bundle.get("combined_key"):
        storage.delete(str(bundle["combined_key"]))
        bundle["combined_key"] = None
    bundle["copies"] = [c for c in bundle.get("copies") or [] if c.get("child_id") != cid]
    cb.bundle = bundle
    if removed:
        cb.flags = list(dict.fromkeys([*(cb.flags or []), "child_removed"]))
    return removed
