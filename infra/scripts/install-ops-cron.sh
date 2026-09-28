#!/usr/bin/env bash
# Schedules the nightly backup and the 5-minute health check (Phase 6). Run once on the server as root.
#
#   infra/scripts/install-ops-cron.sh
#
# Settings for both jobs go in /etc/default/qamra-ops (created here with comments), for example
# QAMRA_PROD=1, BACKUP_RCLONE_REMOTE=r2backup:qamra-backups, ALERT_WEBHOOK_URL=https://hooks.slack.com/…
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }
APP_DIR="${APP_DIR:-/opt/qamra}"

if [[ ! -f /etc/default/qamra-ops ]]; then
  cat > /etc/default/qamra-ops <<'CONF'
# Qamra ops jobs (backup.sh, monitor.sh). Uncomment what applies.
# QAMRA_PROD=1                                   # use compose.prod.yaml too
# BACKUP_RCLONE_REMOTE=r2backup:qamra-backups    # off-site copy (rclone config in /root/.config/rclone)
# ALERT_WEBHOOK_URL=https://hooks.slack.com/services/…
CONF
  chmod 600 /etc/default/qamra-ops
fi
if [[ ! -s /root/.qamra-backup-passphrase ]]; then
  (umask 077; openssl rand -base64 32 > /root/.qamra-backup-passphrase)
  echo "⚠ created /root/.qamra-backup-passphrase. Copy it somewhere safe outside this server:"
  echo "  without it the backups cannot be decrypted."
fi

cat > /etc/cron.d/qamra-ops <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
30 2 * * * root set -a; . /etc/default/qamra-ops; set +a; flock -n /run/qamra-backup.lock $APP_DIR/infra/scripts/backup.sh >> /var/log/qamra-backup.log 2>&1
*/5 * * * * root flock -n /run/qamra-monitor.lock $APP_DIR/infra/scripts/monitor.sh >> /var/log/qamra-monitor.log 2>&1
CRON
chmod 644 /etc/cron.d/qamra-ops

cat > /etc/logrotate.d/qamra-ops <<'ROTATE'
/var/log/qamra-backup.log /var/log/qamra-monitor.log {
  weekly
  rotate 8
  compress
  missingok
  notifempty
}
ROTATE
echo "✓ installed: backup at 02:30 UTC daily, health check every 5 minutes"
echo "  logs: /var/log/qamra-backup.log, /var/log/qamra-monitor.log"
