/**
 * A typed name in the accusative and after «يا» (الأسماء الخمسة), as the Python side does it
 * (packages/pdf/src/qamra_pdf/arabic_names.py, `accusative`).
 */

/** Tashkeel: tanween, harakat, shadda, sukun (U+064B–U+0652) and the dagger alif (U+0670). */
const MARK = "[ً-ْٰ]";
const FATHA = "َ";

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

/** «يا» as a word of its own (not the end of «هَيّا»), and the spaces after it. */
const YA = `(?<![\\u0600-\\u06ff])ي${MARK}*ا${MARK}*\\s+`;

/**
 * `{slot}` and `{slot:acc}` in a template filled with `name`, as the Python `fill_name` does: the accusative
 * at `{slot:acc}` and right after «يا», the name as typed everywhere else (the template studio's previews).
 */
export function fillName(text: string, slot: string, name: string): string {
  const form = accusativeName(name);
  let out = text.replaceAll(`{${slot}:acc}`, form);
  if (form !== name) out = out.replace(new RegExp(`(${YA})\\{${slot}\\}`, "g"), (_, ya: string) => ya + form);
  return out.replaceAll(`{${slot}}`, name);
}
