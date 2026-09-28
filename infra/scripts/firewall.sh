#!/usr/bin/env bash
# Firewall for the Qamra server (Addendum 3 §6.3): allow only SSH, HTTP and HTTPS from the internet.
#
#   sudo infra/scripts/firewall.sh           # dry run: prints what would change (default)
#   sudo infra/scripts/firewall.sh --apply   # applies it
#
# Two layers, because Docker-published ports bypass ufw:
# - ufw: deny incoming except 22, 80, 443;
# - DOCKER-USER chain (via /etc/ufw/after.rules): drop new connections from the internet to any container port.
#   Qamra's edge is published on 127.0.0.1 only once HTTPS is set up, and the host nginx reaches it locally.
#
# ⚠ On a shared server this also closes every other project's public ports (e.g. 3300, 4000, 8080, 5432).
#   Run it only after agreeing on that. SSH (22) stays open, and existing connections keep working.
set -euo pipefail

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1
[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }
EXT_IF="$(ip route show default | awk '{print $5; exit}')"

RULES="
# BEGIN QAMRA DOCKER-USER
*filter
:DOCKER-USER - [0:0]
-A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
-A DOCKER-USER -i $EXT_IF -m conntrack --ctstate NEW -j DROP
-A DOCKER-USER -j RETURN
COMMIT
# END QAMRA DOCKER-USER
"

echo "external interface: $EXT_IF"
echo "public listeners now:"
ss -ltnp | awk 'NR>1 && $4 !~ /^(127\.0\.0\.1|\[::1\]):/ {print "  " $4}' | sort -u
echo
echo "plan:"
echo "  ufw default deny incoming; ufw default allow outgoing"
echo "  ufw allow 22/tcp; ufw allow 80/tcp; ufw allow 443/tcp; ufw enable"
echo "  append to /etc/ufw/after.rules:$RULES"

if [[ $APPLY -eq 0 ]]; then
  echo "dry run only. Re-run with --apply to make these changes."
  exit 0
fi

ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
if ! grep -q "BEGIN QAMRA DOCKER-USER" /etc/ufw/after.rules; then
  printf '%s\n' "$RULES" >> /etc/ufw/after.rules
fi
ufw --force enable
ufw reload
systemctl restart docker  # re-creates Docker's own chains after the DOCKER-USER rules
ufw status verbose
