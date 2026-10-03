"""«قلبي يعرف الله» (Addendum 10 §3.3, §10): the scholar's review of every unit, page by page.

A unit's status moves draft → scholar_review → approved, or back to `changes_requested` with the scholar's
notes. Only a staff member with the `scholar` role decides (approve, request changes, answer a
`scholar_decision` point); the reviewer's name and the date are stored with the decision. A volume is sold
and printed only while every one of its units is approved (`qamra_core.islamic_review`).

The units come from the content (`content/islamic/units.yaml`, plus one «front and back matter» unit per
volume); a row here is created the first time a unit is listed. Nothing here is a child's data.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qamra_core.db.base import Base, CreatedAtMixin, IdMixin, TimestampMixin, str_enum


class ReviewStatus(enum.StrEnum):
    draft = "draft"  # being written; the scholar has not seen it
    scholar_review = "scholar_review"  # waiting for the scholar
    changes_requested = "changes_requested"  # the scholar asked for changes (see the notes)
    approved = "approved"  # the scholar signed it off: it may print and sell


class IslamicUnitReview(TimestampMixin, Base):
    __tablename__ = "islamic_unit_reviews"

    unit_id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. "u-allah", "matter-v1"
    volume: Mapped[str] = mapped_column(String(4), index=True)  # V1…V5, R
    status: Mapped[ReviewStatus] = mapped_column(
        str_enum(ReviewStatus, "islamic_review_status"), default=ReviewStatus.draft
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # the last decision (approve or request changes): who, under which name, when, on which previews
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewer_name: Mapped[str | None] = mapped_column(String(120))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # None unless approved
    preview_run: Mapped[str | None] = mapped_column(String(32))  # the previews the scholar decided on


class IslamicReviewEvent(IdMixin, CreatedAtMixin, Base):
    """The unit's history: submissions, decisions and notes (a note may point at a page or a source)."""

    __tablename__ = "islamic_review_events"

    unit_id: Mapped[str] = mapped_column(
        ForeignKey("islamic_unit_reviews.unit_id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(
        String(24)
    )  # submitted | approved | changes_requested | reopened | note
    page: Mapped[int | None] = mapped_column(SmallInteger)  # the page number in the volume
    source_id: Mapped[str | None] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text, default="")
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    author_name: Mapped[str] = mapped_column(String(120), default="")
    scholar: Mapped[bool] = mapped_column(Boolean, default=False)  # written by the scholar


class IslamicScholarDecision(TimestampMixin, Base):
    """The scholar's answer to a `scholar_decision` point of the source register (§3.4): the content follows
    it wherever the source is used. Nobody picks a madhab silently."""

    __tablename__ = "islamic_scholar_decisions"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question: Mapped[str] = mapped_column(Text, default="")  # the point as it was asked
    decision: Mapped[str] = mapped_column(Text)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_by_name: Mapped[str] = mapped_column(String(120))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IslamicReviewer(TimestampMixin, Base):
    """The scholar's own details: the name as it would be printed, and whether they agree to be named in the
    book («راجعه علميًّا: …»). Set by the scholar on the review page."""

    __tablename__ = "islamic_reviewers"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    may_be_named: Mapped[bool] = mapped_column(Boolean, default=False)
    named_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IslamicReviewPreview(TimestampMixin, Base):
    """The latest preview render of a volume for the review page: one PNG per page in private storage."""

    __tablename__ = "islamic_review_previews"

    volume: Mapped[str] = mapped_column(String(4), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | ready | failed
    pages: Mapped[list[str]] = mapped_column(JSONB, default=list)  # storage keys, page 1 first
    cover_key: Mapped[str | None] = mapped_column(String(300))
    problems: Mapped[list[Any]] = mapped_column(JSONB, default=list)  # what the preview build reported
    error: Mapped[str | None] = mapped_column(Text)
    rendered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
