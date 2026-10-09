/**
 * A typed name in the accusative and after «يا» (lib/arabicName.ts), checked against the Python helper
 * (packages/pdf/src/qamra_pdf/arabic_names.py, `accusative`), and the Arabic messages that use it: `npm test`.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { accusativeName, fillName } from "./arabicName.ts";

describe("accusativeName", () => {
  const changed: [string, string][] = [
    ["أبو بكر", "أبا بكر"],
    ["ابو بكر", "ابا بكر"], // the parent's spelling (no hamza) is kept
    ["ذو الفقار", "ذا الفقار"],
    ["أَبُو بَكْر", "أَبَا بَكْر"], // a mark on the ب becomes a fatha, the alif takes none
    ["أبُو بكر", "أبَا بكر"],
    ["أَبو بكر", "أَبا بكر"],
    ["ذُو الْفَقار", "ذَا الْفَقار"],
    ["  أبو بكر", "  أبا بكر"], // leading spaces
  ];
  for (const [name, acc] of changed) {
    it(`«${name}» → «${acc}»`, () => assert.equal(accusativeName(name), acc));
  }

  const kept = ["أبوبكر", "أبو", "أبو ", "محمد أبو بكر", "سلمى أبو غوش", "سلمى", "أبي بكر", "Abu Bakr", ""];
  for (const name of kept) {
    it(`«${name}» stays as typed`, () => assert.equal(accusativeName(name), name));
  }
});

describe("fillName", () => {
  it("«يا {name}» and {name:acc} take the accusative, other slots the name as typed", () =>
    assert.equal(
      fillName("رائِعٌ يا {name}! وَضَمَّتْ {name:acc}، ثُمَّ {name} نامَ. هَيّا {name}", "name", "أبو بكر"),
      "رائِعٌ يا أبا بكر! وَضَمَّتْ أبا بكر، ثُمَّ أبو بكر نامَ. هَيّا أبو بكر",
    ));
  it("«يَا» with tashkeel is a vocative too", () =>
    assert.equal(fillName("يَا {name}", "name", "أبو علي"), "يَا أبا علي"));
  it("a name without «أبو» stays as typed", () =>
    assert.equal(fillName("يا {name}، {name:acc}", "name", "سلمى"), "يا سلمى، سلمى"));
  it("no braces are left for an empty name (the studio's broken-placeholder check)", () =>
    assert.equal(fillName("{companion:acc} يا {companion}", "companion", ""), " يا "));
});

type Tree = { [key: string]: string | string[] | Tree };
const messages = (locale: string): Tree =>
  JSON.parse(readFileSync(new URL(`../../messages/${locale}.json`, import.meta.url), "utf8")) as Tree;

/** Every message string of a locale file, by its dotted key. */
function strings(tree: Tree, prefix = ""): [string, string][] {
  return Object.entries(tree).flatMap(([k, v]): [string, string][] => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "string") return [[key, v]];
    if (Array.isArray(v)) return v.map((s, i): [string, string] => [`${key}.${i}`, s]);
    return strings(v, key);
  });
}

/** The messages that print a child's or a family member's name in the accusative; each call site passes the
 * variable with `accusativeName` (a missing variable shows next-intl's error instead of the sentence). */
const ACCUSATIVE: Record<string, "nameAcc" | "labelAcc"> = {
  "companion.name.ask": "nameAcc",
  "companion.intro.steps.three": "nameAcc",
  "companion.choose.body": "nameAcc", // the companion (a drawing) the child named: «رسمنا أبا شنب»
  "companion.mine.deleted": "nameAcc",
  "portal.board.message": "nameAcc",
  "portal.invite.lead": "nameAcc",
  "portal.invite.character.drawing": "nameAcc",
  "portal.planner.holding": "nameAcc",
  "portal.planner.putHere": "nameAcc",
  "orderPath.gift.placeholder": "nameAcc",
  "voice.invite.message": "labelAcc",
  "voice.elder.hello": "labelAcc",
  "create.child.drawAs": "nameAcc",
  "create.photo.why.story": "nameAcc",
  "create.line.classicPages": "nameAcc",
  "create.style.title": "nameAcc",
  "create.character.title": "nameAcc",
  "create.character.drawing": "nameAcc",
  "create.character.approve": "nameAcc",
  "create.activity.summary.address": "nameAcc",
  "create.activity.summary.praise": "nameAcc",
};

describe("ar.json", () => {
  const AR = strings(messages("ar"));
  const EN = new Map(strings(messages("en")));

  it("no vocative of a name variable as typed: «يا {name}», «يا {label}», «يا {child}»", () => {
    const vocative = /(?<![؀-ۿ])ي[ً-ْٰ]*ا[ً-ْٰ]*\s*\{(name|label|child)\}/;
    const bad = AR.filter(([, s]) => vocative.test(s)).map(([k]) => k);
    assert.deepEqual(bad, [], "a vocative takes the accusative variable ({nameAcc}, {labelAcc})");
  });

  it("the messages with {nameAcc} / {labelAcc} are exactly the known ones, so every call site passes them", () => {
    const found = AR.filter(([, s]) => /\{(nameAcc|labelAcc)\}/.test(s)).map(([k]) => k);
    assert.deepEqual(found.sort(), Object.keys(ACCUSATIVE).sort());
  });

  it("every known accusative message exists in Arabic (with its variable) and in English", () => {
    const ar = new Map(AR);
    for (const [key, variable] of Object.entries(ACCUSATIVE)) {
      assert.ok(ar.get(key)?.includes(`{${variable}}`), `${key} in ar.json uses {${variable}}`);
      assert.ok(EN.has(key), `${key} is missing in en.json`);
    }
  });
});
