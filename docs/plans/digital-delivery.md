# Digital delivery: the parent downloads the PDF they bought

2026-10-08. The store sells files: a story's «نسخة رقمية» (`classic-digital`, 19 ₪) and the activity books'
«ملف PDF» (the foundation volumes and set 29/75 ₪, the journey stages 29 ₪, the family book 35 ₪, the Islamic
volumes 35 ₪). Until now a parent had no way to get the file: no endpoint, nothing on the account or order page,
nothing in the emails. Only staff could download print files (`admin_portal.py _download`).

**Paths:** `api/` = `apps/api/src/qamra_api/`, `worker/` = `apps/worker/src/qamra_worker/jobs/`,
`web/` = `apps/web/src/`.

## 1. What a line gives (`packages/core/src/qamra_core/downloads.py`)

| Line | File(s) |
| --- | --- |
| any `format: digital` variant | the whole book with its cover, cut for home printing (one file per volume or stage; a set gives every one), **plus** the extra files its job renders: the answer key (journey, Islamic, foundation), the sticker sheet (family book, every journey stage, every Islamic volume: `files["stickers"]`, order-flows.md «The included sticker sheets») and the family book's card sheets, since a digital buyer gets no printed insert |
| a printed «رحلتي الأولى» stage | only its answer key, a free download (Addendum 6 §5) |
| any other printed line | nothing. The free «نسخة رقمية مع المطبوع» stays the web reader (owner's audit, 2026-10-07), and a PDF of the printed book would undercut the digital variants |

## 2. When (the same gates as the reader and the print approval)

- **Story** (Classic, Magic): once staff confirmed its words («تأكيد النص واعتماد الكتاب»: `approved`, `ordered`,
  `printed`). `in_review` is not ready (commit 1b297a6).
- **Activity book**: once its render passed: `in_review` with every preflight report passed and none of the flags
  a reviewer must see first (`preflight_failed`, `scholar_review`, `pages_missing`, `text_changed`,
  `name_en_guessed`, `name_not_traceable`); or once an admin approved it. A digital file does not wait for the
  print approval.
- **Set**: each volume as soon as it is ready; the line is "ready" (and emailed) when every volume is.
- **Order**: confirmed and not cancelled (a `new` order's line is listed as "preparing"); the child's data not
  deleted.
- **Owner**: the child's guardian, on an order placed from their account or as a guest (checked out signed out).
  Someone else's line: **403** `download_not_yours`. A line that doesn't exist or offers nothing: 404.

## 3. API (`api/routers/downloads.py`)

| Method and path | Answer |
| --- | --- |
| `GET /api/downloads[?order=QM-…][&lang=ar\|en]` | the parent's lines, newest order first: `{item_id, order_code, placed_at, child_id, child_name, line, sku, name_ar, name_en, options, book_title, status: ready\|preparing, parts_total, parts_ready, files: [{book_id, kind, part, level, name}]}`; `files` are the ready books' files |
| `GET /api/downloads/{item_id}` | one line (the order page's button); 401 signed out, 403 someone else's, 404 nothing to offer |
| `POST /api/downloads/{item_id}/files/{book_id}/{kind}` | `{status: ready, name, url}` or `{status: preparing, name}`; asks the worker for the home copy once (a failed copy is asked for again) |
| `GET /api/downloads/{item_id}/files/{book_id}/{kind}` | the copy's state: `ready` (with `url`), `preparing` or `failed` |
| `GET /api/downloads/{item_id}/files/{book_id}/{kind}/pdf` | the file, streamed: `Content-Disposition: attachment; filename="qamra-qm-ab12cd-v1.pdf"; filename*=UTF-8''قلبي-يعرف-الله-المجلد-1-ضحى.pdf`, `Cache-Control: private, no-store`; 409 `download_preparing` while the copy is being made |

- `kind`: `book`, `answer-key`, `stickers`, `card-money-recipes`, `card-games-roles`.
- Errors: 409 `download_not_ready` (a story before «تأكيد», a render still running), 429 `too_many_attempts`
  (120 prepares and 60 downloads per parent per hour, Redis counters).
- **Audit:** every download writes `download.file` (entity `order_item`, data: order, book and kind ids). No name,
  no file name.
- **Streaming, not a signed URL:** the bucket stays private and no storage URL reaches the browser (the local
  SeaweedFS endpoint isn't even reachable from it). `ObjectStorage.stream` reads 1 MB chunks, so the API never
  holds a whole file.
- The order tracking (`GET /api/store/orders/{code}`) now sends each line's `id` and `downloadable` (a digital
  line), for the order page's button.

## 4. The home copy (`packages/pdf/src/qamra_pdf/home.py`, `worker/downloads.py`)

The print files have a 3 mm bleed with exact TrimBox/BleedBox (`qamra_pdf.render.set_boxes`) and **no crop
marks**. So no renderer changes: the worker cuts every page to its TrimBox (MediaBox = CropBox = TrimBox) with
pypdf. Nothing is re-rendered: vector text, embedded fonts and 300 DPI pictures stay. Measured on our samples: a
24-page story in 0.5 s, a 120-page Islamic volume in 0.5 s, a 120-page journey stage in 0.8 s.

- **Cover:** front first, back last.
  - An activity book's cover is two pages of the interior's size.
  - A story's cover is one wrap, [front | spine | back] for an Arabic book and [back | spine | front] for an
    English one. Each panel is cut at the interior's trim width, so the spine formula never matters.
  - A cover of any other shape is left out rather than printed wrong.
- **Size:** the book's own trim (21×21, 21×28 or A4). The page tells parents to print on A4 with «ملاءمة للصفحة».
- **Where:** `children/{child}/books/{book}/home/{kind}/{version}.pdf`. The version is a hash of the print files'
  ETags (`ObjectStorage.etag`): a re-render makes a new copy and the old one is deleted. It sits under the child's
  prefix, so «حذف كل بيانات طفلي» (`delete_prefix(children/{id}/)`) removes it with everything else (tested).
- **When:** on the parent's first tap (`prepare_file`, queue `pdf`), or before the email (below), so the first tap
  usually downloads at once. Redis keeps the state for the API with ids only: `dl:prep:{book}:{kind}:{version}`
  (15 min) and `dl:failed:…` (1 h).

## 5. The email (`worker/downloads.py`, `content/emails/messages.yaml` `download_ready`)

- `scan_ready_lines` runs every 5 minutes (`cron_config`). It finds the digital lines of live orders from the last
  60 days whose books are all ready and whose parent wasn't told yet. It queues `deliver_line` once per line
  (Redis guard).
- `deliver_line` makes the line's home copies, then sends one email per line (the `notifications` ledger,
  `download:{item_id}`). It links to `/{lang}/account#downloads`, **never to the file**.
- Printed lines (the journey's free answer key) get no email.
- A digital story also gets the existing "book ready" email at «تأكيد» (the reader link); this one is about the
  file.

## 6. Web

- `web/lib/downloads.ts`: the types and calls.
- `web/components/order/DownloadButton.tsx`:
  - **`<DownloadButton itemId line? />`**
    - `itemId`: the order line's id (the order page: the tracking's `items[].id`; the account page: `item_id`).
    - `line` (optional): the line as `GET /api/downloads` returned it; without it the component fetches it.
    - It shows one row per ready file («المجلد الأول · الكتاب مع غلافه» + «تنزيل PDF»). States: preparing (a
      spinner, the state polled every 3 s for about 3 minutes), ready (the download starts; «لم يبدأ التنزيل؟
      اضغطوا هنا» stays), failed and slow (a friendly message and «حاولوا مرة أخرى»), an API error (its
      message).
    - A digital line not ready yet says that we'll email. Signed out, it offers «تسجيل الدخول» and comes back to
      the page. Someone else's order shows the API's message. A line with nothing to download renders nothing.
  - **`<DownloadsSection lines />`**: the account page's «ملفات للتنزيل» (`id="downloads"`, scrolled to from the
    email), each line with its title, its variant and its order code.
- `web/components/AccountView.tsx`: the section above the tabs, filtered by the selected child; it is emptied for
  a deleted child.
- `web/components/store/OrderView.tsx`: `<DownloadButton itemId={item.id} />` on every `downloadable` line, in the
  slot chunk 7 left.
- Messages: the `downloads` namespace in `messages/{ar,en}.json`. An independent language review set the
  words: «تنزيل» (download) as in the order line's «تنزّلون الملف…», because the site uses «تحميل» for
  "loading"; «سنخبركم بالبريد الإلكتروني»; «الحساب الذي استخدمتموه في الطلب».

## 7. Not done (decisions to take later)

- **No per-order home render at A4.** The copy is the book's own size; a parent prints it with «ملاءمة للصفحة».
  An A4 imposition would need renderer work and gains little.
- **The Islamic printed parent guide** (`printed-parent-guide`, 15 ₪) stays a printed add-on. Addendum 10 doesn't
  promise a free download, unlike the journey's (Addendum 6 §5).
- **Guests without an account:** a guest order is downloadable once the parent signs in to the account that owns
  the child. Every line with a child was made in the create flow, which needs an account.
