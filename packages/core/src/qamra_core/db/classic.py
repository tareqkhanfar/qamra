"""«قمرة كلاسيك» (Addendum 4 §1A, §3): template books and the child's identity portrait.

- A template is one theme × art style × variant (girl, girl_hijab, boy; a string, so skin and hair variants
  can be added later), drawn once around a placeholder hero and reviewed: draft → in_review → approved → live.
- Each template page keeps its print-resolution image, a small preview, whether the hero is on it, the hero's
  box and the text box (normalized x, y, w, h), a lock, manual redraws and its one-time cost.
- A child's identity portrait (one per art style) lives under the child's storage prefix and is deleted with
  the child: "delete all my child's data" removes it too.
Template images are the shop's artwork, not a child's data: they live under `classic/templates/`.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qamra_core.db.base import Base, IdMixin, TimestampMixin, str_enum
from qamra_core.db.models import PageStatus


class TemplateStatus(enum.StrEnum):
    draft = "draft"  # being drawn or redrawn
    in_review = "in_review"  # drawn; an editor checks every page, the hero boxes and the text boxes
    approved = "approved"  # checked; pages locked
    live = "live"  # used by new Classic books


class TemplateJob(enum.StrEnum):
    idle = "idle"
    queued = "queued"
    running = "running"
    failed = "failed"


class ClassicTemplate(IdMixin, TimestampMixin, Base):
    __tablename__ = "classic_templates"
    __table_args__ = (UniqueConstraint("theme_id", "art_style", "variant"),)

    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("themes.id", ondelete="RESTRICT"), index=True)
    theme_version: Mapped[int] = mapped_column(Integer)
    art_style: Mapped[str] = mapped_column(String(40))
    variant: Mapped[str] = mapped_column(String(40))  # girl | girl_hijab | boy (more later)
    lang: Mapped[str] = mapped_column(
        String(2), default="ar"
    )  # the reading direction the art was laid out for
    status: Mapped[TemplateStatus] = mapped_column(
        str_enum(TemplateStatus, "classic_template_status"), default=TemplateStatus.draft
    )
    job: Mapped[TemplateJob] = mapped_column(
        str_enum(TemplateJob, "classic_template_job"), default=TemplateJob.idle
    )
    source: Mapped[str] = mapped_column(String(16), default="generated")  # generated | sample_book
    source_book_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))
    # theme_def (pinned), seed, outfits, plan, models, placeholder sheet key, progress, offline
    generation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))  # one-time, all runs
    budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # per generation run
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    live_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClassicTemplatePage(IdMixin, TimestampMixin, Base):
    __tablename__ = "classic_template_pages"
    __table_args__ = (UniqueConstraint("template_id", "beat"),)

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classic_templates.id", ondelete="CASCADE"), index=True
    )
    beat: Mapped[int] = mapped_column(SmallInteger)  # theme page index; 0 = cover
    layout: Mapped[str | None] = mapped_column(String(16))  # cover | full | split | spread
    image_key: Mapped[str | None] = mapped_column(String(300))  # print resolution, bleed included
    raw_key: Mapped[str | None] = mapped_column(String(300))  # as drawn
    preview_key: Mapped[str | None] = mapped_column(String(300))  # small JPEG for the studio
    has_hero: Mapped[bool] = mapped_column(Boolean, default=True)
    hero_box: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # {x, y, w, h} in 0..1
    text_box: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # {x, y, w, h, area}
    status: Mapped[PageStatus] = mapped_column(
        str_enum(PageStatus, "classic_page_status"), default=PageStatus.pending
    )
    qa: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    qa_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    attempts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    regen_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))  # one-time


class ChildPortrait(IdMixin, TimestampMixin, Base):
    """The child's identity portrait in one art style, reused by every Classic page and book."""

    __tablename__ = "child_portraits"
    __table_args__ = (UniqueConstraint("child_id", "art_style"),)

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    art_style: Mapped[str] = mapped_column(String(40))
    image_key: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(16))  # sheet | photo
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(100))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # seed, likeness check


class FreeCoverStatus(enum.StrEnum):
    drawing = "drawing"
    ready = "ready"
    failed = "failed"


class FreeCover(IdMixin, TimestampMixin, Base):
    """A free cover (Addendum 9): the child's hero edited onto a theme's Classic cover, small and watermarked.

    One per account and theme. The images live under the child's storage prefix and go with the child.
    """

    __tablename__ = "free_covers"
    __table_args__ = (UniqueConstraint("user_id", "theme_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"))
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("classic_templates.id", ondelete="SET NULL")
    )
    status: Mapped[FreeCoverStatus] = mapped_column(
        str_enum(FreeCoverStatus, "free_cover_status"), default=FreeCoverStatus.drawing
    )
    lang: Mapped[str] = mapped_column(String(2), default="ar")
    image_key: Mapped[str | None] = mapped_column(String(300))  # watermarked cover, 1024 px
    story_key: Mapped[str | None] = mapped_column(String(300))  # 1080 × 1920 for sharing
    reference: Mapped[str | None] = mapped_column(String(16))  # portrait | sheet | photo
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    qa: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
