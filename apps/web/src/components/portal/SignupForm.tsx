"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { Link, useRouter } from "@/i18n/navigation";
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
import { normalizePhone } from "@/lib/phone";
import { portalApi } from "@/lib/portal";
import { deliveryCountries, type Catalog } from "@/lib/store";

const ORDER = ["school_name", "contact_name", "city", "address", "phone", "email", "password"] as const;
const RULES: Partial<Record<(typeof ORDER)[number], Rule>> = {
  school_name: { required: true, min: [2, "nameShort"] },
  contact_name: { required: true, min: [2, "nameShort"] },
  city: { required: true, min: [2] },
  phone: { required: "phoneMissing", phone: true }, // ٠٥٩٩… and ۰۵۹۹… are fine
  email: { required: true, email: true },
  password: { required: true, min: [8, "passwordShort"] },
};

/** A kindergarten asks to join the portal: the account works at once, the school waits for our approval. */
export function SignupForm() {
  const t = useTranslations("portal.signup");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [form, setForm] = useState({
    school_name: "",
    contact_name: "",
    city: "",
    phone: "",
    email: "",
    password: "",
    address: "",
    country: "PS" as "PS" | "JO",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({}); // messages under the fields
  const formRef = useRef<HTMLFormElement>(null);
  // the country choice shows only while we deliver to more than one country (West Bank + Jerusalem only now)
  const [countries, setCountries] = useState<string[]>([]);
  useEffect(() => {
    void api<Catalog>("/api/store/catalog").then((r) => r.ok && setCountries(deliveryCountries(r.data.zones)));
  }, []);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    setErrors((current) => withoutField(current, k));
  };

  function mark(marked: FieldErrors) {
    setErrors(marked);
    setError(te("checkFields"));
    focusFirstInvalid(formRef.current, ORDER, marked);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const problems = checkFields(form, RULES as Record<string, Rule>);
    if (Object.keys(problems).length) return mark(problemTexts(problems, te));
    setBusy(true);
    setError(null);
    setErrors({});
    const r = await portalApi.signup({
      ...form,
      phone: normalizePhone(form.phone) ?? form.phone,
      address: form.address || undefined,
      locale: locale === "en" ? "en" : "ar",
    });
    setBusy(false);
    if (r.ok) return router.replace("/portal");
    const marked = onlyFields(serverFieldErrors(r.error, locale), ORDER);
    if (Object.keys(marked).length) mark(marked);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <form
      ref={formRef}
      onSubmit={submit}
      noValidate
      className="mx-auto flex w-full max-w-xl flex-col gap-4 rounded-xl border border-line bg-paper-raised p-5 md:p-8"
    >
      <div className="flex flex-col gap-1.5">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <p className="text-body text-ink-muted">{t("lead")}</p>
      </div>
      <TextField
        name="school_name"
        error={errors.school_name}
        label={t("school")}
        value={form.school_name}
        onChange={set("school_name")}
        required
        minLength={2}
        maxLength={200}
        autoComplete="organization"
      />
      <TextField
        name="contact_name"
        error={errors.contact_name}
        label={t("contact")}
        value={form.contact_name}
        onChange={set("contact_name")}
        required
        minLength={2}
        maxLength={120}
        autoComplete="name"
      />
      <div className={countries.length > 1 ? "grid gap-4 md:grid-cols-2" : "flex flex-col"}>
        <TextField
          name="city"
          error={errors.city}
          label={t("city")}
          value={form.city}
          onChange={set("city")}
          required
          minLength={2}
          maxLength={100}
        />
        {countries.length > 1 && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="country" className="text-small font-semibold text-ink">
              {t("country")}
            </label>
            <select
              id="country"
              value={form.country}
              onChange={set("country")}
              className="min-h-[52px] rounded-sm border border-line bg-paper-raised px-4 text-body"
            >
              {countries.map((c) => (
                <option key={c} value={c}>
                  {t.has(`countries.${c}`) ? t(`countries.${c}`) : c}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      <TextField
        name="address"
        error={errors.address}
        label={t("address")}
        hint={t("addressHint")}
        value={form.address}
        onChange={set("address")}
        maxLength={300}
        autoComplete="street-address"
      />
      <TextField
        name="phone"
        error={errors.phone}
        label={t("phone")}
        value={form.phone}
        onChange={set("phone")}
        required
        type="tel"
        inputMode="tel"
        ltr
        autoComplete="tel"
      />
      <TextField
        name="email"
        error={errors.email}
        label={t("email")}
        value={form.email}
        onChange={set("email")}
        required
        type="email"
        ltr
        autoComplete="email"
      />
      <TextField
        name="password"
        error={errors.password}
        label={t("password")}
        hint={t("passwordHint")}
        value={form.password}
        onChange={set("password")}
        required
        minLength={8}
        type="password"
        autoComplete="new-password"
        revealLabels={{ show: t("show"), hide: t("hide") }}
      />
      {error && <Alert>{error}</Alert>}
      <Button type="submit" loading={busy} size="lg">
        {t("cta")}
      </Button>
      <p className="text-small text-ink-muted">
        {t("haveAccount")}{" "}
        <Link href="/login?next=/portal" className="font-semibold text-night-900 underline underline-offset-4">
          {t("login")}
        </Link>
      </p>
    </form>
  );
}
