/**
 * What a public page ships of the messages (Tareq, 2026-10-16): no staff namespace, no cost, margin or printer
 * text, and no price template while prices are hidden; and every namespace a public component uses is shipped.
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join, sep } from "node:path";
import { describe, it } from "node:test";
import {
  adminGateMessages,
  isPriceMessage,
  type Messages,
  PUBLIC_CLIENT_NAMESPACES,
  publicClientMessages,
  STAFF_ONLY_PATHS,
} from "./clientMessages.ts";

const web = new URL("../../", import.meta.url).pathname;
const messages = (locale: "ar" | "en") =>
  JSON.parse(readFileSync(join(web, "messages", `${locale}.json`), "utf8")) as Messages;

/** What a visitor may never find in a public page's source. */
const INTERNAL = /تكلفتنا|هامش|المطبعة|our cost|margin|printer/i;
const PRICE = /₪|شيكل|دينار|\bJOD\b|\bILS\b|\{\s*(price|amount|unit|retail|cost|balance)\b/;

/** Every `useTranslations("…")` outside the admin's folders, with its file. */
function publicNamespaces(): { file: string; ns: string }[] {
  const src = join(web, "src");
  const staff = [join("components", "admin") + sep, join("app", "[locale]", "admin") + sep];
  return (readdirSync(src, { recursive: true }) as string[])
    .filter((f) => /\.tsx?$/.test(f) && !f.endsWith(".test.ts") && !staff.some((s) => f.startsWith(s)))
    .flatMap((file) =>
      [...readFileSync(join(src, file), "utf8").matchAll(/useTranslations\(\s*"([^"]+)"\s*\)/g)].map((m) => ({
        file,
        ns: m[1]!,
      })),
    );
}

const at = (all: Messages, path: string): unknown =>
  path.split(".").reduce<unknown>((node, key) => (node as Messages | undefined)?.[key], all);

describe("the messages a public page ships", () => {
  it("cover every namespace a component outside /admin uses, and none of the staff's parts", () => {
    const shipped = new Set<string>(PUBLIC_CLIENT_NAMESPACES);
    for (const { file, ns } of publicNamespaces()) {
      assert.ok(shipped.has(ns.split(".")[0]!), `${file}: "${ns}" is not in PUBLIC_CLIENT_NAMESPACES`);
      assert.ok(
        !STAFF_ONLY_PATHS.some((p) => ns === p || ns.startsWith(`${p}.`)),
        `${file}: "${ns}" is staff-only (STAFF_ONLY_PATHS)`,
      );
    }
  });

  for (const locale of ["ar", "en"] as const) {
    const all = messages(locale);

    it(`${locale}: every staff-only path exists (no typo leaves one shipped)`, () => {
      for (const path of STAFF_ONLY_PATHS) assert.ok(at(all, path), path);
    });

    it(`${locale}: never the admin's namespaces, costs, margins or the printer`, () => {
      for (const prices of [true, false]) {
        const shipped = publicClientMessages(all, { prices });
        assert.deepEqual(Object.keys(shipped).sort(), [...PUBLIC_CLIENT_NAMESPACES].sort());
        for (const path of STAFF_ONLY_PATHS) assert.equal(at(shipped, path), undefined, path);
        const text = JSON.stringify(shipped);
        assert.doesNotMatch(text, INTERNAL);
      }
    });

    it(`${locale}: no price template while prices are hidden, every one while they are shown`, () => {
      const hidden = JSON.stringify(publicClientMessages(all, { prices: false }));
      assert.doesNotMatch(hidden, PRICE);
      assert.doesNotMatch(hidden, /\{total\}[^"]*(عند الاستلام|on delivery)/);
      const shown = publicClientMessages(all, { prices: true });
      assert.match(String(at(shown, "common.priceFrom")), /\{price\}/);
      assert.equal(at(publicClientMessages(all, { prices: false }), "common.priceFrom"), ""); // emptied, not missing
      // the counts stay: «الخطوة {n} من {total}»
      assert.equal(at(publicClientMessages(all, { prices: false }), "create.stepOf"), at(all, "create.stepOf"));
    });

    it(`${locale}: the admin gate gets its two lines and nothing else of the admin's`, () => {
      const gate = adminGateMessages(all, { prices: false });
      assert.deepEqual(Object.keys(gate.admin as Messages).sort(), ["forbiddenBody", "forbiddenTitle"]);
      assert.doesNotMatch(JSON.stringify(gate), INTERNAL);
    });
  }

  it("tells a price from a count", () => {
    assert.ok(isPriceMessage("common.priceFrom", "يبدأ من {price} ₪"));
    assert.ok(isPriceMessage("orderPath.checkout.confirm", "أكّدوا الطلب · {total} عند الاستلام"));
    assert.ok(!isPriceMessage("create.stepOf", "الخطوة {n} من {total}"));
    assert.ok(!isPriceMessage("create.child.lookHint", "Details the photo may not show."));
  });
});
