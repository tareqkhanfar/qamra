#!/usr/bin/env bash
# Is Qamra healthy? (Phase 6). Run every 5 minutes by install-ops-cron.sh; safe to run by hand.
#
# Checks the edge and the API through the edge, every container's state and health, free disk, the age of
# the last backup, and the job queues. Prints the problems and exits 1 when there are any. When
# ALERT_WEBHOOK_URL is set (Slack-compatible JSON {"text": …}), it posts only when the state changes
# (healthy → problem, or problem → healthy), so a long outage sends two messages, not hundreds.
set -uo pipefail
[[ -f /etc/default/qamra-ops ]] && . /etc/default/qamra-ops

APP_DIR="${APP_DIR:-/opt/qamra}"
PORT="$(grep -E '^QAMRA_WEB_PORT=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2)"
PORT="${PORT:-3000}"
STATE_DIR="${STATE_DIR:-/var/lib/qamra-monitor}"
DISK_MAX="${DISK_MAX_PCT:-85}"
QUEUE_MAX="${QUEUE_MAX:-100}"
BACKUP_MAX_HOURS="${BACKUP_MAX_HOURS:-26}"
compose=(docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml")
[[ "${QAMRA_PROD:-0}" == 1 ]] && compose+=(-f "$APP_DIR/compose.prod.yaml")
problems=()

curl -fsS -m 10 -o /dev/null "http://127.0.0.1:$PORT/healthz" || problems+=("the site (edge) does not answer")
curl -fsS -m 10 -o /dev/null -H "X-Qamra-Client: monitor" "http://127.0.0.1:$PORT/api/health" \
  || problems+=("the API health check fails")

while read -r service state health; do
  [[ "$service" == migrate ]] && continue
  [[ "$state" != running ]] && problems+=("$service is $state")
  [[ "$health" == unhealthy ]] && problems+=("$service is unhealthy")
done < <("${compose[@]}" ps -a --format '{{.Service}} {{.State}} {{.Health}}')

used="$(df --output=pcent / | tail -1 | tr -dc 0-9)"
(( used > DISK_MAX )) && problems+=("disk ${used}% full")

if [[ -f /var/backups/qamra/last-success ]]; then
  age=$(( ( $(date +%s) - $(cat /var/backups/qamra/last-success) ) / 3600 ))
  (( age > BACKUP_MAX_HOURS )) && problems+=("last backup ${age}h ago")
elif [[ -f /etc/cron.d/qamra-ops ]]; then
  problems+=("no successful backup yet")
fi

redis=("${compose[@]}" exec -T redis sh -c)
while read -r queue; do
  [[ -z "$queue" ]] && continue
  len="$("${redis[@]}" "REDISCLI_AUTH=\"\$REDIS_PASSWORD\" redis-cli llen $queue" 2>/dev/null | tr -dc 0-9)"
  (( ${len:-0} > QUEUE_MAX )) && problems+=("${queue#rq:queue:} queue has $len waiting jobs")
done < <("${redis[@]}" 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --scan --pattern "rq:queue:*"' 2>/dev/null)

mkdir -p "$STATE_DIR"
now="ok"; (( ${#problems[@]} )) && now="problem"
before="$(cat "$STATE_DIR/state" 2>/dev/null || echo ok)"
echo "$now" > "$STATE_DIR/state"
stamp="$(date -u +%FT%TZ)"
if (( ${#problems[@]} )); then
  printf '%s ✗ %s\n' "$stamp" "${problems[@]}"
else
  echo "$stamp ✓ healthy"
fi
if [[ -n "${ALERT_WEBHOOK_URL:-}" && "$now" != "$before" ]]; then
  if [[ "$now" == problem ]]; then
    text="قمرة ($(hostname)): $(IFS='; '; echo "${problems[*]}")"
  else
    text="قمرة ($(hostname)): all healthy again"
  fi
  curl -fsS -m 10 -H 'Content-Type: application/json' \
    -d "$(printf '{"text": "%s"}' "${text//\"/\'}")" "$ALERT_WEBHOOK_URL" -o /dev/null || true
fi
[[ "$now" == ok ]]
