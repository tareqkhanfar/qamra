"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { api, errorText } from "@/lib/api";
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

type Labels = {
  fields: Record<"org" | "city" | "person" | "role" | "rolePh" | "phone" | "count" | "date" | "notes", string>;
  cities: string[];
  submit: string;
  sending: string;
  done: string;
  doneAgain: string;
  network: string;
  unknown: string;
};

const input =
  "min-h-[52px] w-full rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body text-ink outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100 aria-[invalid=true]:border-danger";

const ORDER = ["org_name", "city", "contact_name", "contact_role", "phone", "children_count", "event_date", "notes"];
const RULES: Record<string, Rule> = {
  org_name: { required: true },
  contact_name: { required: true },
  phone: { required: "phoneMissing", phone: true }, // ٠٥٩٩… and ۰۵۹۹… are fine
  children_count: { int: [1, 500] }, // «٢٥» too
};

/** Kindergarten demo request (design: Kindergartens › #demo). */
export function LeadForm({ labels }: { labels: Labels }) {
  const locale = useLocale();
  const te = useTranslations("errors");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({}); // messages under the fields
  const [done, setDone] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const element = e.currentTarget;
    const f = new FormData(element);
    const text = (k: string) => String(f.get(k) ?? "").trim();
    const mark = (marked: FieldErrors) => {
      setErrors(marked);
      setError(te("checkFields"));
      focusFirstInvalid(element, ORDER, marked);
    };
    const problems = checkFields(Object.fromEntries(ORDER.map((k) => [k, text(k)])), RULES);
    if (Object.keys(problems).length) return mark(problemTexts(problems, te));
    const count = toAsciiDigits(text("children_count"));
    const month = text("event_month");
    setBusy(true);
    setError(null);
    setErrors({});
    const res = await api("/api/leads", {
      json: {
        org_name: text("org_name"),
        city: text("city") || null,
        contact_name: text("contact_name"),
        contact_role: text("contact_role") || null,
        phone: normalizePhone(text("phone")) ?? text("phone"),
        children_count: count ? Number(count) : null,
        event_date: month ? `${month}-01` : null,
        notes: text("notes") || null,
        locale,
      },
    });
    setBusy(false);
    if (res.ok) {
      setDone(true);
      return;
    }
    const marked = onlyFields(serverFieldErrors(res.error, locale, { event_date: "event_month" }), ORDER);
    if (Object.keys(marked).length) mark(marked);
    else setError(errorText(res.error, locale, res.status === 0 ? labels.network : labels.unknown));
  }

  const invalid = (name: string) =>
    errors[name] ? { "aria-invalid": true as const, "aria-describedby": `lead-${name}-error` } : {};
  const message = (name: string) =>
    errors[name] && (
      <span id={`lead-${name}-error`} className="text-caption font-semibold text-danger">
        {errors[name]}
      </span>
    );

  if (done) {
    return (
      <div className="flex flex-col items-start gap-4 rounded-2xl border border-line bg-paper-raised p-9">
        <Alert tone="success">{labels.done}</Alert>
        <button
          type="button"
          onClick={() => setDone(false)}
          className="font-bold text-amber-700 underline underline-offset-4"
        >
          {labels.doneAgain}
        </button>
      </div>
    );
  }

  const L = labels.fields;
  return (
    <form
      onSubmit={onSubmit}
      onInput={(e) => setErrors((current) => withoutField(current, (e.target as HTMLInputElement).name))}
      noValidate
      className="grid gap-5 rounded-2xl border border-line bg-paper-raised p-5 sm:grid-cols-2 md:p-9"
    >
      {error && (
        <div className="sm:col-span-2">
          <Alert>{error}</Alert>
        </div>
      )}
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold">
        {L.org}
        <input name="org_name" required maxLength={200} className={input} {...invalid("org_name")} />
        {message("org_name")}
      </label>
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold">
        {L.city}
        <select name="city" className={input} defaultValue={labels.cities[0]}>
          {labels.cities.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold">
        {L.person}
        <input
          name="contact_name"
          required
          maxLength={120}
          autoComplete="name"
          className={input}
          {...invalid("contact_name")}
        />
        {message("contact_name")}
      </label>
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold">
        {L.role}
        <input name="contact_role" maxLength={120} placeholder={L.rolePh} className={input} />
      </label>
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold">
        {L.phone}
        <input
          name="phone"
          required
          type="tel"
          dir="ltr"
          inputMode="tel"
          autoComplete="tel"
          maxLength={40}
          className={`${input} rtl:text-right`}
          {...invalid("phone")}
        />
        {message("phone")}
      </label>
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold">
        {L.count}
        <input
          name="children_count"
          inputMode="numeric"
          maxLength={4}
          className={input}
          {...invalid("children_count")}
        />
        {message("children_count")}
      </label>
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold">
        {L.date}
        <input name="event_month" type="month" className={input} {...invalid("event_month")} />
        {message("event_month")}
      </label>
      <label className="flex flex-col gap-1.5 text-[15px] font-semibold sm:col-span-2">
        {L.notes}
        <textarea name="notes" rows={3} maxLength={2000} className={`${input} min-h-24 resize-y py-3.5`} />
      </label>
      <button
        type="submit"
        disabled={busy}
        className="min-h-14 rounded-full bg-amber-500 text-[18px] font-bold text-night-950 disabled:bg-paper-sunk disabled:text-ink-faint sm:col-span-2"
      >
        {busy ? labels.sending : labels.submit}
      </button>
    </form>
  );
}
