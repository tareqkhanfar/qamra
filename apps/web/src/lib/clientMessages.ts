/**
 * What the browser receives of messages/{ar,en}.json (Tareq, 2026-10-16: no costs, margins or printer prices in
 * a public page's source, and no price templates while prices are hidden).
 *
 * The root layout gives the client provider only the namespaces that client components on public pages use; the
 * staff's namespaces come from `app/[locale]/admin/layout.tsx`, and only to a verified admin. Server components
 * read every message from the request config, so this list only matters for `"use client"` code (and the modules
 * it imports). `clientMessages.test.ts` fails when a public component uses a namespace that isn't listed here.
 */

export type Messages = { [key: string]: unknown };

/** The namespaces client components outside /admin use (whole, minus `STAFF_ONLY_PATHS`). */
export const PUBLIC_CLIENT_NAMESPACES = [
  "account",
  "auth",
  "classic",
  "common",
  "companion",
  "create",
  "customStory",
  "downloads",
  "errors",
  "examples",
  "familyCharacters",
  "familyQuote",
  "freeCover",
  "journeyAudio",
  "mfa",
  "nav",
  "orderPath",
  "password",
  "portal",
  "quiz",
  "reader",
  "shop",
  "store",
  "storyShowcase",
  "themeDetail",
  "themes",
  "voice",
  "workbook",
  "workbookShowcase",
] as const;

/** Staff-only parts of public namespaces: used only by components under /admin (costs, margins, packing slips). */
export const STAFF_ONLY_PATHS = [
  "examples.admin",
  "journeyAudio.admin",
  "orderPath.admin",
  "orderPath.orders",
  "orderPath.slip",
  "portal.admin",
  "portal.priceLists",
  "quiz.admin",
] as const;

/** What the admin gate shows before the staff's messages arrive (a visitor, or a session still being checked). */
export const ADMIN_GATE_KEYS = ["forbiddenTitle", "forbiddenBody"] as const;

/** A currency, or an amount placeholder: «يبدأ من {price} ₪», «+{amount}», «النسخ: {n} × {unit}». */
const MONEY = /₪|شيكل|دينار|\bJOD\b|\bILS\b|\{\s*(price|amount|unit|retail|cost|balance)\b/;

/** Price messages whose amount is `{total}` (every other `{total}` is a count: «الخطوة {n} من {total}»). */
const MONEY_TOTALS = new Set(["orderPath.checkout.confirm", "store.checkout.confirm", "portal.order.orderLine"]);

/** True for a message that states a price (its path is "namespace.key.subkey"). */
export const isPriceMessage = (path: string, text: string): boolean => MONEY.test(text) || MONEY_TOTALS.has(path);

const isObject = (v: unknown): v is Messages => typeof v === "object" && v !== null && !Array.isArray(v);

/**
 * A copy of `node` without the staff-only paths and, while prices are hidden, with every price message emptied.
 * Emptied, not removed: the screens already skip their prices when `show_prices` is off, and an empty string can
 * never raise next-intl's MISSING_MESSAGE (nor show a raw key) if one of them is still asked for.
 */
function prune(node: unknown, path: string, prices: boolean): unknown {
  if (typeof node === "string") return !prices && isPriceMessage(path, node) ? "" : node;
  if (Array.isArray(node)) return node.map((v, i) => prune(v, `${path}.${i}`, prices));
  if (!isObject(node)) return node;
  const out: Messages = {};
  for (const [key, value] of Object.entries(node)) {
    const child = `${path}.${key}`;
    if ((STAFF_ONLY_PATHS as readonly string[]).includes(child)) continue;
    out[key] = prune(value, child, prices);
  }
  return out;
}

/** The messages a public page ships to the browser. `prices`: the admin switch `show_prices`. */
export function publicClientMessages(all: Messages, { prices }: { prices: boolean }): Messages {
  const out: Messages = {};
  for (const ns of PUBLIC_CLIENT_NAMESPACES) {
    if (ns in all) out[ns] = prune(all[ns], ns, prices);
  }
  return out;
}

/** The public messages plus the admin gate's own lines: what /admin ships until the session is a verified admin. */
export function adminGateMessages(all: Messages, { prices }: { prices: boolean }): Messages {
  const admin = isObject(all.admin) ? all.admin : {};
  return {
    ...publicClientMessages(all, { prices }),
    admin: Object.fromEntries(ADMIN_GATE_KEYS.filter((k) => k in admin).map((k) => [k, admin[k]])),
  };
}
