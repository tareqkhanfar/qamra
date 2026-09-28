# Addendum 4 — Product tiers, templates, art styles, add-ons and an enterprise-grade store (for Claude Code)

> Save as `docs/ADDENDUM-04.md` and add to the top of `CLAUDE.md`: "Read docs/ADDENDUM-04.md — it overrides earlier prompts where they conflict." Plan in `docs/plans/addendum-04.md`, then implement in the order of section 9.

Goal: turn Qamra into a well-organized store with a **low-cost product line** (template-based) next to the **premium AI line**, multiple art styles, priced add-ons, and full admin control. Every product must show its cost and margin so pricing always stays profitable.

---

## 1. Two product lines

### A) «قمرة كلاسيك» — template books (low cost, high volume)

- Each theme has a **ready-made illustrated template** per art style: all pages are illustrated once (by us, in advance) with a placeholder hero child.
- Per order, only the **hero's face/appearance** is adapted to the child, using the cheapest reliable reference-edit model. Target: FLUX.2 [klein] on fal or an equivalent. Verify endpoint, price and **commercial license** first.
- Default hero pages: only pages where the hero is visible are edited (usually 60–70% of pages). Pages without the hero are reused as-is.
- The parent chooses gender/look variant of the template (boy/girl, hijab/no hijab, skin tone, hair type) so the base template already looks close before editing.
- Text is editable per page (within length limits); name and gender grammar are automatic.
- **Target AI cost: ≤ 2₪ per book.**
- Drawing companion is not included by default (available as an add-on — see section 4).

### B) «قمرة سحري» — full AI generation (premium)

- The current pipeline: unique illustrations for every page, character sheet, drawing companion included, custom story builder available.
- Target AI cost ≤ $2.50 per book (Addendum 3 rules still apply).

### C) Class books (B2B)

Available in both lines: Classic class book (templates with each child's face on their personal cover + portrait page) and Magic class book (full generation).

## 2. Art styles

- Styles are data, not code: an `ArtStyle` table with:
  - name ar/en
  - style prompt block
  - sample images
  - price modifier
  - availability per line (Classic templates must exist for a style before it's sellable in Classic)
  - active flag
- Initial styles:
  1. **مائي ناعم** (watercolor storybook — the Qamra signature)
  2. **كرتون ملوّن** (bright 2D cartoon)
  3. **ثلاثي الأبعاد** (3D animated-film look — describe the look, never name a studio)
  4. **شبه واقعي** (semi-realistic painted portrait style — not photorealistic, to avoid uncanny results with children)
  5. **كتاب تلوين** (black-and-white line art — cheap to print, great upsell)
- Never use studio or artist names in prompts or marketing (no "Pixar", "Disney", "Ghibli" etc.).
- Each style gets its own style guide file in `packages/ai/prompts/style/` and its own QA thresholds.

## 3. Template studio (admin) — enterprise-grade theme editing

Build a proper editor so the team can manage themes without code:

1. **Theme** → versions (draft/in review/approved/live), with change history and rollback.
2. For each theme × art style × variant (boy/girl/hijab…): the page list with the template illustration, the hero region/mask (for Classic editing), and the text box position.
3. **Page editor (WYSIWYG, RTL):**
   - drag/resize the text box
   - font size within allowed range
   - text for m/f/en with placeholders (`{child}`, `{companion}`, `{family.mom}`)
   - live preview with a sample child
4. **Template generation tool:** generate the base template illustrations with the premium model once per theme/style/variant; review, regenerate per page, lock when approved. Log the one-time cost per template.
5. **Bulk actions:** duplicate a theme to a new style, translate texts, publish/unpublish, seasonal scheduling (auto-live and auto-hide dates).
6. **Roles & permissions:**

   | Role | Permissions |
   | --- | --- |
   | owner | everything |
   | admin | settings, prices, users |
   | editor | themes/templates |
   | reviewer | approve content and books |
   | production | print batches, shipping |
   | support | orders, customers, refunds/reprints |

   Audit log of every change (who, what, when).

## 4. Add-ons (each with its own price and cost)

All add-ons are configured in admin (name ar/en, price ₪/JD, unit cost, availability per product line, active). Initial set with suggested prices (editable):

| Add-on | Suggested price | Notes |
| --- | --- | --- |
| Hardcover upgrade | +30₪ | softcover is base in Classic |
| Premium gift box + card | +15₪ | |
| Custom dedication page | +5₪ | free in Magic |
| Drawing companion (Classic) | +20₪ | included in Magic |
| Extra character (sibling/friend with photo) | +20₪ each | max 3 |
| Family voice QR (recordings) | +15₪ | |
| Extra copy of the same book (e.g., for grandma) | 50% off | print cost + margin only |
| Coloring-book version of the same story | +25₪ | line-art style, cheap print |
| Cover poster A3 | +25₪ | |
| Express production (48h) | +20₪ | capacity-limited |
| Digital copy with a printed order | +0₪ | always free — increases perceived value |

Rules: add-ons can have dependencies (e.g., extra copy requires a printed format) and exclusions; they are shown as simple toggles with images at the right moment in the flow (not all at once), plus a summary before checkout.

## 5. Store structure (catalog, cart, pricing)

- **Product model:** Product (line: Classic/Magic/Class/Coloring) → Variant (format: digital/softcover/hardcover, size 21×21 / 15×15, style) → price per currency. Add-ons attach to variants.
- **Cart** with multiple books (e.g., siblings), editable items, saved cart, guest checkout with phone number.
- **Pricing engine (admin-configurable):**
  - base price by product/variant/style + add-ons
  - bundles (e.g., 2 books −15%, sibling bundle)
  - coupons (percent/fixed, limits, expiry, first-order)
  - seasonal sales with start/end dates
  - B2B price lists per organization with volume tiers
  - JOD pricing for Jordan
- **Shipping:** zones (West Bank cities, Jerusalem, Jordan…) with fees, free-shipping threshold, COD fee if any.
- **Checkout:** COD now; payment gateway interface ready; order summary shows everything clearly in Arabic.
- **Order management:**
  - statuses (new → confirmed → generating → review → printing → shipped → delivered / cancelled / reprint)
  - partial reprints, notes, customer messages via WhatsApp/email templates
- **Invoices/receipts** as PDF (Arabic), numbering per year.

## 6. Cost & margin control (make profit visible)

- Every product, variant, style and add-on has a **unit cost**: AI estimate, print, packaging, shipping cost to us, payment fee.
- Actual AI cost per order comes from `GenerationCost`.
- Admin shows **price, cost and margin (₪ and %)** for every product and every order. Warn in red when an item's margin falls below a configurable floor (default 35%).
- Price simulator in admin: change a price or cost and see margin impact.
- **Reports:**
  - sales by product/theme/style/add-on
  - average order value
  - add-on attach rate
  - conversion (preview → purchase) per line
  - AI cost trend
  - B2B vs B2C revenue
  - CSV/Excel export

## 7. Suggested starting prices (store in admin, not code)

| Product | Price | Target |
| --- | --- | --- |
| Classic digital | 19₪ | entry/impulse |
| Classic softcover | 69₪ | main volume product |
| Classic hardcover | 99₪ | |
| Magic hardcover | 139₪ | premium, drawing companion included |
| Magic + custom story | 169₪ | |
| Coloring book (standalone) | 39₪ | |
| Classic class book (per child, 20+) | 35₪ | |
| Magic class book (per child, 20+) | 50₪ | |

In the create flow, show Classic vs Magic side by side with clear sample pages so the difference is obvious, and suggest the upgrade gently.

## 8. Cheaper infrastructure option (self-hosted) — prepared, not default

- Add a `SelfHostedProvider` that talks to a ComfyUI (or similar) server over HTTP, used only for **Classic template edits**, selectable in admin.
- **Only commercially licensed models are allowed.** Before adding any model, record its license in `docs/licenses.md` and get my approval.
  - Many face-swap and identity tools depend on InsightFace models that are research/non-commercial only (inswapper, antelopev2 etc.). Do NOT use those unless we buy a commercial license.
  - Same for any "dev"/non-commercial model weights.
- Add a **cost comparison** in admin: API spend per month vs estimated GPU server cost. Recommend switching only when monthly Classic image spend exceeds the GPU cost.
- Document setup in `docs/runbooks/self-hosted-gpu.md` (GPU requirements, rental options, deployment with Docker, health checks, fallback to fal when the GPU server is down).

## 9. Implementation order

1. Data model: products, variants, styles, add-ons, price lists, costs, roles (+ migrations, seed with the tables above).
2. Store UI: catalog by line/style, product page with style picker and sample pages, add-on toggles, cart, checkout, order summary. Mobile-first and simple (Production audit rules apply).
3. Classic pipeline (template edit) + QA + cost logging. Prove ≤ 2₪ AI cost per Classic book on 5 test children.
4. Template studio (admin) + roles + audit log.
5. Margins, reports, price simulator.
6. Self-hosted provider scaffolding (inactive).
7. Update the feature matrix and E2E tests: buy Classic softcover + 2 add-ons; buy Magic hardcover with custom story; sibling bundle with coupon; B2B Classic class book with price list.

Report after each step with screenshots (mobile) and the measured cost per book for each line.
