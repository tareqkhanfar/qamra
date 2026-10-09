/**
 * A typed name in its case (الأسماء الخمسة), as the Python side does it
 * (packages/pdf/src/qamra_pdf/arabic_names.py, `accusative`, `genitive`, `fill_name`).
 */

/** Tashkeel: tanween, harakat, shadda, sukun (U+064B–U+0652) and the dagger alif (U+0670). */
const MARK = "[ً-ْٰ]";
const FATHA = "َ";
const KASRA = "ِ";
const ALIF = "اأإآٱ";

/** The first word «أبو» / «ابو» / «ذو» (tashkeel allowed) when another word follows it. */
const HEAD = new RegExp(`^(\\s*(?:[أا]${MARK}*ب|ذ))(${MARK}*)و${MARK}*(?=\\s+\\S)`);

/**
 * The name in the accusative and after «يا»: «يا أبا بكر», «نرسم أبا بكر», never «يا أبو بكر».
 * Only a name whose first word is «أبو», «ابو» or «ذو» followed by another word changes: «أبو بكر» → «أبا بكر»,
 * «ابو بكر» → «ابا بكر», «ذو الفقار» → «ذا الفقار», and with the parent's tashkeel «أَبُو بَكْر» → «أَبَا بَكْر»
 * (a mark on the ب becomes a fatha, the marks on the و go, the alif takes none). Every other name is returned
 * as typed: a one-word «أبوبكر», «أبو» alone, «محمد أبو بكر» (the family part is a surname), Latin names.
 */
export function accusativeName(name: string): string {
  return name.replace(HEAD, (_, head: string, mark: string) => head + (mark ? FATHA : "") + "ا");
}

/**
 * The name in the genitive, after a preposition or owning a noun: «مع أبي بكر», «رسمة أبي بكر», never
 * «مع أبو بكر». The same names change as in `accusativeName`: «أبو بكر» → «أبي بكر», «ذو الفقار» → «ذي الفقار»,
 * «أَبُو بَكْر» → «أَبِي بَكْر»; every other name is returned as typed.
 */
export function genitiveName(name: string): string {
  return name.replace(HEAD, (_, head: string, mark: string) => head + (mark ? KASRA : "") + "ي");
}

/**
 * Names that start with «ال» with no article in them, typed without their hamza (أَلين، آلاء، إلهام، إلياس…),
 * as in the Python `NOT_ARTICLE`: «لـ» joins them as «لا» and keeps every letter («لالين», never «للين»).
 */
const NOT_ARTICLE = new Set([
  "الين",
  "الاء",
  "الهام",
  "الياس",
  "الما",
  "اليسا",
  "اليسار",
  "الينا",
  "اليانا",
  "الان",
  "الينور",
  "اليان",
]);
const MARKS = new RegExp(MARK, "g");

/** The name starts with the article «ال» (hamzat al-wasl): «المعتصم», «الليث»; not «الين», «أحمد», «سلمى». */
export function hasArticle(name: string): boolean {
  const first = name.replace(MARKS, "").trim().split(/\s+/)[0] ?? "";
  return first.startsWith("ال") && first.length >= 4 && !NOT_ARTICLE.has(first);
}

/**
 * The name written onto a «ل» before it when they join (Python `after_lam`): «أبي بكر» (the لا ligature),
 * «المعتصم» → «لمعتصم» («للمعتصم»), «الليث» → «ليث» («لليث»), «الين» → «الين» («لالين»); null when the «ـ» stays.
 */
export function afterLam(form: string): string | null {
  if (form === "" || !ALIF.includes(form.charAt(0))) return null;
  if (!hasArticle(form)) return form;
  const article = new RegExp(`^ا${MARK}*(ل${MARK}*)`).exec(form);
  const rest = form.slice(article ? article[0].length : 2);
  return rest.startsWith("ل") ? rest : (article ? article[1] : "ل") + rest;
}

/**
 * The genitive written onto a «ل» in front of it, for a message that says «ل{nameLam}»: «لـسلمى» (the «ـ» keeps
 * the name apart), but «لأبي بكر», «لأحمد» (the لا ligature, never «لـأبي»), «للمعتصم» (never «لـالمعتصم»), «لليث»
 * and «لالين» (a name with no article keeps its letters).
 */
export function lamName(name: string): string {
  const gen = genitiveName(name);
  return afterLam(gen) ?? `ـ${gen}`;
}

/**
 * The variables a message needs to print a name in every case: `{name}` as typed (a subject, a title),
 * `{nameAcc}` (an object, after «يا», a greeting), `{nameGen}` (after a preposition, or owning a noun) and
 * `{nameLam}` (after «ل»). `key` names them: `nameCases(label, "label")` gives `label`, `labelAcc`, ….
 */
export function nameCases<K extends string = "name">(
  name: string,
  key: K = "name" as K,
): Record<K | `${K}Acc` | `${K}Gen` | `${K}Lam`, string> {
  return {
    [key]: name,
    [`${key}Acc`]: accusativeName(name),
    [`${key}Gen`]: genitiveName(name),
    [`${key}Lam`]: lamName(name),
  } as Record<K | `${K}Acc` | `${K}Gen` | `${K}Lam`, string>;
}

/** «يا» as a word of its own («وَيا», «فَيا» too; not the end of «هَيّا»), and the spaces after it. */
const YA = `(?<![\\u0600-\\u06ff])(?:[وف]${MARK}*)?ي${MARK}*ا${MARK}*\\s+`;

/** A word-final sukun, the letter before it and its marks, before a slot (Python `_SUKUN_END`). */
const SUKUN_END = `(\\S*?)([^\\s\\u064b-\\u0652\\u0670])${MARK}*ْ${MARK}*(\\}?\\s+)`;

/** The helping vowel of a word-final sukun before hamzat al-wasl (Python `_helping_vowel`). */
function helpingVowel(word: string, letter: string, space: string): string {
  if ("اى".includes(letter) || ("وي".includes(letter) && !new RegExp(`َ${MARK}*$`).test(word))) {
    return word + letter + space; // a long vowel («فِيْ»): the sukun goes, no helping vowel
  }
  const plain = (word + letter).replace(MARKS, "");
  if (["من", "ومن", "فمن"].includes(plain)) return word + letter + "َ" + space; // «مِنَ»
  if (letter === "م" && new RegExp(`ُ${MARK}*$`).test(word)) return word + letter + "ُ" + space; // «هُمُ»
  return word + letter + KASRA + space; // «هَمَسَتِ»
}

/**
 * `{slot}`, `{slot:acc}` and `{slot:gen}` in a template filled with `name`, as the Python `fill_name` does: the
 * accusative at `{slot:acc}` and right after «يا», the genitive at `{slot:gen}` (joined to a «لـ» / «لِـ» before
 * it: «لِأبي بكر», «لِلمعتصم»), the name as typed everywhere else (the template studio's previews); a word-final
 * sukun before a name with the article takes its helping vowel («هَمَسَتِ الجود»).
 */
export function fillName(text: string, slot: string, name: string): string {
  const form = accusativeName(name);
  const gen = genitiveName(name);
  let out = text;
  if (hasArticle(name)) {
    const before = new RegExp(`${SUKUN_END}(?=\\{${slot}(?::acc|:gen)?\\})`, "g");
    out = out.replace(before, (_, word: string, letter: string, space: string) => helpingVowel(word, letter, space));
  }
  out = out.replaceAll(`{${slot}:acc}`, form);
  const joined = afterLam(gen);
  if (joined !== null) {
    out = out.replace(new RegExp(`(ل${MARK}*)ـ\\{${slot}:gen\\}`, "g"), (_, lam: string) => lam + joined);
  }
  out = out.replaceAll(`{${slot}:gen}`, gen);
  if (form !== name) out = out.replace(new RegExp(`(${YA})\\{${slot}\\}`, "g"), (_, ya: string) => ya + form);
  return out.replaceAll(`{${slot}}`, name);
}

/** An Arabic letter (hamza to yeh), not a mark and not the tatweel. */
const LETTER = "[ء-غف-ي]";
/** What follows a joined head in the same word: `lead`, then two letters or more (tashkeel allowed), then its end. */
const rest = (lead: string) => `(?=${lead}(?:${LETTER}${MARK}*){2,}(?:\\s|$))`;
const AL = `ا${MARK}*ل${MARK}*`;
/** A word that joins two: «أبوبكر» / «ابوعلي» (أبو + a name), «عبدالله» / «عبدالرحمن», «ذوالفقار». */
const JOINED = [
  new RegExp(`(?<=^|\\s)([أا]${MARK}*ب${MARK}*و${MARK}*)${rest("")}`, "g"),
  new RegExp(`(?<=^|\\s)(ع${MARK}*ب${MARK}*د${MARK}*)${rest(AL)}`, "g"),
  new RegExp(`(?<=^|\\s)(ذ${MARK}*و${MARK}*)${rest(AL)}`, "g"),
];

/**
 * The two-word spelling of a name typed as one word, for the create flow to suggest (never to apply silently):
 * «أبوبكر» → «أبو بكر», «ابوعلي» → «ابو علي», «عبدالله» → «عبد الله», «عبدالرحمن» → «عبد الرحمن», «ذوالفقار» →
 * «ذو الفقار», with the parent's tashkeel kept («أَبُوبَكْر» → «أَبُو بَكْر») and every word of the name checked
 * («محمد عبدالله» → «محمد عبد الله»). Two words are what `accusativeName` / `genitiveName` inflect («يا أبا بكر»).
 * Null when nothing is joined: «أبو بكر», «سلمى», «أبو» alone, «أبوه» (one letter after «أبو»), Latin names.
 */
export function twoWordName(name: string): string | null {
  const split = JOINED.reduce((text, joined) => text.replace(joined, "$1 "), name);
  return split === name ? null : split.trim();
}
