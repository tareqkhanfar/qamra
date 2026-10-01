# Lifestyle photos

Drop the JPEG files listed below into this folder (exact names, lowercase). Each slot renders the photo when
its file exists and falls back to the current illustration (or to nothing) when it doesn't, so a missing file
never breaks a page. Photos are served through `next/image` (resized per device), so upload the full size:
about 2400 px on the long side, sRGB, under 1 MB each. Show no real child's face without written consent;
the site never says these are customers.

| File                       | Ratio | Where it appears                                                                                      |
| -------------------------- | ----- | ----------------------------------------------------------------------------------------------------- |
| `hero-reading.jpg`         | 3:2   | Home hero (a child reading their printed book)                                                        |
| `first-day.jpg`            | 3:2   | How it works, the header (tablet and desktop; hidden on phones)                                       |
| `graduation-class.jpg`     | 3:2   | Kindergartens page hero, and the kindergartens card on the home                                       |
| `family-book-table.jpg`    | 3:2   | «مغامراتي مع عائلتي» product page (below "what's yours")                                              |
| `workbook-tracing.jpg`     | 1:1   | «دوسية التأسيس» product page, and the activity flow on how it works                                   |
| `journey-qr.jpg`           | 3:2   | «رحلتي الأولى للتعلّم» product page (the audio QR)                                                    |
| `grandma-voice.jpg`        | 3:2   | How it works, the «صوت أهلي» section                                                                  |
| `gift-box.jpg`             | 1:1   | Pricing, the add-ons section                                                                          |
| `books-stack.jpg`          | 1:1   | Activity books hub header and the band on the home (desktop), and the activity-books card on the home |
| `kindergarten-teacher.jpg` | 3:2   | Kindergartens page, next to the quote form                                                            |

Slots are declared in `src/components/site/Photo.tsx` (`PHOTOS`); adding a slot means adding a row here and
a name there. Files in this folder are public and cached for a week (`next.config.ts`), so replacing a photo
may take up to a week to show for returning visitors unless its name changes.
