#!/usr/bin/env bash
# Nightly backup of Qamra (Phase 6). Run on the server as root; install-ops-cron.sh schedules it.
#
#   infra/scripts/backup.sh                 # database + object store
#   BACKUP_OBJECTS=0 infra/scripts/backup.sh  # database only
#
# - Database: pg_dump (custom format) of the `qamra` database, encrypted with gpg (AES-256) using the
#   passphrase in $BACKUP_PASSPHRASE_FILE → $BACKUP_DIR/db-YYYYmmdd-HHMM.dump.gpg
# - Object store: a copy of the bucket WITHOUT children's original photos and drawings (they must be gone
#   within 24h of approval, CLAUDE.md §3.1, so backups never keep them), tarred and encrypted the same way.
# - Retention: the 14 newest daily backups, plus Sunday backups for 8 weeks.
# - Off-site: when BACKUP_RCLONE_REMOTE is set (e.g. "r2backup:qamra-backups"), each file is copied there
#   with rclone (docker image rclone/rclone, config in /root/.config/rclone).
# Restore: docs/runbooks/backups.md and infra/scripts/restore.sh.
set -euo pipefail
[[ -f /etc/default/qamra-ops ]] && . /etc/default/qamra-ops
umask 077  # backups hold personal data: owner-only files

APP_DIR="${APP_DIR:-/opt/qamra}"
DEST="${BACKUP_DIR:-/var/backups/qamra}"
PASSFILE="${BACKUP_PASSPHRASE_FILE:-/root/.qamra-backup-passphrase}"
KEEP_DAILY="${KEEP_DAILY:-14}"
KEEP_WEEKLY_DAYS="${KEEP_WEEKLY_DAYS:-56}"
compose=(docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml")
[[ "${QAMRA_PROD:-0}" == 1 ]] && compose+=(-f "$APP_DIR/compose.prod.yaml")

[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }
[[ -s "$PASSFILE" ]] || {
  echo "✗ missing $PASSFILE. Create it once and keep a copy outside the server:"
  echo "  (umask 077; openssl rand -base64 32 > $PASSFILE)"
  exit 1
}
mkdir -p "$DEST" && chmod 700 "$DEST"
stamp="$(date -u +%Y%m%d-%H%M)"
encrypt() { gpg --batch --yes --quiet --pinentry-mode loopback --passphrase-file "$PASSFILE" --symmetric --cipher-algo AES256 -o "$1"; }

db="$DEST/db-$stamp.dump.gpg"
"${compose[@]}" exec -T postgres pg_dump -U qamra -d qamra -Fc | encrypt "$db"
echo "✓ database → $db ($(du -h "$db" | cut -f1))"
files=("$db")

if [[ "${BACKUP_OBJECTS:-1}" == 1 ]] && "${compose[@]}" ps --services --status running | grep -qx s3; then
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT
  net="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$("${compose[@]}" ps -q s3)")"
  key="$("${compose[@]}" exec -T api printenv S3_ACCESS_KEY_ID)"
  secret="$("${compose[@]}" exec -T api printenv S3_SECRET_ACCESS_KEY)"
  bucket="$("${compose[@]}" exec -T api printenv S3_BUCKET)"
  docker run --rm --network "$net" -v "$work":/backup \
    -e RCLONE_CONFIG_SRC_TYPE=s3 -e RCLONE_CONFIG_SRC_PROVIDER=SeaweedFS \
    -e RCLONE_CONFIG_SRC_ENDPOINT=http://s3:8333 \
    -e RCLONE_CONFIG_SRC_ACCESS_KEY_ID="$key" -e RCLONE_CONFIG_SRC_SECRET_ACCESS_KEY="$secret" \
    rclone/rclone:1.69 copy "src:$bucket" /backup/objects --quiet \
    --exclude "children/*/photos/**" --exclude "children/*/companions/*/drawing*"
  objects="$DEST/objects-$stamp.tar.gpg"
  tar -C "$work" -cf - objects | encrypt "$objects"
  echo "✓ objects (without children's photos) → $objects ($(du -h "$objects" | cut -f1))"
  files+=("$objects")
fi

# retention: keep the newest $KEEP_DAILY of each kind; older ones only if taken on a Sunday and younger than
# $KEEP_WEEKLY_DAYS days
for kind in db objects; do
  mapfile -t all < <(ls -1t "$DEST"/"$kind"-*.gpg 2>/dev/null || true)
  for f in "${all[@]:$KEEP_DAILY}"; do
    day="$(basename "$f" | sed -E 's/^[a-z]+-([0-9]{8}).*/\1/')"
    age=$(( ( $(date -u +%s) - $(date -u -d "$day" +%s) ) / 86400 ))
    if [[ "$(date -u -d "$day" +%u)" != 7 || $age -gt $KEEP_WEEKLY_DAYS ]]; then
      rm -f "$f" && echo "  removed old $(basename "$f")"
    fi
  done
done

if [[ -n "${BACKUP_RCLONE_REMOTE:-}" ]]; then
  for f in "${files[@]}"; do
    docker run --rm -v /root/.config/rclone:/config/rclone:ro -v "$DEST":/backups:ro rclone/rclone:1.69 \
      copy "/backups/$(basename "$f")" "$BACKUP_RCLONE_REMOTE" --quiet
  done
  echo "✓ copied off-site → $BACKUP_RCLONE_REMOTE"
fi
date -u +%s > "$DEST/last-success"
