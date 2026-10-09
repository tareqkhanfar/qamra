# Runbook: production

How to put Qamra on a production server, deploy updates, and check that it works. Production is not set up yet. This runbook and `compose.prod.yaml` make it a checklist rather than a project. CLAUDE.md: anything touching production needs Tareq's go-ahead.

## What production needs from Tareq

- **A VPS:** 4 vCPU, 8 GB RAM, 80 GB disk minimum; the worker renders PDFs with Chromium. Ubuntu 24.04 with Docker Engine and the Compose plugin.
- **A domain** pointed at the server (A record). Put Cloudflare in front for DNS and DDoS protection; keep the SSL mode on *Full (strict)*.
- **A Cloudflare R2 bucket:**
  - private, no public access;
  - an API token limited to that bucket (object read/write);
  - optionally a second bucket for off-site backups.
- **An SMTP account** for emails, entered later in the admin.
- **The AI keys**, entered later in the admin; they are encrypted in the database.

## First install

1. **Server basics:** a non-root sudo user, SSH keys only, unattended security upgrades.
2. **Code:** copy the repository to `/opt/qamra`, the same layout as the test server.
3. **Secrets:** create `/opt/qamra/.env` from `.env.example` and set at least:
   - `QAMRA_ENV=prod`;
   - `WEB_BASE_URL=https://<domain>` and `BRAND_DOMAIN=<domain>`;
   - `JWT_SECRET` (`openssl rand -hex 32`);
   - `POSTGRES_PASSWORD` and `REDIS_PASSWORD` (long random strings);
   - `SETTINGS_ENCRYPTION_KEYS` (a Fernet key; see `.env.example`). Keep a copy outside the server: without it the admin-managed secrets can't be decrypted.
   - `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` for R2;
   - `SENTRY_DSN` (optional).

   Then `chmod 600 .env`. `compose.prod.yaml` refuses to start without the required values.
4. **Start:** `docker compose -f compose.yaml -f compose.prod.yaml up -d --build`. The migrate job applies the migrations and seeds themes and the store (the seed is insert-only).
5. **HTTPS:** `sudo infra/scripts/setup-https.sh <domain> <email>` (host nginx + Let's Encrypt, HTTP→HTTPS, HSTS). With Cloudflare in front, keep the origin certificate from this script.
6. **Firewall:** `sudo infra/scripts/firewall.sh` (dry run), then `--apply`. Only 22, 80 and 443 stay open.
7. **The first admin:** `docker compose exec api qamra create-user --role admin --email <email> --name "<name>"` (the password is prompted, so it stays out of the shell history). Sign in, turn on 2FA (the admin area requires it), and add staff roles for other team members.
8. **Admin → Settings:** AI keys and models, prices and rates, contact details, SMTP, the printer's email, the photo retention hours (24 at most).
9. **Backups and monitoring:**
   - `sudo infra/scripts/install-ops-cron.sh`;
   - then set `QAMRA_PROD=1`, `BACKUP_RCLONE_REMOTE` and `ALERT_WEBHOOK_URL` in `/etc/default/qamra-ops`;
   - copy `/root/.qamra-backup-passphrase` to a password manager;
   - run `infra/scripts/backup.sh`, then `infra/scripts/restore.sh --check` (see backups.md).
10. **Smoke test** (below).

## Deploying an update

1. Tests are green in CI (`make check` locally: lint, types, tests, web checks).
2. Take a backup first: `infra/scripts/backup.sh`.
3. Sync the code (git pull, or rsync without `.env`), then `docker compose -f compose.yaml -f compose.prod.yaml up -d --build`. Compose rebuilds the images, runs the migrate job, and replaces the containers. A migration that fails stops the deploy before the new API starts.
4. The voices behind the activity books' printed QR codes (content/journey/clips, one per item of content/journey/audio.yaml): `docker compose exec worker python -m qamra_worker.journey_voices` stores what storage lacks (a new storage, a new item) and never replaces a recording staff uploaded; `--check` only reports. Running it on every deploy is safe: when everything is in place it changes nothing.
5. Smoke test.
6. Rollback: redeploy the previous commit. If a migration must be undone, restore the backup from step 2 (`restore.sh --replace`) rather than hand-editing the schema.

## Smoke test (5 minutes, on a phone)

- The home page and a story page load; the story page shows «كلاسيك» and «سحري» with prices.
- Sign in; the account page loads.
- `/ar/create`: add a test child, give consent, and upload a test photo (the photo check answers); stop before drawing, or draw one character (a few cents).
- Add a book to the cart and view the checkout. Don't place an order on production unless you delete it afterwards.
- Admin (2FA): orders, the catalog, reports, and the cost dashboard load; the GPU card shows «غير مُعدّ».
- The printed QR codes: https://qamra.app/a/ogjmg6ob («رحلتي الأولى», stage 1 p. 28) shows the animals and its play button plays the sounds; a story page's code (`https://qamra.app/v/<token>/<page>`, from a book with «أصوات العائلة») opens its listen page.
- `infra/scripts/monitor.sh` prints «healthy».
- Delete the test child from the account page.
