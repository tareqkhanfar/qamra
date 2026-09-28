#!/usr/bin/env bash
# HTTPS for Qamra on a server whose port 80 is already served by the host's nginx (Addendum 3 §6.1).
#
#   sudo infra/scripts/setup-https.sh qamra.example.com you@example.com
#
# 1. checks the domain resolves to this server;
# 2. installs certbot + its nginx plugin if missing;
# 3. adds a host nginx site for the domain → 127.0.0.1:$QAMRA_WEB_PORT (tests the config before reloading,
#    so other sites on this nginx are never taken down by a bad file);
# 4. gets a Let's Encrypt certificate with HTTP→HTTPS redirect (auto-renewal via certbot's timer) + HSTS;
# 5. binds the Qamra edge to localhost only and switches the app to secure cookies + HTTPS mode.
set -euo pipefail

DOMAIN="${1:?usage: setup-https.sh DOMAIN EMAIL}"
EMAIL="${2:?usage: setup-https.sh DOMAIN EMAIL}"
APP_DIR="${APP_DIR:-/opt/qamra}"
PORT="$(grep -E '^QAMRA_WEB_PORT=' "$APP_DIR/.env" | cut -d= -f2 || true)"
PORT="${PORT:-3000}"
SITE="/etc/nginx/sites-available/qamra.conf"

[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || { echo "invalid domain"; exit 1; }

server_ip="$(curl -fsS https://api.ipify.org || true)"
dns_ip="$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}')"
if [[ -z "$dns_ip" || "$dns_ip" != "$server_ip" ]]; then
  echo "✗ $DOMAIN resolves to '${dns_ip:-nothing}', this server is '$server_ip'. Point the DNS A record here first."
  exit 1
fi

command -v certbot >/dev/null || { apt-get update -qq && apt-get install -y -qq certbot python3-certbot-nginx; }

sed -e "s/__DOMAIN__/$DOMAIN/g" -e "s/__PORT__/$PORT/g" "$APP_DIR/infra/nginx/host-vhost.conf.template" > "$SITE"
ln -sf "$SITE" /etc/nginx/sites-enabled/qamra.conf
nginx -t
systemctl reload nginx

certbot --nginx -d "$DOMAIN" --redirect --agree-tos -m "$EMAIL" --non-interactive
grep -q Strict-Transport-Security "$SITE" || \
  sed -i '/listen 443 ssl/a\    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;' "$SITE"
nginx -t
systemctl reload nginx

cd "$APP_DIR"
set_env() { grep -q "^$1=" .env && sed -i "s|^$1=.*|$1=$2|" .env || echo "$1=$2" >> .env; }
set_env QAMRA_BIND 127.0.0.1
set_env QAMRA_HTTPS 1
set_env COOKIE_SECURE true
set_env WEB_BASE_URL "https://$DOMAIN"
docker compose up -d
echo "✓ https://$DOMAIN is live. The app port now listens on 127.0.0.1:$PORT only."
