"""The free cover (Addendum 9): one small hero edit on the theme's live Classic cover, burned-in title and
preview mark, and a story-size copy for sharing. A few cents, logged and capped (`free_cover_budget_usd`).

The likeness reference costs nothing new: the child's identity portrait when one exists, else the approved
character sheet, else the photo itself. The photo then gets its deletion time: 24 hours after upload.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.cost import CostEntry
from qamra_ai.errors import QamraError
from qamra_ai.pipeline import cover_art
from qamra_ai.pipeline.assemble import split_title
from qamra_ai.pipeline.budget import Budget, BudgetExceeded
from qamra_ai.pipeline.classic import free_cover_edit
from qamra_ai.pipeline.classic_geometry import HeroBox, mirror
from qamra_ai.pipeline.models import Lang
from qamra_ai.pipeline.theme import load_style
from qamra_core.db.classic import (
    ChildPortrait,
    ClassicTemplate,
    ClassicTemplatePage,
    FreeCover,
    FreeCoverStatus,
)
from qamra_core.db.models import Character, CharacterStatus, Child, ChildPhoto, GenerationCost, PhotoStatus
from qamra_core.storage import ObjectStorage
from qamra_pdf.arabic_names import genitive
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_classic_runtime
from qamra_worker.jobs.books import ai_child, resolved_settings
from qamra_worker.jobs.classic import get_bytes, template_lang, template_theme
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.free_cover")
PHOTO_HOURS = 24  # a free cover's photo is deleted a day after upload unless a book keeps it sooner


def cover_key(cover: FreeCover, name: str) -> str:
    return f"children/{cover.child_id}/free-covers/{cover.id}/{name}"


@dataclass
class FreeCoverSink:
    """Its cost rows (`free_cover:<step>`, no book) and the cover's own total."""

    db: Session
    cover: FreeCover

    def __call__(self, entry: CostEntry) -> None:
        usd = Decimal(str(round(entry.usd, 5)))
        self.db.add(
            GenerationCost(
                book_id=None,
                child_id=self.cover.child_id,
                step=f"free_cover:{entry.step}"[:64],
                provider=entry.provider[:32],
                model=entry.model[:100],
                units=entry.units,
                usd=usd,
                estimated=entry.estimated,
            )
        )
        self.cover.cost_usd = (self.cover.cost_usd or Decimal("0")) + usd
        self.db.commit()


def reference(db: Session, storage: ObjectStorage, child: Child, style: str) -> tuple[str, bytes, str] | None:
    """(kind, image, label): the identity portrait, else the approved character sheet, else the photo."""
    portrait = db.scalar(
        select(ChildPortrait).where(ChildPortrait.child_id == child.id, ChildPortrait.art_style == style)
    )
    if (data := get_bytes(storage, portrait.image_key if portrait else None)) is not None:
        return "portrait", data, "the child's identity portrait"
    sheet = db.scalars(
        select(Character)
        .where(
            Character.child_id == child.id,
            Character.status == CharacterStatus.approved,
            Character.sheet_image_key.is_not(None),
        )
        .order_by(Character.approved_at.desc())
    ).first()
    if (data := get_bytes(storage, sheet.sheet_image_key if sheet else None)) is not None:
        return "sheet", data, "the child's character reference sheet (use the front view)"
    photo = db.scalars(
        select(ChildPhoto)
        .where(
            ChildPhoto.child_id == child.id,
            ChildPhoto.status == PhotoStatus.accepted,
            ChildPhoto.storage_key.is_not(None),
        )
        .order_by(ChildPhoto.created_at.desc())
    ).first()
    if (data := get_bytes(storage, photo.storage_key if photo else None)) is not None:
        return "photo", data, "a photo of the child"
    return None


def schedule_photo_deletion(db: Session, child: Child, now: datetime) -> None:
    """Addendum 9: a free cover's photo is deleted 24 hours after upload (the cleanup job does it)."""
    for photo in db.scalars(select(ChildPhoto).where(ChildPhoto.child_id == child.id)).all():
        due = photo.created_at + timedelta(hours=PHOTO_HOURS) if photo.created_at else now
        if photo.delete_after is None or photo.delete_after > due:
            photo.delete_after = due


def _fail(db: Session, cover: FreeCover, reason: str) -> dict[str, Any]:
    cover.status, cover.error = FreeCoverStatus.failed, reason[:300]
    db.commit()
    return {"status": "failed", "reason": reason}


async def run_free_cover(
    db: Session, storage: ObjectStorage, cover: FreeCover, *, offline: bool | str = False
) -> dict[str, Any]:
    resolved = resolved_settings(db)
    core = get_settings()
    settings = ai_settings(resolved, core, offline=offline)
    rt = make_classic_runtime(settings)
    rt.on_cost = FreeCoverSink(db, cover)
    rt.budget = Budget(cap_usd=float(Decimal(str(resolved.values["free_cover_budget_usd"]))))
    child = db.get(Child, cover.child_id)
    template = db.get(ClassicTemplate, cover.template_id) if cover.template_id else None
    page = db.scalar(
        select(ClassicTemplatePage).where(
            ClassicTemplatePage.template_id == cover.template_id, ClassicTemplatePage.beat == 0
        )
    )
    art = get_bytes(storage, page.image_key if page else None)
    if child is None or template is None or page is None or art is None:
        return _fail(db, cover, "the story's cover template is missing")
    ref = reference(db, storage, child, template.art_style)
    if ref is None:
        return _fail(db, cover, "no photo or character to draw from")
    kind, ref_image, ref_label = ref
    box = HeroBox.from_dict(page.hero_box)
    if template_lang(template) != cover.lang:  # an English cover reads left to right
        art = await asyncio.to_thread(mirror, art)
        box = box.mirrored() if box else None
    theme = template_theme(template)
    ai = ai_child(child)
    try:
        res = await free_cover_edit(
            rt,
            child=ai,
            style=load_style(template.art_style),
            cover=art,
            box=box,
            reference=ref_image,
            ref_label=ref_label,
            scene=theme.cover.scene if theme.cover else "",
            seed=int(cover.id.int % 2_000_000_000),
        )
    except (BudgetExceeded, QamraError) as e:
        return _fail(db, cover, f"{type(e).__name__}: {e}")
    if res.page is None:
        return _fail(db, cover, "the cover could not be drawn: " + ", ".join(res.flags))
    lang: Lang = "en" if cover.lang == "en" else "ar"
    name, subtitle = split_title(theme.title(lang, ai.gender, ai.name), ai.name)
    brand_ar, brand_en = core.brand_name_ar, core.brand_name_en
    mark = (
        cover_art.printable(f"معاينة · {brand_ar}", f"Preview · {brand_en}")
        if lang == "ar"
        else (f"Preview · {brand_en}")
    )
    finished = cover_art.watermarked(cover_art.titled(res.page, name, subtitle), mark)
    headline = f"غلاف حكاية {genitive(ai.name)}" if lang == "ar" else f"{ai.name}'s storybook cover"
    footer = f"{brand_ar if lang == 'ar' else brand_en} · {core.brand_domain}"
    story = cover_art.story(
        finished,
        cover_art.printable(headline, f"{ai.name}'s storybook cover"),
        cover_art.printable(footer, core.brand_domain),
    )
    cover.image_key, cover.story_key = cover_key(cover, "cover.jpg"), cover_key(cover, "story.jpg")
    storage.put(cover.image_key, cover_art.jpeg(finished), "image/jpeg")
    storage.put(cover.story_key, cover_art.jpeg(story), "image/jpeg")
    cover.reference = kind
    cover.qa = res.qa.model_dump() if res.qa else {"unchecked": True}
    cover.status, cover.error = FreeCoverStatus.ready, None
    if kind == "photo":
        schedule_photo_deletion(db, child, datetime.now(UTC))
    db.commit()
    log.info("free_cover.ready", cover=str(cover.id), cost=float(cover.cost_usd), reference=kind)
    return {"status": "ready", "cost_usd": float(cover.cost_usd), "reference": kind}


def draw_free_cover(cover_id: str) -> dict[str, Any]:
    """RQ entry point, enqueued by the free cover endpoint."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        cover = db.get(FreeCover, cover_id)
        if cover is None:
            return {"status": "missing"}
        try:
            return asyncio.run(run_free_cover(db, storage, cover))
        except Exception as e:
            db.rollback()
            cover = db.get(FreeCover, cover_id)
            if cover is not None:
                _fail(db, cover, f"{type(e).__name__}: {str(e)[:200]}")
            log.exception("free_cover.failed", cover=cover_id)
            raise
