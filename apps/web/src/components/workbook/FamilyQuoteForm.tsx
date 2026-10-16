"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { useShowPrices } from "@/components/site/Prices";
import { Alert } from "@/components/ui/Alert";
import { errorText, upload } from "@/lib/api";
import {
  checkFields,
  focusFirstInvalid,
  onlyFields,
  problemTexts,
  serverFieldErrors,
  type FieldErrors,
  type Rule,
  withoutField,
} from "@/lib/fieldErrors";
import { normalizePhone, toAsciiDigits } from "@/lib/phone";
import { priceWording } from "@/lib/catalog";

const input =
  "min-h-[52px] w-full rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body text-ink outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100 aria-[invalid=true]:border-danger";
const MAX_LOGO = 5 * 1024 * 1024;
const ORDER = [
  "org_name",
  "city",
  "contact_name",
  "contact_role",
  "phone",
  "email",
  "quantity",
  "desired_date",
  "notes",
  "logo",
];
const RULES: Record<string, Rule> = {
  org_name: { required: true },
  contact_name: { required: true },
  phone: { required: "phoneMissing", phone: true }, // ٠٥٩٩… and ۰۵۹۹… are fine
  email: { email: true },
  quantity: { required: true, int: [10, 5000] }, // «٤٠» too
};

/** «طلب عرض سعر» for organizations (Addendum 7 §8): a request, never an order; the logo goes on the back cover. */
export function FamilyQuoteForm() {
  const locale = useLocale();
  const t = useTranslations("familyQuote");
  const te = useTranslations("errors");
  const prices = useShowPrices(); // while prices are hidden the form asks for a request, not a quote
  const w = (key: string) => t(priceWording(key, prices, (k) => t.has(k)));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({}); // messages under the fields
  const [done, setDone] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const element = e.currentTarget;
    const form = new FormData(element);
    const mark = (marked: FieldErrors) => {
      setErrors(marked);
      setError(te("checkFields"));
      focusFirstInvalid(element, ORDER, marked);
    };
    const text = (k: string) => String(form.get(k) ?? "").trim();
    const problems = checkFields(Object.fromEntries(ORDER.map((k) => [k, text(k)])), RULES);
    if (Object.keys(problems).length) return mark(problemTexts(problems, te));
    form.set("phone", normalizePhone(text("phone")) ?? text("phone"));
    form.set("quantity", toAsciiDigits(text("quantity")));
    const logo = form.get("logo");
    if (logo instanceof File && logo.size > MAX_LOGO) return setError(t("tooBig"));
    if (logo instanceof File && !logo.size) form.delete("logo");
    for (const [k, v] of [...form.entries()]) if (v === "") form.delete(k);
    form.set("locale", locale === "en" ? "en" : "ar");
    setBusy(true);
    setError(null);
    setErrors({});
    const r = await upload("/api/leads/family-quote", form);
    setBusy(false);
    if (r.ok) return setDone(true);
    const marked = onlyFields(serverFieldErrors(r.error, locale), ORDER);
    if (Object.keys(marked).length) mark(marked);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  if (done) return <Alert tone="success">{w("done")}</Alert>;
  const field = (name: string, label: string, props: Record<string, unknown> = {}) => (
    <label className="flex flex-col gap-1.5 text-small font-semibold text-night-900">
      {label}
      <input
        name={name}
        className={input}
        aria-invalid={errors[name] ? true : undefined}
        aria-describedby={errors[name] ? `quote-${name}-error` : undefined}
        {...props}
      />
      {errors[name] && (
        <span id={`quote-${name}-error`} className="text-caption font-semibold text-danger">
          {errors[name]}
        </span>
      )}
    </label>
  );
  return (
    <form
      id="family-quote"
      onSubmit={(e) => void onSubmit(e)}
      onInput={(e) => setErrors((current) => withoutField(current, (e.target as HTMLInputElement).name))}
      noValidate
      className="grid gap-5 rounded-2xl border border-line bg-paper-raised p-5 sm:grid-cols-2 md:p-9"
    >
      <div className="flex flex-col gap-2 sm:col-span-2">
        <h2 className="text-[24px] text-night-900">{t("title")}</h2>
        <p className="text-body text-ink">{w("lead")}</p>
        <p className="bg-amber-50 text-amber-800 rounded-[14px] px-4 py-3 text-small font-bold">{w("request")}</p>
      </div>
      {field("org_name", t("org"), { required: true, maxLength: 200 })}
      {field("city", t("city"), { maxLength: 100 })}
      {field("contact_name", t("person"), { required: true, maxLength: 120 })}
      {field("contact_role", t("role"), { maxLength: 120 })}
      {field("phone", t("phone"), {
        required: true,
        type: "tel",
        inputMode: "tel",
        autoComplete: "tel",
        maxLength: 40,
        dir: "ltr",
        className: `${input} rtl:text-right`,
      })}
      {field("email", t("email"), { type: "email", maxLength: 200, dir: "ltr" })}
      {field("quantity", t("quantity"), { required: true, inputMode: "numeric", maxLength: 5, defaultValue: 30 })}
      {field("desired_date", t("date"), { type: "date" })}
      <label className="flex flex-col gap-1.5 text-small font-semibold text-night-900 sm:col-span-2">
        {t("notes")}
        <textarea name="notes" maxLength={2000} rows={3} className={`${input} py-3`} />
      </label>
      <label className="flex flex-col gap-1.5 text-small font-semibold text-night-900 sm:col-span-2">
        {t("logo")}
        <input name="logo" type="file" accept="image/png,image/jpeg" className="text-small" />
        <span className="text-caption font-normal text-ink-faint">{t("logoPrivate")}</span>
      </label>
      {error && (
        <div className="sm:col-span-2">
          <Alert>{error}</Alert>
        </div>
      )}
      <button
        type="submit"
        disabled={busy}
        className="min-h-14 rounded-full bg-amber-500 px-8 text-[17px] font-bold text-night-950 hover:shadow-lamp disabled:opacity-60 sm:col-span-2 sm:justify-self-start"
      >
        {busy ? t("sending") : w("submit")}
      </button>
    </form>
  );
}
