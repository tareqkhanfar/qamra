"""The worker queue: routers enqueue jobs by dotted path, so the API never imports worker code."""

from typing import Annotated

from fastapi import Depends, Request
from rq import Queue, Retry

JOB_TIMEOUT = 3600


def get_queue(request: Request) -> Queue:
    return Queue("generation", connection=request.app.state.rq_redis)


QueueDep = Annotated[Queue, Depends(get_queue)]


def enqueue(queue: Queue, func_path: str, *args: object) -> None:
    queue.enqueue(func_path, *args, job_timeout=JOB_TIMEOUT, retry=Retry(max=2, interval=[60, 300]))
