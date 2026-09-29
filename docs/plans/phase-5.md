# Phase 5 — Polish

Scope as updated on 2026-09-29 (Addendum 9: cash on delivery only, email the only automatic channel):
«صوت أهلي» first, the WhatsApp adapter interface only, SEO for the story pages, and a short performance pass.
Gift cards moved to the Addendum 9 cart work, and English and JOD pricing were already done.

## «صوت أهلي» (Addendum 1 §3, Addendum 4 §4 `family-voice`) — done

| Piece | Where |
| --- | --- |
| Feature switch: the order line's `family-voice` add-on | `qamra_core/voice.py` (`addon_query`) |
| Parent API: book, record, re-record, delete, invites, pause listening | `routers/voice.py` |
| No-account API: grandparent link, listen page, signed audio, narrator | `routers/voice_public.py`, `voice_common.py` |
| QR per story page in the print PDF, and the back cover | worker `voice.py` → `assemble.py` `voice_url` → `qamra_pdf` `PageSpec.qr_url` |
| TTS adapter (off: `tts_provider` = none) | `qamra_ai/tts/` |
| Screens (designs VoiceRecord, VoiceInvite, VoiceElder, VoiceListen) | `components/voice/`, routes `/books/[id]/voice`, `/books/[id]/voice/invite`, `/r/[token]`, `/v/[token]/[page]` |
| Migration | `19ebf7d578eb`: `share_tokens.pages`, `share_tokens.opened_at` |

Differences from the designs:
- The copy addresses families in the plural, like the rest of the site («اقرؤوا»، «أعيدوا»), not «اقرئي». The voice is typed by the family, so its gender isn't known.
- A grandparent's recording is saved the moment they stop. There is one less button to find.
- The record screen adds «على هذه الصفحة» (play or delete each voice) and the pause-listening switch.
- The QR is on every story page, not only the recorded ones (see decisions).

## WhatsApp adapter interface — done, nothing sent

`qamra_api/whatsapp.py`: links (default), log, Twilio (disabled until Tareq approves it and gives the account).

## SEO for `/stories/[slug]` — done

- Metadata per language, with canonical and hreflang.
- The Open Graph picture from the published example's cover.
- Product + Book JSON-LD.
- `app/sitemap.ts` (per request) and `app/robots.ts`.
- Private pages noindex.

## Performance pass — measured

Lighthouse 13, mobile with simulated slow 4G, on a local production build. The API ran against the tunnelled test database, so the TTFB of about 0.9 s is higher than production will be.

| Page | Score before → after | LCP | CLS | JS (KB) | Total (KB) |
| --- | --- | --- | --- | --- | --- |
| `/ar` | 80 → 82 | 5.1 → 4.8 s | 0 | 162 | 660 |
| `/ar/stories` | 85 → 85 | 4.3 → 4.3 s | 0 | 161 | 531 |
| `/ar/stories/first-day` | 82 → 84 | 4.9 → 4.5 s | 0 | 167 | 628 |
| `/ar/shop` | 84 → 86 | 4.4 → 4.0 s | 0 | 155 | 543 |
| `/ar/v/…/3` (new listen page) | 87 | 3.9 s | 0 | 158 | 486 |

- First-load changes are within run-to-run noise. The weight is fonts (13 files, about 380 KB) and the framework (about 160 KB).
- Preloading only the Arabic font files was tried and reverted (FCP 1.4 → 2.1 s): Latin digits and punctuation appear on every page, so those files load anyway.
- Kept:
  - `/public` images, audio and the icon are cached for a week (they were `max-age=0`);
  - the workbook cover's character image has its box reserved.
- Images elsewhere were already sized and lazy (`ExampleImage`, workbook thumbnails), and the catalog calls stay cached as before.
- Open: fewer font weights (7 weights in Arabic and Latin) would cut the most, but that is a design decision.
