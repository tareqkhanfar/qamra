"""The guardian's optional choice to keep the child's original photo for later books (owner, 2026-10-16).

By default the original photo is deleted `photo_retention_hours` (24 h at most) after the character is
approved (CLAUDE.md §3.1). A guardian may opt in, separately and never pre-ticked, to keep it so a later
book, workbook or art style draws from it without a new upload. The choice is its own versioned consent
(`Consent.scope` `photo_keep`, with time, IP and user agent); turning it off sets `Consent.withdrawn_at`.

While it is on, the photo stays encrypted in private storage under the same access rules (the guardian's
private no-store route, signed URLs of 15 minutes at most for the image model), the 24-hour rule does not
delete it, and the cleanup deletes it `kept_photo_retention_months` (admin setting, default 12) after its
last use (`ChildPhoto.last_used_at`: a drawing or cover made from it, or the opt-in itself). Turning it
off schedules the deletion within `photo_retention_hours`; «احذفوا الصورة الآن» and "delete all my child's
data" delete it at once.
"""

import calendar
import uuid
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, Exists, select
from sqlalchemy.orm import InstrumentedAttribute

from qamra_core.db.models import ChildPhoto, Consent

KEEP_SCOPE = "photo_keep"
# the text of the choice (web messages: photoKeep.consent): a new wording gets a new version
KEEP_CONSENT_VERSION = "photo-keep-2026-10"
RETENTION_SETTING = "kept_photo_retention_months"
DEFAULT_RETENTION_MONTHS = 12


def keeps_photo(
    child_id: InstrumentedAttribute[uuid.UUID] | ColumnElement[uuid.UUID] | uuid.UUID,
) -> Exists:
    """SQL: the child's guardian chose to keep the photo and has not taken it back."""
    return (
        select(Consent.id)
        .where(Consent.child_id == child_id, Consent.scope == KEEP_SCOPE, Consent.withdrawn_at.is_(None))
        .exists()
    )


def add_months(moment: datetime, months: int) -> datetime:
    """The same day `months` calendar months later (earlier when negative), or the month's last day."""
    index = moment.year * 12 + moment.month - 1 + months
    year, month = divmod(index, 12)
    day = min(moment.day, calendar.monthrange(year, month + 1)[1])
    return moment.replace(year=year, month=month + 1, day=day)


def last_use(photo: ChildPhoto) -> datetime:
    return photo.last_used_at or photo.created_at


def kept_until(photo: ChildPhoto, months: int) -> datetime:
    """When the cleanup deletes a kept photo that is not used again."""
    return add_months(last_use(photo), months)


def schedule_after_opt_out(photo: ChildPhoto, now: datetime, hours: int) -> None:
    """The choice was turned off: the photo goes within `hours`. A photo whose character is not approved yet
    keeps the usual rules (deleted `hours` after the approval, or with the abandoned drafts)."""
    if photo.delete_after is None:
        return
    due = now + timedelta(hours=hours)
    if photo.delete_after <= now or photo.delete_after > due:
        photo.delete_after = due  # an overdue date gets the same grace, so an accidental tap can be undone
