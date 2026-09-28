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

## Admin access (Addendum 3 §6.2)

- **Two-step verification is required for every admin endpoint.**
  - TOTP (RFC 6238) from any authenticator app, accepting ±1 time step.
  - A code is never accepted twice: the last used step is stored, which stops replay.
  - The secret is encrypted like the other admin secrets. The browser sees it only once, during setup, which asks for the password again.
- **Recovery codes:**
  - 10 single-use codes, stored as sha256 hashes and shown once.
  - Admins can't turn 2FA off. If both the phone and the codes are lost: `docker compose exec api qamra reset-2fa --email …` on the server, which also signs the account out everywhere.
- **Sessions:**
  - A password-only session (e.g. from before 2FA was set up) gets `mfa_required` on admin endpoints.
  - Turning 2FA on signs out every other session.
  - The 2FA step of a login lives in a 5-minute signed cookie, and code attempts are rate-limited per login and per IP.
- **Optional admin IP allowlist** (admin → Security): comma-separated addresses or networks, checked on every admin endpoint.

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

## AI providers and children's photos (Addendum 3 §6.5)

- **Anthropic:** "Anthropic may not train models on Customer Content from Services" (Commercial Terms).
- **Google (Nano Banana 2 behind fal):** paid Gemini API prompts and responses are not used to improve Google's products; they are logged for a limited time for abuse detection.
- **fal:**
  - Every call sends `X-Fal-Store-IO: 0` (no 30-day request history) and a 15-minute expiry for any generated file.
  - Reference images go inline, never to fal's CDN.
  - fal's DPA limits personal data to our instructions but allows de-identified data to improve their services. **Get written confirmation from fal before real children's photos go through it.**
- Error messages from fal echo the request (our images), so only the error type and message are logged.
- The public `/privacy` page states all of this with links to the terms.

## Infrastructure

- **Only the nginx `edge` is public:**
  - It sets the real client IP; the client can't spoof it. It trusts `X-Forwarded-For` only from Docker bridge addresses (the host nginx in front of it). Internet clients keep their real address: re-tested with spoofed headers, blocked at attempt 11.
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
  - Stored encrypted at rest. The bundled SeaweedFS encrypts every volume (`-s3.encryptVolumeData`); R2 in production encrypts every object. Per-object SSE-S3 is off (`S3_SSE=none`) because SeaweedFS 4.47 corrupts SSE objects over 8 MB, which print PDFs are. See `docs/decisions.md`.
  - Original photos and drawings are deleted automatically; the cleanup job runs every 15 minutes.
  - Deleting a child cascades to all their data.
  - Audit logs hold no personal data.

## Automated checks (2026-09-28)

| Check | Result |
|---|---|
| `bandit` (Python security lint) | 0 issues. Three false positives are annotated: a public URL, the dev JWT default that production refuses, and the enum name `"secret"`. The jinja2 `autoescape=False` in AI prompt templates is intentional (plain text, never HTML). |
| `pip-audit` (88 Python packages) | No known vulnerabilities (re-run after adding pyotp, python-multipart, pdfplumber) |
| `npm audit --omit=dev` (web) | 0 vulnerabilities |
| Test suite | 256 Python tests, including auth, 2FA (replay, recovery, rate limit, admin enforcement, IP allowlist), rate limits, CSRF, role checks, secret masking/encryption, settings validation, sample-upload checks (consent, face check, metadata stripped) and security headers. Plus a browser e2e and a CSP-violation check in a real browser. |

## Open items: must do before real customers

1. **HTTPS.**
   - The test site still runs on plain HTTP (`http://62.84.179.155:3300`), so passwords and cookies cross the network unencrypted.
   - Ready to switch on: point a domain at the server, then run `sudo infra/scripts/setup-https.sh DOMAIN EMAIL`. It adds a host-nginx site + Let's Encrypt with HSTS, binds the edge to localhost, and sets `COOKIE_SECURE=true` and `QAMRA_HTTPS=1`.
2. **Firewall.** `infra/scripts/firewall.sh` (ufw 22/80/443 + DOCKER-USER) is ready but **not applied**: on this shared server it would also close other projects' ports. It runs as a dry run unless given `--apply`.
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
