"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { portalApi } from "@/lib/portal";

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
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const r = await portalApi.signup({
      ...form,
      address: form.address || undefined,
      locale: locale === "en" ? "en" : "ar",
    });
    setBusy(false);
    if (r.ok) router.replace("/portal");
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <form
      onSubmit={submit}
      className="mx-auto flex w-full max-w-xl flex-col gap-4 rounded-xl border border-line bg-paper-raised p-5 md:p-8"
    >
      <div className="flex flex-col gap-1.5">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <p className="text-body text-ink-muted">{t("lead")}</p>
      </div>
      <TextField
        label={t("school")}
        value={form.school_name}
        onChange={set("school_name")}
        required
        minLength={2}
        maxLength={200}
        autoComplete="organization"
      />
      <TextField
        label={t("contact")}
        value={form.contact_name}
        onChange={set("contact_name")}
        required
        minLength={2}
        maxLength={120}
        autoComplete="name"
      />
      <div className="grid gap-4 md:grid-cols-2">
        <TextField label={t("city")} value={form.city} onChange={set("city")} required minLength={2} maxLength={100} />
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
            <option value="PS">{t("countries.PS")}</option>
            <option value="JO">{t("countries.JO")}</option>
          </select>
        </div>
      </div>
      <TextField
        label={t("address")}
        hint={t("addressHint")}
        value={form.address}
        onChange={set("address")}
        maxLength={300}
        autoComplete="street-address"
      />
      <TextField
        label={t("phone")}
        value={form.phone}
        onChange={set("phone")}
        required
        type="tel"
        ltr
        autoComplete="tel"
      />
      <TextField
        label={t("email")}
        value={form.email}
        onChange={set("email")}
        required
        type="email"
        ltr
        autoComplete="email"
      />
      <TextField
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
