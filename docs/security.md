# Security

Last full review: 2026-09-28. No system can be proven free of vulnerabilities. This page lists what is protected and how, what the automated checks found, and what is still open. Re-run the checks (bottom of this page) before every release.

## Accounts and sessions

- **Passwords:**
  - Hashed with argon2id.
  - At least 8 characters. Common passwords, low-variety passwords and passwords equal to the email name are refused.
  - Unknown emails take the same time to reject as wrong passwords, so accounts can't be discovered by timing.
- **Brute force:**
  - Login: 10 attempts per email+IP and 50 per IP per 15 minutes (Redis). Nginx also limits `/api/auth/*` to 2 requests per second per IP.
  - Sign-up: 10 per IP per hour.
  - Kindergarten form: 5 per IP per hour.
  - Password change: limited per user.
- **Sessions:**
  - Access JWT: 15 minutes, HS256 pinned (`alg: none` is impossible).
  - Refresh token: opaque, 30 days, stored only as a sha256 hash, rotated on every use.
  - A reused rotated token revokes the whole login.
  - Changing the password signs out every other session.
- **Cookies:**
  - `httpOnly` and `SameSite=Lax`. The refresh cookie is sent only to `/api/auth`.
  - `Secure` is on whenever HTTPS is on (`COOKIE_SECURE=true`; production refuses to start without it).
- **CSRF:** every POST/PUT/PATCH/DELETE must carry the `X-Qamra-Client` header. Browsers can't add it cross-site, and the API allows no cross-origin requests.
- **Authorization:**
  - Every request loads the user and role from the database, not from the token.
  - Admin endpoints check `role == admin` on the server.
  - Tests cover anonymous → 401 and parent → 403.

## Admin settings and secrets

- **Where settings live:** prices, contact details, AI keys and models, notifications and site switches are edited in `/admin/settings`. Infrastructure secrets (database, JWT, encryption key) stay in the server environment.
- **Secrets:**
  - Encrypted at rest with Fernet (AES + HMAC) using `SETTINGS_ENCRYPTION_KEYS`. Production refuses to start without it, and the key can be rotated.
  - Never returned in full; only "set" plus the last 4 characters.
  - Never written to logs or the audit trail.
- **Validation:**
  - Every setting is checked against its type and limits, and a save is all-or-nothing.
  - Links must be `https://`, so `javascript:` links are impossible.
  - Privacy retention can't exceed the policy (photos 24 h, drafts 30 days).
- **Audit:** every change is recorded with who changed which keys, never the values.

## Browser protections

- **Content-Security-Policy on every page, with a fresh nonce per request:**
  - Scripts run only with that request's nonce (`strict-dynamic`).
  - Also set: `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `frame-ancestors 'none'`.
  - `style-src-attr 'unsafe-inline'` is allowed. It covers React style attributes only; CSS can't run scripts.
  - `upgrade-insecure-requests` turns on with `QAMRA_HTTPS=1`.
- **Other headers:**
  - `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`.
  - `Cross-Origin-Opener-Policy: same-origin`.
  - `Permissions-Policy`: camera and microphone for our own origin only (photos, family voice); geolocation, payment and usb off.
- **API responses:** `default-src 'none'`, `nosniff`, `no-store` on account/admin/children/books data, `X-Robots-Tag: noindex`, and no `Server` header.
- **No raw HTML** anywhere (no `dangerouslySetInnerHTML`). React escapes all text, and redirect targets are checked to be same-site paths.

## Infrastructure

- **Only the nginx `edge` is public:**
  - It sets the real client IP; the client can't spoof it.
  - Allowed methods: GET, HEAD, POST, PUT, PATCH, DELETE.
  - Per-IP request and connection limits.
  - Slow-client timeouts; 20 MB body limit.
  - Dotfiles blocked (`/.well-known/` still allowed for certificates); no version headers.
- **Internal-only services:** Postgres, Redis (password-protected), S3 and the API port are bound to 127.0.0.1 or the Docker network.
- **Containers:**
  - Non-root users.
  - `no-new-privileges`.
  - `cap_drop: ALL` for the app containers; nginx keeps only the capabilities it needs.
  - Memory limits, so one service can't starve the server.
- **Database access** goes through SQLAlchemy only (no string-built SQL).
- **Child data:**
  - Original photos and drawings are deleted automatically; the cleanup job runs every 15 minutes.
  - Deleting a child cascades to all their data.
  - Audit logs hold no personal data.

## Automated checks (2026-09-28)

| Check | Result |
|---|---|
| `bandit` (Python security lint) | 0 issues. Three false positives are annotated: a public URL, the dev JWT default that production refuses, and the enum name `"secret"`. The jinja2 `autoescape=False` in AI prompt templates is intentional (plain text, never HTML). |
| `pip-audit` (275 Python packages) | No known vulnerabilities |
| `npm audit --omit=dev` (web) | 0 vulnerabilities |
| Test suite | 141 Python tests, including auth, rate limits, CSRF, role checks, secret masking/encryption, settings validation and security headers. Plus a browser e2e and a CSP-violation check in a real browser (none found). |

## Open items: must do before real customers

1. **HTTPS.** The test site runs on plain HTTP (`http://62.84.179.155:3300`), so passwords and cookies cross the network unencrypted. With a domain behind Cloudflare, or a certificate on port 443, set `COOKIE_SECURE=true` and `QAMRA_HTTPS=1` and add HSTS at the edge.
2. **Two-factor sign-in for admins** (TOTP). The admin panel holds the AI keys.
3. **The test server itself** (outside Qamra):
   - Root logs in by SSH with a password that has been shared in chat. Change it and switch to SSH keys.
   - `namer-postgres` is published on `0.0.0.0:5432` to the whole internet.
   - Other projects share the machine.
4. **Before launch:** backups and restore drills (Phase 6), monitoring/alerts, and an external penetration test.
5. **Phase 2 features** get their own review: photo and drawing uploads (type/size checks, stripping EXIF location, private storage with signed URLs only) and payments.

## Re-running the checks

```bash
uvx bandit -q -r apps/api/src apps/worker/src packages/core/src packages/ai/src packages/pdf/src
uv export --frozen --no-dev --no-emit-workspace --no-hashes > /tmp/reqs.txt && uvx pip-audit -r /tmp/reqs.txt
cd apps/web && npm audit --omit=dev
make check
curl -sI https://<site>/ar | grep -i content-security-policy
```
