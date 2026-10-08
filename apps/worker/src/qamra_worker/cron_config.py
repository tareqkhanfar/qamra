"""`rq cron qamra_worker.cron_config` — periodic jobs."""

from rq import cron

from qamra_worker.jobs.downloads import scan_ready_lines
from qamra_worker.jobs.maintenance import run_cleanup
from qamra_worker.jobs.studio import run_scheduled_publish
from qamra_worker.queues import MAINTENANCE

# Every 15 minutes, so "deleted within 24h after approval" holds with a wide margin.
cron.register(run_cleanup, MAINTENANCE, interval=15 * 60, job_timeout=600)
# The template studio's scheduled go-lives (Addendum 4 §3.5): within 5 minutes of their date.
cron.register(run_scheduled_publish, MAINTENANCE, interval=5 * 60, job_timeout=120)
# Digital delivery: a digital line whose files became ready gets its copies and its email within 5 minutes.
cron.register(scan_ready_lines, MAINTENANCE, interval=5 * 60, job_timeout=300)
