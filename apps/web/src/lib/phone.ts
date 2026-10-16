/**
 * Phone numbers as people type them on Arabic keyboards (Tareq, 2026-10-16): the same rules as the API's
 * `qamra_core.phone`, so the form says «رقم الجوال غير صحيح» before sending, and accepts what the API accepts.
 *
 * - Arabic-Indic (٠-٩) and Persian (۰-۹) digits count as 0-9; spaces, dashes, dots, brackets and the invisible
 *   direction marks of a right-to-left page are ignored.
 * - Local numbers: 05/07 + 8 digits (mobiles), 0 + 8 digits (landlines); a bare 599123456 gets its zero back.
 * - International: +970 / +972 / +962 (or 00…, or 970… without the +), the country code kept as typed; other
 *   countries as + and 8–15 digits.
 */

const ARABIC_ZERO = 0x0660;
const PERSIAN_ZERO = 0x06f0;

/** «٠٥٩٩» and «۰۵۹۹» → "0599"; everything else unchanged. */
export function toAsciiDigits(value: string): string {
  return value.replace(/[\u{0660}-\u{0669}\u{06F0}-\u{06F9}]/gu, (ch) => {
    const code = ch.codePointAt(0) ?? 0;
    return String(code >= PERSIAN_ZERO ? code - PERSIAN_ZERO : code - ARABIC_ZERO);
  });
}

const SEPARATORS =
  /[\s\u{00A0}\u{2000}-\u{200F}\u{2028}-\u{202F}\u{2066}-\u{2069}\u{FEFF}().\-\u{2010}-\u{2015}\u{2212}/_]/gu;
const LOCAL = /^0(?:[57]\d{8}|[2-9]\d{7})$/;
const NATIONAL: Record<string, RegExp> = {
  "970": /^(?:5\d{8}|[2-9]\d{7})$/,
  "972": /^(?:[57]\d{8}|[2-9]\d{7})$/,
  "962": /^(?:7\d{8}|[2-9]\d{7})$/,
};
const INTERNATIONAL = /^[1-9]\d{7,14}$/;

function international(digits: string): string | null {
  const country = digits.slice(0, 3);
  const rule = NATIONAL[country];
  if (rule) {
    const national = digits.slice(3).replace(/^0/, ""); // +970 0599…: no trunk zero after the country code
    return rule.test(national) ? `+${country}${national}` : null;
  }
  return INTERNATIONAL.test(digits) ? `+${digits}` : null;
}

/** The stored form of a phone number (0599123456, +970599123456, …), or null when it isn't one. */
export function normalizePhone(value: string | null | undefined): string | null {
  if (!value) return null;
  let text = toAsciiDigits(value).replace(SEPARATORS, "").replace(/＋/g, "+");
  if (text.endsWith("+") && !text.startsWith("+")) text = `+${text.slice(0, -1)}`; // RTL paste
  let plus = text.startsWith("+");
  let digits = plus ? text.slice(1) : text;
  if (!/^\d+$/.test(digits)) return null;
  if (!plus && digits.startsWith("00")) [plus, digits] = [true, digits.slice(2)];
  if (plus) return international(digits);
  if (LOCAL.test(digits)) return digits;
  if (digits.length === 9 && "57".includes(digits[0])) return `0${digits}`; // the zero dropped: 599123456
  if (digits.slice(0, 3) in NATIONAL && digits.length >= 11) return international(digits);
  return null;
}
