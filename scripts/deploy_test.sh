#!/usr/bin/env bash
# Deploy the committed HEAD to the Qamra TEST server (never production).
#
#     scripts/deploy_test.sh            # asks for the server password once (ssh), never stores it
#
# 1. saves the worker's log lines about failed/stalled jobs to out/deploy/ (the containers' logs are lost
#    when they are recreated), 2. copies the committed code (git archive: no .env, no local files) into
#    /opt/qamra, 3. rebuilds, runs the migrate job (migrations and seeds) and only then restarts with the
#    compose files the server already uses, 4. prints the containers' state and the site's health.
set -euo pipefail

HOST="${QAMRA_TEST_HOST:-root@62.84.179.155}"
DIR="/opt/qamra"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOCK="$(mktemp -u /tmp/qamra-deploy.XXXXXX)"
SSH=(ssh -o ControlMaster=auto -o ControlPath="$SOCK" -o ControlPersist=600 "$HOST")

cd "$ROOT"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "Uncommitted changes: only the committed HEAD is deployed (they will not be included)."
fi
REV="$(git rev-parse --short HEAD)"
echo "Deploying $REV to $HOST:$DIR"

"${SSH[@]}" true  # the one password prompt; the connection is reused below
trap '"${SSH[@]}" -O exit >/dev/null 2>&1 || true' EXIT

mkdir -p out/deploy
LOG="out/deploy/worker-before-$REV.log"
"${SSH[@]}" "cd $DIR && W=\$(docker ps --format '{{.Names}}' | grep -E 'worker' | grep -v cron | head -1); \
  [ -n \"\$W\" ] && docker logs --since 72h \"\$W\" 2>&1 | grep -E 'failed|stalled|Killed|MemoryError|Traceback|exhausted|locked' | tail -400" \
  > "$LOG" || true
echo "Worker log lines saved: $LOG ($(wc -l < "$LOG") lines)"

FILES="$("${SSH[@]}" "docker compose ls --format json 2>/dev/null" | python3 -c '
import json, sys
rows = [r for r in json.load(sys.stdin) if r.get("Name") == "qamra"]
print(" ".join("-f " + f for f in rows[0]["ConfigFiles"].split(",")) if rows else "")')"
[ -n "$FILES" ] || FILES="-f $DIR/compose.yaml"
echo "Compose files on the server: $FILES"

git archive --format=tar HEAD | "${SSH[@]}" "mkdir -p $DIR && tar -x -C $DIR && echo $REV > $DIR/REVISION"
"${SSH[@]}" "cd $DIR && docker compose $FILES build 2>&1 | tail -5"
# The migrate job (migrations, then seed-themes and seed-store) runs every time, before the new code starts:
# `up` alone recreates it only when compose sees it changed, so a new migration could be skipped.
"${SSH[@]}" "cd $DIR && set -o pipefail && docker compose $FILES run --rm migrate 2>&1 | tail -6" \
  || { echo "✗ the migrate job failed: the running version was left as it was"; exit 1; }
"${SSH[@]}" "cd $DIR && docker compose $FILES up -d --remove-orphans 2>&1 | tail -25"

echo
"${SSH[@]}" "cd $DIR && docker compose $FILES ps --format 'table {{.Name}}\t{{.Status}}'"
"${SSH[@]}" "cd $DIR && P=\$(grep -E '^QAMRA_WEB_PORT=' .env | cut -d= -f2); \
  curl -s -o /dev/null -w 'health: %{http_code}\n' http://127.0.0.1:\${P:-3000}/healthz || true"
echo "Deployed $REV."
