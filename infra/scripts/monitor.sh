#!/usr/bin/env bash
# Is Qamra healthy? (Phase 6). Run every 5 minutes by install-ops-cron.sh; safe to run by hand.
#
# Checks the edge and the API through the edge, every container's state and health, free disk, the age of
# the last backup, the job queues, and an empty fal balance (the image provider refuses every drawing). Prints
# the problems and exits 1 when there are any. It alerts only when the state changes (healthy → problem, or
# problem → healthy), so a long outage sends two messages, not hundreds; and it announces each new order.
# Alert channels (in /etc/default/qamra-ops; either or both):
# - ALERT_WEBHOOK_URL: a Slack- or Discord-compatible webhook (JSON {"text": …, "content": …});
# - ALERT_TELEGRAM_BOT_TOKEN + ALERT_TELEGRAM_CHAT_ID: a Telegram bot (made with @BotFather) and the owner's
#   chat with it. No child's name or photo is ever sent: only the order code.
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

# fal answers "User is locked. Reason: Exhausted balance" to every drawing once the balance is empty: books
# and characters fail until someone tops up. A failure in the last hour keeps the problem raised.
if "${compose[@]}" logs --since 60m worker 2>/dev/null | grep -q "Exhausted balance"; then
  problems+=("fal balance exhausted: drawing has stopped (top up at fal.ai/dashboard/billing)")
fi

redis=("${compose[@]}" exec -T redis sh -c)
while read -r queue; do
  [[ -z "$queue" ]] && continue
  len="$("${redis[@]}" "REDISCLI_AUTH=\"\$REDIS_PASSWORD\" redis-cli llen $queue" 2>/dev/null | tr -dc 0-9)"
  (( ${len:-0} > QUEUE_MAX )) && problems+=("${queue#rq:queue:} queue has $len waiting jobs")
done < <("${redis[@]}" 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --scan --pattern "rq:queue:*"' 2>/dev/null)

alert() {  # $1: the message; sent to every configured channel, never fails the check
  local text="${1//\"/\'}"
  if [[ -n "${ALERT_WEBHOOK_URL:-}" ]]; then
    curl -fsS -m 10 -H 'Content-Type: application/json' \
      -d "$(printf '{"text": "%s", "content": "%s"}' "$text" "$text")" "$ALERT_WEBHOOK_URL" -o /dev/null || true
  fi
  if [[ -n "${ALERT_TELEGRAM_BOT_TOKEN:-}" && -n "${ALERT_TELEGRAM_CHAT_ID:-}" ]]; then
    curl -fsS -m 10 "https://api.telegram.org/bot${ALERT_TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${ALERT_TELEGRAM_CHAT_ID}" --data-urlencode "text=$1" -o /dev/null || true
  fi
}
channel=0
[[ -n "${ALERT_WEBHOOK_URL:-}" || ( -n "${ALERT_TELEGRAM_BOT_TOKEN:-}" && -n "${ALERT_TELEGRAM_CHAT_ID:-}" ) ]] \
  && channel=1

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
if (( channel )) && [[ "$now" != "$before" ]]; then
  if [[ "$now" == problem ]]; then
    alert "قمرة ($(hostname)): $(IFS='; '; echo "${problems[*]}")"
  else
    alert "قمرة ($(hostname)): all healthy again"
  fi
fi

# New orders since the last run (the first run only remembers the time): the owner hears at once, without SMTP.
if (( channel )); then
  since="$(cat "$STATE_DIR/orders-since" 2>/dev/null || true)"
  until="$(date -u +%s)"
  if [[ -n "$since" ]]; then
    codes="$("${compose[@]}" exec -T postgres psql -U qamra -d qamra -At -c \
      "select code from orders where created_at > to_timestamp($since) and created_at <= to_timestamp($until)
       order by created_at" 2>/dev/null)" || until="$since"  # the database didn't answer: try again next run
    while read -r code; do
      [[ -n "$code" ]] && alert "قمرة: طلب جديد $code — ${SITE_URL:-https://qamra.app}/ar/admin/orders"
    done <<< "$codes"
  fi
  echo "$until" > "$STATE_DIR/orders-since"
fi
[[ "$now" == ok ]]
