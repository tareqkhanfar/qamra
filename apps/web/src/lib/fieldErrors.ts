/**
 * Messages under the right field (Tareq, 2026-10-16: «بعض البيانات غير صحيحة» alone never said what to fix).
 *
 * - `checkFields`: what a form checks before sending (required, phone after turning Arabic digits into ASCII,
 *   lengths, e-mail, whole numbers); each problem is a key of `errors.fields` in messages/{ar,en}.json.
 * - `serverFieldErrors`: the API's `details.field_errors` ({field: {ar, en}}), or for older refusals the
 *   `details.fields` list with the refusal's own message.
 * - `firstInvalid` / `focusFirstInvalid`: the first marked field in the form's order gets the focus.
 *
 * Pure functions (no React) so `fieldErrors.test.ts` runs them with `node --test`.
 */

import { normalizePhone, toAsciiDigits } from "./phone.ts";

export type FieldErrors = Record<string, string>;

type ShortKey = "tooShort" | "nameShort" | "passwordShort" | "addressShort";

/** Keys of `errors.fields` (the number limits take `{n}`). */
export type Problem =
  | { key: "required" | "phone" | "phoneMissing" | "email" | "number" | "choose" | "city" | "terms" | "tooLong" }
  | { key: ShortKey }
  | { key: "numberMin" | "numberMax"; n: number };

export type Rule = {
  /** Must not be empty; the key says how to ask (default `required`). */
  required?: boolean | "phoneMissing" | "choose" | "city" | "terms";
  phone?: boolean;
  email?: boolean;
  /** At least n characters (after trimming); the key says what is short (default `tooShort`). */
  min?: readonly [number, ShortKey?];
  max?: number;
  /** A whole number (Arabic digits too) between min and max. */
  int?: readonly [number, number];
};

const EMAIL = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$/;

/** The first problem of one value, or null. */
export function checkValue(raw: string | boolean, rule: Rule): Problem | null {
  if (typeof raw === "boolean") return rule.required && !raw ? { key: "terms" } : null;
  const value = raw.trim();
  if (!value) {
    if (!rule.required) return null;
    return { key: rule.required === true ? "required" : rule.required };
  }
  if (rule.phone && normalizePhone(value) === null) return { key: "phone" };
  if (rule.email && !EMAIL.test(value)) return { key: "email" };
  if (rule.min && [...value].length < rule.min[0]) return { key: rule.min[1] ?? "tooShort" };
  if (rule.max && [...value].length > rule.max) return { key: "tooLong" };
  if (rule.int) {
    const digits = toAsciiDigits(value);
    if (!/^\d+$/.test(digits)) return { key: "number" };
    const n = Number(digits);
    if (n < rule.int[0]) return { key: "numberMin", n: rule.int[0] };
    if (n > rule.int[1]) return { key: "numberMax", n: rule.int[1] };
  }
  return null;
}

/** Every field's first problem, in the rules' order (the form's order). */
export function checkFields(
  values: Record<string, string | boolean>,
  rules: Record<string, Rule>,
): Record<string, Problem> {
  const out: Record<string, Problem> = {};
  for (const [field, rule] of Object.entries(rules)) {
    const problem = checkValue(values[field] ?? "", rule);
    if (problem) out[field] = problem;
  }
  return out;
}

/** Problems as text, through the form's translator for `errors.fields.*`. */
export function problemTexts(
  problems: Record<string, Problem>,
  t: (key: string, values?: Record<string, number>) => string,
): FieldErrors {
  return Object.fromEntries(
    Object.entries(problems).map(([field, p]) => [field, t(`fields.${p.key}`, "n" in p ? { n: p.n } : undefined)]),
  );
}

type ErrorLike = {
  code?: string;
  message?: { ar: string; en: string };
  details?: Record<string, unknown>;
} | null;

/**
 * The API's messages by field: `details.field_errors` first, else each of `details.fields` with the refusal's
 * own message. `aliases` points a server field at the form's field (e.g. the checkout's `zone` is its city).
 */
export function serverFieldErrors(error: ErrorLike, locale: string, aliases: Record<string, string> = {}): FieldErrors {
  const out: FieldErrors = {};
  if (!error?.details) return out;
  const pick = (m: { ar?: string; en?: string } | undefined) => (locale === "ar" ? m?.ar : m?.en) ?? "";
  const marked = error.details.field_errors;
  if (marked && typeof marked === "object") {
    for (const [field, message] of Object.entries(marked as Record<string, { ar: string; en: string }>)) {
      const name = aliases[field] ?? field;
      if (!(name in out)) out[name] = pick(message);
    }
    return out;
  }
  const fields = error.details.fields;
  if (Array.isArray(fields)) {
    for (const field of fields.map(String)) {
      const name = aliases[field] ?? field;
      if (!(name in out)) out[name] = pick(error.message);
    }
  }
  return out;
}

/** Only the errors this form can show under a field (`fields` lists them in the form's order). */
export function onlyFields(errors: FieldErrors, fields: readonly string[]): FieldErrors {
  return Object.fromEntries(fields.filter((f) => errors[f]).map((f) => [f, errors[f]]));
}

/** The errors without one field's (it was just edited). */
export function withoutField(errors: FieldErrors, field: string): FieldErrors {
  if (!(field in errors)) return errors;
  const rest = { ...errors };
  delete rest[field];
  return rest;
}

/** The first marked field in the form's order. */
export function firstInvalid(order: readonly string[], errors: FieldErrors): string | undefined {
  return order.find((f) => errors[f]);
}

/** Focus (and bring into view) the first marked field: inputs are found by their `name`. */
export function focusFirstInvalid(form: HTMLFormElement | null, order: readonly string[], errors: FieldErrors) {
  const name = firstInvalid(order, errors);
  if (!form || !name) return;
  const el = form.elements.namedItem(name);
  const target = el && "focus" in el ? (el as HTMLElement) : null;
  target?.focus();
  target?.scrollIntoView?.({ block: "center", behavior: "smooth" });
}
