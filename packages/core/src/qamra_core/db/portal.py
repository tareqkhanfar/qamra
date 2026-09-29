"""The kindergarten portal (CLAUDE.md §8 B2B, Addendum 1 §2 «كتاب الصف», Addendum 4 §1C).

- `ChildInvite`: one tokenized, expiring link per child. The parent opens it, signs in, and the child becomes
  theirs (`children.guardian_user_id`); consent, the photo and the character then follow the parent flow. The
  school only ever sees statuses, never a photo.
- `ClassBook`: one per classroom. One theme and one line (Classic or Magic) for the whole class, the teacher's
  message, the school logo and the class photo, and the page plan (which children appear on which page).
- `ClassBookPage`: a shared page, drawn once for the class, with the children assigned to its slots.
  Each child's own copy (personal cover, portrait page, print files) is an ordinary `Book` row whose
  `generation["class_book_id"]` points here, so the admin review queue and print approval apply unchanged.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qamra_core.db.base import Base, IdMixin, TimestampMixin, str_enum
from qamra_core.db.models import PageStatus


class ClassBookStatus(enum.StrEnum):
    setup = "setup"  # the school is choosing the theme, the line, the message and the photos
    generating = "generating"  # the batch is drawing
    review = "review"  # drawn: the school reviews the pages and covers
    approved = "approved"  # the school approved; its copies wait in the admin review queue
    ordered = "ordered"  # one order and one invoice for the class
    printing = "printing"  # the print bundle is built and handed to the printer
    failed = "failed"


class ChildInvite(IdMixin, TimestampMixin, Base):
    __tablename__ = "child_invites"

    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), unique=True, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"), index=True
    )
    # A capability link sent by the school (WhatsApp, SMS): stored as-is so the school can copy it again.
    token: Mapped[str] = mapped_column(String(64), unique=True)
    parent_name: Mapped[str | None] = mapped_column(String(120))  # from the school's list
    parent_phone: Mapped[str | None] = mapped_column(String(32))
    parent_email: Mapped[str | None] = mapped_column(String(254))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # when the school copied or shared the link
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClassBook(IdMixin, TimestampMixin, Base):
    __tablename__ = "class_books"

    classroom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"), unique=True, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    theme_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("themes.id", ondelete="RESTRICT"))
    line: Mapped[str] = mapped_column(String(16), default="magic")  # classic | magic (Addendum 4 §1C)
    art_style: Mapped[str] = mapped_column(String(40), default="watercolor")
    language: Mapped[str] = mapped_column(String(2), default="ar")
    min_appearances: Mapped[int] = mapped_column(SmallInteger, default=2)
    teacher_message: Mapped[str | None] = mapped_column(Text)
    # The real class photo, printed on the school page. Stored privately; the school admin confirms that the
    # parents agreed to it being printed.
    class_photo_key: Mapped[str | None] = mapped_column(String(300))
    class_photo_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    class_photo_consent_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    options: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # portraits, friends page…
    status: Mapped[ClassBookStatus] = mapped_column(
        str_enum(ClassBookStatus, "class_book_status"), default=ClassBookStatus.setup
    )
    # {"template": slug, "pages": [{"index", "key", "slots", "children": [child ids]}]}
    plan: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    generation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # seed, models, offline, redraws
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    school_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    school_approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    print_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("print_batches.id", ondelete="SET NULL")
    )
    bundle: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # combined file, per-child names


class ClassBookPage(IdMixin, TimestampMixin, Base):
    __tablename__ = "class_book_pages"
    __table_args__ = (UniqueConstraint("class_book_id", "index"),)

    class_book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("class_books.id", ondelete="CASCADE"), index=True
    )
    index: Mapped[int] = mapped_column(SmallInteger)  # story order, from 1
    scene_key: Mapped[str] = mapped_column(String(64))
    child_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)  # who was drawn on it
    text: Mapped[str | None] = mapped_column(Text)
    image_key: Mapped[str | None] = mapped_column(String(300))
    print_image_key: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[PageStatus] = mapped_column(
        str_enum(PageStatus, "class_page_status"), default=PageStatus.pending
    )
    qa: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # per child: recognizable, likeness
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    attempts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    redraw: Mapped[bool] = mapped_column(Boolean, default=False)  # the school asked for a new drawing
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
