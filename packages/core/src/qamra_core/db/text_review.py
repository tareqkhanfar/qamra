"""Staff edits of a story book's words in the admin review, before «تأكيد» (plans/admin-story-text-review.md).

One row per saved change: which words (a story page, or the title, the dedication, the parent's message,
«للأهل», the back-cover blurb), the text before and after, who and when, and the note staff wrote when they
kept words the instant screen flagged. The text carries the child's name, so the rows live and die with the
book (ON DELETE CASCADE: «احذف كل بيانات طفلي» removes them); `audit_logs` only gets ids and action names.
"""

import uuid

from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qamra_core.db.base import Base, CreatedAtMixin, IdMixin

PAGE = "page"  # a story page (`beat` says which)
STORY_FIELDS = ("title", "dedication", "parent_message", "parents_lesson", "parents_questions", "blurb")


class BookTextEdit(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "book_text_edits"

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(24))  # PAGE or one of STORY_FIELDS
    beat: Mapped[int | None] = mapped_column(SmallInteger)  # the theme page, for PAGE
    old_text: Mapped[str | None] = mapped_column(Text)
    new_text: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16), default="edit")  # edit | revert (to the generated words)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(300))  # why words the instant screen flagged were kept
    screen: Mapped[list[str]] = mapped_column(JSONB, default=list)  # what the instant screen found
