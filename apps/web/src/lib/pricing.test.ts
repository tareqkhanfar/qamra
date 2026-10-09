/**
 * The pricing page's rows (lib/pricing.ts) and the contact numbers (lib/catalog.ts): `npm test`.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { displayPhone, telLink, whatsappLink } from "./catalog.ts";
import { priceFamilies, priceRows } from "./pricing.ts";
import type { CatalogProduct } from "./store.ts";

const product = (
  slug: string,
  line: CatalogProduct["line"],
  variants: [Record<string, string>, string | null][],
): CatalogProduct => ({
  slug,
  line,
  name_ar: slug,
  name_en: slug,
  description_ar: "",
  description_en: "",
  option_names: [],
  features: {},
  min_qty: 1,
  from_price: null,
  variants: variants.map(([options, price], i) => ({ sku: `${slug}-${i}`, options, price })),
});

const ISLAMIC_SETS = { L1: ["V1", "V2"], L2: ["V3", "V4", "V5"], set: ["V1", "V2", "V3", "V4", "V5"] };
const CATALOG = [
  product("classic-book", "classic", [
    [{ format: "digital" }, "19.00"],
    [{ format: "softcover" }, "69.00"],
    [{ format: "hardcover" }, "99.00"],
  ]),
  product("magic-book", "magic", [[{ format: "hardcover" }, "139.00"]]),
  product("magic-custom-story", "magic", [[{ format: "hardcover" }, "169.00"]]),
  product(
    "foundation-workbook",
    "workbook",
    ["kg1", "kg2"].flatMap((level) =>
      ["1", "2", "3", "set"].flatMap((volume): [Record<string, string>, string | null][] => [
        [{ level, volume, format: "spiral" }, volume === "set" ? "179.00" : "69.00"],
        [{ level, volume, format: "digital" }, volume === "set" ? "75.00" : "29.00"],
      ]),
    ),
  ),
  product("learning-journey", "journey", [
    [{ stage: "1", format: "digital" }, "29.00"],
    [{ stage: "2", format: "spiral" }, "69.00"],
    [{ stage: "1", format: "spiral" }, "69.00"],
    [{ stage: "set", format: "spiral" }, "179.00"],
  ]),
  product("family-adventures", "family", [
    [{ format: "spiral" }, "89.00"],
    [{ format: "digital" }, "35.00"],
  ]),
  product("islamic-series", "islamic", [
    ...["V1", "V2", "V3", "V4", "V5", "R"].map((volume): [Record<string, string>, string | null] => [
      { volume, format: "softcover" },
      "79.00",
    ]),
    [{ volume: "L1", format: "softcover" }, "139.00"],
    [{ volume: "L2", format: "softcover" }, "199.00"],
    [{ volume: "set", format: "softcover" }, "329.00"],
    [{ volume: "V1", format: "digital" }, "35.00"],
    [{ volume: "R", format: "digital" }, "35.00"],
  ]),
];

/** "unit format price" per row: easy to compare with the owner's list. */
const said = (rows: ReturnType<typeof priceRows>) =>
  rows.map((r) => `${r.unit ?? "book"}${r.parts ? `(${r.parts})` : ""} ${r.format} ${r.from ? "from " : ""}${r.price}`);

describe("the pricing page's rows", () => {
  const families = priceFamilies(
    CATALOG,
    ["classic", "magic", "coloring", "workbook", "journey", "family", "islamic"],
    {
      islamic: ISLAMIC_SETS,
    },
  );
  const of = (line: string) => families.find((f) => f.line === line)!;

  it("lists each family once, in order, and skips a line with nothing on sale", () => {
    assert.deepEqual(
      families.map((f) => f.line),
      ["classic", "magic", "workbook", "journey", "family", "islamic"],
    );
  });

  it("gives a story its formats, printed first, and the price it starts from", () => {
    assert.deepEqual(said(of("classic").rows), ["book softcover 69", "book hardcover 99", "book digital 19"]);
    assert.equal(of("classic").from, 19);
    assert.deepEqual(
      of("magic").rows.map((r) => `${r.product} ${r.price}`),
      ["magic-book 139", "magic-custom-story 169"],
    );
  });

  it("folds the levels and volumes of an activity book into a part and a set, in print then PDF", () => {
    assert.deepEqual(said(of("workbook").rows), [
      "one spiral 69",
      "set(3) spiral 179",
      "one digital 29",
      "set(3) digital 75",
    ]);
    assert.deepEqual(said(of("journey").rows), ["one spiral 69", "set(2) spiral 179", "one digital 29"]);
    assert.deepEqual(said(of("family").rows), ["book spiral 89", "book digital 35"]);
  });

  it("names «قلبي يعرف الله»'s bundles with the volumes in each", () => {
    assert.deepEqual(said(of("islamic").rows), [
      "one softcover 79",
      "L1(2) softcover 139",
      "L2(3) softcover 199",
      "set(5) softcover 329",
      "one digital 35",
    ]);
  });

  it("says «from» when one row's prices differ", () => {
    const mixed = product("x", "workbook", [
      [{ volume: "1", format: "spiral" }, "69.00"],
      [{ volume: "2", format: "spiral" }, "79.00"],
      [{ volume: "3", format: "spiral" }, null], // not priced: never a row
    ]);
    assert.deepEqual(said(priceRows(mixed)), ["one spiral from 69"]);
  });

  it("has the words for every part in both languages", () => {
    for (const locale of ["ar", "en"]) {
      const page = JSON.parse(readFileSync(new URL(`../../messages/${locale}.json`, import.meta.url), "utf8"))
        .pricingPage as { unit: Record<string, Record<string, string>> };
      for (const family of families)
        for (const row of family.rows)
          if (row.unit) assert.ok(page.unit[family.line]?.[row.unit], `${locale}: unit.${family.line}.${row.unit}`);
    }
  });
});

describe("the contact numbers", () => {
  it("read as people write them, and link to a call and to WhatsApp", () => {
    assert.equal(displayPhone("+970595870228"), "+970 59 587 0228");
    assert.equal(displayPhone("+972595870228"), "+972 59 587 0228");
    assert.equal(displayPhone("+96279123456"), "+96279123456");
    assert.equal(telLink("+970595870228"), "tel:+970595870228");
    assert.equal(whatsappLink("+972595870228"), "https://wa.me/972595870228");
  });
});
