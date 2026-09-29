"""The printer's email for a print batch (CLAUDE.md §7 step 7, Phase 3).

The API freezes the batch manifest when an admin sends it. This job stores the manifest as CSV beside the
files (the bundle), issues the printer's link token and emails one link per file. A link is
`/api/printer/{token}/files/{n}/{interior|cover}`: the API checks the token and redirects to a signed URL of
at most 15 minutes, so the email never carries a long-lived storage address. Resending issues a new token.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.orm import Session

from qamra_core.db.models import NotificationStatus, PrintBatch, PrintBatchStatus
from qamra_core.printing import (
    INSERT_LABELS,
    batch_code,
    file_name,
    insert_file_name,
    manifest_csv,
    new_token,
)
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.jobs.notify import FORMATS, base_values, sender_and_values
from qamra_worker.notify.email import EmailSender
from qamra_worker.notify.ledger import claim, deliver, finish
from qamra_worker.notify.templates import Item, render
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.print_batches")
LANG = "ar"  # the print partner is local
KIND_LABEL = {"interior": "الصفحات الداخلية", "cover": "الغلاف"}


def bundle_key(batch: PrintBatch) -> str:
    return f"print-batches/{batch.batch_date:%Y/%m}/{batch.id}/manifest.csv"


def _items(manifest: dict[str, Any], link: str) -> list[Item]:
    rows = []
    for item in manifest.get("items", []):
        fmt = FORMATS[LANG].get(str(item.get("format")), str(item.get("format") or ""))
        head = f"{int(item['n']):03d} · {item['order']} · {fmt} {item.get('size') or ''} × {item['copies']}"
        for kind in ("interior", "cover"):
            rows.append(
                Item(
                    f"{head} — {KIND_LABEL[kind]} ({file_name(item, kind)})",
                    f"{link}/files/{item['n']}/{kind}",
                )
            )
        for name in item.get("inserts") or {}:  # a family book's sticker sheet and card stock
            label = INSERT_LABELS.get(name, name)
            rows.append(
                Item(
                    f"{head} — {label} ({insert_file_name(item, name)})",
                    f"{link}/files/{item['n']}/inserts/{name}",
                )
            )
    return rows


def send_batch(
    db: Session,
    storage: ObjectStorage,
    sender: EmailSender,
    batch_id: str,
    base_url: str,
    values: dict[str, Any],
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(UTC)
    batch = db.get(PrintBatch, uuid.UUID(batch_id))
    if batch is None or batch.status == PrintBatchStatus.open or not batch.manifest.get("items"):
        return "not_sent"
    sends = int(batch.manifest.get("sends") or 1)
    note = claim(db, f"batch:{batch.id}:send:{sends}", "printer_batch", print_batch_id=batch.id)
    if note is None:
        return "duplicate"
    batch.bundle_key = bundle_key(batch)
    storage.put(batch.bundle_key, manifest_csv(batch.manifest), "text/csv; charset=utf-8")
    printer = str(values.get("printer_email") or "").strip()
    if not printer:
        db.commit()
        finish(db, note, NotificationStatus.skipped, "no_printer_email")
        log.warning("print_batch.no_printer_email", batch=str(batch.id))
        return NotificationStatus.skipped.value
    token, digest = new_token()
    batch.printer_token_hash = digest
    batch.printer_token_expires_at = now + timedelta(days=int(values.get("printer_link_days") or 14))
    db.commit()
    link = f"{base_url}/api/printer/{token}"
    items = batch.manifest["items"]
    rendered = render(
        "printer_batch",
        LANG,
        {
            **base_values(values, LANG),
            "code": batch_code(batch.id, batch.batch_date),
            "date": f"{batch.batch_date:%Y-%m-%d}",
            "books": len(items),
            "copies": sum(int(i["copies"]) for i in items),
            "expires": f"{batch.printer_token_expires_at:%Y-%m-%d}",
            "manifest_url": f"{link}/manifest.csv",
        },
        _items(batch.manifest, link),
    )
    status = deliver(db, sender, note, printer, rendered)
    if status == NotificationStatus.sent:
        batch.printer_notified_at = now
        db.commit()
    return status.value


def send_to_printer(batch_id: str) -> str:
    """RQ entry point (enqueued by the admin's «أرسل للمطبعة» and «أعد الإرسال»)."""
    context.init_process()
    with context.db_session() as db:
        sender, values = sender_and_values(db)
        return send_batch(
            db, context.storage(), sender, batch_id, get_settings().web_base_url.rstrip("/"), values
        )
