# Admin review of every story's text before it is confirmed (2026-10-06)

Tareq: «لازم يبقى معي صلاحيات اني اعمل لها مراجعة او تعديل للنص المكتوب فيها قبل ما اعمل تاكيد لها».
Covers the story books: «قمرة سحري» (incl. custom stories), «قمرة كلاسيك» and the class copies. The
activity books (family, journey, «قلبي يعرف الله») have no generated story text and keep their own gates.

## What existed

- Status flow: `generating → preview` (Magic/Classic preview, the parent may reword pages: `PATCH
  /api/create/books/{id}/pages/{beat}`) → order → final run → `in_review` → admin «اعتماد» (`POST
  /api/admin/books/{id}/approve`, needs print files + preflight) → `approved` → print batches (only
  `approved` books). Class copies: `preview` → the school approves → `in_review` → the same admin approval.
- Admin queue: `/{locale}/admin/queue` (`AdminQueue.tsx`, `routers/admin_books.py`). Per-page text edit
  existed in the page drawer (`PATCH /api/admin/books/{id}/pages/{beat}`): every save set the book to
  `generating` and re-rendered the PDFs, so a second edit had to wait minutes. No title, dedication,
  «للأهل» or back-cover blurb edits; the audit entry had no old/new text; no revert endpoint.
- Where the text reached people **without** an admin seeing it:
  1. The reader treated `in_review` as final: the parent could read the whole book and create a share
     link as soon as the final files were rendered, before any approval.
  2. The "book ready" email (reader link) was sent by the worker at `in_review`.
  3. The parent could keep editing page text in any status, even after approval (the web reader and share
     link read `BookPage.text`, so unreviewed words could appear there).
  Print itself was already gated: print batches take `approved` books only.
- PDFs read `BookPage.text` (pages) and `Book.story` (title, dedication, «للأهل», blurb) at render time,
  so edits in the database flow into the next render; nothing re-reads a cached generation output.

## The change (one gate: the existing approval, extended)

1. **Gate.** `in_review` is no longer readable or shareable by the parent; only `approved`/`ordered`/
   `printed` are. The "book ready" email goes out when the admin confirms (story lines; class copies and
   samples never got it). The parent cannot edit text once the final files exist (`in_review` and later):
   `text_locked`.
2. **Queue.** Story books in `in_review` carry `text_review: "waiting"` → chip «بانتظار مراجعة النص».
3. **Text panel** in the book's review screen: child name, gender and age (grammar check), then the
   title, dedication, the parent's message, every story page next to its picture, «للأهل» and the
   back-cover blurb, each an RTL textarea in the book's Naskh font (tashkeel kept as typed), with its own
   save, «استرجاع النص المولَّد» and its history (who, when, old → new).
4. **Saving is instant** (no status change, no render): the book gets the flag `text_changed`;
   «إعادة إخراج الملفات» (`POST …/rerender`) builds the PDFs once; `approve` refuses with
   `text_not_rendered` while the flag is on. Editing an approved book reopens its review (`in_review`).
5. **Safety.** Edited text goes through the instant screen used for custom-story briefs (links, phone
   numbers, plainly unsafe words). A hit returns `text_unsafe` with the reasons; the admin may save anyway
   with a note, kept in the history and the audit log. The paid AI review is not re-run on staff edits
   (decisions.md).
6. **Audit.** A new table `book_text_edits` keeps old/new text, who, when, revert/edit and the override
   note; it is deleted with the book (privacy: «احذف كل بيانات طفلي»). `audit_logs` gets an id-only
   entry per edit, render and approval (that table keeps no names or text).
7. **«تأكيد».** The existing approve button becomes «تأكيد النص واعتماد الكتاب»; it records who/when
   (`approved_by_user_id`, `approved_at`, audit entry with the number of text edits) and releases the book.
8. **Alert (optional).** Setting `review_alert_email` (empty = off): one email per book when a story book
   first waits for text review.

## Not done (noted)

- Per-page text regeneration by the AI: the pipeline has no per-page text step (only whole-story writing),
  so there is no «أعد كتابة الصفحة» button.
- Class copies: their story text is shared by the class and re-written from the class template on every
  render, so it is shown read-only in the panel; editing it needs per-class overrides (later).
