/**
 * A typed name in its case (lib/arabicName.ts), checked against the Python helper
 * (packages/pdf/src/qamra_pdf/arabic_names.py and its tests), the two-word hint of the create flow, and the Arabic
 * messages that print a name: `npm test`.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { accusativeName, fillName, genitiveName, hasArticle, lamName, nameCases, twoWordName } from "./arabicName.ts";

describe("accusativeName", () => {
  const changed: [string, string][] = [
    ["أبو بكر", "أبا بكر"],
    ["ابو بكر", "ابا بكر"], // the parent's spelling (no hamza) is kept
    ["أبو بكر الصديق", "أبا بكر الصديق"],
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

  const kept = [
    "أبوبكر",
    "أبو",
    "أبو ",
    "محمد أبو بكر",
    "سلمى أبو غوش",
    "سلمى",
    "أبي بكر",
    "أبيض",
    "ذوق",
    "Abu Bakr",
    "",
  ];
  for (const name of kept) {
    it(`«${name}» stays as typed`, () => assert.equal(accusativeName(name), name));
  }
});

describe("genitiveName", () => {
  const changed: [string, string][] = [
    ["أبو بكر", "أبي بكر"],
    ["ابو بكر", "ابي بكر"], // the parent's spelling (no hamza) is kept
    ["أبو بكر الصديق", "أبي بكر الصديق"],
    ["ذو الفقار", "ذي الفقار"],
    ["أَبُو بَكْر", "أَبِي بَكْر"], // a mark on the ب becomes a kasra, the ي takes none
    ["أبُو بكر", "أبِي بكر"],
    ["ذُو الْفَقار", "ذِي الْفَقار"],
    ["  أبو علي", "  أبي علي"],
  ];
  for (const [name, gen] of changed) {
    it(`«${name}» → «${gen}»`, () => assert.equal(genitiveName(name), gen));
  }

  const kept = [
    "سلمى",
    "محمد",
    "عبد الرحمن",
    "أبوبكر",
    "أبو",
    "محمد أبو بكر",
    "سلمى أبو غوش",
    "أبي بكر",
    "Abu Bakr",
    "",
  ];
  for (const name of kept) {
    it(`«${name}» stays as typed`, () => assert.equal(genitiveName(name), name));
  }
});

describe("lamName", () => {
  // what a message «ل{nameLam}» prints
  const written: [string, string][] = [
    ["سلمى", "لـسلمى"], // the «ـ» keeps the name apart
    ["محمد", "لـمحمد"],
    ["أبو بكر", "لأبي بكر"], // the genitive, and the لا ligature: never «لـأبي» or «لـأبو»
    ["ابو بكر", "لابي بكر"],
    ["ذو الفقار", "لـذي الفقار"],
    ["أحمد", "لأحمد"],
    ["إياد", "لإياد"],
    ["آدم", "لآدم"],
    ["المعتصم", "للمعتصم"], // never «لـالمعتصم»
    ["الليث", "لليث"], // «ل» + «الل» is written «لل»
    ["الين", "لالين"], // no article (أَلين): the name keeps its letters, never «للين»
    ["الاء", "لالاء"],
    ["الهام", "لالهام"],
    ["Sami", "لـSami"],
  ];
  for (const [name, text] of written) {
    it(`«ل» + «${name}» → «${text}»`, () => assert.equal(`ل${lamName(name)}`, text));
  }
});

describe("nameCases", () => {
  it("every case of a name, under the message's variable names", () => {
    assert.deepEqual(nameCases("أبو بكر"), {
      name: "أبو بكر",
      nameAcc: "أبا بكر",
      nameGen: "أبي بكر",
      nameLam: "أبي بكر",
    });
    assert.deepEqual(nameCases("سلمى", "child"), {
      child: "سلمى",
      childAcc: "سلمى",
      childGen: "سلمى",
      childLam: "ـسلمى",
    });
    assert.deepEqual(nameCases("ذو الفقار", "label"), {
      label: "ذو الفقار",
      labelAcc: "ذا الفقار",
      labelGen: "ذي الفقار",
      labelLam: "ـذي الفقار",
    });
  });
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
  it("no braces are left for an empty name (the studio's broken-placeholder check)", () => {
    assert.equal(fillName("{companion:acc} يا {companion}", "companion", ""), " يا ");
    assert.equal(fillName("{child:gen}", "child", ""), "");
    assert.equal(fillName("لِـ{companion:gen}", "companion", ""), "لِـ");
  });

  it("{name:gen} takes the genitive and joins a «لـ» / «لِـ» before it", () => {
    const text = "هذا الكِتابُ لِـ{child:gen}، رِحْلَةُ {child:gen} مَعَ {child:gen}. يا {child}، {child:acc} و{child}";
    assert.equal(
      fillName(text, "child", "أبو بكر"),
      "هذا الكِتابُ لِأبي بكر، رِحْلَةُ أبي بكر مَعَ أبي بكر. يا أبا بكر، أبا بكر وأبو بكر",
    ); // «لِـ» + an alif: the لا ligature, never «لِـأبي»
    assert.equal(fillName(text, "child", "سلمى"), "هذا الكِتابُ لِـسلمى، رِحْلَةُ سلمى مَعَ سلمى. يا سلمى، سلمى وسلمى"); // any other letter keeps the «ـ»
    assert.equal(fillName("لِـ{child:gen}", "child", "محمد"), "لِـمحمد");
    assert.equal(fillName("لِـ{child:gen}", "child", "أحمد"), "لِأحمد");
    assert.equal(fillName("لـ{child:gen}", "child", "إياد"), "لإياد");
    assert.equal(fillName("لِـ{child:gen}", "child", "المعتصم"), "لِلمعتصم"); // «ال» after «لِـ» is written «لل»
    assert.equal(fillName("بِـ{child:gen}", "child", "أبو بكر"), "بِـأبي بكر"); // only «ل» makes a ligature
    assert.equal(
      fillName(fillName("إلى {name:gen} وَ{companion:gen}", "name", "ذو الفقار"), "companion", "أبو شنب"),
      "إلى ذي الفقار وَأبي شنب",
    );
    assert.equal(fillName("لِـ{child:gen}", "child", "الليث"), "لِليث");
    assert.equal(fillName("لِـ{child:gen}", "child", "الين"), "لِالين");
  });

  it("a word-final sukun before a name with the article takes its helping vowel, as in Python", () => {
    const text = "هَمَسَتْ {name} وَضَمَّتْ {name:acc} مِنْ {name:gen} عَلَيْكُمْ {name} أَوْ {name} فِيْ {name}";
    assert.equal(
      fillName(text, "name", "الجود"),
      "هَمَسَتِ الجود وَضَمَّتِ الجود مِنَ الجود عَلَيْكُمُ الجود أَوِ الجود فِي الجود",
    );
    for (const name of ["سلمى", "الين", "أبو بكر"]) assert.ok(fillName(text, "name", name).startsWith("هَمَسَتْ "));
  });

  it("«وَيا» and «فَيا» are vocatives, «هَيّا» is not", () =>
    assert.equal(
      fillName("وَيا {name}، فَيَا {name}، هَيّا {name}", "name", "أبو بكر"),
      "وَيا أبا بكر، فَيَا أبا بكر، هَيّا أبو بكر",
    ));
});

describe("hasArticle", () => {
  for (const [name, article] of [
    ["المعتصم", true],
    ["الْحَسَن", true],
    ["الليث", true],
    ["الين", false],
    ["الاء", false],
    ["أحمد", false],
    ["", false],
  ] as const) {
    it(`«${name}» ${article ? "has" : "has no"} article`, () => assert.equal(hasArticle(name), article));
  }
});

describe("twoWordName", () => {
  const split: [string, string][] = [
    ["أبوبكر", "أبو بكر"],
    ["ابوبكر", "ابو بكر"], // the parent's spelling (no hamza) is kept
    ["أبوعلي", "أبو علي"],
    ["أبوالعلا", "أبو العلا"],
    ["عبدالله", "عبد الله"],
    ["عبدالرحمن", "عبد الرحمن"],
    ["عبداللطيف", "عبد اللطيف"],
    ["ذوالفقار", "ذو الفقار"],
    ["أَبُوبَكْر", "أَبُو بَكْر"], // the parent's tashkeel is kept, and ignored to find the word
    ["عَبْدُالله", "عَبْدُ الله"],
    ["  أبوبكر ", "أبو بكر"],
    ["أبوبكر الصديق", "أبو بكر الصديق"],
    ["محمد عبدالله", "محمد عبد الله"], // every word of the name
    ["سلمى ابوغوش", "سلمى ابو غوش"],
  ];
  for (const [name, two] of split) {
    it(`«${name}» → «${two}»`, () => assert.equal(twoWordName(name), two));
  }

  const kept = [
    "أبو بكر",
    "عبد الله",
    "ذو الفقار",
    "سلمى",
    "عبد",
    "أبو",
    "أبوه", // one letter after «أبو»: a word in the making, not a name
    "أبوب",
    "عبدال",
    "عبدالـ",
    "عبدالل",
    "عبدربه", // only «عبد» + «ال…» is split
    "ذوق",
    "أبيض",
    "محمد",
    "Abu Bakr",
    "",
  ];
  for (const name of kept) {
    it(`«${name}»: no suggestion`, () => assert.equal(twoWordName(name), null));
  }

  it("the suggestion is final: it never suggests again", () => {
    for (const [name] of split) assert.equal(twoWordName(twoWordName(name) ?? ""), null);
  });
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

/** The messages that print a child's, a companion's or a person's name in the accusative (an object, after «يا»,
 * a greeting); each call site passes the variables with `nameCases` (a missing variable shows next-intl's error
 * instead of the sentence). */
const ACCUSATIVE: Record<string, "nameAcc" | "labelAcc"> = {
  "companion.name.ask": "nameAcc",
  "companion.intro.steps.three": "nameAcc",
  "companion.choose.body": "nameAcc", // the companion (a drawing) the child named: «رسمنا أبا شنب»
  "companion.mine.deleted": "nameAcc",
  "portal.dash.hello": "nameAcc", // «صباح الخير، أبا أحمد»: a greeting calls the person
  "portal.board.message": "nameAcc",
  "portal.invite.lead": "nameAcc",
  "portal.invite.character.drawing": "nameAcc",
  "portal.planner.holding": "nameAcc",
  "portal.planner.putHere": "nameAcc",
  "orderPath.gift.placeholder": "nameAcc",
  "voice.invite.message": "labelAcc",
  "voice.elder.hello": "labelAcc",
  "account.greeting": "nameAcc",
  "create.child.drawAs": "nameAcc",
  "create.photo.why.story": "nameAcc",
  "create.line.classicPages": "nameAcc",
  "create.style.title": "nameAcc",
  "create.character.title": "nameAcc",
  "create.character.drawing": "nameAcc",
  "create.character.approve": "nameAcc",
  "create.character.drawingsHint": "nameAcc", // «التي تشبه أبا بكر أكثر»
  "create.activity.summary.address": "nameAcc",
  "create.activity.summary.praise": "nameAcc",
};

/** The messages that print a name in the genitive: after a preposition or owning a noun (`…Gen`: «مع أبي بكر»,
 * «كتاب أبي بكر»), or written onto a «ل» (`…Lam`, the message says «ل{nameLam}»: «لأبي بكر», «لـسلمى»). */
const GENITIVE: Record<string, string> = {
  "companion.name.cta": "nameGen", // «حوّلوا الرسمة إلى أبي شنب»
  "companion.name.drawingAlt": "nameGen",
  "companion.gen.messages.0": "childGen", // filled in CompanionGen (a raw list)
  "companion.choose.body": "childGen",
  "companion.choose.optionAlt": "nameGen",
  "companion.intro.title": "nameGen",
  "companion.intro.steps.one": "nameGen",
  "companion.intro.mine": "nameGen",
  "companion.intro.start": "nameGen",
  "companion.intro.use": "nameGen",
  "companion.summary.none": "nameGen",
  "companion.mine.of": "nameGen",
  "companion.mine.meta": "nameGen",
  "companion.mine.confirm": "nameGen", // «حذفُ أبي شنب»: a verbal noun owns its object
  "customStory.tagline": "nameLam",
  "customStory.intro": "nameLam",
  "classic.noStyle": "nameLam",
  "examples.synthetic": "nameGen", // «لـ«أبي بكر»»: the quote keeps the «ـ»
  "examples.madeFor": "nameLam",
  "reader.previewEnd": "nameGen",
  "reader.ownerEnd": "nameGen",
  "freeCover.photoRule": "nameGen",
  "freeCover.readyTitle": "nameGen",
  "freeCover.alt": "nameGen",
  "freeCover.shareText": "nameGen",
  "freeCover.onlyDrawn": "nameGen",
  "freeCover.magicBody": "nameLam",
  "freeCover.privacy": "nameGen",
  "freeCover.ctaBook": "nameGen",
  "freeCover.ctaPlain": "nameGen",
  "portal.board.drawingOf": "nameGen",
  "portal.board.stepsLabel": "nameGen",
  "portal.board.removeConfirm": "nameGen",
  "portal.planner.remove": "nameGen",
  "portal.review.coverOf": "nameGen",
  "portal.review.choose": "nameGen",
  "portal.invite.title": "nameGen",
  "portal.invite.accept": "nameGen",
  "portal.invite.mineTitle": "nameGen",
  "portal.invite.doneBody": "nameGen",
  "portal.invite.consent.title": "nameGen",
  "portal.invite.consent.p1": "nameGen",
  "portal.invite.consent.p3": "nameGen",
  "portal.invite.consent.p4": "nameGen",
  "portal.invite.consent.accept": "nameGen",
  "portal.invite.photo.title": "nameLam",
  "portal.invite.character.drawTitle": "nameGen",
  "portal.invite.character.title": "nameGen",
  "portal.invite.character.alt": "nameGen",
  "workbook.cover.workbook": "nameGen",
  "workbook.cover.journey": "nameGen",
  "workbook.cover.family": "nameGen",
  "orderPath.bookOf": "nameGen",
  "orderPath.bookFor": "nameGen",
  "orderPath.cross.title": "nameGen",
  "orderPath.line.title.story": "nameGen", // lib/variantSummary.ts passes `nameCases`
  "orderPath.line.title.workbook": "nameGen",
  "orderPath.line.title.journey": "nameGen",
  "orderPath.line.title.family": "nameGen",
  "voice.invite.message": "childLam",
  "voice.elder.hello": "childLam",
  "voice.elder.done": "childGen", // «وصارت حكاية أبي بكر بصوتكم»
  "studio.preview.note": "nameGen",
  "studio.staff.confirmRemove": "nameGen",
  "account.booksOf": "nameGen",
  "landing.samplesTitle": "nameGen",
  "landing.howCharacterAlt": "nameGen",
  "create.bookOf": "nameGen",
  "create.consent.title": "nameGen",
  "create.consent.p1.body": "nameGen",
  "create.consent.p4.body": "nameGen",
  "create.consent.accept": "nameGen",
  "create.consent.why.story": "nameLam",
  "create.consent.why.activity": "nameLam",
  "create.photo.tip": "nameGen",
  "create.photo.why.activity": "nameGen",
  "create.photo.keep": "nameGen",
  "create.photo.next.story": "nameGen",
  "create.photo.next.activity": "nameGen",
  "create.line.title": "nameLam",
  "create.line.magicPages": "nameLam",
  "create.line.next.photo": "nameLam",
  "create.line.next.draw": "nameGen",
  "create.line.next.drawn": "nameGen",
  "create.style.cta": "nameGen",
  "create.style.next": "nameGen",
  "create.style.bodyActivity": "nameGen", // the activity books' style step (2026-10-09)
  "create.character.alt": "nameGen",
  "create.character.keep": "nameGen",
  "create.character.drawings": "nameGen", // «رسومات أبي بكر حتى الآن»
  "create.story.body": "nameGen",
  "create.story.suggested": "nameLam",
  "create.story.chosenTitle": "nameLam",
  "create.writing.title": "nameGen",
  "create.format.title": "nameGen",
  "create.format.classicTitle": "nameGen",
  "create.format.classicNote": "nameGen",
  "create.format.examplePages": "nameGen",
  "create.delete.button": "nameGen",
  "create.delete.confirm": "nameGen",
  "create.activity.family.title": "nameGen",
  "create.activity.family.nameHint": "nameGen", // «عائلة أبي بكر» when the family name is empty
  "create.activity.summary.ages": "nameGen",
  "create.activity.summary.characterAlt": "nameGen",
  "create.activity.summary.title": "nameGen",
  "create.titles.family": "nameGen",
  "create.titles.journey": "nameGen",
  "create.titles.story": "nameGen",
  "create.titles.workbook": "nameGen",
  "create.who.edit.title": "nameGen",
  "create.who.known.alt": "nameGen",
  "create.who.known.confirm": "nameLam",
  "store.cart.bookFor": "nameGen",
  "orders.by": "nameGen",
};

/** A name variable as typed right after a preposition, or after a greeting: it needs its case variable. */
const NAME = "\\{(?:name|label|child)\\}";
const PREPOSITION = "(?<![؀-ۿ])[وف]?(?:(?:مع|إلى|الى|من|عن|في|على|عند|لدى|حتى|بواسطة|باسم)\\s+|[لبك]ـ?)";
const GREETING = "(?:صباح الخير|مساء الخير|أهلًا|أهلا|مرحبًا|مرحبا)[،,]?\\s*";
/** A name that is not a person's, printed as its owner wrote it (a kindergarten's). */
const NOT_A_PERSON = ["portal.pendingTitle"];

describe("ar.json", () => {
  const AR = strings(messages("ar"));
  const ar = new Map(AR);
  const EN = new Map(strings(messages("en")));

  it("no vocative of a name variable as typed: «يا {name}», «يا {label}», «يا {child}»", () => {
    const vocative = /(?<![؀-ۿ])ي[ً-ْٰ]*ا[ً-ْٰ]*\s*\{(name|label|child)\}/;
    const bad = AR.filter(([, s]) => vocative.test(s)).map(([k]) => k);
    assert.deepEqual(bad, [], "a vocative takes the accusative variable ({nameAcc}, {labelAcc})");
  });

  it("no name variable as typed after a preposition or a greeting: «لـ{name}», «مع {name}», «أهلًا {name}»…", () => {
    const after = new RegExp(`(?:${PREPOSITION}|${GREETING})${NAME}`);
    const bad = AR.filter(([k, s]) => after.test(s) && !NOT_A_PERSON.includes(k)).map(([k]) => k);
    assert.deepEqual(bad, [], "after a preposition: «ل{nameLam}», «مع {nameGen}»; after a greeting: {nameAcc}");
  });

  it("«ل» is written with the …Lam variable, never «لـ{nameGen}» or «لـ{nameLam}»", () => {
    const bad = AR.filter(([, s]) => /ل[ً-ْٰ]*ـ?\{(?:name|label|child)Gen\}|لـ\{(?:name|label|child)Lam\}/.test(s));
    assert.deepEqual(
      bad.map(([k]) => k),
      [],
    );
    const lam = AR.filter(([, s]) => /\{(?:name|label|child)Lam\}/.test(s));
    for (const [key, s] of lam) assert.match(s, /(?<![؀-ۿ])[وف]?ل\{(?:name|label|child)Lam\}/, key);
  });

  it("the messages with {nameAcc} / {labelAcc} are exactly the known ones, so every call site passes them", () => {
    const found = AR.filter(([, s]) => /\{(nameAcc|labelAcc|childAcc)\}/.test(s)).map(([k]) => k);
    assert.deepEqual(found.sort(), Object.keys(ACCUSATIVE).sort());
  });

  it("the messages with a genitive variable (…Gen, …Lam) are exactly the known ones", () => {
    const found = AR.filter(([, s]) => /\{(?:name|label|child)(?:Gen|Lam)\}/.test(s)).map(([k]) => k);
    assert.deepEqual(found.sort(), Object.keys(GENITIVE).sort());
  });

  it("every known message exists in Arabic (with its variable) and in English", () => {
    for (const [key, variable] of [...Object.entries(ACCUSATIVE), ...Object.entries(GENITIVE)]) {
      assert.ok(ar.get(key)?.includes(`{${variable}}`), `${key} in ar.json uses {${variable}}`);
      assert.ok(EN.has(key), `${key} is missing in en.json`);
    }
  });

  it("the two-word hint of the create flow, in both languages", () => {
    for (const key of ["create.child.twoWords", "create.child.twoWordsUse"]) {
      assert.ok(ar.get(key)?.includes("{suggestion}"), `${key} in ar.json`);
      assert.ok(EN.get(key)?.includes("{suggestion}"), `${key} in en.json`);
    }
  });
});
