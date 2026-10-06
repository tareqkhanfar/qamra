"""Customer emails from the API: enqueued on the worker's default queue, sent by `qamra_worker.jobs.notify`.

Only these order moments email the customer (the rest stay in the order history): placed, confirmed,
printing, shipped, delivered; and a book's "ready to read" once staff confirm its words («تأكيد»). An email
is never worth failing a checkout or a status change, so a queue error is logged and swallowed. The job
itself makes sure each order and status (and each book) is emailed once.
"""

import uuid
from collections.abc import Iterable

import structlog
from redis import Redis
from rq import Queue, Retry

from qamra_core.db.models import OrderStatus

log = structlog.get_logger("qamra.api.notify")
EMAIL_QUEUE = "default"
JOB_TIMEOUT = 120
ORDER_EMAIL_STATUSES = frozenset(
    {OrderStatus.confirmed, OrderStatus.printing, OrderStatus.shipped, OrderStatus.delivered}
)


def _enqueue(connection: Redis, func_path: str, *args: object) -> None:
    try:
        Queue(EMAIL_QUEUE, connection=connection).enqueue(
            func_path, *args, job_timeout=JOB_TIMEOUT, retry=Retry(max=3, interval=[60, 300, 900])
        )
    except Exception as e:
        log.warning("notify.enqueue_failed", func=func_path, error=type(e).__name__)


def order_placed(connection: Redis, order_id: uuid.UUID) -> None:
    _enqueue(connection, "qamra_worker.jobs.notify.send_order_email", str(order_id), "placed")


def order_statuses(connection: Redis, order_id: uuid.UUID, statuses: Iterable[OrderStatus]) -> None:
    """One email per status that has one (a multi-step move may pass through several)."""
    for status in statuses:
        if status in ORDER_EMAIL_STATUSES:
            _enqueue(connection, "qamra_worker.jobs.notify.send_order_email", str(order_id), status.value)


def book_ready(connection: Redis, book_id: uuid.UUID) -> None:
    """Staff confirmed the book's words («تأكيد»): the family can read it now (once per book)."""
    _enqueue(connection, "qamra_worker.jobs.notify.send_book_email", str(book_id), "book_ready")


def print_batch_sent(connection: Redis, batch_id: uuid.UUID) -> None:
    _enqueue(connection, "qamra_worker.jobs.print_batches.send_to_printer", str(batch_id))
