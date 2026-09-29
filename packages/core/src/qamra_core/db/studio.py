"""Template studio (Addendum 4 §3): theme versions with review, publishing, history and rollback.

The live definition stays in `themes.definition`, which new books read. Every definition a theme has had,
or may have next, is a `theme_versions` row: draft → in_review → approved → live. A live version replaced by
a newer one becomes `retired`, and a rollback makes it live again.
- At most one version per theme is open (draft, in review or approved), so edits never fork.
- Books keep the definition they started with (`books.generation.theme_def`).
- Classic templates keep theirs (`generation.theme_def`, `theme_version`) until their texts are refreshed:
  their art never changes with a text edit.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qamra_core.db.base import Base, IdMixin, TimestampMixin, str_enum


class ThemeVersionStatus(enum.StrEnum):
    draft = "draft"  # being edited
    in_review = "in_review"  # waiting for a reviewer
    approved = "approved"  # ready to publish
    live = "live"  # the theme's definition now (exactly one per theme)
    retired = "retired"  # was live until a newer version replaced it; a rollback publishes it again


OPEN_STATUSES = (ThemeVersionStatus.draft, ThemeVersionStatus.in_review, ThemeVersionStatus.approved)


class ThemeVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "theme_versions"
    __table_args__ = (
        UniqueConstraint("theme_id", "version"),
        Index("uq_theme_versions_live", "theme_id", unique=True, postgresql_where=text("status = 'live'")),
        Index(
            "uq_theme_versions_open",
            "theme_id",
            unique=True,
            postgresql_where=text("status IN ('draft', 'in_review', 'approved')"),
        ),
    )

    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[ThemeVersionStatus] = mapped_column(
        str_enum(ThemeVersionStatus, "theme_version_status"), default=ThemeVersionStatus.draft
    )
    source: Mapped[str] = mapped_column(String(16), default="studio")  # file (content/themes) | studio
    base_version: Mapped[int | None] = mapped_column(Integer)  # the version it was copied from
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(String(300))  # what changed, in the editor's words
    # {"translate": {"state": queued|running|done|failed, "estimate_usd", "cost_usd", "at", "error"}}
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # last time it went live
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
