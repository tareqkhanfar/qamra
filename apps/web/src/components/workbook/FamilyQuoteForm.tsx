"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { errorText, upload } from "@/lib/api";

const input =
  "min-h-[52px] w-full rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body text-ink outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100";
const MAX_LOGO = 5 * 1024 * 1024;

/** «طلب عرض سعر» for organizations (Addendum 7 §8): a request, never an order; the logo goes on the back cover. */
export function FamilyQuoteForm() {
  const locale = useLocale();
  const t = useTranslations("familyQuote");
  const te = useTranslations("errors");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const logo = form.get("logo");
    if (logo instanceof File && logo.size > MAX_LOGO) return setError(t("tooBig"));
    if (logo instanceof File && !logo.size) form.delete("logo");
    for (const [k, v] of [...form.entries()]) if (v === "") form.delete(k);
    form.set("locale", locale === "en" ? "en" : "ar");
    setBusy(true);
    setError(null);
    const r = await upload("/api/leads/family-quote", form);
    setBusy(false);
    if (r.ok) setDone(true);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  if (done) return <Alert tone="success">{t("done")}</Alert>;
  const field = (name: string, label: string, props: Record<string, unknown> = {}) => (
    <label className="flex flex-col gap-1.5 text-small font-semibold text-night-900">
      {label}
      <input name={name} className={input} {...props} />
    </label>
  );
  return (
    <form
      id="family-quote"
      onSubmit={(e) => void onSubmit(e)}
      className="grid gap-5 rounded-2xl border border-line bg-paper-raised p-5 sm:grid-cols-2 md:p-9"
    >
      <div className="flex flex-col gap-2 sm:col-span-2">
        <h2 className="text-[24px] text-night-900">{t("title")}</h2>
        <p className="text-body text-ink">{t("lead")}</p>
        <p className="bg-amber-50 text-amber-800 rounded-[14px] px-4 py-3 text-small font-bold">{t("request")}</p>
      </div>
      {field("org_name", t("org"), { required: true, maxLength: 200 })}
      {field("city", t("city"), { maxLength: 100 })}
      {field("contact_name", t("person"), { required: true, maxLength: 120 })}
      {field("contact_role", t("role"), { maxLength: 120 })}
      {field("phone", t("phone"), { required: true, type: "tel", maxLength: 32, dir: "ltr" })}
      {field("email", t("email"), { type: "email", maxLength: 200, dir: "ltr" })}
      {field("quantity", t("quantity"), { required: true, type: "number", min: 10, max: 5000, defaultValue: 30 })}
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
        {busy ? t("sending") : t("submit")}
      </button>
    </form>
  );
}
