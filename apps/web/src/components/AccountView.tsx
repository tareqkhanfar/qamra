"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { useRouter } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";

export function AccountView() {
  const t = useTranslations("account");
  const tn = useTranslations("nav");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    let alive = true;
    api<User>("/api/auth/me").then((res) => {
      if (!alive) return;
      if (res.ok) setUser(res.data);
      else if (res.status === 401) router.replace(`/login?next=${encodeURIComponent("/account")}`);
      else setError(errorText(res.error, locale, res.status === 0 ? te("network") : te("unknown")));
    });
    return () => {
      alive = false;
    };
  }, [locale, router, te]);

  async function logout() {
    setLeaving(true);
    await api("/api/auth/logout", { method: "POST", json: {} });
    router.replace("/");
    router.refresh();
  }

  if (error)
    return (
      <div className="mx-auto mt-10 max-w-md">
        <Alert>{error}</Alert>
      </div>
    );
  if (!user) {
    return (
      <div className="mx-auto mt-10 max-w-2xl animate-pulse space-y-4" aria-busy="true" aria-label={t("loading")}>
        <div className="bg-paper-sunk h-10 w-1/2 rounded-sm" />
        <div className="bg-paper-sunk h-40 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="mx-auto mt-8 flex max-w-2xl flex-col gap-6 sm:mt-12">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-h1 text-night-900 font-extrabold">{t("greeting", { name: user.full_name })}</h1>
        <Button variant="secondary" size="sm" onClick={logout} loading={leaving}>
          {tn("logout")}
        </Button>
      </div>

      <dl className="border-line bg-paper-raised shadow-1 grid gap-4 rounded-xl border p-6 sm:grid-cols-2">
        <div>
          <dt className="text-caption text-ink-muted">{t("email")}</dt>
          <dd dir="ltr" className="mt-1 font-semibold rtl:text-right">
            {user.email}
          </dd>
        </div>
        <div>
          <dt className="text-caption text-ink-muted">{t("role")}</dt>
          <dd className="mt-1 font-semibold">{t(`roles.${user.role}`, { brand: brandName(locale) })}</dd>
        </div>
      </dl>

      <section className="border-line bg-paper-raised/60 flex flex-col items-center gap-3 rounded-xl border border-dashed px-6 py-10 text-center">
        <h2 className="text-h3 text-night-900 font-bold">{t("empty")}</h2>
        <p className="text-body text-ink-muted">{t("emptyHint")}</p>
        <Button variant="primary" size="md" disabled title={t("soon")}>
          {t("start")} · {t("soon")}
        </Button>
      </section>
    </div>
  );
}
