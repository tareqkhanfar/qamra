# Phase 4 — Kindergarten portal and «كتاب الصف» (built)

Scope: CLAUDE.md §8 B2B and §9 Phase 4, Addendum 1 §2 (the class book), Addendum 4 §1C (Classic and Magic class
books) and §5 (B2B price lists), `remaining-work.md` item W4.

**Acceptance: "a class of 30 can be generated in one batch and exported as one print bundle."** It is checked by
`apps/worker/tests/test_classbooks.py::test_a_class_of_30_is_drawn_in_one_batch_and_exported_as_one_bundle`, with
the offline providers:
- 20 shared pages, at most 3 children per picture;
- every child on at least 2 pages;
- 30 personal covers, and 30 copies whose interior and cover pass preflight;
- one combined print file of 30 × (cover + 24 interior pages).

## The flow

1. **Sign-up** (`/portal/signup`). A kindergarten gives its name, contact, city, address and phone. It gets a
   `school_admin` account at once, and the organization stays `pending`. Until our team approves it in the admin
   (`/admin/organizations`, with an audit entry), only the dashboard answers.
2. **Classes**: a name, a teacher and a school year.
3. **Children from CSV**. The school downloads a template and uploads its list: name, gender, birth year or age,
   and the parent's phone or email. It gets a row-by-row preview with reasons in Arabic and English, then imports
   the valid rows.
   - Headers can be Arabic or English, in any order.
   - Both CSV encodings Excel writes are read (UTF-8, and Windows-1256 for Arabic Excel), with commas, semicolons
     or tabs.
   - `.xlsx` is refused with a friendly "save as CSV" message (see decisions).
4. **An invite link per child** (`/invite/{token}`), tokenized and expiring (`portal_invite_days`, 30 by default).
   The school copies it or shares it on WhatsApp from its own phone.
   - The parent opens the link, signs in or creates an account, and accepts. The child becomes theirs, with every
     right of the create flow, including "delete all my child's data".
   - The parent then gives the invite's consent (version `school-2026-09`: it also covers the class book), uploads
     one photo and approves the character.
   - These steps reuse the create flow's handlers: consent through the shared `qamra_api.consent.record_consent`,
     the photo upload with its face check, and the drawing in the class's art style through
     `create.draw_character`.
5. **The teacher's status board**: invited → consent → photo → drawing → character approved, per child.
   - Only states reach the school. It sees that a photo was uploaded, never the photo or its address.
   - The school can see the parent-approved drawing (an illustration), the same drawing that goes into the book.
6. **Class book setup** (`/portal/classes/{id}/book`):
   - one story and one line for the class (Magic or Classic), and the art style;
   - the minimum number of appearances (2 by default, the `class_book_min_appearances` setting);
   - the teacher's message and the school logo;
   - the class photo, accepted only with the school's confirmation that the parents agreed to it being printed.
     The photo is stored privately with its EXIF stripped, and the confirmation is audited.
7. **The plan** (`/portal/classes/{id}/planner`):
   - The shared scenes come from `content/class-books/<theme>.yaml`. Core scenes are always in; `extra` scenes are
     added in their story position until everyone fits.
   - Places per picture are capped per image provider (`class_book_refs`, e.g. `fal:3`).
   - The automatic plan gives every child exactly N appearances, spread over the book, never twice on a page, with
     the pages filled evenly.
   - The teacher can move children: tap a child, then a page (phones), or drag and drop (desktop).
   - Generation refuses a plan where a child is below N.
8. **The batch**: one RQ job per class (`jobs.classbooks.generate_class_book`), with a live progress board.
   - It draws the shared pages. Each picture gets every child's approved character sheet as a reference, then a
     vision check that looks for each child. An unrecognized child triggers a redraw, then a flag for a human.
   - It then draws a personal cover per child.
   - Finally it renders every copy: the school page, the child's portrait page, the shared story pages, the class
     group page ("my friends"), and padding to the printer's signature.
   - The job resumes: pages already drawn for the same children stay drawn.
9. **Review and bulk approval**. The school sees every shared page with who is on it (and who wasn't recognized),
   every copy's cover and PDF, and can request a few free redraws (6 per class).
   - It approves all copies, or the ones it selects. Approved copies go to the admin review queue as ordinary
     books (`in_review`).
   - Staff approve them one by one, or all at once from `/admin/organizations`. Both paths use the queue's own
     approval checks: preflight, files and audit.
10. **The order** (`/portal/classes/{id}/order`):
    - wholesale prices from the school's own price list, else the default kindergarten list;
    - the store's pricing engine, with tiers by the order's total quantity;
    - one order with one item per approved copy, and one invoice (the store's `issue_invoice`, rendered by the
      invoice job);
    - delivery to the school's address, cash on delivery.

    Once staff confirm the order, the print-batch collector picks it up after every copy has passed print approval.
11. **The print bundle per class**:
    - each child's interior and cover under their own storage prefix, served as `{school}-{class}-{child}.pdf` and
      `…-cover.pdf`;
    - one combined print file: each child's cover, then their interior, with the shared pictures stored once.

    Everything is private and listed for admins with per-child coverage.
12. **B2B price lists** in the catalog admin (the «أسعار الروضات» tab):
    - the default list and per-kindergarten lists;
    - tiers per variant, with the margin per tier;
    - every edit audited.

## Where the code is

- **Data** (`packages/core`):
  - `db/portal.py`: `ChildInvite`, `ClassBook`, `ClassBookPage`;
  - `Organization.address`;
  - settings `class_book_min_appearances`, `class_book_refs` and `portal_invite_days`;
  - the `organizations` permission (admin role);
  - migration `e6b4b0230d6a`.
- **Pipeline** (`packages/ai`):
  - `pipeline/classbook.py`: the template, the plan, the multi-child pictures and their check;
  - prompts `class_scene.v1.j2` and `class_scene_qa.v1.j2`;
  - `content/class-books/graduation.yaml`.
- **PDF** (`packages/pdf`): `qamra_pdf/classbook.py`, and the templates `class_interior`, `class_portrait`,
  `class_cover` and `_class.css`.
- **Worker**: `jobs/classbooks.py`.
- **API**:
  - routers `portal.py`, `portal_children.py`, `portal_book.py`, `portal_order.py`, `invite.py`, `admin_portal.py`;
  - price lists appended to `admin_catalog.py`;
  - the package `qamra_api/portal/` (access, importer, status, planning, ordering);
  - `consent.py`.
- **Web**:
  - `components/portal/*`, `lib/portal.ts`;
  - pages under `app/[locale]/portal/`, `app/[locale]/invite/[token]`, `app/[locale]/admin/organizations`;
  - `components/admin/catalog/PriceListsPanel.tsx`.
- **Tests**:
  - `apps/api/tests/test_portal.py` (the whole flow), `test_portal_access.py` (isolation, planner, class photo,
    price lists) and `test_portal_import.py`;
  - `apps/worker/tests/test_classbooks.py`;
  - `packages/ai/tests/test_classbook.py` and `packages/pdf/tests/test_classbook_render.py`.

## Not done here (see the report's open points)

- Reading `.xlsx` directly; this needs a new dependency.
- The drawing-companion upload in the invite flow. W3 is building the parents' «ارسم صاحبك» step. The board already
  shows the "drawing" step, and the portrait page shows an approved companion when there is one.
- A second class-book story. Only `graduation` has a class template for now.
- Bank transfer as a payment method. The design shows it; orders are cash on delivery until it exists.
- Extra copies for the school or teacher with a class cover (design ClassPrint).
