# Qamra social kit (Instagram + Facebook)

HTML/CSS templates rendered to PNG with Playwright (Chromium). Every word is in `copy.yaml`, every post caption
in `captions.yaml`, every photo slot in `images.yaml`. The art is drawn in code: sky, moon, stars, tatreez band,
book mockups and icons. The only bitmaps are images that are already public on the website.

```bash
uv run python scripts/social_kit.py                     # everything → out/social/*.png + out/social/contact-sheet.png
uv run python scripts/social_kit.py --only ad-b         # one design or a group (prefix match, repeatable)
uv run python scripts/social_kit.py --incoming DIR      # read delivered photos from DIR instead of design/incoming/
uv run python scripts/social_kit.py --videos --package  # + the MP4s (out/social/video/) + out/social/package/
uv run python scripts/social_kit.py --videos --only cut-1   # one video, from the PNGs already in out/social/
```

`--videos` needs ffmpeg (`--ffmpeg PATH`, `$FFMPEG`, ffmpeg on PATH, or the `imageio-ffmpeg` binary) and the brand
film's folder `out/video/` (made by `scripts/build_film.py`). Every video is H.264 with the brand soundtrack (AAC
48 kHz stereo, −14 LUFS), at most 8 MB (the cutter raises the CRF until it fits), and gets three review frames in
`out/social/video/frames/`. Each video comes twice: `<name>.mp4` with the Arabic voiceover over the music, and
`<name>-music.mp4` with the music and sound effects only (for ads that run muted or need no voice).

The soundtrack (`scripts/film_audio.py`, design and cue sheets in `content/marketing/film-audio/soundtrack.yaml`):
one gentle lullaby bed (Google Lyria 2), a sparkle chime when the moon or the magic appears, a page-turn whoosh on
each scene change (ElevenLabs sound effects), and one calm female voice (ElevenLabs Multilingual v2) reading the
words the video shows. The sounds are made once on fal and kept in that folder, so cutting costs nothing; the
cutter warns when a line would not fit its shot.

`out/` is gitignored. Each render also runs a layout check (`templates/qa.js`). It fails the run if text leaves
its box or the safe zone, a headline line wraps, text boxes overlap, or a paragraph ends with a lone word.

## What it renders

| File | Size | Notes |
|---|---|---|
| `profile.png` | 1080×1080 | Moon mark + wordmark on night blue; reads inside a 110 px circle |
| `fb-cover.png` | 1640×624 | Text and books sit in x 285–1355 (phones crop the sides); bottom corners kept free |
| `highlight-1…6-*.png` | 1080×1920 | كتب القصص، الدوسيات، الروضات، كيف نطلب، التوصيل، العروض. Icon + label inside the centre circle |
| `ad-a-launch` … `ad-g-trust.png` | 1080×1350 | Seven feed ads on one grid: logo top-right, pill top-left, headline, one line, picture, CTA + qamra.app |
| `carousel-1…4-*.png` | 1080×1350 | «كيف نعمل»: الصورة ← الشخصية ← الحكاية ← الكتاب المطبوع |
| `story-a-launch`, `story-b-kindergarten`, `story-f-gifts.png` | 1080×1920 | Nothing in the top 220 px; CTA ends 250 px above the bottom |

Grid: 88 px margins, 8 px spacing steps, Baloo Bhaijaan 2 for headlines and IBM Plex Sans Arabic for text.
Noto Naskh appears only inside a book page (the vowelized story line in carousel 3), as in the printed books.

### October 2026 set (posts, carousels, Meta ads, videos)

| Files | Size | Notes |
|---|---|---|
| `post-01-qamour` … `post-18-faq-2.png` | 1080×1350 | A month of feed posts, numbered in posting order (`calendar.md`) |
| `carousel-photo-to-book-1…5`, `carousel-kindergartens-1…5.png` | 1080×1350 | Slide 1 is a cover (no step tracker) |
| `meta-<set>-1x1.png`, `meta-<set>-4x5.png` | 1080×1080, 1080×1350 | Four ad sets: parents, kindergartens, activity-books, gifts. Texts in `ads.md` |
| `end-*.png` | 1080×1920 | Video end cards and the frames of the activity-books video; nothing under y 1560 |
| `overlay-*.png` | 1080×1920, 1080×1350 | Transparent: logo + line above the film, CTA bar «اطلبوا الآن · qamra.app» below |
| `video/reel-film-9x16`, `video/feed-film-4x5.mp4` | 1080×1920, 1080×1350 | The 20-second film centred over a blurred, enlarged copy of itself |
| `video/cut-1…3-*-9x16.mp4` | 1080×1920 | 7–8 s cut-downs: photo → character, the printed book, kindergartens |
| `video/ad-<set>-9x16.mp4` | 1080×1920 | The 9:16 variant of each Meta ad set (11–13 s) |
| `video/*-music.mp4` | as above | The same videos with the music only (no voice) |

`--package` collects what Tareq uploads into `out/social/package/`: `posts/`, `reels/`, `ads/<set>/`, `stories/`,
`profile/` (profile picture, Facebook cover, highlight covers),
`ads.md`, `calendar.md` and `captions.md` (captions.yaml as a sheet to copy from).

Their pictures come from the `media:` registry at the end of `images.yaml` (site photos, theme plates, the film's
stills and mockups), each checked by eye: **no little girl in a hijab in our marketing** (adults in a hijab are
fine). `content/cast/classmates-*` breaks that rule and is never used; `photos/graduation-class.jpg` is the
2026-10-03 file without hijabs. The film's sample girl is AI-made, so every post or video that shows her as "the
photo" says «مثال توضيحي». Never mention «قلبي يعرف الله» here: it is not on sale yet.

## Pictures in each design

| Design | Drawn in code | Public images used (apps/web/public/…) | Incoming image that replaces the picture |
|---|---|---|---|
| profile, highlights | all | none | none |
| fb-cover | sky, moon, hardcover «ليان في أوّل يوم بالروضة» | `workbooks/character.webp`, `workbooks/learning-journey/01.jpg` | none |
| ad-a-launch, story-a-launch | hardcover «ليان في أوّل يوم بالروضة» | `character.webp` | **A1-hero-reading**, else **B1** (once it has a `cover_quad`) |
| ad-b-kindergarten, story-b | stack of «يوم تخرّج …» books + «يوم تخرّج ليان» | `character.webp` | **A3-graduation-class** |
| ad-c-family | spiral binding, stickers | `workbooks/family-adventures/01, 02, 04.jpg` | **A4-family-book-table** |
| ad-d-journey | spiral binding, phone | `workbooks/learning-journey/01, 10.jpg` | **A6-journey-qr**, else **B4** (once it has a `cover_quad`) |
| ad-e-foundation | spiral binding | `workbooks/foundation-workbook/01, 02, 09.jpg` | **A5-workbook-tracing** |
| ad-f-gifts, story-f-gifts | hardcover «ليان وضيفنا الصغير», ribbon, tag | `character.webp` | **A8-gift-box** |
| ad-g-trust | icons only | none | none |
| carousel-1-photo | phone, face guide, a head-and-shoulders shape (never a real photo) | none | none |
| carousel-2-character | character card | `character.webp` | none |
| carousel-3-story | open book with the vowelized first page of «أوّل يوم في الروضة» | `character.webp` | **B2-mockup-open-spread** (once it has a `cover_quad`) |
| carousel-4-book | hardcover «يوم تخرّج ليان» | `character.webp` | **B1-mockup-hardcover-angle** (once it has a `cover_quad`) |

A2, A7, A9, A10 and B3 are not used here. Nothing comes from `out/`, and no real child's photo is used. ليان, يوسف,
سلمى, آدم, جنى and كريم are invented sample names. `character.webp` is the site's AI-drawn sample character.

### Adding Tareq's photos and mockups

1. Save the file in `design/incoming/` under its name from `docs/image-prompts.md` (e.g. `A1-hero-reading.png`).
2. Re-render. A photo (A…) fills the picture box. Its `focus` in `images.yaml` decides what stays in view when
   it is cropped.
3. Mockups (B…) have a blank white cover, so the renderer lays our cover onto them. That only works once you
   fill in `cover_quad`: the cover's four corners in the photo's own pixels, in this order: top-left,
   top-right, bottom-right, bottom-left (as printed; the spine is on the right). Read them in any image
   viewer. Until then the renderer keeps the code-drawn book and prints a note.

## Editing the copy

- All copy rules are at the top of `copy.yaml`: MSA, parents addressed as أنتم, real products and facts only,
  and Arabic-Indic digits.
- Headlines are lists of lines. Each line is set as written, and the check fails if a line wraps.
- `~` glues two words so a line never breaks between them (`أولياء~أمره`). It prints as a space.
- Book covers (`covers:`) follow the theme title templates in `content/themes/*/theme.yaml`. They use only
  stories that are «available».
- No prices appear on the images or in the captions, so nothing goes stale when the admin changes prices. Only
  `ads.md` quotes «يبدأ من» prices from `content/store/catalog.yaml`; check them against the admin before a campaign.
