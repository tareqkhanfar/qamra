/**
 * «إخفاء الأسعار» (Tareq, 2026-10-16): while the admin switch `show_prices` is off the API sends no price, and the
 * site must neither show one nor treat a book without its price as not for sale: `npm test`.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { priceWording, pricesShown } from "./catalog.ts";
import { priceRows } from "./pricing.ts";
import type { Catalog, CatalogAddOn, CatalogProduct } from "./store.ts";
import { freeDigitalCopy, offer, storyFrom } from "./story.ts";

/** A catalog as the API sends it: with its prices, or (hidden) without any price field at all. */
function catalog(hidden: boolean): Catalog {
  const variant = (sku: string, format: string, price: string) =>
    hidden
      ? ({ sku, options: { format } } as unknown as CatalogProduct["variants"][number])
      : { sku, options: { format }, price };
  const product = (slug: string, line: CatalogProduct["line"], variants: CatalogProduct["variants"]) =>
    ({
      slug,
      line,
      name_ar: slug,
      name_en: slug,
      description_ar: "",
      description_en: "",
      option_names: ["format"],
      features: {},
      min_qty: 1,
      variants,
      ...(hidden ? {} : { from_price: "69.00" }),
    }) as CatalogProduct;
  const digital = {
    slug: "digital-copy",
    name_ar: "نسخة رقمية",
    name_en: "Digital copy",
    description_ar: "",
    description_en: "",
    image: null,
    lines: ["classic", "magic"],
    included_lines: [],
    requires: {},
    excludes: [],
    max_qty: 1,
    step: "format",
    ...(hidden ? {} : { price: "0.00", percent: null }),
  } as unknown as CatalogAddOn;
  return {
    products: [
      product("classic-book", "classic", [
        variant("classic-soft-21", "softcover", "69.00"),
        variant("classic-hard-21", "hardcover", "99.00"),
      ]),
      product("magic-book", "magic", [variant("magic-hard-21", "hardcover", "139.00")]),
    ],
    styles: [],
    addons: [digital],
    zones: [],
    ...(hidden ? {} : { currency: "ILS" }),
  } as Catalog;
}

describe("the admin switch", () => {
  it("shows prices only when the admin turned it on", () => {
    assert.equal(pricesShown(null), false); // the API is down: no price by mistake
    assert.equal(pricesShown({}), false); // an older API without the setting
    assert.equal(pricesShown({ show_prices: false }), false);
    assert.equal(pricesShown({ show_prices: true }), true);
  });

  it("uses the no-price wording only while prices are hidden, and only when there is one", () => {
    const has = (k: string) => ["b2b.ctaNoPrice"].includes(k);
    assert.equal(priceWording("b2b.cta", false, has), "b2b.ctaNoPrice");
    assert.equal(priceWording("b2b.cta", true, has), "b2b.cta");
    assert.equal(priceWording("b2b.title", false, has), "b2b.title");
  });
});

describe("a catalog without prices", () => {
  it("still sells its books, with no price to show", () => {
    const hidden = catalog(true);
    const classic = offer(hidden, "classic");
    assert.ok(classic?.available && classic.formats.length === 2); // the books are for sale…
    assert.equal(classic.from, null); // …with no "from" price
    assert.equal(storyFrom(hidden, null), null);
    assert.equal(freeDigitalCopy(hidden, "classic"), null); // no «مجانية» claim without its price
    assert.deepEqual(priceRows(hidden.products[0]!), []); // the prices page has no row
  });

  it("is the same catalog as with prices, less the prices", () => {
    const shown = catalog(false);
    assert.equal(offer(shown, "classic")?.from, 69);
    assert.equal(storyFrom(shown, null), 69);
    assert.ok(freeDigitalCopy(shown, "classic"));
    assert.equal(priceRows(shown.products[0]!).length, 2);
  });
});

describe("the no-price wording", () => {
  const messages = (lang: string) =>
    JSON.parse(readFileSync(new URL(`../../messages/${lang}.json`, import.meta.url), "utf8")) as Record<
      string,
      unknown
    >;
  const PRICE =
    /₪|شيكل|JOD|\bJD\b|ILS|سعر|أسعار|خصم|أوفر|مجان|[Pp]rice|[Qq]uote|[Dd]iscount|[Ff]ree|\{(price|amount|total)\}/;

  /** Every `…NoPrice` / `…Plain` text, at any depth, with its path. */
  function noPrice(node: unknown, path: string[] = [], inside = false): [string, string][] {
    if (typeof node === "string") return inside ? [[path.join("."), node]] : [];
    if (Array.isArray(node)) return node.flatMap((v, i) => noPrice(v, [...path, String(i)], inside));
    if (node && typeof node === "object")
      return Object.entries(node).flatMap(([k, v]) => noPrice(v, [...path, k], inside || /(NoPrice|Plain)$/.test(k)));
    return [];
  }

  for (const lang of ["ar", "en"]) {
    it(`says nothing about price in ${lang}`, () => {
      const texts = noPrice(messages(lang));
      assert.ok(texts.length >= 30, `only ${texts.length} texts`);
      for (const [key, text] of texts) assert.doesNotMatch(text, PRICE, key);
    });
  }

  it("has the same keys in Arabic and English", () => {
    const keys = (lang: string) => noPrice(messages(lang)).map(([k]) => k);
    assert.deepEqual(keys("ar"), keys("en"));
  });
});
