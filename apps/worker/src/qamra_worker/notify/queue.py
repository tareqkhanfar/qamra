"""Enqueue email jobs from inside other jobs (a book's preview or final files are ready).

Emails run as their own jobs on the default queue: an SMTP hiccup is retried there and never fails or
repeats the (expensive) book job. Outside RQ (scripts, most tests) there is no queue, so nothing is sent.
"""

from typing import Any

import structlog
from redis import Redis
from rq import Queue, Retry, get_current_job

from qamra_core.db.models import Book
from qamra_worker.queues import DEFAULT

log = structlog.get_logger("qamra.worker.notify")
JOB_TIMEOUT = 120
_override: list[Redis | None] = [None]  # tests point this at a fake Redis


def set_connection(connection: Redis | None) -> None:
    _override[0] = connection


def connection() -> Redis | None:
    if _override[0] is not None:
        return _override[0]
    job = get_current_job()
    return job.connection if job is not None else None


def enqueue(func_path: str, *args: Any) -> bool:
    conn = connection()
    if conn is None:
        log.info("notify.no_queue", func=func_path)
        return False
    try:
        Queue(DEFAULT, connection=conn).enqueue(
            func_path, *args, job_timeout=JOB_TIMEOUT, retry=Retry(max=3, interval=[60, 300, 900])
        )
    except Exception as e:  # a notification must never break the job that triggered it
        log.warning("notify.enqueue_failed", func=func_path, error=type(e).__name__)
        return False
    return True


def book_ready(book: Book, mode: str) -> None:
    """After a book's files are rendered: "preview ready" or "book ready" to the parent (never samples)."""
    if book.is_sample:
        return
    event = "book_ready" if mode == "final" else "preview_ready"
    enqueue("qamra_worker.jobs.notify.send_book_email", str(book.id), event)
