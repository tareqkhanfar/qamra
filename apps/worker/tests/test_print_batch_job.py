"""The printer's email for a print batch: the manifest CSV stored as the bundle, a link token (only its hash
kept), one link per file, once per send; no printer address means no token and no email."""

import re
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from qamra_core.db.models import NotificationStatus, PrintBatch, PrintBatchStatus
from qamra_core.printing import token_hash
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.print_batches import send_batch
from qamra_worker.notify.email import FakeEmailSender

BASE = "https://qamra.test"
VALUES: dict[str, Any] = {
    "printer_email": "orders@printer.test",
    "printer_link_days": 14,
    "support_email": "",
}


def _batch(db: Session, status: PrintBatchStatus = PrintBatchStatus.sent) -> PrintBatch:
    items = [
        {
            "n": n,
            "order": f"QM-PRNT0{n}",
            "sku": "magic-hard-21",
            "format": "hardcover",
            "size": "21",
            "copies": n,
            "extras": ["gift-box"] if n == 2 else [],
            "interior_key": f"children/x/books/{n}/files/interior.pdf",
            "cover_key": f"children/x/books/{n}/files/cover.pdf",
            # the second is a family book: its sticker sheet is printed apart
            "inserts": {"stickers": f"children/x/books/{n}/files/inserts/stickers.pdf"} if n == 2 else {},
        }
        for n in (1, 2)
    ]
    batch = PrintBatch(
        id=uuid.uuid4(),
        batch_date=date(2026, 9, 29),
        status=status,
        manifest={"sends": 1, "items": items, "orders": ["QM-PRNT01", "QM-PRNT02"]},
    )
    db.add(batch)
    db.commit()
    return batch


def test_the_printer_gets_one_link_per_file_once(db: Session, storage: ObjectStorage) -> None:
    batch = _batch(db)
    sender = FakeEmailSender()
    now = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    assert send_batch(db, storage, sender, str(batch.id), BASE, VALUES, now) == "sent"
    [mail] = sender.outbox
    assert mail.to == "orders@printer.test" and "3 نسخة" in mail.subject
    links = re.findall(rf"{BASE}/api/printer/([A-Za-z0-9_-]+)/files/(\d)/(interior|cover)", mail.text)
    assert {(n, kind) for _, n, kind in links} == {
        ("1", "interior"),
        ("1", "cover"),
        ("2", "interior"),
        ("2", "cover"),
    }
    token = links[0][0]
    db.refresh(batch)
    assert batch.printer_token_hash == token_hash(token) and token not in str(batch.manifest)
    assert batch.printer_token_expires_at == datetime(2026, 10, 13, 9, 0, tzinfo=UTC)
    assert batch.printer_notified_at == now
    assert batch.bundle_key == f"print-batches/2026/09/{batch.id}/manifest.csv"
    csv = storage.get(batch.bundle_key).decode("utf-8-sig")
    header = "n,order,sku,format,size,copies,extras,interior_file,cover_file,gift,gift_message"
    header += ",insert_files"
    assert csv.splitlines()[0] == header
    assert "002-QM-PRNT02-cover.pdf" in csv and "gift-box" in csv and "children/" not in csv
    assert "002-QM-PRNT02-insert-stickers.pdf" in csv and "001-QM-PRNT01-insert" not in csv
    assert "/files/2/inserts/stickers" in mail.text and "ورقة الملصقات" in mail.text

    # the same send again (a duplicated job): nothing new, the printer's link keeps working
    assert send_batch(db, storage, sender, str(batch.id), BASE, VALUES, now) == "duplicate"
    assert len(sender.outbox) == 1 and batch.printer_token_hash == token_hash(token)

    # an admin resend: a new token replaces the old one
    batch.manifest = {**batch.manifest, "sends": 2}
    db.commit()
    assert send_batch(db, storage, sender, str(batch.id), BASE, VALUES, now) == "sent"
    db.refresh(batch)
    assert len(sender.outbox) == 2 and batch.printer_token_hash != token_hash(token)


def test_no_printer_address_means_no_link(db: Session, storage: ObjectStorage) -> None:
    batch = _batch(db)
    sender = FakeEmailSender()
    assert send_batch(db, storage, sender, str(batch.id), BASE, {**VALUES, "printer_email": ""}) == "skipped"
    db.refresh(batch)
    assert (
        sender.outbox == [] and batch.printer_token_hash is None and batch.bundle_key
    )  # the CSV is still built
    open_batch = _batch(db, PrintBatchStatus.open)
    assert send_batch(db, storage, sender, str(open_batch.id), BASE, VALUES) == "not_sent"


def test_a_failed_printer_email_is_recorded(db: Session, storage: ObjectStorage) -> None:
    from qamra_core.db.models import Notification

    batch = _batch(db)
    try:
        send_batch(db, storage, FakeEmailSender(fail=True), str(batch.id), BASE, VALUES)
    except Exception as e:  # RQ retries the job
        assert type(e).__name__ == "SMTPServerDisconnected"
    note = db.query(Notification).filter(Notification.print_batch_id == batch.id).one()
    assert note.status == NotificationStatus.failed
    assert send_batch(db, storage, FakeEmailSender(), str(batch.id), BASE, VALUES) == "sent"
