"""`rq cron qamra_worker.cron_config` — periodic jobs."""

from rq import cron

from qamra_worker.jobs.maintenance import run_cleanup
from qamra_worker.queues import MAINTENANCE

# Every 15 minutes, so "deleted within 24h after approval" holds with a wide margin.
cron.register(run_cleanup, MAINTENANCE, interval=15 * 60, job_timeout=600)
