/**
 * The line summaries of the cart, the checkout and the order page (lib/variantSummary.ts), checked against
 * docs/plans/order-flows.md §c.9: `npm test`.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { summarize, type LineInput, type Part, type Summary } from "./variantSummary.ts";

type Tree = { [key: string]: string | Tree };
const messages = (locale: string): Tree =>
  (JSON.parse(readFileSync(new URL(`../../messages/${locale}.json`, import.meta.url), "utf8")) as Tree)
    .orderPath as Tree;
const AR = messages("ar");
const EN = messages("en");

/** A message under orderPath.line, or undefined. */
function lookup(tree: Tree, key: string): string | undefined {
  let node: string | Tree | undefined = tree.line;
  for (const k of key.split(".")) node = typeof node === "object" ? node[k] : undefined;
  return typeof node === "string" ? node : undefined;
}

/** The Arabic words of a part, without ICU: enough to compare with the plan's examples. */
function ar(part: Part): string {
  if ("text" in part) return part.text;
  const text = lookup(AR, part.key);
  assert.ok(text, `orderPath.line.${part.key} is missing in ar.json`);
  assert.ok(lookup(EN, part.key), `orderPath.line.${part.key} is missing in en.json`);
  return Object.entries(part.values ?? {}).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v)), text);
}
const details = (s: Summary) => s.details.map(ar).join(" · ");

const NAMES = { product: "دوسية التأسيس" };

describe("activity books (§c.9)", () => {
  it("«دوسية ضحى»: KG2 · الجزء الأول · ملوّن · مطبوع, and the English name", () => {
    const s = summarize(
      {
        line: "workbook",
        options: { format: "spiral", interior: "color", volume: "1", level: "kg2" },
        child_name: "ضحى",
        child_name_en: "Duha",
      },
      "activity",
      NAMES,
    );
    assert.equal(ar(s.title), "دوسية ضحى");
    assert.equal(details(s), "KG2 · الجزء الأول · ملوّن · مطبوع");
    assert.deepEqual(s.facts.map(ar), ["الاسم بالإنجليزية: Duha"]);
    assert.equal(s.family, null);
  });

  it("a line still waiting for its child is the product's name", () => {
    const s = summarize({ line: "workbook", options: { level: "kg1", volume: "set" } }, "activity", NAMES);
    assert.deepEqual(s.title, { text: "دوسية التأسيس" });
    assert.deepEqual(s.facts, []);
  });

  it("every variant the catalog sells has its words, in Arabic and English", () => {
    const variants: [string, Record<string, string>][] = [
      ...["kg1", "kg2"].flatMap((level) =>
        ["1", "2", "3", "set"].flatMap((volume) =>
          ["color", "bw"].flatMap((interior) =>
            ["spiral", "digital"].map((format): [string, Record<string, string>] => [
              "workbook",
              { level, volume, interior, format },
            ]),
          ),
        ),
      ),
      ...["1", "2", "3", "set"].flatMap((stage) =>
        ["spiral", "digital"].map((format): [string, Record<string, string>] => ["journey", { stage, format }]),
      ),
      ["family", { format: "spiral" }],
      ["family", { format: "digital" }],
      ...["V1", "V2", "V3", "V4", "V5", "R", "L1", "L2", "set"].flatMap((volume) =>
        ["softcover", "digital"].map((format): [string, Record<string, string>] => ["islamic", { volume, format }]),
      ),
    ];
    for (const [line, options] of variants) {
      const s = summarize({ line, options, child_name: "ضحى" }, "activity", NAMES);
      [s.title, ...s.details].forEach(ar); // asserts both languages
      assert.equal(s.details.length, Object.keys(options).length, `${line} ${JSON.stringify(options)}`);
    }
  });

  it("«رحلة ضحى الأولى» and «قلبي يعرف الله · ضحى»", () => {
    const journey = summarize(
      { line: "journey", options: { stage: "2", format: "spiral" }, child_name: "ضحى" },
      "activity",
      NAMES,
    );
    assert.equal(ar(journey.title), "رحلة ضحى الأولى");
    assert.equal(details(journey), "المحطة الثانية · مطبوع");
    const islamic = summarize(
      { line: "islamic", options: { volume: "R", format: "digital" }, child_name: "ضحى" },
      "activity",
      NAMES,
    );
    assert.equal(ar(islamic.title), "قلبي يعرف الله · ضحى");
    // the child's name in its case: «رحلة أبي بكر الأولى», «قلبي يعرف الله · أبو بكر»
    const abu = (line: string) => ar(summarize({ line, options: {}, child_name: "أبو بكر" }, "activity", NAMES).title);
    assert.equal(abu("journey"), "رحلة أبي بكر الأولى");
    assert.equal(abu("workbook"), "دوسية أبي بكر");
    assert.equal(abu("family"), "مغامرات أبي بكر");
    assert.equal(abu("islamic"), "قلبي يعرف الله · أبو بكر");
    assert.equal(ar(summarize({ child_name: "أبو بكر" }, "story", NAMES).title), "كتاب أبي بكر");
    assert.equal(details(islamic), "كتاب رمضان والعيد · ملف PDF");
    assert.deepEqual(islamic.facts, [{ key: "download" }]); // where the file is downloaded, once ready
    ar(islamic.facts[0]);
    assert.deepEqual(journey.facts, []); // printed: nothing to download
  });

  it("the family book: the family as printed («عائلة ضحى» when its name is empty)", () => {
    const line: LineInput = {
      line: "family",
      options: { format: "spiral" },
      child_name: "ضحى",
      family: {
        name: "",
        city: " نابلس ",
        members: [
          { relation: "mother", role: "ماما", name: "سارة" },
          { relation: "brother", role: "أخي", name: "" },
        ],
      },
    };
    const s = summarize(line, "activity", NAMES);
    assert.deepEqual(s.family, {
      name: "ضحى",
      city: "نابلس",
      members: [
        { relation: "mother", name: "سارة" },
        { relation: "brother", name: "" },
      ],
    });
    assert.equal(summarize({ ...line, child_name: null }, "activity", NAMES).family, null); // not decided yet
    assert.deepEqual(summarize({ ...line, family: null }, "activity", NAMES).family, {
      name: "ضحى",
      city: "",
      members: [],
    }); // skipped: one neutral grown-up
    const abuBakr = summarize({ ...line, child_name: "أبو بكر" }, "activity", NAMES).family;
    assert.equal(abuBakr?.name, "أبي بكر"); // «عائلة أبي بكر», as the book prints it
  });
});

describe("stories (§c.9)", () => {
  const magic = { product: "قمرة سحري", theme: "يوم التخرّج", style: "سينمائي ثلاثي الأبعاد" };

  it("the book's title, then the line, the format and the style, the story and the dedication", () => {
    const s = summarize(
      {
        line: "magic",
        options: { format: "hardcover", size: "21x21" },
        child_name: "كرم",
        book_title: "يوم تخرّج كرم",
        dedication: true,
      },
      "story",
      magic,
    );
    assert.equal(ar(s.title), "يوم تخرّج كرم");
    assert.equal(details(s), "قمرة سحري · غلاف مقوّى · سينمائي ثلاثي الأبعاد");
    assert.deepEqual(s.facts.map(ar), ["الحكاية: يوم التخرّج", "إهداء ✓"]);
  });

  it("Classic's paid dedication is its add-on; a line waiting for its child shows the story as its title", () => {
    const classic = { product: "قمرة كلاسيك", theme: "موسم الزيتون", style: null };
    const s = summarize(
      { line: "classic", options: { format: "softcover" }, addons: [{ slug: "dedication-page" }] },
      "story",
      classic,
    );
    assert.deepEqual(s.title, { text: "موسم الزيتون" });
    assert.equal(details(s), "قمرة كلاسيك · غلاف ورقي");
    assert.deepEqual(s.facts.map(ar), ["إهداء ✓"]);
    const digital = summarize({ line: "classic", options: { format: "digital" } }, "story", classic);
    assert.deepEqual(digital.facts, [{ key: "download" }]);
  });
});
