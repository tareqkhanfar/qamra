#!/usr/bin/env bash
# Restore a Qamra database backup (Phase 6). Run on the server as root.
#
#   infra/scripts/restore.sh --check [FILE]    # drill: restore into a scratch database, compare row counts
#                                              # with the live one, then drop the scratch database
#   infra/scripts/restore.sh --replace FILE    # disaster recovery: replaces the live database (asks first)
#
# FILE defaults to the newest db-*.dump.gpg in $BACKUP_DIR. The object-store archive (objects-*.tar.gpg) is
# restored by hand: docs/runbooks/backups.md.
set -euo pipefail
[[ -f /etc/default/qamra-ops ]] && . /etc/default/qamra-ops

APP_DIR="${APP_DIR:-/opt/qamra}"
DEST="${BACKUP_DIR:-/var/backups/qamra}"
PASSFILE="${BACKUP_PASSPHRASE_FILE:-/root/.qamra-backup-passphrase}"
compose=(docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml")
[[ "${QAMRA_PROD:-0}" == 1 ]] && compose+=(-f "$APP_DIR/compose.prod.yaml")
psql() { "${compose[@]}" exec -T postgres psql -U qamra -v ON_ERROR_STOP=1 "$@"; }

[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }
mode="${1:-}"
file="${2:-$(ls -1t "$DEST"/db-*.dump.gpg 2>/dev/null | head -1)}"
[[ -f "$file" ]] || { echo "no backup file found"; exit 1; }
decrypt() { gpg --batch --quiet --pinentry-mode loopback --passphrase-file "$PASSFILE" -d "$file"; }

counts() {  # "table count" for the main tables of database $1
  psql -d "$1" -At -F ' ' -c "select 'users', count(*) from users union all select 'children', count(*) from children
    union all select 'books', count(*) from books union all select 'orders', count(*) from orders
    union all select 'invoices', count(*) from invoices order by 1"
}

case "$mode" in
  --check)
    scratch="qamra_restore_check"
    psql -d postgres -c "drop database if exists $scratch" -c "create database $scratch" >/dev/null
    decrypt | "${compose[@]}" exec -T postgres pg_restore -U qamra -d "$scratch" --no-owner --exit-on-error
    echo "restored $(basename "$file") into $scratch"
    diff <(counts qamra) <(counts "$scratch") && echo "✓ row counts match the live database" \
      || echo "(differences above are rows written since the backup was taken)"
    psql -d postgres -c "drop database $scratch" >/dev/null
    echo "✓ scratch database dropped"
    ;;
  --replace)
    read -r -p "Replace the LIVE database with $(basename "$file")? Type the word restore: " answer
    [[ "$answer" == restore ]] || { echo "cancelled"; exit 1; }
    "${compose[@]}" stop api worker cron web
    psql -d postgres -c "select pg_terminate_backend(pid) from pg_stat_activity where datname = 'qamra' and pid <> pg_backend_pid()" >/dev/null
    psql -d postgres -c "drop database qamra" -c "create database qamra owner qamra"
    decrypt | "${compose[@]}" exec -T postgres pg_restore -U qamra -d qamra --no-owner --exit-on-error
    "${compose[@]}" up -d
    echo "✓ restored and restarted; run the smoke test in docs/runbooks/production.md"
    ;;
  *)
    sed -n '2,10p' "$0"
    exit 1
    ;;
esac
