"""At most one email per `dedupe_key` (notifications table): jobs can run twice, people hear once.

`claim` takes the right to send a key; a failed attempt (or one stuck by a crashed worker) can be claimed
again, up to MAX_ATTEMPTS. `deliver` sends through the configured sender and records the outcome — without
the address, subject or body (they can name a child).
"""

import smtplib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, func, or_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from qamra_core.db.models import Notification, NotificationStatus
from qamra_worker.notify.email import EmailMessage, EmailSender
from qamra_worker.notify.templates import Rendered

log = structlog.get_logger("qamra.worker.notify")
MAX_ATTEMPTS = 4
STALE = timedelta(minutes=10)
N = NotificationStatus


def claim(db: Session, key: str, template: str, **refs: Any) -> Notification | None:
    """The row to send under, or None when this key was already handled (or is being sent right now)."""
    row_id = db.execute(
        insert(Notification)
        .values(
            id=uuid.uuid4(),
            dedupe_key=key,
            template=template,
            channel="email",
            status=N.pending,
            attempts=1,
            **refs,
        )
        .on_conflict_do_nothing(index_elements=["dedupe_key"])
        .returning(Notification.id)
    ).scalar_one_or_none()
    if row_id is None:
        stale = datetime.now(UTC) - STALE
        row_id = db.execute(
            update(Notification)
            .where(
                Notification.dedupe_key == key,
                Notification.attempts < MAX_ATTEMPTS,
                or_(
                    Notification.status == N.failed,
                    and_(Notification.status == N.pending, Notification.updated_at < stale),
                ),
            )
            .values(status=N.pending, attempts=Notification.attempts + 1, updated_at=func.now())
            .returning(Notification.id)
        ).scalar_one_or_none()
    db.commit()
    return db.get(Notification, row_id) if row_id is not None else None


def finish(db: Session, note: Notification, status: NotificationStatus, error: str | None = None) -> None:
    note.status = status
    note.error = error[:200] if error else None
    if status in (N.sent, N.logged):
        note.sent_at = datetime.now(UTC)
    db.commit()


def _reason(e: Exception) -> str:
    """The kind of failure only: SMTP error texts can quote the recipient's address."""
    if isinstance(e, smtplib.SMTPResponseException):
        return f"{type(e).__name__} {e.smtp_code}"
    return type(e).__name__


def deliver(
    db: Session, sender: EmailSender, note: Notification, to: str, rendered: Rendered
) -> NotificationStatus:
    message = EmailMessage(to=to, subject=rendered.subject, text=rendered.text, html=rendered.html)
    try:
        sender.send(message)
    except Exception as e:
        finish(db, note, N.failed, _reason(e))
        log.warning("email.failed", notification=str(note.id), template=note.template, error=_reason(e))
        raise  # RQ retries the job; `claim` lets the retry take the key again
    status = N.logged if sender.name == "log" else N.sent
    finish(db, note, status)
    log.info(
        "email.done", notification=str(note.id), template=note.template, status=status.value, via=sender.name
    )
    return status
