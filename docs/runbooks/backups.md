# Runbook: backups and restore

## What is backed up

| What | How | Where | Kept |
|---|---|---|---|
| Database (`qamra`) | `pg_dump -Fc`, gpg AES-256 | `/var/backups/qamra/db-*.dump.gpg` (+ off-site) | 14 daily + Sundays for 8 weeks |
| Object store | an rclone copy of the bucket **without children's original photos and drawings**, tar + gpg | `/var/backups/qamra/objects-*.tar.gpg` (+ off-site) | same |

- **Schedule:** `infra/scripts/backup.sh` runs every night at 02:30 UTC, from `/etc/cron.d/qamra-ops` (installed by `infra/scripts/install-ops-cron.sh`). Log: `/var/log/qamra-backup.log`. It writes `/var/backups/qamra/last-success`, and the monitor alerts when that is older than 26 hours.
- **The passphrase** is in `/root/.qamra-backup-passphrase`. **Keep a copy outside the server** (a password manager). Without it no backup can be decrypted.
- **Off-site copy:** set `BACKUP_RCLONE_REMOTE` in `/etc/default/qamra-ops`, e.g. an R2 bucket configured with `rclone config` in `/root/.config/rclone`.
- **In production on R2,** the object backup is skipped (the local store isn't running). R2 is durable on its own; for a second copy, add an R2 bucket and an rclone sync with the same two excludes.

## Privacy

- **No children's photos in backups.** Original photos and drawings are deleted within 24 hours of approval (CLAUDE.md §3.1), so backups never keep them: `children/*/photos/**` and `children/*/companions/*/drawing*` are excluded. Checked on the test server on 2026-09-28: 219 objects backed up, 0 photos, 0 drawings.
- **Deletion requests:** data a parent deletes ("delete my child's data") is gone from the live system at once. It leaves the backups when they expire (at most 8 weeks). The privacy page should say so.
- **Access:** backup files are owner-only (root) and encrypted.

## Restore drill (monthly, and after any change to the scripts)

```bash
sudo infra/scripts/restore.sh --check            # newest backup
sudo infra/scripts/restore.sh --check FILE       # a specific one
```

It restores into a scratch database, compares the row counts of users, children, books, orders and invoices with the live database, and drops the scratch database. Differences mean rows were written after the backup was taken.

Last drill: 2026-09-28 on the test server; the row counts matched.

## Disaster recovery

1. **Database:** `sudo infra/scripts/restore.sh --replace FILE`.
   - It asks you to type `restore`, stops the app containers, and recreates the database from the backup.
   - Then it starts everything again. Run the smoke test in production.md.
2. **Objects (local store only):**
   - `gpg -d objects-….tar.gpg | tar -xf -` into a temporary folder;
   - then `rclone copy` the `objects/` folder back into the bucket.
   - Children's photos are not in backups by design. A parent whose character isn't approved yet uploads the photo again.
3. **Lost server:** a new server per production.md, restore the database, then the objects, then check the admin settings. They're in the database, encrypted with `SETTINGS_ENCRYPTION_KEYS`, so that key must come from the password manager.
