# Phase 5 — Polish (outline)

Changes from Addendum 1 — «صوت أهلي» family voice:
- QR per story page (18 mm + 2 mm quiet zone, outer bottom corner inside the 10 mm safe area) → `https://{BRAND_DOMAIN}/v/{book_token}/{page}`.
- Record screen (large text, record/listen/re-record), voices ماما/بابا/ستّي/سيدي (max 3 per page), listener can switch. Real voices only — no cloning.
- Remote elder recording link (no account, expires in 7 days).
- TTS fallback when no recording exists.
- Data model designed earlier (Phase 1): `Recording`, `ShareToken` (scope, expires_at, revoked).
- Add-on `family_voice` (+15₪ per book).
