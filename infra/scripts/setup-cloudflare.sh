#!/usr/bin/env bash
# Qamra on a domain proxied by Cloudflare, on a server whose port 80 is already served by the host's nginx.
#
#   sudo infra/scripts/setup-cloudflare.sh qamra.app
#
# 1. makes a self-signed origin certificate (for Cloudflare's "Full" mode; "Flexible" uses port 80);
# 2. writes Cloudflare's current IP ranges into the site so only Cloudflare may set the visitor's address;
# 3. adds a host nginx site for the domain (and www → the domain) → 127.0.0.1:$QAMRA_WEB_PORT, tests the
#    config before reloading so the other sites on this nginx are never taken down by a bad file;
# 4. binds the Qamra edge to localhost only and switches the app to secure cookies + HTTPS links.
# Unlike setup-https.sh there is no Let's Encrypt step: Cloudflare holds the public certificate.
set -euo pipefail

DOMAIN="${1:?usage: setup-cloudflare.sh DOMAIN}"
APP_DIR="${APP_DIR:-/opt/qamra}"
PORT="$(grep -E '^QAMRA_WEB_PORT=' "$APP_DIR/.env" | cut -d= -f2 || true)"
PORT="${PORT:-3000}"
SITE="/etc/nginx/sites-available/qamra-cloudflare.conf"
CERT_DIR="/etc/nginx/qamra-origin"

[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || { echo "invalid domain"; exit 1; }

mkdir -p "$CERT_DIR"
chmod 700 "$CERT_DIR"
if [[ ! -s "$CERT_DIR/origin.crt" ]]; then
  openssl req -x509 -nodes -newkey rsa:2048 -days 3650 -subj "/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:www.$DOMAIN" \
    -keyout "$CERT_DIR/origin.key" -out "$CERT_DIR/origin.crt" 2>/dev/null
  chmod 600 "$CERT_DIR/origin.key"
fi

ranges="$(
  { curl -fsS https://www.cloudflare.com/ips-v4; echo; curl -fsS https://www.cloudflare.com/ips-v6; } \
    | grep -E '^[0-9a-f:.]+/[0-9]+$' | sed 's/^/    set_real_ip_from /; s/$/;/'
)"
[[ -n "$ranges" ]] || { echo "✗ could not fetch Cloudflare's IP ranges"; exit 1; }

tmp="$(mktemp)"
sed -e "s/__DOMAIN__/$DOMAIN/g" -e "s/__PORT__/$PORT/g" -e "s|__CERT_DIR__|$CERT_DIR|g" \
  "$APP_DIR/infra/nginx/host-vhost-cloudflare.conf.template" \
  | awk -v r="$ranges" '{ if ($0 == "__CF_RANGES__") print r; else print }' > "$tmp"
backup=""
[[ -f "$SITE" ]] && backup="$(mktemp)" && cp "$SITE" "$backup"
mv "$tmp" "$SITE"
chmod 644 "$SITE"
ln -sf "$SITE" /etc/nginx/sites-enabled/qamra-cloudflare.conf
if ! nginx -t; then
  echo "✗ nginx config test failed; putting things back"
  if [[ -n "$backup" ]]; then mv "$backup" "$SITE"; else rm -f "$SITE" /etc/nginx/sites-enabled/qamra-cloudflare.conf; fi
  exit 1
fi
systemctl reload nginx

cd "$APP_DIR"
set_env() { grep -q "^$1=" .env && sed -i "s|^$1=.*|$1=$2|" .env || echo "$1=$2" >> .env; }
set_env QAMRA_BIND 127.0.0.1
set_env QAMRA_HTTPS 1
set_env COOKIE_SECURE true
set_env WEB_BASE_URL "https://$DOMAIN"
FILES="$(docker compose ls --format json 2>/dev/null | python3 -c '
import json, sys
rows = [r for r in json.load(sys.stdin) if r.get("Name") == "qamra"]
print(" ".join("-f " + f for f in rows[0]["ConfigFiles"].split(",")) if rows else "")')"
# shellcheck disable=SC2086
docker compose ${FILES:--f compose.yaml} up -d
echo "✓ https://$DOMAIN goes through Cloudflare to this server. The app port listens on 127.0.0.1:$PORT only."
