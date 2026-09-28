# Runbook: monitoring and incidents

## Monitoring

- **Health check:** `infra/scripts/monitor.sh` runs every 5 minutes (from `/etc/cron.d/qamra-ops`) and logs to `/var/log/qamra-monitor.log`. It checks:
  - the site through the edge, and the API health through the edge;
  - every container's state and health;
  - the disk (alert above 85%);
  - the last backup (alert after 26 hours);
  - the job queues (alert above 100 waiting jobs).
- **Alerts:** set `ALERT_WEBHOOK_URL` in `/etc/default/qamra-ops` (a Slack-compatible incoming webhook). It posts once when something breaks, and once when it's healthy again.
- **Outside view:** add a free uptime check (e.g. UptimeRobot) on `https://<domain>/healthz` from outside the server; it also catches the whole server going down.
- **Errors:** with `SENTRY_DSN` set, API and worker exceptions go to Sentry without personal data (`send_default_pii=False`).
- **Money:** Admin → Cost & conversion (AI cost per book, the budget stops) and Admin → التقارير (sales, margins, orders under the floor).

## Common incidents

| Symptom | Look | Fix |
|---|---|---|
| The site is down (monitor: "the site (edge) does not answer") | `docker compose ps`; `docker compose logs --tail 100 edge web` | `docker compose up -d`. If the web container fails its health check, see its logs (usually the API is down, see the next row) |
| The API health check fails | `docker compose logs --tail 200 api`; database and redis health | A failed migration: `docker compose logs migrate`; fix and redeploy. Database down: disk full, or check `docker compose logs postgres` |
| Books stuck in «نرسم» | `docker compose logs --tail 200 worker`; the queue length in the monitor log; Admin → queue | Restart the worker (`docker compose restart worker`). An AI provider outage: the fallback provider takes over after 2 failures; a budget stop marks the book failed with `budget_exceeded` |
| The queue keeps growing | provider errors in the worker logs; the cost dashboard | Lower `image_concurrency`, or switch the image provider in Admin → Settings |
| Disk above 85% | `du -sh /var/lib/docker /var/backups/qamra`; `docker system df` | `docker image prune -f`; old backups are pruned by the retention; container logs are capped at 5 × 20 MB each |
| No backup for 26 hours | `/var/log/qamra-backup.log` | Run `infra/scripts/backup.sh` by hand and read the error (the passphrase file, disk, the rclone remote) |
| A parent reports a wrong or unsafe page | Admin → the book → the page | Redraw the page; printed products always go through admin approval first |
| A data deletion request by email | the account email | The parent can do it from the account page («حذف … وكل بياناته»); staff can do it for them. The audit log records it without personal data |
| A secret leaked (JWT, database, R2, AI key) | — | Rotate it: new value in `.env` or Admin → Settings, then `docker compose up -d`. Rotating `JWT_SECRET` signs everyone out |

## Photos: the 24-hour rule

The cron container runs the cleanup every 15 minutes: original photos are deleted 24 hours after the character is approved, and abandoned drafts after 30 days. If the cron container is down (the monitor alerts), photos wait until it restarts. Check the log after an outage: `docker compose logs cron | grep photo.auto_deleted`.
